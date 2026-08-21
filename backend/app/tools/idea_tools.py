from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.idea_service import IdeaService


def _serialize_idea(idea) -> Dict[str, Any]:
    """Helper to convert an Idea ORM model into a JSON-serializable dictionary."""
    return {
        "id": str(idea.id),
        "user_id": idea.user_id,
        "title": idea.title,
        "description": idea.description,
        "created_at": idea.created_at.isoformat() if idea.created_at else None,
        "updated_at": idea.updated_at.isoformat() if idea.updated_at else None,
    }


def save_idea(
    db: Session, user_id: str, title: str, description: str
) -> Dict[str, Any]:
    """
    Saves a new startup idea persistently for a user.

    Args:
        db: SQLAlchemy database session.
        user_id: The ID of the founder/user.
        title: The short title of the idea.
        description: Detailed explanation or concept of the idea.

    Returns:
        JSON-serializable dictionary containing creation status and saved idea details.
    """
    idea = IdeaService.create_idea(
        db, user_id=user_id, title=title, description=description
    )
    return {
        "status": "success",
        "message": "Idea saved successfully.",
        "idea": _serialize_idea(idea),
    }


def get_idea(db: Session, user_id: str, identifier: str) -> Dict[str, Any]:
    """
    Retrieves a specific idea for a user by title or UUID string.

    Args:
        db: SQLAlchemy database session.
        user_id: The ID of the founder/user.
        identifier: Title string or UUID string of the idea.

    Returns:
        JSON-serializable dictionary with idea payload or error message.
    """
    idea = None

    # First try lookup by title
    idea = IdeaService.get_idea_by_title(db, user_id=user_id, title=identifier)

    # If not found by title, try lookup by UUID if identifier looks like UUID/id
    if not idea:
        try:
            idea = IdeaService.get_idea_by_id(db, user_id=user_id, idea_id=identifier)
        except (ValueError, TypeError):
            idea = None

    if not idea:
        return {
            "status": "error",
            "message": f"Idea with identifier '{identifier}' not found for user.",
            "idea": None,
        }

    return {
        "status": "success",
        "idea": _serialize_idea(idea),
    }


def list_ideas(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Lists all persistent ideas saved by a user.

    Args:
        db: SQLAlchemy database session.
        user_id: The ID of the founder/user.

    Returns:
        JSON-serializable dictionary containing list of saved ideas.
    """
    ideas = IdeaService.list_ideas(db, user_id=user_id)
    serialized_list: List[Dict[str, Any]] = [_serialize_idea(i) for i in ideas]
    return {
        "status": "success",
        "count": len(serialized_list),
        "ideas": serialized_list,
    }
