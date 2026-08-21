import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.database.models import Message
from app.services import (
    UserService,
    ConversationService,
    MessageService,
    MemoryService,
)
from app.context import ContextManager


class ContextManagerTestCase(unittest.TestCase):
    def setUp(self):
        """Set up in-memory database session."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_empty_context(self):
        ctx = ContextManager.build_context(
            self.db, user_id="founder_1", conversation_id="non_existent_conv"
        )
        self.assertIsNone(ctx["summary"])
        self.assertEqual(ctx["recent_messages"], [])
        self.assertEqual(ctx["memories"], [])

    def test_summary_retrieval(self):
        conv = ConversationService.create_conversation(
            self.db, user_id="founder_1", summary="Previous discussion on RocketCat MVP."
        )
        ctx = ContextManager.build_context(
            self.db, user_id="founder_1", conversation_id=conv.id
        )
        self.assertEqual(ctx["summary"], "Previous discussion on RocketCat MVP.")

    def test_memories_retrieval_and_user_scoping(self):
        MemoryService.create_memory(
            self.db,
            user_id="founder_1",
            type="preference",
            key="tool_name",
            value="RocketCat",
        )
        MemoryService.create_memory(
            self.db,
            user_id="founder_2",
            type="preference",
            key="tool_name",
            value="OtherTool",
        )

        conv = ConversationService.create_conversation(self.db, user_id="founder_1")
        ctx = ContextManager.build_context(
            self.db, user_id="founder_1", conversation_id=conv.id
        )

        self.assertEqual(len(ctx["memories"]), 1)
        self.assertEqual(ctx["memories"][0].value, "RocketCat")

    def test_history_limit_and_chronological_order(self):
        conv = ConversationService.create_conversation(self.db, user_id="founder_1")
        base_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Create 15 messages
        for i in range(1, 16):
            msg = Message(
                conversation_id=conv.id,
                role="user" if i % 2 != 0 else "assistant",
                content=f"Message {i}",
                created_at=base_time + timedelta(seconds=i),
            )
            self.db.add(msg)
        self.db.commit()

        ctx = ContextManager.build_context(
            self.db, user_id="founder_1", conversation_id=conv.id, history_limit=5
        )

        messages = ctx["recent_messages"]
        self.assertEqual(len(messages), 5)
        contents = [m.content for m in messages]
        self.assertEqual(
            contents,
            ["Message 11", "Message 12", "Message 13", "Message 14", "Message 15"],
        )


if __name__ == "__main__":
    unittest.main()
