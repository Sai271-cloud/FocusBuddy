



import json
import os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "focus-goals-demo.db")
if os.path.exists(DB_PATH):
    os.unlink(DB_PATH)
os.environ["DATABASE_URL"] = "sqlite:///" + DB_PATH.replace("\\", "/")

from backend import crud, models  # noqa: E402
from backend.database import Base, SessionLocal, engine  # noqa: E402

Base.metadata.create_all(engine)
db = SessionLocal()
ws = crud.ensure_default_workspace(db)

LOCAL_TZ = datetime.now().astimezone().tzinfo
NOW_LOCAL = datetime.now(LOCAL_TZ)


def day_key(offset: int) -> str:
    return (NOW_LOCAL + timedelta(days=offset)).strftime("%Y-%m-%d")


def at(offset: int, hour: int, minute: int = 0) -> datetime:
    d = (NOW_LOCAL + timedelta(days=offset)).date()
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def today_recent(total_min: int) -> datetime:
    start = NOW_LOCAL - timedelta(minutes=total_min + 20)
    floor = NOW_LOCAL.replace(hour=0, minute=15, second=0, microsecond=0)
    return max(start, floor).astimezone(timezone.utc)


db.add(models.UserProfile(
    workspace_id=ws.id,
    about="Grad student. Mornings are my best focus; afternoons drift. Two-monitor desk setup.",
))

def task(name, desc="", completed=False, completed_offset=None):
    t = models.Task(
        workspace_id=ws.id, name=name, description=desc, completed=completed,
        completed_at=at(completed_offset, 18) if completed_offset is not None else None,
    )
    db.add(t)
    return t


t_chapter = task("Write chapter 3", "The core argument — needs deep blocks.")
t_figures = task("Make the figures", "Charts and diagrams for chapters 2-3.")
t_outline = task("Outline the literature review", "", completed=True, completed_offset=-8)
t_stats = task("Statistics problem sets", "Practice for the final.")
t_portfolio = task("Portfolio homepage copy", "Rewrite the intro section.")
t_reading = task("Evening reading", "Current book: deep-work habits.")
t_declutter = task("Declutter the office", "", completed=True, completed_offset=-18)
t_advisor = task("Email the advisor", "Send the updated timeline.")
t_meals = task("Plan next week's meals", "Sunday batch-cook list.")
db.flush()

def goal(title, target_offset, created_offset, status="active", done_offset=None, tasks=()):
    g = models.Goal(
        workspace_id=ws.id, title=title,
        target_day_key=day_key(target_offset),
        status=status,
        created_day_key=day_key(created_offset),
        done_day_key=day_key(done_offset) if done_offset is not None else None,
    )
    db.add(g)
    db.flush()
    for t in tasks:
        t.goal_id = g.id
    return g


goal("Finish my research paper", +12, -20, tasks=(t_chapter, t_figures, t_outline))
goal("Prepare for the statistics final", +3, -15, tasks=(t_stats,))
goal("Launch the portfolio site", 0, -10, tasks=(t_portfolio,))
goal("Read three books this summer", -5, -40, tasks=(t_reading,))
goal("Learn touch typing", +45, -3)
goal("Spring cleaning sprint", -12, -30, status="done", done_offset=-10, tasks=(t_declutter,))
goal("Daily journaling experiment", -20, -35, status="archived")

def session(t, start, focused, distracted=0, uncertain=0, away=0):
    total = focused + distracted + uncertain + away
    db.add(models.FocusSession(
        workspace_id=ws.id, task_id=t.id, task_name=t.name,
        started_at=start, ended_at=start + timedelta(minutes=total),
        seconds_focused=focused * 60, seconds_distracted=distracted * 60,
        seconds_uncertain=uncertain * 60, seconds_away=away * 60,
    ))


session(t_outline, at(-16, 9), 45, 10)
session(t_outline, at(-15, 9), 50, 8)
session(t_chapter, at(-13, 9), 55, 10, 5)
session(t_chapter, at(-11, 10), 60, 8)
session(t_chapter, at(-9, 9), 40, 15, 5)
session(t_figures, at(-7, 14), 35, 10)
session(t_chapter, at(-6, 9), 65, 5)
session(t_chapter, at(-4, 10), 50, 12)
session(t_chapter, at(-2, 9), 70, 5, 5)
session(t_figures, at(-1, 15), 30, 10)
session(t_chapter, today_recent(45), 40, 5)

session(t_stats, at(-12, 16), 40, 10)

session(t_portfolio, at(-1, 11), 50, 10)

session(t_reading, at(-30, 20), 30, 5)
session(t_reading, at(-25, 20), 30, 5)

session(t_declutter, at(-20, 13), 45, 10)
session(t_declutter, at(-18, 13), 40, 5)

session(t_meals, at(-3, 17), 25, 5)

db.add(models.DailyPlan(
    workspace_id=ws.id, period_key=day_key(0), available_min=180,
    plan_json=json.dumps([
        {"task_id": t_chapter.id, "name": t_chapter.name, "estimate_min": 90,
         "difficulty": "hard", "scheduled_min": None},
        {"task_id": t_stats.id, "name": t_stats.name, "estimate_min": 45,
         "difficulty": "medium", "scheduled_min": None},
    ]),
))

for hour, pct in {8: 86, 9: 90, 10: 84, 11: 78, 14: 60, 15: 55, 20: 65}.items():
    db.add(models.HourlyFocus(workspace_id=ws.id, hour=hour, focus_pct=float(pct), sessions=3))
for text, aff in [
    ("Mornings start clean and hold focus best.", 3),
    ("Afternoon blocks tend to dip after the first stretch.", 2),
]:
    db.add(models.Observation(workspace_id=ws.id, text=text, affirmations=aff, rejections=0, active=True))

db.commit()
goals_n = db.query(models.Goal).count()
tasks_n = db.query(models.Task).count()
sess_n = db.query(models.FocusSession).count()
print(f"Seeded {goals_n} goals, {tasks_n} tasks, {sess_n} sessions into {DB_PATH}")
print("Start the backend against it with:")
print('  $env:DATABASE_URL = "sqlite:///./focus-goals-demo.db"; uvicorn backend.main:app --reload')
print("Frontend as usual (frontend folder):  python -m http.server 5500")
db.close()
