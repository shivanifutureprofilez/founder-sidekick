from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.memory_service import MemoryService
from app.database.models import Memory, Message


class ContextManager:
    @staticmethod
    def build_context(
        db: Session,
        user_id: str,
        conversation_id: str,
        history_limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Builds a bounded context payload for a chat turn.
        Retrieves conversation summary, recent chronological messages,
        and durable memories scoped to user_id.
        """
        # 1. Fetch conversation summary
        conversation = ConversationService.get_conversation(db, conversation_id)
        summary: Optional[str] = conversation.summary if conversation else None

        # 2. Fetch bounded recent messages in chronological (ASC) order
        recent_messages: List[Message] = MessageService.get_recent_messages(
            db, conversation_id=conversation_id, limit=history_limit
        )

        # 3. Fetch durable memories scoped to user_id
        memories: List[Memory] = MemoryService.list_memories(db, user_id=user_id)

        return {
            "summary": summary,
            "recent_messages": recent_messages,
            "memories": memories,
        }
