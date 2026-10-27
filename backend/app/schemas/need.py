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
    is_public: bool = Field(default=False, description="Share this need on the public board")
    contact: str | None = Field(
        default=None,
        max_length=200,
        description="How neighbors can reach you (shown only on the public board)",
        examples=["Text 555-0100 or porch at 12 Main St"],
    )


class NeedPatch(BaseModel):
    """Input for partial need update."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    completed: bool | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None
    is_public: bool | None = None
    contact: str | None = Field(default=None, max_length=200)


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
    is_public: bool
    contact: str | None
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
                "is_public": True,
                "contact": "Text 555-0100",
                "created_at": "2026-02-24T10:30:00",
                "updated_at": "2026-02-24T10:30:00",
            }
        },
    )
