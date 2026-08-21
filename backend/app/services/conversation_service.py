from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.database.models import Conversation
from app.services.user_service import UserService


class ConversationService:
    @staticmethod
    def create_conversation(
        db: Session,
        user_id: str,
        conversation_id: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation, ensuring user exists."""
        UserService.get_or_create_user(db, user_id)
        
        kwargs = {"user_id": user_id, "summary": summary}
        if conversation_id:
            kwargs["id"] = conversation_id
            
        conversation = Conversation(**kwargs)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    @staticmethod
    def get_or_create_conversation(
        db: Session, user_id: str, conversation_id: Optional[str] = None
    ) -> Conversation:
        """Fetch existing conversation or create a new one."""
        if conversation_id:
            conv = ConversationService.get_conversation(db, conversation_id)
            if conv:
                return conv
        return ConversationService.create_conversation(
            db, user_id=user_id, conversation_id=conversation_id
        )

    @staticmethod
    def update_summary(
        db: Session, conversation_id: str, summary: str
    ) -> Optional[Conversation]:
        """Update the high-level summary of a conversation."""
        conv = ConversationService.get_conversation(db, conversation_id)
        if conv:
            conv.summary = summary
            db.commit()
            db.refresh(conv)
        return conv

    @staticmethod
    def update_timestamp(db: Session, conversation_id: str) -> Optional[Conversation]:
        """Touch and update the updated_at timestamp of a conversation."""
        conv = ConversationService.get_conversation(db, conversation_id)
        if conv:
            conv.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(conv)
        return conv
