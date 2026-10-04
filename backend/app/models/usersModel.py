from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # Basic user information
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Store a hashed password, never the plain password
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # User language: en, fr, ar
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
    )

    # User role
    role: Mapped[str] = mapped_column(
        String(50),
        default="farmer",
        nullable=False,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Account creation date
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Last update date
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<User "
            f"id={self.id} "
            f"email={self.email} "
            f"role={self.role}>"
        )