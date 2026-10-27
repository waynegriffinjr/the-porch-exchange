"""Schemas for the public needs board and matching."""

from datetime import datetime

from pydantic import BaseModel, Field


class BoardNeed(BaseModel):
    """A need shared on the public board."""

    id: int
    title: str
    description: str | None
    priority: str
    created_at: datetime
    poster: str = Field(description="Username of the neighbor who posted the need")
    contact: str | None = Field(description="How to reach the poster, if they chose to share it")
    is_mine: bool
    matched_skills: list[str] = Field(default_factory=list, description="Your skills that fit this need")
    score: int = 0


class SkillMatch(BaseModel):
    """A neighbor whose skill fits one of your needs."""

    username: str
    skills: list[str]
    score: int
