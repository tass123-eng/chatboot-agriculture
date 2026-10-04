from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.usersModel import User
from app.schemas.userSchema import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch a single user by primary key ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email address."""
        return self.db.query(User).filter(User.email == email).first()

    def get_multi(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Fetch a paginated list of users."""
        return self.db.query(User).offset(skip).limit(limit).all()

    def create(self, user_in: UserCreate) -> User:
        """Create a new user account with hashed password."""
        existing_user = self.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        db_user = User(
            full_name=user_in.full_name,
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            language=user_in.language,
            role=user_in.role,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update(self, user_id: int, user_in: UserUpdate) -> User:
        """Update existing user fields."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        update_data = user_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password."""
        user = self.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    def delete(self, user_id: int) -> User:
        """Delete a user account."""
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        self.db.delete(db_user)
        self.db.commit()
        return db_user