import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.services import MessageService, ConversationService
from app.agent.sidekick_agent import create_sidekick_agent, run_agent_turn


class AgentTestCase(unittest.TestCase):
    def setUp(self):
        """Set up in-memory SQLite database session."""
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

    def test_agent_construction_and_tools(self):
        """Verifies Agno Agent construction and persistent tool registration."""
        agent = create_sidekick_agent(self.db, user_id="founder_1")

        self.assertIsNotNone(agent)
        # Check that 3 persistent tools are registered
        self.assertEqual(len(agent.tools), 3)

        tool_names = [getattr(t, "__name__", str(t)) for t in agent.tools]
        self.assertIn("bound_save_idea", tool_names)
        self.assertIn("bound_get_idea", tool_names)
        self.assertIn("bound_list_ideas", tool_names)

    @patch("app.agent.sidekick_agent.create_sidekick_agent")
    def test_run_agent_turn_persistence(self, mock_create_agent):
        """
        Tests agent turn orchestration with a mocked LLM response.
        Verifies both user input and assistant response are persisted to database.
        """
        # Set up mock agent and response
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "RocketCat is a fantastic name for your developer tool!"
        mock_agent.run.return_value = mock_response
        mock_create_agent.return_value = mock_agent

        conv_id = "conv_test_1"
        user_msg = "We're naming our developer tool RocketCat."

        # Execute agent turn
        reply = run_agent_turn(
            self.db, user_id="founder_1", conversation_id=conv_id, message=user_msg
        )

        self.assertEqual(reply, "RocketCat is a fantastic name for your developer tool!")

        # Verify messages persisted in database
        messages = MessageService.get_recent_messages(
            self.db, conversation_id=conv_id, limit=10
        )
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[0].content, user_msg)
        self.assertEqual(messages[1].role, "assistant")
        self.assertEqual(messages[1].content, reply)


if __name__ == "__main__":
    unittest.main()
