"""Public needs board and skill-to-need matching."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.matching import score_match
from app.models.need import Need
from app.models.skill import Skill
from app.models.user import User
from app.schemas.board import BoardNeed

router = APIRouter()


def to_board_need(need: Need, user_id: int, matched_skills: list[str] | None = None, score: int = 0) -> BoardNeed:
    """Build the public view of a need; never exposes the poster's email."""
    return BoardNeed(
        id=need.id,
        title=need.title,
        description=need.description,
        priority=need.priority,
        created_at=need.created_at,
        poster=need.owner.username,
        contact=need.contact,
        is_mine=need.owner_id == user_id,
        matched_skills=matched_skills or [],
        score=score,
    )


def open_public_needs(db: Session):
    """Query of public needs that are not yet met, newest first."""
    return db.query(Need).filter(Need.is_public.is_(True), Need.completed.is_(False)).order_by(Need.id.desc())


@router.get("/", response_model=list[BoardNeed], summary="Browse the public needs board")
def list_board(
    search: str | None = Query(default=None, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List open needs that neighbors chose to share, optionally filtered by a search term."""
    query = open_public_needs(db)
    if search and search.strip():
        like = f"%{search.strip()}%"
        query = query.filter(Need.title.ilike(like) | Need.description.ilike(like))
    return [to_board_need(n, current_user.id) for n in query.offset(skip).limit(limit).all()]


@router.get("/matches", response_model=list[BoardNeed], summary="Public needs that fit my skills")
def my_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Open public needs posted by others that overlap with the current user's skills, best match first."""
    skills = db.query(Skill).filter(Skill.owner_id == current_user.id).all()
    results = []
    for need in open_public_needs(db).filter(Need.owner_id != current_user.id).all():
        scored = [(score_match(need.title, need.description, s.name, s.description), s.name) for s in skills]
        hits = [(sc, name) for sc, name in scored if sc > 0]
        if hits:
            results.append(
                to_board_need(
                    need, current_user.id, [n for _, n in sorted(hits, reverse=True)], sum(s for s, _ in hits)
                )
            )
    return sorted(results, key=lambda r: r.score, reverse=True)
