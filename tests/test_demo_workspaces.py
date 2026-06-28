import json
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

    def test_seeded_daily_unwinds_start_empty_but_keep_history_rows(self):
        meta = self.client.post("/demo/early-morning/reset").json()
        self.assertEqual(meta["seed_version"], crud.CURRENT_DEMO_SEED_VERSION)

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
        self.assertTrue(all(item["summary"] == "" for item in recaps))
        self.assertTrue(all(item["ai_recap"] == "" for item in recaps))
        self.assertNotIn("2026-06-28", dates)

        periods = self.client.get("/work-periods", headers={"X-Demo-Slug": "early-morning"}).json()
        history_periods = [p for p in periods if p["kind"] == "day" and p["period_key"] in dates]
        self.assertEqual(len(history_periods), 6)
        self.assertTrue(all(p["reflection"] for p in history_periods))
        self.assertTrue(all((p["seconds_focused"] + p["seconds_distracted"] + p["seconds_uncertain"] + p["seconds_away"]) > 0 for p in history_periods))
        self.assertFalse(any(p["period_key"] == "2026-06-28" for p in periods))

    def test_demo_daily_unwinds_expose_seeded_plan_reality(self):
        self.client.post("/demo/overplanner/reset")

        recaps = self.client.get("/demo/overplanner/daily-unwinds").json()

        reports = []
        self.assertEqual(len(recaps), len(crud.DEMO_HISTORY_DATES))
        for item in recaps:
            raw = item.get("plan_reality_json")
            self.assertIsInstance(raw, str)
            self.assertTrue(raw, item["period_key"])
            report = json.loads(raw)
            reports.append(report)

            self.assertTrue(report.get("has_plan"), item["period_key"])
            self.assertGreater(report.get("planned_total_min", 0), 0)
            self.assertGreater(report.get("actual_total_min", 0), 0)
            self.assertTrue(report.get("rows"), item["period_key"])

        self.assertTrue(
            any(
                report["planned_total_min"] > report["actual_total_min"]
                or any(row["status"] == "not_started" for row in report["rows"])
                for report in reports
            )
        )

    def test_seeded_personas_have_historical_plans_and_plan_reality_rows(self):
        for seed in crud.DEMO_PERSONA_SEEDS:
            with self.subTest(slug=seed["slug"]):
                self.client.post(f"/demo/{seed['slug']}/reset")
                with self.SessionLocal() as db:
                    workspace = crud.get_workspace_by_slug(db, seed["slug"])
                    plans = (
                        db.query(models.DailyPlan)
                        .filter(models.DailyPlan.workspace_id == workspace.id)
                        .order_by(models.DailyPlan.period_key)
                        .all()
                    )
                    periods = (
                        db.query(models.WorkPeriod)
                        .filter(
                            models.WorkPeriod.workspace_id == workspace.id,
                            models.WorkPeriod.kind == "day",
                        )
                        .order_by(models.WorkPeriod.period_key)
                        .all()
                    )

                    self.assertEqual([p.period_key for p in plans], crud.DEMO_HISTORY_DATES)
                    self.assertEqual([p.period_key for p in periods], crud.DEMO_HISTORY_DATES)
                    self.assertTrue(all(json.loads(p.plan_json) for p in plans))

                    for period in periods:
                        report = json.loads(period.plan_reality_json or "{}")
                        self.assertTrue(report.get("has_plan"), period.period_key)
                        self.assertGreater(report.get("planned_total_min", 0), 0)
                        self.assertGreater(report.get("actual_total_min", 0), 0)
                        self.assertGreater(report.get("focused_total_min", 0), 0)
                        self.assertIsInstance(report.get("summary"), str)
                        self.assertTrue(report.get("rows"), period.period_key)

    def test_overplanner_seed_shows_more_planned_than_tracked_or_not_started_work(self):
        self.client.post("/demo/overplanner/reset")
        with self.SessionLocal() as db:
            workspace = crud.get_workspace_by_slug(db, "overplanner")
            periods = (
                db.query(models.WorkPeriod)
                .filter(models.WorkPeriod.workspace_id == workspace.id, models.WorkPeriod.kind == "day")
                .all()
            )

        reports = [json.loads(period.plan_reality_json) for period in periods]
        self.assertTrue(any(r["planned_total_min"] > r["actual_total_min"] for r in reports))
        self.assertTrue(
            any(any(row["status"] == "not_started" for row in r["rows"]) for r in reports)
        )

    def test_generated_seeded_daily_unwind_persists_until_reset(self):
        headers = {"X-Demo-Slug": "early-morning"}
        self.client.post("/demo/early-morning/reset")
        self.client.post("/work-periods", headers=headers, json={
            "kind": "day",
            "period_key": "2026-06-22",
            "ended_at": "2026-06-22T21:00:00-04:00",
            "seconds_focused": 3720,
            "seconds_distracted": 1260,
            "seconds_uncertain": 360,
            "seconds_away": 120,
            "ai_recap": '{"summary":"Generated by the judge.","win":"Used the first block well.","next_action":"When you sit down, you could start with the hardest problem."}',
        })

        recaps = self.client.get("/demo/early-morning/daily-unwinds").json()
        first = next(item for item in recaps if item["period_key"] == "2026-06-22")
        self.assertEqual(first["summary"], "Generated by the judge.")
        self.assertIn("hardest problem", first["next_action"])

        self.client.post("/demo/early-morning/reset")
        reset_recaps = self.client.get("/demo/early-morning/daily-unwinds").json()
        reset_first = next(item for item in reset_recaps if item["period_key"] == "2026-06-22")
        self.assertEqual(reset_first["summary"], "")
        self.assertEqual(reset_first["ai_recap"], "")

    def test_seed_version_mismatch_reseeds_existing_seeded_workspace(self):
        headers = {"X-Demo-Slug": "early-morning"}
        self.client.post("/demo/early-morning/reset")
        self.client.post("/tasks", headers=headers, json={"name": "Temporary judge edit"})
        self.client.post("/work-periods", headers=headers, json={
            "kind": "day",
            "period_key": "2026-06-22",
            "ended_at": "2026-06-22T21:00:00-04:00",
            "seconds_focused": 1,
            "seconds_distracted": 0,
            "seconds_uncertain": 0,
            "seconds_away": 0,
            "ai_recap": '{"summary":"Old generated recap"}',
        })

        with self.SessionLocal() as db:
            workspace = crud.get_workspace_by_slug(db, "early-morning")
            workspace.seed_version = crud.CURRENT_DEMO_SEED_VERSION - 1
            db.commit()

        meta = self.client.get("/demo/early-morning").json()
        self.assertEqual(meta["seed_version"], crud.CURRENT_DEMO_SEED_VERSION)
        self.assertFalse(any(t["name"] == "Temporary judge edit" for t in self.client.get("/tasks", headers=headers).json()))
        recaps = self.client.get("/demo/early-morning/daily-unwinds").json()
        self.assertEqual(next(item for item in recaps if item["period_key"] == "2026-06-22")["ai_recap"], "")

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

    def test_seeded_hourly_profiles_make_demo_timing_patterns_obvious(self):
        seeds = {seed["slug"]: seed for seed in crud.DEMO_PERSONA_SEEDS}

        early = seeds["early-morning"]["hourly"]
        early_top = {hour for hour, _ in sorted(early.items(), key=lambda item: item[1], reverse=True)[:3]}
        self.assertTrue(early_top.issubset({7, 8, 9, 10}))
        self.assertTrue(all(early.get(hour, 0) <= 45 for hour in (18, 19, 20)))

        night = seeds["night-owl"]["hourly"]
        night_top = {hour for hour, _ in sorted(night.items(), key=lambda item: item[1], reverse=True)[:3]}
        self.assertTrue(night_top.issubset({16, 17, 18, 19}))
        self.assertTrue(all(night.get(hour, 0) <= 45 for hour in (8, 9, 10)))


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
        self.assertIn("generateHistoricalDailyUnwind", demo_js)
        self.assertIn('data-act="generate-history-daily"', demo_js)
        self.assertIn("Regenerate", demo_js)
        self.assertIn("Reset demo data", demo_js)
        self.assertIn("Clear my demo data", demo_js)
        self.assertIn("AI credits are unavailable", demo_js)
        self.assertNotIn("seeded examples above", demo_js)
        self.assertIn("FocusBuddyDemo.now", planning_js)
        self.assertNotIn("fb-demo-slug", demo_js)
        self.assertIn("fb-demo-anon-id", demo_js)

    def test_demo_context_renders_historical_plan_reality(self):
        root = Path(__file__).resolve().parents[1]
        demo_js = (root / "frontend" / "js" / "demo-context.js").read_text(encoding="utf-8")

        self.assertIn("Plan vs reality", demo_js)
        self.assertIn("Task", demo_js)
        self.assertIn("Planned", demo_js)
        self.assertIn("Actual", demo_js)
        self.assertIn("Status", demo_js)
        self.assertIn("plan_reality_summary", demo_js)
        self.assertIn("plan_reality_json", demo_js)

    def test_coaching_prompts_share_plain_student_language_rule(self):
        root = Path(__file__).resolve().parents[1]
        main_py = (root / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIn("PLAIN_COACHING_LANGUAGE", main_py)
        self.assertIn("helpful older student", main_py)
        self.assertIn("everyday words", main_py)
        self.assertGreaterEqual(main_py.count("{PLAIN_COACHING_LANGUAGE}"), 3)
        self.assertNotIn("THOUROUGLY", main_py)

    def test_weekly_and_planner_prompts_prioritize_best_focus_windows(self):
        root = Path(__file__).resolve().parents[1]
        main_py = (root / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIn("best focus windows are a primary weekly insight", main_py)
        self.assertIn("must include one best-focus-window insight", main_py)
        self.assertIn("reason must explain why the task fits that best focus window", main_py)
        self.assertNotIn("productive times", main_py)


if __name__ == "__main__":
    unittest.main()
