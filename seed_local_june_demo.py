

import json
import os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "focus-demo-june.db")
if os.path.exists(DB_PATH):
    os.unlink(DB_PATH)
os.environ["DATABASE_URL"] = "sqlite:///" + DB_PATH.replace("\\", "/")

from backend import crud, models  # noqa: E402
from backend.database import Base, SessionLocal, engine  # noqa: E402

Base.metadata.create_all(engine)
db = SessionLocal()
ws = crud.ensure_default_workspace(db)

db.add(models.UserProfile(
    workspace_id=ws.id,
    about="I study best in the mornings and keep afternoons for lighter work. Two-monitor desk setup.",
))

tasks = []
for name, desc in [
    ("Thesis writing", "The big one — deep morning blocks."),
    ("Problem sets", "Focused practice, mid-morning."),
    ("Reading & notes", "Afternoon, lower energy."),
]:
    t = models.Task(workspace_id=ws.id, name=name, description=desc, completed=False)
    db.add(t)
    tasks.append(t)
db.flush()

week_secs = {}
month_secs = {}


def monday_key(d):
    m = d - timedelta(days=d.weekday())
    return m.strftime("%Y-%m-%d")


def add_session(y, mo, d, focused, distracted, uncertain, away, task_i=0):
    start = datetime(y, mo, d, 16, 0, tzinfo=timezone.utc)
    total = focused + distracted + uncertain + away
    end = start + timedelta(minutes=total)
    task = tasks[task_i % len(tasks)]
    db.add(models.FocusSession(
        workspace_id=ws.id, task_id=task.id, task_name=task.name,
        started_at=start, ended_at=end,
        seconds_focused=focused * 60, seconds_distracted=distracted * 60,
        seconds_uncertain=uncertain * 60, seconds_away=away * 60,
    ))
    wk = monday_key(datetime(y, mo, d))
    mk = f"{y}-{mo:02d}"
    for bucket, key in ((week_secs, wk), (month_secs, mk)):
        b = bucket.setdefault(key, {"focused": 0, "distracted": 0, "uncertain": 0, "away": 0})
        b["focused"] += focused * 60
        b["distracted"] += distracted * 60
        b["uncertain"] += uncertain * 60
        b["away"] += away * 60


add_session(2026, 5, 5, 40, 25, 5, 0)
add_session(2026, 5, 7, 35, 20, 10, 0, 2)
add_session(2026, 5, 12, 45, 30, 0, 5)
add_session(2026, 5, 14, 30, 25, 5, 10, 2)
add_session(2026, 5, 19, 50, 20, 5, 0, 1)
add_session(2026, 5, 21, 40, 30, 0, 5, 2)
add_session(2026, 5, 26, 45, 25, 5, 0, 1)
add_session(2026, 5, 28, 35, 20, 10, 5, 2)

add_session(2026, 6, 2, 55, 10, 5, 0)
add_session(2026, 6, 3, 60, 8, 2, 0, 1)
add_session(2026, 6, 5, 50, 12, 3, 0, 2)
add_session(2026, 6, 9, 65, 8, 2, 0)
add_session(2026, 6, 11, 55, 10, 5, 0, 1)
add_session(2026, 6, 12, 45, 10, 0, 5, 2)
add_session(2026, 6, 16, 70, 5, 5, 0)
add_session(2026, 6, 17, 75, 5, 0, 0)
add_session(2026, 6, 19, 65, 8, 2, 0, 1)
add_session(2026, 6, 23, 60, 10, 5, 0)
add_session(2026, 6, 25, 55, 12, 3, 0, 1)
add_session(2026, 6, 26, 50, 15, 5, 0, 2)

add_session(2026, 7, 1, 40, 10, 5, 0)
add_session(2026, 7, 2, 45, 8, 2, 0, 1)

db.flush()


def wp(kind, period_key, secs, end, recap=None):
    db.add(models.WorkPeriod(
        workspace_id=ws.id, kind=kind, period_key=period_key,
        ended_at=end,
        seconds_focused=secs["focused"], seconds_distracted=secs["distracted"],
        seconds_uncertain=secs["uncertain"], seconds_away=secs["away"],
        ai_recap=json.dumps(recap) if recap else "",
    ))


june_week_recaps = {
    "2026-06-01": {"summary": "You protected the first morning hour most days, and it anchored the week.",
                   "theme": "Morning anchor"},
    "2026-06-08": {"summary": "A couple of afternoon dips, but you came back each time instead of drifting off.",
                   "theme": "Steady returns"},
    "2026-06-15": {"summary": "Your strongest week — long, unbroken blocks on Tuesday and Wednesday.",
                   "theme": "Deep weeks"},
    "2026-06-22": {"summary": "You held the rhythm even as energy tapered toward the weekend.",
                   "theme": "Holding the line"},
}
for wk_key, recap in june_week_recaps.items():
    end = datetime.strptime(wk_key, "%Y-%m-%d") + timedelta(days=6, hours=21)
    wp("week", wk_key, week_secs[wk_key], end.replace(tzinfo=timezone.utc), recap)

may_recap = {
    "summary": "May was uneven — strong mornings, but afternoons kept slipping to distraction.",
    "theme": "Finding footing",
    "insights": ["Mornings carried the month; afternoons were where focus leaked."],
    "improvements": [],
    "carry_forward": "When you start an afternoon block, you could put your phone in another room first.",
}
wp("month", "2026-05", month_secs["2026-05"],
   datetime(2026, 5, 31, 21, 0, tzinfo=timezone.utc), may_recap)

for hour, pct in {8: 88, 9: 90, 10: 85, 11: 80, 14: 62, 15: 58, 16: 60}.items():
    db.add(models.HourlyFocus(workspace_id=ws.id, hour=hour, focus_pct=float(pct), sessions=3))
for text, aff, rej in [
    ("Mornings start clean and hold focus best.", 3, 0),
    ("Afternoon blocks tend to dip after the first stretch.", 2, 0),
    ("Coming back after a drift has become a reliable habit.", 2, 0),
]:
    db.add(models.Observation(workspace_id=ws.id, text=text, affirmations=aff, rejections=rej, active=True))

db.commit()
sess_n = db.query(models.FocusSession).count()
wp_n = db.query(models.WorkPeriod).count()
print(f"Seeded {sess_n} sessions and {wp_n} work periods into {DB_PATH}")
may_total = sum(month_secs["2026-05"].values())
jun_total = sum(month_secs["2026-06"].values())
print(f"May focus {round(100*month_secs['2026-05']['focused']/may_total)}%  "
      f"June focus {round(100*month_secs['2026-06']['focused']/jun_total)}%  (expect a RISING trend)")
db.close()
