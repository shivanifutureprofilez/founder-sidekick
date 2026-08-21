from typing import Optional
from sqlalchemy.orm import Session
from app.database.models import User


class UserService:
    @staticmethod
    def get_user(db: Session, user_id: str) -> Optional[User]:
        """Retrieve a user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_or_create_user(db: Session, user_id: str) -> User:
        """Retrieve a user by ID, or create a new user if one does not exist."""
        user = UserService.get_user(db, user_id)
        if not user:
            user = User(id=user_id)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
