import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.tools.idea_tools import save_idea, get_idea, list_ideas


class IdeaToolsTestCase(unittest.TestCase):
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

    def test_save_idea(self):
        res = save_idea(
            self.db,
            user_id="founder_1",
            title="RocketCat CLI",
            description="Terminal client for RocketCat",
        )
        self.assertEqual(res["status"], "success")
        self.assertIn("idea", res)
        self.assertEqual(res["idea"]["title"], "RocketCat CLI")
        self.assertEqual(res["idea"]["user_id"], "founder_1")

    def test_get_idea_by_title(self):
        saved = save_idea(
            self.db,
            user_id="founder_1",
            title="RocketCat Web",
            description="Web app for RocketCat",
        )
        res = get_idea(self.db, user_id="founder_1", identifier="RocketCat Web")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["idea"]["id"], saved["idea"]["id"])

    def test_get_idea_by_id(self):
        saved = save_idea(
            self.db,
            user_id="founder_1",
            title="RocketCat API",
            description="REST API for RocketCat",
        )
        idea_id = saved["idea"]["id"]
        res = get_idea(self.db, user_id="founder_1", identifier=idea_id)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["idea"]["title"], "RocketCat API")

    def test_get_idea_not_found(self):
        res = get_idea(self.db, user_id="founder_1", identifier="NonExistentTitle")
        self.assertEqual(res["status"], "error")
        self.assertIsNone(res["idea"])
        self.assertIn("not found", res["message"])

    def test_list_ideas(self):
        save_idea(
            self.db,
            user_id="founder_1",
            title="Idea 1",
            description="Description 1",
        )
        save_idea(
            self.db,
            user_id="founder_1",
            title="Idea 2",
            description="Description 2",
        )

        res = list_ideas(self.db, user_id="founder_1")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["count"], 2)
        self.assertEqual(len(res["ideas"]), 2)

    def test_user_isolation(self):
        save_idea(
            self.db,
            user_id="user_a",
            title="Secret A",
            description="Secret idea A",
        )

        # user_b lists ideas -> count 0
        list_b = list_ideas(self.db, user_id="user_b")
        self.assertEqual(list_b["count"], 0)
        self.assertEqual(list_b["ideas"], [])

        # user_b attempts to get user_a's idea by title -> error
        get_b = get_idea(self.db, user_id="user_b", identifier="Secret A")
        self.assertEqual(get_b["status"], "error")
        self.assertIsNone(get_b["idea"])


if __name__ == "__main__":
    unittest.main()
