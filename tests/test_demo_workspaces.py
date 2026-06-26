import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import crud, main, models
from backend.database import Base


class DemoWorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[main.get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        main.app.dependency_overrides.clear()
        self.engine.dispose()

    def test_seeded_demo_workspaces_are_isolated_and_resettable(self):
        early = {"X-Demo-Slug": "early-morning"}
        doom = {"X-Demo-Slug": "doomscroller"}

        self.assertEqual(self.client.post("/demo/early-morning/reset").status_code, 200)
        self.assertEqual(self.client.post("/demo/doomscroller/reset").status_code, 200)

        early_tasks = self.client.get("/tasks", headers=early).json()
        doom_tasks = self.client.get("/tasks", headers=doom).json()

        self.assertTrue(any("Morning" in t["name"] for t in early_tasks))
        self.assertTrue(any("Blocker" in t["name"] or "scroll" in t["name"].lower() for t in doom_tasks))
        self.assertNotEqual({t["name"] for t in early_tasks}, {t["name"] for t in doom_tasks})

        created = self.client.post("/tasks", headers=early, json={"name": "Judge custom task"}).json()
        self.assertEqual(created["name"], "Judge custom task")
        self.assertTrue(any(t["name"] == "Judge custom task" for t in self.client.get("/tasks", headers=early).json()))
        self.assertFalse(any(t["name"] == "Judge custom task" for t in self.client.get("/tasks", headers=doom).json()))

        self.client.post("/demo/early-morning/reset")
        names_after_reset = {t["name"] for t in self.client.get("/tasks", headers=early).json()}
        self.assertNotIn("Judge custom task", names_after_reset)

    def test_anonymous_new_demo_is_blank_and_per_browser(self):
        browser_a = {"X-Demo-Anonymous-Id": "judge-browser-a"}
        browser_b = {"X-Demo-Anonymous-Id": "judge-browser-b"}

        self.assertEqual(self.client.get("/tasks", headers=browser_a).json(), [])
        self.assertEqual(self.client.get("/tasks", headers=browser_b).json(), [])

        self.client.post("/tasks", headers=browser_a, json={"name": "Try my own session"})

        self.assertEqual(
            [t["name"] for t in self.client.get("/tasks", headers=browser_a).json()],
            ["Try my own session"],
        )
        self.assertEqual(self.client.get("/tasks", headers=browser_b).json(), [])

        self.client.post("/demo/new/clear", headers=browser_a)
        self.assertEqual(self.client.get("/tasks", headers=browser_a).json(), [])

    def test_seeded_daily_unwinds_cover_history_but_not_demo_today(self):
        self.client.post("/demo/early-morning/reset")

        recaps = self.client.get("/demo/early-morning/daily-unwinds").json()
        dates = [item["period_key"] for item in recaps]

        self.assertEqual(dates, [
            "2026-06-22",
            "2026-06-23",
            "2026-06-24",
            "2026-06-25",
            "2026-06-26",
            "2026-06-27",
        ])
        self.assertTrue(all(item["summary"] for item in recaps))
        self.assertNotIn("2026-06-28", dates)

    def test_default_workspace_still_works_without_demo_headers(self):
        self.client.post("/tasks", json={"name": "Local task"})
        self.assertEqual([t["name"] for t in self.client.get("/tasks").json()], ["Local task"])
        early_tasks = self.client.get("/tasks", headers={"X-Demo-Slug": "early-morning"}).json()
        self.assertFalse(any(t["name"] == "Local task" for t in early_tasks))

    def test_unknown_seeded_demo_slug_returns_404(self):
        self.assertEqual(self.client.get("/demo/not-real").status_code, 404)
        self.assertEqual(
            self.client.get("/tasks", headers={"X-Demo-Slug": "not-real"}).status_code,
            404,
        )


class DemoWorkspaceCrudTests(unittest.TestCase):
    def test_seed_definitions_have_distinct_readable_slugs(self):
        self.assertEqual(
            [seed["slug"] for seed in crud.DEMO_PERSONA_SEEDS],
            ["early-morning", "doomscroller", "overplanner", "night-owl", "self-improver"],
        )
        self.assertTrue(all(seed["display_name"] for seed in crud.DEMO_PERSONA_SEEDS))


class DemoFrontendStaticTests(unittest.TestCase):
    def test_demo_frontend_assets_are_loaded_on_app_pages(self):
        root = Path(__file__).resolve().parents[1]
        for name in ["index.html", "plan.html", "tracker.html", "analytics.html"]:
            html = (root / "frontend" / name).read_text(encoding="utf-8")
            self.assertIn('js/config.js', html)
            self.assertIn('js/demo-context.js', html)
            self.assertLess(html.index('js/demo-context.js'), html.index('js/api.js'))

    def test_api_wrapper_sends_demo_workspace_headers(self):
        root = Path(__file__).resolve().parents[1]
        api_js = (root / "frontend" / "js" / "api.js").read_text(encoding="utf-8")

        self.assertIn("demoHeaders", api_js)
        self.assertIn("X-Demo-Slug", api_js)
        self.assertIn("X-Demo-Anonymous-Id", api_js)
        self.assertIn("getDemoDailyUnwinds", api_js)
        self.assertIn("resetDemoWorkspace", api_js)
        self.assertIn("clearNewDemoWorkspace", api_js)

    def test_demo_context_freezes_today_and_adds_judge_demo_entry(self):
        root = Path(__file__).resolve().parents[1]
        demo_js = (root / "frontend" / "js" / "demo-context.js").read_text(encoding="utf-8")
        planning_js = (root / "frontend" / "js" / "planning-insights.js").read_text(encoding="utf-8")

        self.assertIn("2026, 5, 28, 9, 0, 0", demo_js)
        self.assertIn("Judge Demo", demo_js)
        self.assertIn("Reset demo data", demo_js)
        self.assertIn("Clear my demo data", demo_js)
        self.assertIn("AI credits are unavailable", demo_js)
        self.assertIn("FocusBuddyDemo.now", planning_js)


if __name__ == "__main__":
    unittest.main()
