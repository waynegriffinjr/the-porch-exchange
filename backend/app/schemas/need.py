# app/schemas/need.py

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NeedCreate(BaseModel):
    """Input for creating a need."""

    title: str = Field(
        min_length=1,
        max_length=200,
        description="The name of the need",
        examples=["Write unit tests for the auth module"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Detailed description of what needs to be done",
        examples=["Cover register, login, and token validation with pytest"],
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium", description="Need priority level", examples=["high"]
    )
    completed: bool = False


class NeedPatch(BaseModel):
    """Input for partial need update."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    completed: bool | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None


class NeedDelete(BaseModel):
    """Input for deleting a need."""

    id: int = Field(description="The ID of the need to delete", examples=[1])


class NeedResponse(BaseModel):
    """Returned to clients."""

    id: int
    title: str
    description: str | None
    priority: str
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Write unit tests",
                "description": "Cover auth module with pytest",
                "priority": "high",
                "completed": False,
                "created_at": "2026-02-24T10:30:00",
                "updated_at": "2026-02-24T10:30:00",
            }
        },
    )
