from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.skill import Skill
from app.models.user import User
from app.schemas.skill import SkillCreate, SkillResponse

router = APIRouter()


@router.post("/", response_model=SkillResponse, status_code=201)
def create_skill(
    skill: SkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a skill the current user can offer the community."""
    row = Skill(name=skill.name, description=skill.description, owner_id=current_user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/", response_model=list[SkillResponse])
def list_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's skills."""
    return db.query(Skill).filter(Skill.owner_id == current_user.id).order_by(Skill.id).all()


@router.delete("/{skill_id}", status_code=204)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove one of the current user's skills."""
    row = db.query(Skill).filter(Skill.id == skill_id, Skill.owner_id == current_user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(row)
    db.commit()
