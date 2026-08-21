import uuid
from typing import Optional, List, Union
from sqlalchemy.orm import Session
from app.database.models import Idea
from app.services.user_service import UserService


class IdeaService:
    @staticmethod
    def _to_uuid(val: Union[uuid.UUID, str]) -> uuid.UUID:
        if isinstance(val, str):
            return uuid.UUID(val)
        return val

    @staticmethod
    def create_idea(
        db: Session, user_id: str, title: str, description: str
    ) -> Idea:
        """Create a new idea record for a user, ensuring user exists."""
        UserService.get_or_create_user(db, user_id)
        idea = Idea(user_id=user_id, title=title, description=description)
        db.add(idea)
        db.commit()
        db.refresh(idea)
        return idea

    @staticmethod
    def get_idea_by_id(
        db: Session, user_id: str, idea_id: Union[uuid.UUID, str]
    ) -> Optional[Idea]:
        """Retrieve an idea by ID scoped by user_id."""
        id_uuid = IdeaService._to_uuid(idea_id)
        return (
            db.query(Idea)
            .filter(Idea.user_id == user_id, Idea.id == id_uuid)
            .first()
        )

    @staticmethod
    def get_idea_by_title(
        db: Session, user_id: str, title: str
    ) -> Optional[Idea]:
        """Retrieve an idea by title scoped by user_id."""
        return (
            db.query(Idea)
            .filter(Idea.user_id == user_id, Idea.title == title)
            .first()
        )

    @staticmethod
    def list_ideas(db: Session, user_id: str) -> List[Idea]:
        """List all ideas owned by user_id."""
        return (
            db.query(Idea)
            .filter(Idea.user_id == user_id)
            .order_by(Idea.created_at.desc())
            .all()
        )

    @staticmethod
    def update_idea(
        db: Session,
        user_id: str,
        idea_id: Union[uuid.UUID, str],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Idea]:
        """Update title and/or description of an idea owned by user_id."""
        idea = IdeaService.get_idea_by_id(db, user_id, idea_id)
        if idea:
            if title is not None:
                idea.title = title
            if description is not None:
                idea.description = description
            db.commit()
            db.refresh(idea)
        return idea

    @staticmethod
    def delete_idea(
        db: Session, user_id: str, idea_id: Union[uuid.UUID, str]
    ) -> bool:
        """Delete an idea owned by user_id."""
        idea = IdeaService.get_idea_by_id(db, user_id, idea_id)
        if idea:
            db.delete(idea)
            db.commit()
            return True
        return False
