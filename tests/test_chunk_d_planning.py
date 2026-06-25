import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from backend import schemas


class ChunkDPlanningTests(unittest.TestCase):
    def test_plan_reality_matches_by_task_id_and_reports_unplanned_work(self):
        from backend.main import _build_plan_reality_report

        plan = SimpleNamespace(
            period_key="2026-06-24",
            plan_json=json.dumps([
                {
                    "task_id": 1,
                    "name": "Essay",
                    "estimate_min": 30,
                    "difficulty": "hard",
                    "scheduled_min": 9 * 60,
                },
                {
                    "task_id": 2,
                    "name": "Math",
                    "estimate_min": 20,
                    "difficulty": "medium",
                    "scheduled_min": 10 * 60,
                },
            ]),
        )
        sessions = [
            SimpleNamespace(
                id=11,
                task_id=1,
                task_name="Essay renamed later",
                started_at=datetime(2026, 6, 24, 9, 20, tzinfo=timezone.utc),
                seconds_focused=1200,
                seconds_distracted=300,
                seconds_uncertain=0,
                seconds_away=0,
            ),
            SimpleNamespace(
                id=12,
                task_id=99,
                task_name="Email",
                started_at=datetime(2026, 6, 24, 11, 0, tzinfo=timezone.utc),
                seconds_focused=600,
                seconds_distracted=0,
                seconds_uncertain=0,
                seconds_away=0,
            ),
        ]

        report = _build_plan_reality_report("2026-06-24", plan, sessions)
        rows = {row.task_id: row for row in report.rows}

        self.assertTrue(report.has_plan)
        self.assertEqual(rows[1].actual_start_min, 9 * 60 + 20)
        self.assertEqual(rows[1].start_delta_min, 20)
        self.assertEqual(rows[1].actual_total_min, 25)
        self.assertEqual(rows[1].duration_delta_min, -5)
        self.assertEqual(rows[2].status, "not_started")
        self.assertEqual(rows[99].status, "unscheduled_work")
        self.assertIn("1 planned task not started", report.summary)

    def test_calibration_requires_two_samples_and_flags_underestimation(self):
        from backend.main import _build_plan_calibration

        scorecards = [
            {
                "period_key": "2026-06-23",
                "rows": [
                    {
                        "task_id": 7,
                        "planned_estimate_min": 30,
                        "actual_total_min": 45,
                        "status": "ran_long",
                    }
                ],
            },
            {
                "period_key": "2026-06-22",
                "rows": [
                    {
                        "task_id": 7,
                        "planned_estimate_min": 40,
                        "actual_total_min": 60,
                        "status": "ran_long",
                    }
                ],
            },
        ]

        calibration = _build_plan_calibration(scorecards)
        self.assertEqual(calibration.overall.tendency, "under")
        self.assertGreaterEqual(calibration.overall.avg_delta_pct, 20)
        self.assertEqual(calibration.by_task[0].task_id, 7)

        thin = _build_plan_calibration(scorecards[:1])
        self.assertEqual(thin.overall.tendency, "unknown")

    def test_reschedule_packs_remaining_work_without_overwriting_completed_work(self):
        from backend.main import _build_reschedule_response

        entries = [
            schemas.PlanEntry(task_id=1, name="Done", estimate_min=30, difficulty="easy", scheduled_min=9 * 60),
            schemas.PlanEntry(task_id=2, name="Half done", estimate_min=50, difficulty="hard", scheduled_min=10 * 60),
            schemas.PlanEntry(task_id=3, name="Fresh", estimate_min=20, difficulty="medium", scheduled_min=11 * 60),
        ]
        req = schemas.PlanRescheduleRequest(
            period_key="2026-06-24",
            entries=entries,
            current_min=12 * 60 + 3,
            day_end_min=13 * 60,
            actual_by_task={1: 35, 2: 20},
            completed_task_ids=[1],
        )

        result = _build_reschedule_response(req)
        starts = {block.task_id: block.start_hour * 60 + block.start_min for block in result.scheduled}

        self.assertNotIn(1, starts)
        self.assertEqual(starts[2], 12 * 60 + 15)
        self.assertEqual(starts[3], 12 * 60 + 45)
        self.assertTrue(result.over_plan_note)


if __name__ == "__main__":
    unittest.main()
