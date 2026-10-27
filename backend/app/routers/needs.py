# project/starter/app/routers/needs.py
# Module 5 Project — Need endpoints (auth-scoped)
#

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.exceptions import NotFoundException
from app.matching import score_match
from app.models.need import Need
from app.models.skill import Skill
from app.models.user import User
from app.schemas.board import SkillMatch
from app.schemas.need import NeedCreate, NeedPatch, NeedResponse

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def log_need_activity(need_id: int, action: str) -> None:
    """
    Record need activity without delaying the API response.
    Scheduled to run after the response.
    """
    logger.info("need_id=%s action=%s", need_id, action)


@router.post(
    "/",
    response_model=NeedResponse,
    status_code=201,
    responses={
        422: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
    },
    summary="Create a new need"
    """When the client send a POST request, run the create_need function.""",
)
def create_need(
    need: NeedCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new need for the authenticated user.

    The need is associated with the currently logged-in user. The **priority** field
    accepts: low, medium, high, or critical (defaults to medium).
    """
    need_data = Need(
        title=need.title,
        description=need.description,
        priority=need.priority,
        completed=need.completed,
        is_public=need.is_public,
        contact=need.contact,
        owner_id=current_user.id,  # Associate the need with the current user's ID
    )

    db.add(need_data)  # Add the new need to the database session
    db.commit()  # Commit the transaction to save the need in the database permanently
    db.refresh(
        need_data
    )  # Refresh the need_data instance to get the updated data from the database, including the auto-generated id.

    background_tasks.add_task(log_need_activity, need_data.id, "created")

    return need_data  # Return the newly created need data as the response


@router.get("/", response_model=list[NeedResponse])
def list_needs(
    completed: bool | None = Query(default=None),
    priority: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all needs for the authenticated user.

    Returns a list of needs associated with the currently logged-in user.
    """
    query = db.query(Need).filter(Need.owner_id == current_user.id)
    if completed is not None:
        query = query.filter(Need.completed == completed)
    if priority is not None:
        query = query.filter(Need.priority == priority)

    needs = query.offset(skip).limit(limit).all()
    return needs  # Return the list of needs as the response


@router.get("/{need_id}", response_model=NeedResponse)
def get_need(need_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return one of the current user's needs."""
    need = db.query(Need).filter(Need.id == need_id).first()
    if not need:
        raise NotFoundException("Need not found")
    if need.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this need")
    return need  # Return the need data as the response


@router.patch("/{need_id}", response_model=NeedResponse)
def patch_need(
    need_id: int, need_data: NeedPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Partially update one of the current user's needs."""
    patched_need = db.query(Need).filter(Need.id == need_id).first()
    if not patched_need:
        raise NotFoundException("Need not found")
    if patched_need.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this need")

    update_data = need_data.model_dump(exclude_unset=True)  # Get the fields that were provided in the request body
    for key, value in update_data.items():
        setattr(patched_need, key, value)  # Update the need attributes with the provided values
    db.commit()  # Commit the transaction to save the changes in the database
    db.refresh(patched_need)  # Refresh the patched_need instance to get the updated data from the database

    return patched_need  # Return the patched need data as the response


@router.delete("/{need_id}")
def delete_need(need_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete one of the current user's needs."""
    need_to_delete = db.query(Need).filter(Need.id == need_id).first()
    if not need_to_delete:
        raise NotFoundException("Need not found")
    if need_to_delete.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this need")

    db.delete(need_to_delete)  # Delete the need from the database session
    db.commit()  # Commit the transaction to remove the need from the database

    return {"detail": "Need deleted successfully"}  # Return a success message as the response


@router.post("/{need_id}/suggest")
def suggest_need_action(need_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Suggest an action for a specific need based on its details.
    This endpoint is intended to provide suggestions for need actions based on the need's details.
    The suggestion logic can be implemented using AI or other algorithms in the future.

    """
    need = db.query(Need).filter(Need.id == need_id).first()
    if not need:
        raise NotFoundException("Need not found")
    if need.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this need")

    # Placeholder for AI suggestion logic
    suggestion = f"Consider prioritizing this need: {need.title} becasue of the following logical analysis:..."

    return {"suggestion": suggestion}  # Return the suggestion as the response


@router.get("/{need_id}/matches", response_model=list[SkillMatch], summary="Neighbors whose skills fit this need")
def need_matches(need_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Find neighbors offering skills that overlap with one of your needs, best match first."""
    need = db.query(Need).filter(Need.id == need_id).first()
    if not need:
        raise NotFoundException("Need not found")
    if need.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this need")

    by_user: dict[str, SkillMatch] = {}
    for skill, owner in db.query(Skill, User).join(User, User.id == Skill.owner_id).filter(User.id != current_user.id):
        score = score_match(need.title, need.description, skill.name, skill.description)
        if score > 0:
            match = by_user.setdefault(owner.username, SkillMatch(username=owner.username, skills=[], score=0))
            match.skills.append(skill.name)
            match.score += score
    return sorted(by_user.values(), key=lambda m: m.score, reverse=True)
