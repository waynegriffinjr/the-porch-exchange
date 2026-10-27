# app/models/user.py
# Module 5 Project — User model
#

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.need import Need


class User(Base):
    """A registered account."""

    __tablename__ = "users"

    # index=True creates a database index so lookups and filtering by id are faster.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), nullable=False)

    needs: Mapped[list["Need"]] = relationship("Need", back_populates="owner")
    # The needs attribute establishes a one-to-many relationship with the Need model. It allows you to access all needs associated with a user. The back_populates parameter indicates that the Need model has a corresponding owner attribute that refers back to the User model.
