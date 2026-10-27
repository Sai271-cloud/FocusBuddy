



import json
import os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "focus-demo-full.db")
if os.path.exists(DB_PATH):
    os.unlink(DB_PATH)
os.environ["DATABASE_URL"] = "sqlite:///" + DB_PATH.replace("\\", "/")

from backend import crud, models, schemas  # noqa: E402
from backend.database import Base, SessionLocal, engine  # noqa: E402

Base.metadata.create_all(engine)
db = SessionLocal()
ws = crud.ensure_default_workspace(db)

LOCAL_TZ = datetime.now().astimezone().tzinfo
NOW_LOCAL = datetime.now(LOCAL_TZ)


def day_key(offset):
    return (NOW_LOCAL + timedelta(days=offset)).strftime("%Y-%m-%d")


def monday_key(offset):
    d = NOW_LOCAL + timedelta(days=offset)
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def month_key(offset):
    return (NOW_LOCAL + timedelta(days=offset)).strftime("%Y-%m")


def at(offset, hour, minute=0):
    d = (NOW_LOCAL + timedelta(days=offset)).date()
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def timeline(*runs):
    entries, minute = [], 0
    for state, length in runs:
        for _ in range(int(length)):
            entries.append({"minute": minute, "state": state})
            minute += 1
    return entries


def journal(*events):
    out = []
    for t, kind, val in events:
        if kind == "site":
            out.append({"t": t * 60, "type": "site", "site": val[0], "title": val[1]})
        else:
            out.append({"t": t * 60, "type": "note", "note": val})
    return json.dumps(out)


db.add(models.UserProfile(
    workspace_id=ws.id,
    about=("Master's student writing my thesis — draft due next month. Mornings are my "
           "deep-work window; I hit the gym around noon, so afternoons start slower. "
           "Two-monitor desk: papers open on the second screen."),
))

def task(name, desc="", completed=False, completed_offset=None):
    t = models.Task(
        workspace_id=ws.id, name=name, description=desc, completed=completed,
        completed_at=at(completed_offset, 18) if completed_offset is not None else None,
    )
    db.add(t)
    return t


t_chapter = task("Write chapter 3", "The core argument. Zotero + Google Docs; papers on screen two.")
t_figures = task("Make the figures", "Matplotlib charts for chapters 2-3.")
t_outline = task("Outline the literature review", "", completed=True, completed_offset=-8)
t_stats = task("Statistics problem sets", "Past papers for the final on Monday.")
t_portfolio = task("Portfolio site refresh", "Rewrite the intro, swap the project screenshots.")
t_reading = task("Evening reading", "Current book: Deep Work.")
t_project = task("Course project — final report", "", completed=True, completed_offset=-24)
t_finals = task("Spring finals revision", "", completed=True, completed_offset=-55)
t_advisor = task("Email the advisor", "Send the updated thesis timeline.")
t_meals = task("Plan next week's meals", "Sunday batch-cook list.")
db.flush()

def goal(title, target_offset, created_offset, status="active", done_offset=None, tasks=()):
    g = models.Goal(
        workspace_id=ws.id, title=title,
        target_day_key=day_key(target_offset), status=status,
        created_day_key=day_key(created_offset),
        done_day_key=day_key(done_offset) if done_offset is not None else None,
    )
    db.add(g)
    db.flush()
    for t in tasks:
        t.goal_id = g.id
    return g


goal("Finish my research paper", +12, -20, tasks=(t_chapter, t_figures, t_outline))
goal("Pass the statistics final", +3, -15, tasks=(t_stats,))
goal("Ship my portfolio site refresh", 0, -10, tasks=(t_portfolio,))
goal("Read three books this summer", -5, -40, tasks=(t_reading,))
goal("Learn to touch type", +45, -3)
goal("Submit the course project", -25, -60, status="done", done_offset=-24, tasks=(t_project,))
goal("5am mornings experiment", -30, -70, status="archived")

day_secs, week_secs, month_secs = {}, {}, {}
sessions_by_offset = {}
total_focused_min = 0

J_DEFAULT = journal((0, "note", "Started with a clear task intention."),
                    (20, "note", "Still on the main document."))
J_DRIFT = journal((0, "note", "Started with a clear task intention."),
                  (11, "site", ("instagram.com", "Feed")),
                  (14, "note", "Caught the drift and came back to the task."),
                  (26, "site", ("twitter.com", "Home")),
                  (29, "note", "Second drift — closed the tab."))
J_TUTORIAL = journal((0, "site", ("docs.google.com", "Chapter 3 — draft")),
                     (16, "site", ("youtube.com", "SPSS tutorial: mixed models explained")),
                     (24, "note", "Tutorial was exactly what the analysis needed."),
                     (31, "site", ("docs.google.com", "Chapter 3 — draft")))
J_RESEARCH = journal((0, "site", ("docs.google.com", "Chapter 3 — draft")),
                     (14, "site", ("scholar.google.com", "mixed effects longitudinal review")),
                     (27, "site", ("stats.stackexchange.com", "Random slopes vs intercepts")),
                     (39, "note", "Found the citation I was missing."))
J_BEST = journal((0, "note", "Phone in the other room. One block, one section."),
                 (33, "note", "Halfway — the argument is holding together."),
                 (61, "note", "Longest clean stretch this month."))


def session(t, offset, hour, minute, runs, intention=None, journal_js=None, start=None):
    global total_focused_min
    secs = {"focused": 0, "distracted": 0, "uncertain": 0, "away": 0}
    for state, m in runs:
        secs[state] += m
    total = sum(secs.values())
    started = start or at(offset, hour, minute)
    s = models.FocusSession(
        workspace_id=ws.id, task_id=t.id, task_name=t.name,
        started_at=started, ended_at=started + timedelta(minutes=total),
        seconds_focused=secs["focused"] * 60, seconds_distracted=secs["distracted"] * 60,
        seconds_uncertain=secs["uncertain"] * 60, seconds_away=secs["away"] * 60,
        timeline_json=json.dumps(timeline(*runs)),
        journal_json=journal_js or J_DEFAULT,
        intention=intention or f"Make visible progress on {t.name}.",
    )
    db.add(s)
    sessions_by_offset.setdefault(offset, []).append(s)
    total_focused_min += secs["focused"]
    for bucket, key in ((day_secs, day_key(offset)), (week_secs, monday_key(offset)),
                        (month_secs, month_key(offset))):
        b = bucket.setdefault(key, {"focused": 0, "distracted": 0, "uncertain": 0, "away": 0})
        for k in secs:
            b[k] += secs[k] * 60


def choppy(a, b, c):
    return [("focused", a), ("distracted", 8), ("focused", b), ("distracted", 7),
            ("uncertain", 5), ("focused", c), ("away", 8)]


def mid(lead, main):
    return [("focused", lead), ("distracted", 5), ("focused", main), ("distracted", 6),
            ("uncertain", 3), ("away", 2)]


def deep(lead, main):
    return [("focused", lead), ("distracted", 3), ("focused", main), ("uncertain", 2)]


def light(main):
    return [("focused", main), ("distracted", 7), ("uncertain", 4), ("away", 3)]


session(t_finals, -72, 14, 10, choppy(12, 9, 11), "Get through two past papers.", J_DRIFT)
session(t_finals, -71, 19, 30, light(24), "One more revision pass before bed.")
session(t_finals, -69, 14, 45, choppy(14, 11, 13), journal_js=J_DRIFT)
session(t_finals, -66, 10, 20, light(27), "Morning revision — flashcards first.")
session(t_project, -66, 15, 30, choppy(10, 8, 9), "Sketch the project structure.")
session(t_finals, -64, 13, 50, choppy(13, 10, 12), journal_js=J_DRIFT)
session(t_project, -61, 14, 15, choppy(15, 12, 14), "Data cleaning for the project.")
session(t_finals, -58, 11, 5, light(25))
session(t_finals, -55, 9, 40, deep(14, 26), "Last exam tomorrow — targeted review.")
session(t_project, -53, 10, 10, mid(16, 27), "First real project morning post-finals.")
session(t_project, -50, 15, 20, choppy(12, 10, 11), journal_js=J_DRIFT)

session(t_project, -47, 9, 30, mid(17, 29), "Results section, first pass.")
session(t_project, -45, 9, 5, mid(19, 36), "Finish the results tables.", J_RESEARCH)
session(t_project, -45, 15, 40, light(21))
session(t_project, -43, 14, 20, choppy(14, 12, 10), journal_js=J_DRIFT)
session(t_project, -41, 9, 15, mid(18, 32), "Discussion section outline.")
session(t_project, -38, 9, 50, deep(21, 37), "Full draft by Friday.", J_RESEARCH)
session(t_reading, -38, 20, 15, [("focused", 27), ("distracted", 3)],
        "Thirty pages before sleep.")
session(t_project, -36, 15, 10, light(31))
session(t_project, -34, 9, 25, mid(17, 36), "Revise intro + methods.")
session(t_project, -31, 9, 0, deep(22, 41), "Advisor feedback pass.", J_RESEARCH)
session(t_reading, -31, 20, 30, [("focused", 26), ("uncertain", 3)])
session(t_project, -29, 10, 5, mid(16, 31), "Formatting + references.")
session(t_project, -27, 14, 35, choppy(13, 11, 12), journal_js=J_DRIFT)
session(t_project, -25, 9, 10, deep(20, 40), "Final read-through before submission.")
session(t_project, -24, 9, 35, mid(15, 26), "Submit it. Done is done.",
        journal((0, "note", "Submission day — one last pass."),
                (30, "note", "Submitted. Closing the tab felt great.")))
session(t_chapter, -22, 9, 20, mid(14, 27), "Thesis becomes the main thing now.")
session(t_chapter, -20, 9, 45, deep(18, 34), "Chapter 3 skeleton.", J_RESEARCH)
session(t_reading, -20, 20, 45, [("focused", 28), ("distracted", 2)])

session(t_outline, -16, 9, 10, deep(16, 27), "Map the literature review sections.")
session(t_outline, -15, 9, 30, deep(19, 31), "Finish the outline today.", J_RESEARCH)
session(t_reading, -15, 20, 20, [("focused", 25), ("uncertain", 2)])
session(t_chapter, -13, 9, 5, deep(18, 34), "Draft the core argument.", J_TUTORIAL)
session(t_stats, -12, 16, 30, [("focused", 22), ("distracted", 6), ("focused", 13)],
        "One past paper for the stats final.")
session(t_chapter, -11, 9, 40, deep(21, 38), "Second half of section 3.2.")
session(t_chapter, -9, 14, 50, choppy(13, 12, 11), "Push through the slow afternoon.", J_DRIFT)
session(t_figures, -7, 14, 15, [("focused", 24), ("distracted", 5), ("focused", 9)],
        "Rough versions of figures 4-6.")
session(t_chapter, -6, 9, 15, deep(22, 39), "Rewrite 3.3 with the new citations.", J_RESEARCH)
session(t_chapter, -4, 10, 0, deep(16, 31), "Address the advisor's margin notes.")
session(t_figures, -4, 15, 30, light(23))
session(t_meals, -3, 17, 20, [("focused", 21), ("distracted", 4)], "Batch-cook plan for the week.")
session(t_chapter, -2, 9, 0, deep(11, 62), "One section, one sitting.", J_BEST)
session(t_portfolio, -1, 10, 30, deep(15, 33), "Rewrite the portfolio intro.")
session(t_figures, -1, 15, 10, [("focused", 26), ("uncertain", 4)])
_today_start = max(NOW_LOCAL - timedelta(minutes=70),
                   NOW_LOCAL.replace(hour=0, minute=15, second=0, microsecond=0))
session(t_chapter, 0, 0, 0, deep(14, 31), "Morning block before the demo.",
        journal((0, "note", "Coffee, phone away, straight into 3.4."),
                (28, "note", "Good start — stopping while it's still going well.")),
        start=_today_start.astimezone(timezone.utc))
db.flush()

DIFFS = {t_chapter.id: "hard", t_figures.id: "medium", t_outline.id: "medium",
         t_stats.id: "medium", t_portfolio.id: "medium", t_reading.id: "easy",
         t_meals.id: "easy"}


def local_start_min(s):
    local = s.started_at.astimezone(LOCAL_TZ)
    return local.hour * 60 + local.minute


def seed_plan_day(offset, tweaks=None):
    tweaks = tweaks or {}
    todays = sessions_by_offset.get(offset, [])
    entries, rows = [], []
    planned_total = actual_total = focused_total = 0
    seen = []
    for s in sorted(todays, key=lambda x: x.started_at):
        if s.task_id in seen:
            continue
        seen.append(s.task_id)
        task_sessions = [x for x in todays if x.task_id == s.task_id]
        actual = sum(round(((x.ended_at - x.started_at).total_seconds()) / 60) for x in task_sessions)
        focused = round(sum(x.seconds_focused or 0 for x in task_sessions) / 60)
        est_delta, start_delta = tweaks.get(s.task_id, (0, 0))
        planned = max(15, actual - est_delta)
        planned_start = local_start_min(s) - start_delta
        entries.append({"task_id": s.task_id, "name": s.task_name,
                        "estimate_min": planned, "difficulty": DIFFS.get(s.task_id, "medium"),
                        "scheduled_min": planned_start})
        planned_total += planned
        actual_total += actual
        focused_total += focused
        rows.append(schemas.PlanRealityRow(
            task_id=s.task_id, name=s.task_name,
            planned_start_min=planned_start, planned_estimate_min=planned,
            actual_start_min=local_start_min(s), actual_total_min=actual,
            actual_focused_min=focused, start_delta_min=start_delta,
            duration_delta_min=actual - planned,
            session_ids=[x.id for x in task_sessions],
            status=crud._seed_row_status(True, start_delta, actual - planned),
        ))
    pieces = [f"Planned {planned_total}m; tracked {actual_total}m"]
    ran_long = sum(1 for r in rows if r.status == "ran_long")
    if ran_long:
        pieces.append(f"{ran_long} task{'s' if ran_long != 1 else ''} ran long")
    report = schemas.PlanRealityReport(
        period_key=day_key(offset), has_plan=True,
        planned_total_min=planned_total, actual_total_min=actual_total,
        focused_total_min=focused_total, rows=rows, summary=". ".join(pieces) + ".",
    )
    db.add(models.DailyPlan(
        workspace_id=ws.id, period_key=day_key(offset),
        available_min=planned_total + 30, plan_json=json.dumps(entries),
    ))
    return json.dumps(report.model_dump())


plan_reality = {
    -6: seed_plan_day(-6),
    -4: seed_plan_day(-4, {t_chapter.id: (15, 0)}),
    -2: seed_plan_day(-2, {t_chapter.id: (20, 0)}),
    -1: seed_plan_day(-1, {t_portfolio.id: (0, 25)}),
}

def wp(kind, period_key, secs, ended_at, reflection="", recap=None, plan_reality_json=""):
    db.add(models.WorkPeriod(
        workspace_id=ws.id, kind=kind, period_key=period_key, ended_at=ended_at,
        seconds_focused=secs["focused"], seconds_distracted=secs["distracted"],
        seconds_uncertain=secs["uncertain"], seconds_away=secs["away"],
        reflection=reflection, ai_recap=json.dumps(recap) if recap else "",
        plan_reality_json=plan_reality_json,
    ))


daily_seed = {
    -6: ("Kept the morning block clean and stopped before it frayed.",
         {"summary": "Today was 84% focused — a clean morning block on the chapter carried the day.",
          "plan_echo": "Planned 95m; tracked close to it, with the chapter getting the deep slot.",
          "win": "You caught the 22-minute mark wobble and came straight back instead of drifting off.",
          "pattern_notes": ["The 9am start held again — that's four mornings in a row it's worked."],
          "advice": ["Since 3.3 opened cleanly, you might start tomorrow in the same section rather than warming up elsewhere."],
          "next_action": "When you sit down tomorrow, you could open the chapter doc before anything else.",
          "shutdown_question": "What's the one sentence you'd tell tomorrow-you about where 3.3 stands?"}),
    -4: ("Advisor notes were heavier than expected but I got through most of them.",
         {"summary": "A split day — 78% focused across the chapter revisions and a lighter figures block.",
          "plan_echo": "The chapter ran about 15 minutes past its estimate — worth padding revision passes.",
          "win": "You switched to the figures when the revision energy dipped instead of forcing it.",
          "pattern_notes": ["Revision passes keep running past their estimates — third time this week."],
          "advice": ["You might estimate revision at 1.5x drafting time; the pattern is consistent."],
          "next_action": "After lunch tomorrow, you could start with the lightest remaining margin note.",
          "shutdown_question": "Which margin note can wait until the final pass?"}),
    -2: ("Best day this month. One section, one sitting.",
         {"summary": "Your longest unbroken stretch this month — 73 minutes on the chapter, right in the 9am window.",
          "plan_echo": "It ran past the plan, and that overrun was the good kind — you rode the momentum.",
          "win": "Phone in the other room before you started; the journal shows zero pull toward it.",
          "pattern_notes": ["Your best blocks keep landing in the first two hours of the day."],
          "advice": [],
          "next_action": "When you plan tomorrow, you could give the 9am slot to whatever scares you most.",
          "shutdown_question": "What made today's setup different, in one line?"}),
    -1: ("Portfolio morning, figures afternoon. Solid, unglamorous.",
         {"summary": "Two medium blocks, 76% focused — the portfolio intro finally reads like you.",
          "plan_echo": "You started the portfolio about 25 minutes late, then held the block once in.",
          "win": "You finished the figures pass even after the late start compressed the afternoon.",
          "pattern_notes": [],
          "advice": ["A 5-minute setup ritual before the first block might close that late-start gap."],
          "next_action": "After breakfast tomorrow, you could open the day's first task before checking anything else.",
          "shutdown_question": "What's left on the portfolio that actually matters before it ships?"}),
    -9: ("Rough afternoon — two Instagram drifts before I found any rhythm.", None),
    -13: ("The argument finally clicked. Wrote past dinner.", None),
}
for off, (reflection, recap) in daily_seed.items():
    key = day_key(off)
    if key in day_secs:
        wp("day", key, day_secs[key], at(off, 21), reflection, recap,
           plan_reality_json=plan_reality.get(off, ""))

weekly_seed = [
    {"summary": "You held the thesis rhythm and the mornings did the heavy lifting again.",
     "theme": "Mornings carry it",
     "insights": ["Every 9am block this week went 45+ minutes clean.",
                  "The one rough patch was Thursday afternoon — and you still salvaged 36 minutes."],
     "improvements": [],
     "next_week_focus": "Keep the 9am slot sacred and let afternoons be lighter on purpose."},
    {"summary": "A dip midweek, but you returned the next morning instead of letting it slide into a slump.",
     "theme": "The comeback week",
     "insights": ["Two Instagram drifts on Wednesday, then your cleanest Thursday this month.",
                  "Evening reading held steady even on the rough days."],
     "improvements": ["Afternoon blocks might start with a 2-minute phone-away ritual."],
     "next_week_focus": "Protect the first ten minutes of afternoon blocks — that's where the drifts start."},
    {"summary": "Your strongest week of the month — two long unbroken blocks and the project submitted.",
     "theme": "Shipping week",
     "insights": ["The final project push ran three mornings back-to-back without a bad day.",
                  "You stopped sessions on your own terms four times — no burnout tail."],
     "improvements": [],
     "next_week_focus": "Carry the submission momentum straight into chapter 3."},
    {"summary": "Steady, unglamorous progress — the drafting rhythm is becoming routine.",
     "theme": "Quiet consistency",
     "insights": ["Focus rate climbed for the third straight week.",
                  "Your session starts are clustering at 9-10am — the habit is forming itself."],
     "improvements": [],
     "next_week_focus": "Try one deliberate deep block on the hardest open section."},
    {"summary": "A lighter week, and that's fine — the streak of morning starts survived intact.",
     "theme": "Holding the line",
     "insights": ["Even the short days opened with a real focused stretch."],
     "improvements": ["The stats final is drifting — a single weekly block would keep it warm."],
     "next_week_focus": "One stats session, any length, before the weekend."},
]
this_monday = monday_key(0)
past_mondays = sorted({k for k in week_secs if k < this_monday}, reverse=True)
for i, mk in enumerate(past_mondays[:5]):
    end = datetime.strptime(mk, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ) + timedelta(days=6, hours=21)
    recap = dict(weekly_seed[i % len(weekly_seed)])
    recap["pomodoro"] = {"recommend": False}
    recap["habit"] = {"propose": False}
    wp("week", mk, week_secs[mk], end.astimezone(timezone.utc), recap=recap)

prior_mk = month_key(-60)
if prior_mk in month_secs:
    wp("month", prior_mk, month_secs[prior_mk], at(-50, 21),
       recap={"summary": "An uneven month — finals fractured the schedule, and focus came in short bursts between exams.",
              "theme": "Surviving finals",
              "insights": ["Morning sessions stayed cleaner than afternoons even at the worst of it.",
                          "Most drifts were social feeds during afternoon slumps, not the work being too hard."],
              "improvements": ["Once exams end, longer uninterrupted blocks should come back quickly."],
              "carry_forward": "Protect the first morning hour — it survived finals; build on it."})

db.add(models.Habit(
    workspace_id=ws.id, code=f"coach-{monday_key(-42)}",
    title="Complete 25 focused minutes",
    why="A small daily block keeps the trail moving even on heavy weeks.",
    kind="auto", check_json=json.dumps({"template": "focus-minutes", "params": {"min": 25}}),
    source="coach", status="active", created_day_key=day_key(-42),
))
db.add(models.Habit(
    workspace_id=ws.id, code="cat-before-10",
    title="Start something before 10:00",
    why="An early first session sets the tone before the day gets loud.",
    kind="auto", check_json=json.dumps({"template": "session-before", "params": {"time": "10:00"}}),
    source="catalog", status="active", created_day_key=day_key(-25),
))
manual = models.Habit(
    workspace_id=ws.id, code="cat-phone-away",
    title="Put the phone in another room before starting",
    why="Distance beats willpower — you tick this one yourself.",
    kind="manual", check_json=None, source="catalog", status="active",
    created_day_key=day_key(-12),
)
db.add(manual)
retired = models.Habit(
    workspace_id=ws.id, code="cat-cold-showers",
    title="Cold shower before the first block",
    why="An experiment from finals season.",
    kind="manual", check_json=None, source="catalog", status="retired",
    created_day_key=day_key(-50),
)
db.add(retired)
db.flush()
for off in (-11, -8, -6, -3, -1):
    db.add(models.HabitCheck(workspace_id=ws.id, habit_id=manual.id,
                             day_key=day_key(off), source="manual"))
for off in (-48, -46, -44, -41):
    db.add(models.HabitCheck(workspace_id=ws.id, habit_id=retired.id,
                             day_key=day_key(off), source="manual"))

db.add(models.DailyPlan(
    workspace_id=ws.id, period_key=day_key(0), available_min=195,
    plan_json=json.dumps([
        {"task_id": t_chapter.id, "name": t_chapter.name, "estimate_min": 90,
         "difficulty": "hard", "scheduled_min": 9 * 60},
        {"task_id": t_stats.id, "name": t_stats.name, "estimate_min": 45,
         "difficulty": "medium", "scheduled_min": 14 * 60},
        {"task_id": t_portfolio.id, "name": t_portfolio.name, "estimate_min": 30,
         "difficulty": "easy", "scheduled_min": 16 * 60},
    ]),
))

HOURLY = {8: 84, 9: 91, 10: 87, 11: 78, 12: 55, 13: 52, 14: 58, 15: 62,
          16: 60, 17: 57, 20: 68, 21: 64}
for hour, pct in HOURLY.items():
    db.add(models.HourlyFocus(workspace_id=ws.id, hour=hour, focus_pct=float(pct),
                              sessions=5 if 8 <= hour <= 11 else 3))
for text, aff, rej in [
    ("Mornings start clean and hold focus best.", 4, 0),
    ("Tutorial videos don't derail you — social feeds do.", 3, 0),
    ("You recover quickly after catching a drift instead of spiraling.", 3, 1),
    ("Estimates for revision passes tend to run short.", 1, 0),
    ("Evening reading sessions stay calm even after rough days.", 1, 0),
]:
    db.add(models.Observation(workspace_id=ws.id, text=text, affirmations=aff,
                              rejections=rej, active=True))

db.commit()
print(f"Seeded into {DB_PATH}:")
print(f"  goals: {db.query(models.Goal).count()}   tasks: {db.query(models.Task).count()}   "
      f"sessions: {db.query(models.FocusSession).count()}")
print(f"  work periods: {db.query(models.WorkPeriod).count()}   "
      f"habits: {db.query(models.Habit).count()}   daily plans: {db.query(models.DailyPlan).count()}")
print(f"  lifetime focused ~ {total_focused_min} min (league ratchets on first load)")
for mk in sorted(month_secs):
    tot = sum(month_secs[mk].values())
    print(f"  {mk}: {round(100 * month_secs[mk]['focused'] / tot)}% focused over {round(tot / 3600, 1)}h")
print("Start the backend against it with:")
print('  $env:DATABASE_URL = "sqlite:///./focus-demo-full.db"; uvicorn backend.main:app --reload')
print("Frontend as usual (frontend folder):  python -m http.server 5500")
db.close()
