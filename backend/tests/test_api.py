import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import Base, get_db
from app.services import MessageService, IdeaService


class APITestCase(unittest.TestCase):
    def setUp(self):
        """Set up in-memory database and FastAPI test client."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.TestingSessionLocal = TestingSessionLocal

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)

    @patch("app.api.chat.run_agent_turn")
    def test_post_chat_success(self, mock_run_turn):
        """Test POST /chat returns HTTP 200 and ChatResponse payload."""
        mock_run_turn.return_value = "RocketCat is a developer CLI tool."

        payload = {
            "user_id": "founder_123",
            "conversation_id": "conv_456",
            "message": "What is RocketCat?",
        }
        response = self.client.post("/chat", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user_id"], "founder_123")
        self.assertEqual(data["conversation_id"], "conv_456")
        self.assertEqual(data["response"], "RocketCat is a developer CLI tool.")

    def test_post_chat_missing_fields(self):
        """Test POST /chat returns HTTP 422 when required fields are missing."""
        # Missing 'message'
        response = self.client.post(
            "/chat", json={"user_id": "founder_123", "conversation_id": "conv_456"}
        )
        self.assertEqual(response.status_code, 422)

        # Empty 'user_id'
        response = self.client.post(
            "/chat",
            json={
                "user_id": "",
                "conversation_id": "conv_456",
                "message": "Hello",
            },
        )
        self.assertEqual(response.status_code, 422)

    @patch("app.agent.sidekick_agent.create_sidekick_agent")
    def test_conversation_and_assistant_persistence(self, mock_create_agent):
        """Test POST /chat persists user message and assistant reply in DB."""
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "I have noted your developer tool RocketCat."
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        payload = {
            "user_id": "founder_789",
            "conversation_id": "conv_789",
            "message": "We call our tool RocketCat.",
        }

        response = self.client.post("/chat", json=payload)
        self.assertEqual(response.status_code, 200)

        # Verify DB records
        db = self.TestingSessionLocal()
        try:
            messages = MessageService.get_recent_messages(
                db, conversation_id="conv_789", limit=10
            )
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0].role, "user")
            self.assertEqual(messages[0].content, "We call our tool RocketCat.")
            self.assertEqual(messages[1].role, "assistant")
            self.assertEqual(
                messages[1].content, "I have noted your developer tool RocketCat."
            )
        finally:
            db.close()

    def test_tool_driven_idea_creation(self):
        """Test persistent idea creation via IdeaService/tools integration."""
        db = self.TestingSessionLocal()
        try:
            IdeaService.create_idea(
                db,
                user_id="founder_789",
                title="RocketCat CLI",
                description="Terminal tool",
            )
            ideas = IdeaService.list_ideas(db, user_id="founder_789")
            self.assertEqual(len(ideas), 1)
            self.assertEqual(ideas[0].title, "RocketCat CLI")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
