# /app/schemas/user.py
# Module 5 Project — User schemas
#
# PYNDANTIC SCHEMAS

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """Registration input."""

    username: str = Field(min_length=3, max_length=50)
    email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "JohnWayne",
                "email": "john@example.com",
                "password": "StrongPass123!",
            }
        }
    )


class UserResponse(BaseModel):
    """Returned to clients — no password fields."""

    id: int
    username: str
    email: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "JohnWayne",
                "email": "john@example.com",
            }
        },
    )


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str
