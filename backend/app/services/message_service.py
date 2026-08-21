from typing import List
from sqlalchemy.orm import Session
from app.database.models import Message, Conversation


class MessageService:
    @staticmethod
    def create_message(
        db: Session, conversation_id: str, role: str, content: str
    ) -> Message:
        """Create a new chat message under a specific conversation."""
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise ValueError(f"Conversation '{conversation_id}' does not exist.")

        message = Message(conversation_id=conversation_id, role=role, content=content)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_recent_messages(
        db: Session, conversation_id: str, limit: int = 10
    ) -> List[Message]:
        """
        Fetch up to `limit` recent messages for a conversation,
        returned in chronological (ASC) order for LLM prompt context.
        """
        if limit <= 0:
            return []

        recent = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(recent))
