import unittest
import time
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
    IdeaService,
)


class ServiceLayerTestCase(unittest.TestCase):
    def setUp(self):
        """Fixture providing an in-memory SQLite database session for unit tests."""
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

    # --- UserService Tests ---

    def test_get_or_create_user(self):
        user = UserService.get_or_create_user(self.db, "founder_1")
        self.assertIsNotNone(user)
        self.assertEqual(user.id, "founder_1")

        # Repeat call returns the same user without creating duplicates
        user_again = UserService.get_or_create_user(self.db, "founder_1")
        self.assertEqual(user_again.id, "founder_1")

    def test_get_user(self):
        self.assertIsNone(UserService.get_user(self.db, "non_existent"))
        created = UserService.get_or_create_user(self.db, "founder_2")
        fetched = UserService.get_user(self.db, "founder_2")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, created.id)

    # --- ConversationService Tests ---

    def test_create_and_get_conversation(self):
        conv = ConversationService.create_conversation(
            self.db, user_id="founder_1", summary="Initial conversation summary"
        )
        self.assertIsNotNone(conv.id)
        self.assertEqual(conv.user_id, "founder_1")
        self.assertEqual(conv.summary, "Initial conversation summary")

        fetched = ConversationService.get_conversation(self.db, conv.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, conv.id)

    def test_get_or_create_conversation(self):
        conv1 = ConversationService.get_or_create_conversation(
            self.db, user_id="founder_1", conversation_id="conv_custom_100"
        )
        self.assertEqual(conv1.id, "conv_custom_100")

        conv2 = ConversationService.get_or_create_conversation(
            self.db, user_id="founder_1", conversation_id="conv_custom_100"
        )
        self.assertEqual(conv2.id, conv1.id)

    def test_update_summary_and_timestamp(self):
        conv = ConversationService.create_conversation(self.db, user_id="founder_1")
        updated = ConversationService.update_summary(
            self.db, conv.id, "Updated summary text"
        )
        self.assertEqual(updated.summary, "Updated summary text")

        prev_updated_at = updated.updated_at
        time.sleep(0.01)
        touched = ConversationService.update_timestamp(self.db, conv.id)
        self.assertGreaterEqual(touched.updated_at, prev_updated_at)

    # --- MessageService Tests ---

    def test_create_message(self):
        conv = ConversationService.create_conversation(self.db, user_id="founder_1")
        msg = MessageService.create_message(
            self.db, conversation_id=conv.id, role="user", content="Hello agent!"
        )
        self.assertIsNotNone(msg.id)
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello agent!")

    def test_create_message_invalid_conversation(self):
        with self.assertRaises(ValueError):
            MessageService.create_message(
                self.db, conversation_id="missing_conv", role="user", content="Test"
            )

    def test_get_recent_messages_order_and_limit(self):
        from datetime import datetime, timedelta, timezone
        conv = ConversationService.create_conversation(self.db, user_id="founder_1")

        base_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        # Insert 15 messages sequentially with distinct created_at timestamps
        for i in range(1, 16):
            msg = Message(
                conversation_id=conv.id,
                role="user" if i % 2 != 0 else "assistant",
                content=f"Message {i}",
                created_at=base_time + timedelta(seconds=i),
            )
            self.db.add(msg)
        self.db.commit()

        # Retrieve limit=5 recent messages
        recent = MessageService.get_recent_messages(
            self.db, conversation_id=conv.id, limit=5
        )
        self.assertEqual(len(recent), 5)

        # Should be the last 5 created messages (11 to 15) in chronological (ASC) order
        contents = [m.content for m in recent]
        self.assertEqual(
            contents,
            ["Message 11", "Message 12", "Message 13", "Message 14", "Message 15"],
        )

    # --- MemoryService Tests ---

    def test_create_and_list_memories(self):
        mem1 = MemoryService.create_memory(
            self.db,
            user_id="founder_1",
            type="preference",
            key="tool_name",
            value="RocketCat",
            importance="high",
        )
        self.assertIsNotNone(mem1.id)

        mem2 = MemoryService.create_memory(
            self.db,
            user_id="founder_1",
            type="decision",
            key="db_choice",
            value="PostgreSQL",
            importance="medium",
        )

        all_mems = MemoryService.list_memories(self.db, user_id="founder_1")
        self.assertEqual(len(all_mems), 2)

        pref_mems = MemoryService.list_memories(
            self.db, user_id="founder_1", memory_type="preference"
        )
        self.assertEqual(len(pref_mems), 1)
        self.assertEqual(pref_mems[0].key, "tool_name")

    def test_upsert_memory(self):
        # Initial creation via upsert
        m1 = MemoryService.upsert_memory(
            self.db,
            user_id="founder_1",
            type="preference",
            key="theme",
            value="dark",
            importance="low",
        )
        self.assertEqual(m1.value, "dark")

        # Upsert with same (user_id, type, key) updates value & importance
        m2 = MemoryService.upsert_memory(
            self.db,
            user_id="founder_1",
            type="preference",
            key="theme",
            value="light",
            importance="high",
        )
        self.assertEqual(m2.id, m1.id)
        self.assertEqual(m2.value, "light")
        self.assertEqual(m2.importance, "high")

        # Verify count is still 1
        memories = MemoryService.list_memories(self.db, user_id="founder_1")
        self.assertEqual(len(memories), 1)

    def test_memory_user_isolation(self):
        MemoryService.create_memory(
            self.db,
            user_id="user_a",
            type="fact",
            key="secret",
            value="SecretA",
        )
        MemoryService.create_memory(
            self.db,
            user_id="user_b",
            type="fact",
            key="secret",
            value="SecretB",
        )

        mems_a = MemoryService.list_memories(self.db, user_id="user_a")
        mems_b = MemoryService.list_memories(self.db, user_id="user_b")
        self.assertEqual(len(mems_a), 1)
        self.assertEqual(len(mems_b), 1)
        self.assertEqual(mems_a[0].value, "SecretA")
        self.assertEqual(mems_b[0].value, "SecretB")

    def test_delete_memory(self):
        mem = MemoryService.create_memory(
            self.db, user_id="founder_1", type="fact", key="temp", value="val"
        )
        self.assertTrue(MemoryService.delete_memory(self.db, "founder_1", mem.id))
        self.assertIsNone(MemoryService.get_memory(self.db, "founder_1", mem.id))

    # --- IdeaService Tests ---

    def test_create_get_list_ideas(self):
        idea1 = IdeaService.create_idea(
            self.db,
            user_id="founder_1",
            title="RocketCat CLI",
            description="A CLI interface for RocketCat",
        )
        self.assertIsNotNone(idea1.id)
        self.assertEqual(idea1.title, "RocketCat CLI")

        idea_by_title = IdeaService.get_idea_by_title(
            self.db, user_id="founder_1", title="RocketCat CLI"
        )
        self.assertIsNotNone(idea_by_title)
        self.assertEqual(idea_by_title.id, idea1.id)

        idea_by_id = IdeaService.get_idea_by_id(
            self.db, user_id="founder_1", idea_id=idea1.id
        )
        self.assertIsNotNone(idea_by_id)
        self.assertEqual(idea_by_id.title, idea1.title)

        ideas = IdeaService.list_ideas(self.db, user_id="founder_1")
        self.assertEqual(len(ideas), 1)

    def test_update_and_delete_idea(self):
        idea = IdeaService.create_idea(
            self.db,
            user_id="founder_1",
            title="Draft Title",
            description="Draft Description",
        )

        updated = IdeaService.update_idea(
            self.db,
            user_id="founder_1",
            idea_id=idea.id,
            title="Final Title",
            description="Final Description",
        )
        self.assertEqual(updated.title, "Final Title")
        self.assertEqual(updated.description, "Final Description")

        deleted = IdeaService.delete_idea(self.db, user_id="founder_1", idea_id=idea.id)
        self.assertTrue(deleted)
        self.assertIsNone(IdeaService.get_idea_by_id(self.db, "founder_1", idea.id))

    def test_idea_user_isolation(self):
        idea_a = IdeaService.create_idea(
            self.db, user_id="user_a", title="Idea A", description="Desc A"
        )
        idea_b = IdeaService.create_idea(
            self.db, user_id="user_b", title="Idea B", description="Desc B"
        )

        # user_a cannot access user_b's idea by ID or title
        self.assertIsNone(IdeaService.get_idea_by_id(self.db, "user_a", idea_b.id))
        self.assertIsNone(IdeaService.get_idea_by_title(self.db, "user_a", "Idea B"))

        # user_a cannot update or delete user_b's idea
        self.assertIsNone(
            IdeaService.update_idea(
                self.db, "user_a", idea_b.id, title="Hacked Title"
            )
        )
        self.assertFalse(IdeaService.delete_idea(self.db, "user_a", idea_b.id))


if __name__ == "__main__":
    unittest.main()
