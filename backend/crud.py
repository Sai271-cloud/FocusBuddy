import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from . import models, schemas

DEFAULT_WORKSPACE_SLUG = "local"
DEFAULT_WORKSPACE_ID = 1
CURRENT_DEMO_SEED_VERSION = 9
DEMO_TODAY_KEY = "2026-06-28"
DEMO_HISTORY_DATES = [
    "2026-06-22",
    "2026-06-23",
    "2026-06-24",
    "2026-06-25",
    "2026-06-26",
    "2026-06-27",
]

DEMO_PERSONA_SEEDS = [
    {
        "slug": "early-morning",
        "display_name": "Early Morning",
        "archetype": "Focused early, fades late",
        "about": "",
        "tasks": [
            ("Morning calculus review", "Best done before lunch while attention is high."),
            ("Biology flashcards", "Spaced repetition for the quiz."),
            ("English outline", "Draft the structure before writing."),
            ("Evening inbox cleanup", "Low-energy admin work."),
        ],
        "observations": [
            ("Morning sessions usually start clean and stay focused.", 3, 0),
            ("Evening study tends to fade after the first short block.", 2, 0),
            ("Admin tasks fit better after energy dips.", 2, 1),
        ],
        "hourly": {7: 92, 8: 94, 9: 90, 10: 86, 11: 78, 18: 38, 19: 32, 20: 26},
        "days": [
            (0, [(0, 8, 10, 42, 7, 2, 0), (1, 19, 0, 20, 14, 4, 2)], "The morning calculus block was the clear focus window; the 7pm review faded once fatigue showed up."),
            (1, [(2, 8, 30, 36, 5, 2, 0), (1, 18, 45, 18, 16, 5, 1)], "The 8:30am outline carried the day, while the later flashcards needed a much smaller target."),
            (2, [(0, 7, 50, 48, 6, 1, 0), (3, 20, 0, 15, 17, 6, 2)], "Calculus before school landed in the strongest window; 8pm inbox cleanup was intentionally low-energy."),
            (3, [(2, 8, 20, 40, 8, 3, 0), (1, 19, 20, 16, 18, 5, 1)], "The morning outline was steady, and the 7:20pm block showed the usual late-day drop-off."),
            (4, [(0, 8, 0, 44, 4, 2, 0), (2, 18, 30, 22, 13, 4, 1)], "Putting the hardest task at 8am was the strongest move; the evening task stayed intentionally lighter."),
            (5, [(1, 9, 0, 35, 7, 2, 0), (3, 19, 15, 18, 15, 5, 2)], "The day stayed workable because the real focus work happened before lunch and evening expectations stayed small."),
        ],
    },
    {
        "slug": "doomscroller",
        "display_name": "Doomscroller",
        "archetype": "Predictable social-scroll loop",
        "about": "",
        "tasks": [
            ("Essay intro draft", "Needs one uninterrupted writing pass."),
            ("Statistics problem set", "Hardest class this week."),
            ("Scroll blocker setup", "Turn on blockers before work blocks."),
            ("Research notes", "Collect sources without drifting."),
        ],
        "observations": [
            ("Social sites appear right after a hard step.", 4, 0),
            ("A blocker before the session reduces the scroll loop.", 3, 0),
            ("Recovery is faster when the phone is out of reach.", 2, 0),
        ],
        "hourly": {9: 72, 10: 68, 11: 60, 13: 48, 14: 42, 15: 39, 20: 36},
        "days": [
            (0, [(0, 9, 10, 24, 20, 3, 0), (3, 14, 0, 22, 18, 4, 0)], "Focus started fine, then Instagram opened right after the first hard paragraph."),
            (1, [(1, 10, 0, 26, 22, 2, 0), (2, 15, 10, 30, 7, 2, 0)], "The blocker setup was the turning point; the second block recovered faster."),
            (2, [(3, 9, 30, 28, 16, 3, 0), (0, 13, 40, 20, 23, 4, 0)], "Reddit and YouTube clustered around research decisions, not boredom."),
            (3, [(2, 8, 50, 34, 6, 2, 0), (1, 14, 20, 24, 19, 4, 0)], "Starting with the blocker changed the morning; skipping it made stats harder later."),
            (4, [(0, 9, 0, 31, 12, 3, 0), (3, 15, 0, 21, 21, 5, 0)], "The writing block held until the phone came back onto the desk."),
            (5, [(2, 10, 15, 32, 5, 2, 0), (1, 13, 30, 25, 17, 3, 0)], "The cleanest block began with the blocker already running."),
        ],
    },
    {
        "slug": "overplanner",
        "display_name": "Overplanner",
        "archetype": "Too many tasks, low estimates",
        "about": "",
        "tasks": [
            ("Chemistry lab writeup", "Needs careful formatting."),
            ("History reading", "Long chapter with notes."),
            ("Club email batch", "Shallow admin."),
            ("Spanish practice", "Short speaking drill."),
            ("Physics worksheet", "Usually takes longer than expected."),
        ],
        "observations": [
            ("Plans often include more work than the available time can hold.", 4, 0),
            ("Estimates run long on writing and problem sets.", 3, 0),
            ("A buffer after the first task prevents the day from cascading.", 2, 0),
        ],
        "hourly": {8: 70, 9: 76, 10: 73, 11: 66, 13: 61, 14: 58, 16: 52},
        "days": [
            (0, [(0, 8, 45, 38, 9, 3, 0), (1, 13, 0, 42, 10, 4, 0), (2, 16, 30, 16, 7, 2, 0)], "Three tasks moved, but the plan had five; the estimates were the bottleneck."),
            (1, [(4, 9, 0, 50, 8, 3, 0), (3, 15, 15, 18, 5, 1, 0)], "Physics ran long again, which squeezed the lighter work."),
            (2, [(0, 8, 30, 44, 6, 2, 0), (1, 13, 30, 35, 12, 3, 0)], "The day improved when the task list got shorter."),
            (3, [(1, 9, 20, 46, 11, 3, 0), (2, 16, 0, 20, 8, 2, 0)], "Reading needed more time than planned, but the admin batch fit well after it."),
            (4, [(4, 8, 50, 47, 10, 2, 0), (0, 14, 15, 35, 11, 2, 0)], "The hard work was real; the plan needed a buffer, not more tasks."),
            (5, [(3, 10, 0, 22, 4, 1, 0), (2, 13, 0, 25, 6, 2, 0)], "A lighter Saturday plan finally matched the available attention."),
        ],
    },
    {
        "slug": "night-owl",
        "display_name": "Night Owl",
        "archetype": "Slow start, stronger later",
        "about": "",
        "tasks": [
            ("AP literature annotations", "Deep reading work."),
            ("Algebra practice", "Problem solving."),
            ("Morning warm-up review", "Low-pressure starting task."),
            ("Project presentation slides", "Creative work that fits later blocks."),
        ],
        "observations": [
            ("Late afternoon and evening sessions are usually stronger.", 3, 0),
            ("Morning blocks need a small warm-up before hard work.", 2, 0),
            ("Creative work fits later energy better than early drills.", 2, 0),
        ],
        "hourly": {8: 34, 9: 39, 10: 44, 15: 70, 16: 80, 17: 87, 18: 84, 19: 78},
        "days": [
            (0, [(2, 9, 0, 18, 16, 4, 0), (0, 17, 0, 42, 6, 2, 0)], "The 9am warm-up was shaky, but the 5pm literature block was the strongest part."),
            (1, [(1, 10, 0, 22, 15, 3, 0), (3, 16, 30, 45, 5, 2, 0)], "The morning algebra block dragged; slides clicked once the later focus window opened."),
            (2, [(2, 8, 45, 20, 14, 4, 0), (1, 17, 15, 40, 7, 2, 0)], "Algebra worked much better after school than in the early warm-up block."),
            (3, [(0, 9, 30, 24, 13, 3, 0), (3, 18, 0, 47, 5, 1, 0)], "The 6pm creative block had the clearest attention after the slow morning start."),
            (4, [(2, 10, 15, 25, 9, 2, 0), (0, 17, 30, 44, 6, 2, 0)], "Starting gently helped, but late-day reading still carried the day."),
            (5, [(1, 11, 0, 28, 10, 2, 0), (3, 18, 20, 46, 5, 1, 0)], "The strongest focus kept showing up in the evening after the day had warmed up."),
        ],
    },
    {
        "slug": "self-improver",
        "display_name": "Self Improver",
        "archetype": "Messy start, visible recovery",
        "about": "",
        "tasks": [
            ("Coding practice", "Build one small feature."),
            ("Reading notes", "Summarize the chapter."),
            ("Focus reset routine", "Write intention, clear desk, start timer."),
            ("Math corrections", "Review mistakes slowly."),
        ],
        "observations": [
            ("Writing a clear intention improves the first ten minutes.", 3, 0),
            ("Recovery after distractions is getting faster.", 3, 0),
            ("Short reset routines help more than longer planning.", 2, 0),
        ],
        "hourly": {9: 50, 10: 58, 11: 63, 13: 62, 14: 68, 15: 72, 16: 75},
        "days": [
            (0, [(0, 9, 0, 18, 25, 5, 0), (1, 14, 0, 20, 20, 4, 0)], "The week opened messy, with distractions taking over after each hard start."),
            (1, [(2, 9, 30, 24, 10, 3, 0), (0, 14, 30, 26, 16, 3, 0)], "The reset routine helped the first block, even though coding still drifted."),
            (2, [(0, 10, 0, 32, 12, 3, 0), (3, 15, 0, 30, 10, 2, 0)], "Recovery got faster; slips were shorter and the work resumed."),
            (3, [(2, 9, 0, 28, 6, 2, 0), (1, 13, 45, 35, 9, 2, 0)], "A written intention gave the day a cleaner start."),
            (4, [(0, 10, 15, 38, 8, 2, 0), (3, 15, 30, 34, 7, 2, 0)], "The improvement was visible: fewer long drifts and faster returns."),
            (5, [(2, 9, 30, 30, 5, 1, 0), (0, 14, 0, 42, 6, 1, 0)], "By Saturday the reset routine became a repeatable skill, not a rescue move."),
        ],
    },
]

def _seed_by_slug(slug: str) -> dict | None:
    return next((seed for seed in DEMO_PERSONA_SEEDS if seed["slug"] == slug), None)

def _clean_anonymous_id(raw: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", (raw or "").strip())[:80]
    return clean or "browser"

def ensure_default_workspace(db: Session) -> models.DemoWorkspace:
    workspace = db.get(models.DemoWorkspace, DEFAULT_WORKSPACE_ID)
    if workspace is None:
        workspace = models.DemoWorkspace(
            id=DEFAULT_WORKSPACE_ID,
            slug=DEFAULT_WORKSPACE_SLUG,
            display_name="Local workspace",
            archetype="Local development",
            workspace_type="local",
            seed_version=0,
        )
        db.add(workspace)
        try:
            db.commit()
            db.refresh(workspace)
        except IntegrityError:
            db.rollback()
            workspace = db.get(models.DemoWorkspace, DEFAULT_WORKSPACE_ID)
    return workspace

def _workspace_id(db: Session, workspace=None) -> int:
    if workspace is None:
        return ensure_default_workspace(db).id
    if isinstance(workspace, int):
        return workspace
    return workspace.id

def get_workspace_by_slug(db: Session, slug: str) -> models.DemoWorkspace | None:
    return db.query(models.DemoWorkspace).filter(models.DemoWorkspace.slug == slug).first()

def _private_seeded_slug(slug: str, anonymous_id: str) -> str:
    return f"{slug}--{_clean_anonymous_id(anonymous_id)}"

def ensure_seeded_workspace(
    db: Session, slug: str, anonymous_id: str | None = None
) -> models.DemoWorkspace | None:
    seed = _seed_by_slug(slug)
    if seed is None:
        return None
    workspace_slug = _private_seeded_slug(slug, anonymous_id) if anonymous_id else slug
    workspace = get_workspace_by_slug(db, workspace_slug)
    if (
        workspace is None
        or workspace.workspace_type != "seeded"
        or workspace.seed_version != CURRENT_DEMO_SEED_VERSION
    ):
        workspace = reset_seeded_workspace(db, slug, anonymous_id)
    return workspace

def ensure_anonymous_workspace(db: Session, anonymous_id: str) -> models.DemoWorkspace:
    clean = _clean_anonymous_id(anonymous_id)
    slug = f"anon-{clean}"
    workspace = get_workspace_by_slug(db, slug)
    if workspace is None:
        workspace = models.DemoWorkspace(
            slug=slug,
            display_name="My blank demo",
            archetype="Blank judge experiment",
            workspace_type="anonymous",
            seed_version=0,
        )
        db.add(workspace)
        try:
            db.commit()
            db.refresh(workspace)
            seed_hourly_focus(db, workspace)
        except IntegrityError:
            db.rollback()
            workspace = get_workspace_by_slug(db, slug)
    return workspace

def resolve_demo_workspace(
    db: Session,
    demo_slug: str | None = None,
    anonymous_id: str | None = None,
) -> models.DemoWorkspace | None:
    if demo_slug and anonymous_id:
        # Per-judge private copy of a seeded persona.
        return ensure_seeded_workspace(db, demo_slug, anonymous_id)
    if anonymous_id:
        return ensure_anonymous_workspace(db, anonymous_id)
    if demo_slug:
        # Slug-only fallback: the shared seeded workspace (old links, blocked localStorage).
        return ensure_seeded_workspace(db, demo_slug)
    return ensure_default_workspace(db)

def create_task(db: Session, task: schemas.TaskCreate, workspace=None) -> models.Task:
    wid = _workspace_id(db, workspace)
    db_task = models.Task(
        workspace_id=wid,
        name=task.name.strip(),
        description=(task.description or "").strip(),
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task(db: Session, task_id: int, workspace=None) -> models.Task | None:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.workspace_id == wid)
        .first()
    )

def get_tasks(db: Session, workspace=None) -> list[models.Task]:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Task)
        .filter(models.Task.workspace_id == wid)
        .order_by(models.Task.created_at.desc())
        .all()
    )

def update_task(db: Session, db_task: models.Task, update: schemas.TaskUpdate, completed_at=None) -> models.Task:
    from datetime import datetime, timezone

    if update.completed is not None:
        db_task.completed = update.completed
        db_task.completed_at = (completed_at or datetime.now(timezone.utc)) if update.completed else None
    if update.name is not None:
        db_task.name = update.name.strip()
    if update.description is not None:
        db_task.description = update.description.strip()
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, db_task: models.Task) -> None:
    db.query(models.FocusSession).filter(
        models.FocusSession.workspace_id == db_task.workspace_id,
        models.FocusSession.task_id == db_task.id,
    ).delete()
    db.delete(db_task)
    db.commit()

def delete_session(db: Session, db_session: models.FocusSession) -> None:
    db.delete(db_session)
    db.commit()

def start_session(db: Session, task: models.Task, workspace=None, started_at=None) -> models.FocusSession:
    wid = _workspace_id(db, workspace)
    now = started_at or datetime.now(timezone.utc)
    db_session = models.FocusSession(
        workspace_id=wid,
        task_id=task.id,
        task_name=task.name,
        started_at=now,
        ended_at=now,
        seconds_focused=0,
        seconds_distracted=0,
        seconds_uncertain=0,
        seconds_away=0,
        timeline_json="[]",
        journal_json="[]",
        intention="",
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def create_session(
    db: Session,
    session: schemas.SessionCreate,
    task: models.Task,
    workspace=None,
) -> models.FocusSession:
    wid = _workspace_id(db, workspace)
    data = session.model_dump()
    data["workspace_id"] = wid
    data["task_name"] = task.name
    data["intention"] = (data.get("intention") or "").strip()[:240]
    db_session = models.FocusSession(**data)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def update_session(
    db: Session,
    db_session: models.FocusSession,
    update: schemas.SessionUpdate,
) -> models.FocusSession:
    from datetime import datetime, timezone

    db_session.ended_at = update.ended_at or datetime.now(timezone.utc)
    db_session.seconds_focused = update.seconds_focused
    db_session.seconds_distracted = update.seconds_distracted
    db_session.seconds_uncertain = update.seconds_uncertain
    db_session.seconds_away = update.seconds_away
    db_session.timeline_json = update.timeline_json
    db_session.journal_json = update.journal_json
    if update.intention is not None:
        db_session.intention = update.intention.strip()[:240]
    db.commit()
    db.refresh(db_session)
    return db_session

def get_sessions(db: Session, workspace=None) -> list[models.FocusSession]:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.FocusSession)
        .filter(models.FocusSession.workspace_id == wid)
        .order_by(models.FocusSession.ended_at.desc())
        .all()
    )

def get_sessions_between(db: Session, start, end, workspace=None) -> list[models.FocusSession]:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.FocusSession)
        .filter(
            models.FocusSession.workspace_id == wid,
            models.FocusSession.started_at >= start,
            models.FocusSession.started_at < end,
        )
        .order_by(models.FocusSession.started_at.asc(), models.FocusSession.id.asc())
        .all()
    )

def upsert_work_period(db: Session, data: schemas.WorkPeriodCreate, workspace=None) -> models.WorkPeriod:
    wid = _workspace_id(db, workspace)
    existing = (
        db.query(models.WorkPeriod)
        .filter(
            models.WorkPeriod.workspace_id == wid,
            models.WorkPeriod.kind == data.kind,
            models.WorkPeriod.period_key == data.period_key,
        )
        .first()
    )
    if existing is None:
        existing = models.WorkPeriod(workspace_id=wid, kind=data.kind, period_key=data.period_key)
        db.add(existing)

    existing.ended_at = data.ended_at
    existing.seconds_focused = data.seconds_focused
    existing.seconds_distracted = data.seconds_distracted
    existing.seconds_uncertain = data.seconds_uncertain
    existing.seconds_away = data.seconds_away
    if data.reflection is not None:
        existing.reflection = data.reflection
    if data.ai_recap is not None:
        existing.ai_recap = data.ai_recap
    if data.plan_reality_json is not None:
        existing.plan_reality_json = data.plan_reality_json
    db.commit()
    db.refresh(existing)
    return existing

def get_work_periods(db: Session, workspace=None) -> list[models.WorkPeriod]:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.WorkPeriod)
        .filter(models.WorkPeriod.workspace_id == wid)
        .order_by(models.WorkPeriod.ended_at.desc())
        .all()
    )

def get_recent_plan_reality_periods(db: Session, limit: int = 14, workspace=None) -> list[models.WorkPeriod]:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.WorkPeriod)
        .filter(
            models.WorkPeriod.workspace_id == wid,
            models.WorkPeriod.kind == "day",
            models.WorkPeriod.plan_reality_json.isnot(None),
            models.WorkPeriod.plan_reality_json != "",
        )
        .order_by(models.WorkPeriod.period_key.desc())
        .limit(max(1, min(int(limit or 14), 60)))
        .all()
    )

def get_plan(db: Session, period_key: str, workspace=None) -> models.DailyPlan | None:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.DailyPlan)
        .filter(models.DailyPlan.workspace_id == wid, models.DailyPlan.period_key == period_key)
        .first()
    )

def upsert_plan(db: Session, data: schemas.DailyPlanUpsert, workspace=None) -> models.DailyPlan:
    wid = _workspace_id(db, workspace)
    existing = get_plan(db, data.period_key, wid)
    if existing is None:
        existing = models.DailyPlan(workspace_id=wid, period_key=data.period_key)
        db.add(existing)
    if data.available_min is not None:
        existing.available_min = data.available_min
    if data.plan_json is not None:
        existing.plan_json = data.plan_json
    if data.advice_json is not None:
        existing.advice_json = data.advice_json
    existing.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(existing)
    return existing

def delete_plan(db: Session, period_key: str, workspace=None) -> bool:
    existing = get_plan(db, period_key, workspace)
    if existing is None:
        return False
    db.delete(existing)
    db.commit()
    return True

def get_profile(db: Session, workspace=None) -> models.UserProfile:
    """The workspace's 'About me' row, created empty on first access."""
    wid = _workspace_id(db, workspace)
    profile = db.query(models.UserProfile).filter(models.UserProfile.workspace_id == wid).first()
    if profile is None:
        profile = models.UserProfile(workspace_id=wid, about="")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

def update_profile(db: Session, about: str, workspace=None) -> models.UserProfile:
    profile = get_profile(db, workspace)
    profile.about = (about or "").strip()[:1000]
    db.commit()
    db.refresh(profile)
    return profile

# ---- The League (Trail Chunk 2) ----
# Traveler ranks driven by lifetime focused minutes, uncapped. Each rank name has
# 3 levels; one level costs a fixed step of minutes, and the step DOUBLES each
# time the rank name changes (Wanderer 300/level, Walker 600, ... Cartographer 9,600).

LEAGUE_RANKS = ["Wanderer", "Walker", "Pathfinder", "Trailblazer", "Voyager", "Cartographer"]
LEAGUE_FIRST_STEP_MIN = 300
LEAGUE_LEVELS_PER_RANK = 3

def league_ladder() -> list:
    """Every level in order with the points total where it begins, generated from
    the doubling rule: [{rank, level, start}, ...] — Wanderer 1 starts at 0."""
    ladder = []
    start = 0
    step = LEAGUE_FIRST_STEP_MIN
    for rank in LEAGUE_RANKS:
        for level in range(1, LEAGUE_LEVELS_PER_RANK + 1):
            ladder.append({"rank": rank, "level": level, "start": start})
            start += step
        step *= 2
    return ladder

def rank_for_points(points_min: int) -> tuple:
    """(rank_name, level, level_progress 0..1) for a points total. Progress is
    within the current level; the summit (Cartographer 3) pins at 1.0."""
    points = max(0, int(points_min or 0))
    ladder = league_ladder()
    current_index = 0
    for i, row in enumerate(ladder):
        if points >= row["start"]:
            current_index = i
    current = ladder[current_index]
    if current_index + 1 >= len(ladder):
        return current["rank"], current["level"], 1.0
    span = ladder[current_index + 1]["start"] - current["start"]
    progress = (points - current["start"]) / span
    return current["rank"], current["level"], round(min(1.0, max(0.0, progress)), 4)

def compute_league_points(db: Session, workspace=None) -> int:
    """Lifetime focused minutes across the workspace's saved sessions — a plain
    aggregate, no local-day or timezone math."""
    wid = _workspace_id(db, workspace)
    total_seconds = (
        db.query(func.coalesce(func.sum(models.FocusSession.seconds_focused), 0))
        .filter(models.FocusSession.workspace_id == wid)
        .scalar()
    )
    return int(total_seconds or 0) // 60

def ratchet_league(db: Session, workspace=None) -> tuple:
    """Write max(stored, computed) league points — points only ever increase, so
    the league structurally cannot demote (deleting sessions keeps the credit,
    and a lost store self-heals from history). Returns (points, stored_before)."""
    profile = get_profile(db, workspace)
    stored_before = int(profile.league_points or 0)
    points = max(stored_before, compute_league_points(db, workspace))
    if points != stored_before:
        profile.league_points = points
        db.commit()
        db.refresh(profile)
    return points, stored_before

# --- landmarks (Trail Chunk 5) ---------------------------------------------
# The whitelist of earnable landmark codes. The FRONTEND detects these (it owns
# the local-day math); the backend only stores them, insert-only (the ratchet).

LANDMARK_CODES = frozenset([
    "first-camp",
    "first-daily-unwind",
    "first-weekly-unwind",
    "first-monthly-unwind",
    "first-plan",
    "unbroken-25",
    "deep-day",
    "camps-10",
    "camps-25",
    "camps-50",
    "camps-100",
    "plan-match",
    "streak-7",
])

def get_landmarks(db: Session, workspace=None) -> list:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Landmark)
        .filter(models.Landmark.workspace_id == wid)
        .order_by(models.Landmark.id)
        .all()
    )

def sync_landmarks(db: Session, items: list, workspace=None) -> tuple:
    """Store any not-yet-earned landmarks from `items` ([{code, day_key}] with
    codes already whitelisted by the route). Insert-only — nothing is ever
    updated or deleted, so re-syncs are idempotent and landmarks can't be lost.
    Returns (all_rows, newly_earned_codes, store_was_empty_before)."""
    wid = _workspace_id(db, workspace)
    existing = {row.code for row in get_landmarks(db, wid)}
    was_empty = not existing
    newly = []
    for item in items:
        if item.code in existing:
            continue
        db.add(models.Landmark(workspace_id=wid, code=item.code, day_key=item.day_key))
        try:
            db.commit()
            newly.append(item.code)
            existing.add(item.code)
        except IntegrityError:
            # A parallel request won the insert — their row is the same landmark.
            db.rollback()
            existing.add(item.code)
    return get_landmarks(db, wid), newly, was_empty

# --- habits (habit tracker v1) ---------------------------------------------
# Habits are adopted from the starter catalog or a weekly-unwind proposal. The
# FRONTEND verifies 'auto' habits from session/plan data (it owns local-day
# math); the backend stores habits + insert-only check rows, so the lifetime
# done count is a row count that only ever grows.

# Whitelist of machine-checkable templates. One source of truth shared by the
# adopt route and the weekly-unwind proposal parser (like LANDMARK_CODES).
HABIT_TEMPLATES = frozenset([
    "any-session",      # at least one session that day
    "focus-minutes",    # params {min: 5..240} — focused minutes that day
    "session-before",   # params {time: "HH:MM"} — a session started before HH:MM
    "unbroken-25",      # a 25-min unbroken focused run in some session that day
    "made-a-plan",      # a plan existed that day
    "did-daily-unwind", # the day was unwound (recap or reflection saved)
])

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

def clean_check_spec(template, params):
    """Validate + clamp one check spec. Returns a canonical {"template","params"}
    dict, or None when the template is unknown or the params are unusable — the
    caller then treats the habit as manual instead of rejecting it."""
    if template not in HABIT_TEMPLATES:
        return None
    params = params if isinstance(params, dict) else {}
    if template == "focus-minutes":
        try:
            minutes = int(params.get("min", 25))
        except (TypeError, ValueError):
            minutes = 25
        return {"template": template, "params": {"min": max(5, min(240, minutes))}}
    if template == "session-before":
        time_str = str(params.get("time", "")).strip()
        if not _HHMM_RE.match(time_str):
            return None
        return {"template": template, "params": {"time": time_str}}
    return {"template": template, "params": {}}

def clean_check_json(check_json):
    """Same validation for the JSON-string form stored on a habit row."""
    if not check_json:
        return None
    try:
        data = json.loads(check_json)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    spec = clean_check_spec(data.get("template"), data.get("params"))
    return json.dumps(spec) if spec else None

def get_habits(db: Session, workspace=None) -> list:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Habit)
        .filter(models.Habit.workspace_id == wid)
        .order_by(models.Habit.id)
        .all()
    )

def get_habit(db: Session, habit_id: int, workspace=None):
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Habit)
        .filter(models.Habit.id == habit_id, models.Habit.workspace_id == wid)
        .first()
    )

def get_habit_check_days(db: Session, workspace=None) -> dict:
    """All completed days for the workspace, as {habit_id: [day_key, ...]} sorted
    ascending — one query drives every habit's density dots + lifetime count."""
    wid = _workspace_id(db, workspace)
    rows = (
        db.query(models.HabitCheck.habit_id, models.HabitCheck.day_key)
        .filter(models.HabitCheck.workspace_id == wid)
        .order_by(models.HabitCheck.day_key)
        .all()
    )
    days = {}
    for habit_id, day_key in rows:
        days.setdefault(habit_id, []).append(day_key)
    return days

def adopt_habit(db: Session, data, workspace=None):
    """Create a habit, or reactivate the retired row with the same code — the
    (workspace, code) unique constraint makes a duplicate structurally
    impossible, so double-adopts and stale Adopt buttons are harmless. On
    reactivation the title/why/check refresh and `created_day_key` moves to the
    new adoption day, so auto-verification never backfills the retired gap."""
    wid = _workspace_id(db, workspace)
    check_json = clean_check_json(data.check_json) if data.kind == "auto" else None
    kind = data.kind if check_json or data.kind == "manual" else "manual"
    existing = (
        db.query(models.Habit)
        .filter(models.Habit.workspace_id == wid, models.Habit.code == data.code)
        .first()
    )
    if existing:
        if existing.status == "retired":
            existing.status = "active"
            existing.title = data.title
            existing.why = data.why
            existing.kind = kind
            existing.check_json = check_json
            existing.created_day_key = data.created_day_key
            db.commit()
            db.refresh(existing)
        return existing
    habit = models.Habit(
        workspace_id=wid,
        code=data.code,
        title=data.title,
        why=data.why,
        kind=kind,
        check_json=check_json,
        source=data.source,
        created_day_key=data.created_day_key,
    )
    db.add(habit)
    try:
        db.commit()
    except IntegrityError:
        # A parallel request won the insert — reuse their row.
        db.rollback()
        return (
            db.query(models.Habit)
            .filter(models.Habit.workspace_id == wid, models.Habit.code == data.code)
            .first()
        )
    db.refresh(habit)
    return habit

def retire_habit(db: Session, habit) -> None:
    habit.status = "retired"
    db.commit()
    db.refresh(habit)

def tick_day_allowed(workspace, day_key: str) -> bool:
    """Sanity bound for manual ticks: within ±1 day of the anchor date — the
    frozen demo date for demo workspaces, else the server's UTC date. ±1 covers
    every real timezone (UTC-12..+14) while making backfill scripting pointless.
    Pure string/date arithmetic; today-only stays a frontend rule."""
    anchor_key = (
        DEMO_TODAY_KEY
        if workspace is not None and getattr(workspace, "workspace_type", "local") != "local"
        else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    try:
        day = datetime.strptime(day_key, "%Y-%m-%d")
        anchor = datetime.strptime(anchor_key, "%Y-%m-%d")
    except ValueError:
        return False
    return abs((day - anchor).days) <= 1

def add_habit_check(db: Session, habit, day_key: str, source: str) -> bool:
    """Insert one completed day (insert-only). Returns True when a row was added;
    a duplicate (same habit + day) is swallowed as idempotent."""
    db.add(models.HabitCheck(
        workspace_id=habit.workspace_id,
        habit_id=habit.id,
        day_key=day_key,
        source=source,
    ))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False

def sync_habit_checks(db: Session, checks, workspace=None) -> int:
    """Store frontend-verified auto checks. Silently skips rows for habits that
    aren't this workspace's, aren't auto, are retired, or predate the habit's
    adoption day — the verifier is trusted but bounded. Insert-only per row."""
    wid = _workspace_id(db, workspace)
    habits = {h.id: h for h in get_habits(db, wid)}
    inserted = 0
    for item in checks:
        habit = habits.get(item.habit_id)
        if habit is None or habit.kind != "auto" or habit.status != "active":
            continue
        if item.day_key < habit.created_day_key:
            continue
        if add_habit_check(db, habit, item.day_key, "auto"):
            inserted += 1
    return inserted

MAX_ACTIVE_GOALS = 10

def get_goals(db: Session, workspace=None) -> list:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Goal)
        .filter(models.Goal.workspace_id == wid)
        .order_by(models.Goal.target_day_key.asc(), models.Goal.id.asc())
        .all()
    )

def get_goal(db: Session, goal_id: int, workspace=None):
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Goal)
        .filter(models.Goal.id == goal_id, models.Goal.workspace_id == wid)
        .first()
    )

def count_active_goals(db: Session, workspace=None) -> int:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Goal)
        .filter(models.Goal.workspace_id == wid, models.Goal.status == "active")
        .count()
    )

def create_goal(db: Session, data, workspace=None):
    wid = _workspace_id(db, workspace)
    goal = models.Goal(
        workspace_id=wid,
        title=data.title.strip(),
        target_day_key=data.target_day_key,
        created_day_key=data.created_day_key,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal

def update_goal(db: Session, goal, update) -> None:
    """Preserve-on-None: only sent fields change. Reopening (status back to
    'active') clears done_day_key so a reopened goal doesn't still claim a
    finish date; the active-goal cap on reopen is the ROUTE's job."""
    if update.title is not None:
        goal.title = update.title.strip()
    if update.target_day_key is not None:
        goal.target_day_key = update.target_day_key
    if update.status is not None:
        goal.status = update.status
        if update.status == "active":
            goal.done_day_key = None
    if update.done_day_key is not None:
        goal.done_day_key = update.done_day_key
    db.commit()
    db.refresh(goal)

def attach_task_to_goal(db: Session, goal, task) -> None:
    """Sets the link (a task already linked elsewhere moves silently — the UI
    only offers unlinked tasks, so this only happens via direct API use)."""
    task.goal_id = goal.id
    db.commit()

def detach_task_from_goal(db: Session, goal, task) -> None:
    """Clears the link only when it points at THIS goal (idempotent; a stale
    detach can't clobber another goal's link)."""
    if task.goal_id == goal.id:
        task.goal_id = None
        db.commit()

def goal_focus_seconds(db: Session, workspace=None) -> dict:
    """Lifetime focused seconds per goal, summed over sessions of attached tasks
    in ONE join query: {goal_id: seconds}. Goals with no attached work are absent."""
    wid = _workspace_id(db, workspace)
    rows = (
        db.query(models.Task.goal_id, func.sum(models.FocusSession.seconds_focused))
        .join(models.FocusSession, models.FocusSession.task_id == models.Task.id)
        .filter(
            models.Task.workspace_id == wid,
            models.Task.goal_id.isnot(None),
            models.FocusSession.workspace_id == wid,
        )
        .group_by(models.Task.goal_id)
        .all()
    )
    return {goal_id: int(total or 0) for goal_id, total in rows}

CONFIRM_NET = 2
RETIRE_NET = 2
MAX_ACTIVE_OBSERVATIONS = 20

SEED_OBSERVATIONS = [
    "Tends to drift within the first 10-15 minutes of a session",
    "Focus fades the longer a session runs",
    "Recovers focus quickly after a distraction",
]

def observation_status(obs: models.Observation) -> str:
    net = (obs.affirmations or 0) - (obs.rejections or 0)
    if not obs.active:
        return "retired"
    if net >= CONFIRM_NET:
        return "confirmed"
    return "emerging"

LEGACY_TIME_OBSERVATIONS = [
    "Focuses best in the morning",
    "Focuses best around midday",
    "Focuses best in the late afternoon or evening",
]

DECAY_DAYS = 30

def cleanup_legacy_time_observations(db: Session, workspace=None) -> int:
    """Remove the obsolete time-of-day seed patterns by exact text. Idempotent —
    after the first run nothing matches. Only the three known seed strings are
    targeted, so AI-made or user notes are never touched. Returns rows deleted."""
    q = db.query(models.Observation).filter(models.Observation.text.in_(LEGACY_TIME_OBSERVATIONS))
    if workspace is not None:
        q = q.filter(models.Observation.workspace_id == _workspace_id(db, workspace))
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return deleted

def decay_stale_observations(db: Session, days: int = DECAY_DAYS, workspace=None) -> int:
    """Erode confidence in notes not affirmed/rejected in `days`: move each stale
    note's net one step toward 0 (a confirmed note drifts back to emerging; a
    retired note can get another chance), then re-stamp updated_at so it only
    decays again after another `days` of inactivity. Reflects that habits change —
    old conclusions fade unless reinforced. Returns how many notes decayed."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    changed = 0
    q = db.query(models.Observation)
    if workspace is not None:
        q = q.filter(models.Observation.workspace_id == _workspace_id(db, workspace))
    for o in q.all():
        ts = o.updated_at
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            continue
        a, r = o.affirmations or 0, o.rejections or 0
        if a > r:
            o.affirmations = a - 1
        elif r > a:
            o.rejections = r - 1
        else:
            continue
        _apply_retire_rule(o)
        o.updated_at = now
        changed += 1
    db.commit()
    return changed

def seed_observations(db: Session, workspace=None) -> None:
    """Insert the starter hypotheses, but ONLY when the table is empty. Note: if the
    user deletes every observation and the app restarts, the starters come back —
    that's acceptable (it just restores neutral direction, never resurrects a single
    pattern the user removed while others remain)."""
    wid = _workspace_id(db, workspace)
    if db.query(models.Observation).filter(models.Observation.workspace_id == wid).count() > 0:
        return
    for text in SEED_OBSERVATIONS:
        db.add(models.Observation(workspace_id=wid, text=text))
    db.commit()

def list_observations(db: Session, active_only: bool = False, workspace=None) -> list[models.Observation]:
    wid = _workspace_id(db, workspace)
    q = db.query(models.Observation).filter(models.Observation.workspace_id == wid)
    if active_only:
        q = q.filter(models.Observation.active == True)  # noqa: E712
    return q.order_by(models.Observation.active.desc(), models.Observation.id.asc()).all()

def get_observation(db: Session, obs_id: int, workspace=None) -> models.Observation | None:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.Observation)
        .filter(models.Observation.id == obs_id, models.Observation.workspace_id == wid)
        .first()
    )

def _apply_retire_rule(obs: models.Observation) -> None:
    """Recompute active from the counts so an affirm can revive a retired pattern
    and a pile of rejections can retire one."""
    net = (obs.affirmations or 0) - (obs.rejections or 0)
    obs.active = (-net) < RETIRE_NET

def affirm_observation(db: Session, obs: models.Observation) -> models.Observation:
    from datetime import datetime, timezone

    obs.affirmations = (obs.affirmations or 0) + 1
    obs.updated_at = datetime.now(timezone.utc)
    _apply_retire_rule(obs)
    db.commit()
    db.refresh(obs)
    return obs

def reject_observation(db: Session, obs: models.Observation) -> models.Observation:
    from datetime import datetime, timezone

    obs.rejections = (obs.rejections or 0) + 1
    obs.updated_at = datetime.now(timezone.utc)
    _apply_retire_rule(obs)
    db.commit()
    db.refresh(obs)
    return obs

def create_observation(db: Session, text: str, workspace=None) -> models.Observation | None:
    """Add a new active pattern. Skips if the active count is already at the cap or
    a same-text active pattern already exists (cheap de-dup). Returns None if skipped."""
    wid = _workspace_id(db, workspace)
    clean = (text or "").strip()[:200]
    if not clean:
        return None
    active = list_observations(db, active_only=True, workspace=wid)
    if len(active) >= MAX_ACTIVE_OBSERVATIONS:
        return None
    if any(o.text.strip().lower() == clean.lower() for o in active):
        return None
    obs = models.Observation(workspace_id=wid, text=clean)
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs

def delete_observation(db: Session, obs: models.Observation) -> None:
    db.delete(obs)
    db.commit()

def seed_hourly_focus(db: Session, workspace=None) -> None:
    """Preboot all 24 hour rows (0-23) once, if the table is empty."""
    wid = _workspace_id(db, workspace)
    if db.query(models.HourlyFocus).filter(models.HourlyFocus.workspace_id == wid).count() > 0:
        return
    for h in range(24):
        db.add(models.HourlyFocus(workspace_id=wid, hour=h, focus_pct=0.0, sessions=0))
    db.commit()

def get_hourly_focus(db: Session, workspace=None) -> list[models.HourlyFocus]:
    wid = _workspace_id(db, workspace)
    return (
        db.query(models.HourlyFocus)
        .filter(models.HourlyFocus.workspace_id == wid)
        .order_by(models.HourlyFocus.hour.asc())
        .all()
    )

def _hours_in_range(start_hour: int, end_hour: int) -> list[int]:
    """Inclusive list of clock hours a session touched, handling midnight wrap
    (e.g. 23 -> 1 gives [23, 0, 1])."""
    start = start_hour % 24
    end = end_hour % 24
    hours = []
    h = start
    while True:
        hours.append(h)
        if h == end or len(hours) >= 24:
            break
        h = (h + 1) % 24
    return hours

def update_hourly_focus(db: Session, start_hour: int, end_hour: int, session_pct: float, workspace=None) -> int:
    """Fold one session's focus % into every hour it touched (running average).
    Returns how many hour rows were updated. Deterministic — no AI involved."""
    wid = _workspace_id(db, workspace)
    pct = max(0.0, min(100.0, float(session_pct)))
    touched = 0
    for h in _hours_in_range(start_hour, end_hour):
        row = db.get(models.HourlyFocus, (wid, h))
        if row is None:
            row = models.HourlyFocus(workspace_id=wid, hour=h, focus_pct=0.0, sessions=0)
            db.add(row)
        n = row.sessions or 0
        row.focus_pct = ((row.focus_pct or 0.0) * n + pct) / (n + 1)
        row.sessions = n + 1
        touched += 1
    db.commit()
    return touched

def _demo_dt(day_key: str, hour: int, minute: int = 0) -> datetime:
    y, m, d = [int(x) for x in day_key.split("-")]
    return datetime(y, m, d, hour, minute, tzinfo=timezone.utc)

def _timeline_json(focused_min: int, distracted_min: int, uncertain_min: int, away_min: int) -> str:
    runs = [
        ("focused", focused_min),
        ("distracted", distracted_min),
        ("uncertain", uncertain_min),
        ("away", away_min),
    ]
    minute = 0
    entries = []
    for state, length in runs:
        for _ in range(max(0, int(length))):
            entries.append({"minute": minute, "state": state})
            minute += 1
    return json.dumps(entries)

def _journal_json(summary: str, distracted_min: int) -> str:
    entries = [{"t": 0, "type": "note", "note": "Started with a clear task intention."}]
    if distracted_min >= 10:
        entries.append({"t": 12 * 60, "type": "site", "site": "instagram.com", "title": "Feed"})
        entries.append({"t": 18 * 60, "type": "note", "note": "Noticed the drift and came back to the task."})
    else:
        entries.append({"t": 15 * 60, "type": "note", "note": "Stayed with the main task after the first checkpoint."})
    entries.append({"t": 25 * 60, "type": "note", "note": summary})
    return json.dumps(entries)

def _seed_session_total_min(session: models.FocusSession) -> int:
    seconds = (
        (session.seconds_focused or 0)
        + (session.seconds_distracted or 0)
        + (session.seconds_uncertain or 0)
        + (session.seconds_away or 0)
    )
    return round(seconds / 60)

def _seed_session_start_min(session: models.FocusSession) -> int:
    return session.started_at.hour * 60 + session.started_at.minute

def _seed_plan_entries(seed: dict, tasks: list[models.Task], sessions: list[models.FocusSession]) -> list[dict]:
    entries = []
    seen_task_ids = set()
    slug = seed["slug"]
    difficulties = ["hard", "medium", "easy", "medium", "hard"]

    for order, session in enumerate(sorted(sessions, key=lambda s: (s.started_at, s.id or 0))):
        if session.task_id in seen_task_ids:
            continue
        seen_task_ids.add(session.task_id)
        actual_min = _seed_session_total_min(session)
        estimate = max(15, actual_min - 10) if slug == "overplanner" else actual_min
        entries.append({
            "task_id": session.task_id,
            "name": session.task_name or "",
            "estimate_min": estimate,
            "difficulty": difficulties[order % len(difficulties)],
            "scheduled_min": _seed_session_start_min(session),
        })

    if slug == "overplanner":
        next_slot = max(
            [entry["scheduled_min"] + entry["estimate_min"] for entry in entries] or [9 * 60]
        ) + 15
        for task in tasks:
            if task.id in seen_task_ids:
                continue
            estimate = 25 + (5 if len(entries) % 2 else 0)
            entries.append({
                "task_id": task.id,
                "name": task.name,
                "estimate_min": estimate,
                "difficulty": difficulties[len(entries) % len(difficulties)],
                "scheduled_min": min(next_slot, 21 * 60),
            })
            next_slot += estimate + 15

    return entries

def _seed_row_status(has_session: bool, start_delta: int | None, duration_delta: int) -> str:
    if not has_session:
        return "not_started"
    if start_delta is not None and start_delta >= 10:
        return "started_late"
    if start_delta is not None and start_delta <= -10:
        return "started_early"
    if duration_delta >= 10:
        return "ran_long"
    if duration_delta <= -10:
        return "ran_short"
    return "on_track"

def _seed_plan_reality_json(day_key: str, entries: list[dict], sessions: list[models.FocusSession]) -> str:
    by_task: dict[int, list[models.FocusSession]] = {}
    for session in sessions:
        by_task.setdefault(session.task_id, []).append(session)

    rows = []
    planned_total = 0
    actual_total = 0
    focused_total = 0
    planned_ids = {entry["task_id"] for entry in entries}

    for entry in entries:
        task_sessions = sorted(by_task.get(entry["task_id"], []), key=lambda s: (s.started_at, s.id or 0))
        planned = int(entry.get("estimate_min") or 0)
        planned_total += planned
        actual = sum(_seed_session_total_min(session) for session in task_sessions)
        focused = round(sum((session.seconds_focused or 0) for session in task_sessions) / 60)
        actual_total += actual
        focused_total += focused
        actual_start = _seed_session_start_min(task_sessions[0]) if task_sessions else None
        planned_start = entry.get("scheduled_min")
        start_delta = actual_start - planned_start if actual_start is not None and planned_start is not None else None
        duration_delta = actual - planned
        rows.append(schemas.PlanRealityRow(
            task_id=entry["task_id"],
            name=entry.get("name") or (task_sessions[0].task_name if task_sessions else ""),
            planned_start_min=planned_start,
            planned_estimate_min=planned,
            actual_start_min=actual_start,
            actual_total_min=actual,
            actual_focused_min=focused,
            start_delta_min=start_delta,
            duration_delta_min=duration_delta,
            session_ids=[session.id for session in task_sessions],
            status=_seed_row_status(bool(task_sessions), start_delta, duration_delta),
        ))

    for task_id, task_sessions in sorted(by_task.items(), key=lambda item: _seed_session_start_min(item[1][0])):
        if task_id in planned_ids:
            continue
        actual = sum(_seed_session_total_min(session) for session in task_sessions)
        focused = round(sum((session.seconds_focused or 0) for session in task_sessions) / 60)
        actual_total += actual
        focused_total += focused
        first = sorted(task_sessions, key=lambda s: (s.started_at, s.id or 0))[0]
        rows.append(schemas.PlanRealityRow(
            task_id=task_id,
            name=first.task_name or "Unplanned work",
            planned_estimate_min=0,
            actual_start_min=_seed_session_start_min(first),
            actual_total_min=actual,
            actual_focused_min=focused,
            duration_delta_min=actual,
            session_ids=[session.id for session in task_sessions],
            status="unscheduled_work",
        ))

    skipped = sum(1 for row in rows if row.status == "not_started")
    ran_long = sum(1 for row in rows if row.status == "ran_long")
    pieces = [f"Planned {planned_total}m; tracked {actual_total}m"]
    if skipped:
        pieces.append(f"{skipped} planned task{'s' if skipped != 1 else ''} not started")
    if ran_long:
        pieces.append(f"{ran_long} task{'s' if ran_long != 1 else ''} ran long")

    report = schemas.PlanRealityReport(
        period_key=day_key,
        has_plan=bool(entries),
        planned_total_min=planned_total,
        actual_total_min=actual_total,
        focused_total_min=focused_total,
        rows=rows,
        summary=". ".join(pieces) + ".",
    )
    return json.dumps(report.model_dump())

def _seed_plan_advice_json(seed: dict, entries: list[dict], available_min: int) -> str:
    scheduled = []
    for entry in entries:
        start = int(entry.get("scheduled_min") or 0)
        if seed["slug"] == "early-morning" and start < 12 * 60:
            reason = "This puts the deeper work inside the morning focus window."
        elif seed["slug"] == "night-owl" and start >= 15 * 60:
            reason = "This fits the later best focus window after the day warms up."
        elif seed["slug"] == "overplanner":
            reason = "This is part of the intentionally crowded plan the recap compares with reality."
        else:
            reason = "This timing follows the pattern shown in the seeded history."
        scheduled.append({
            "task_id": entry["task_id"],
            "start_hour": start // 60,
            "start_min": start % 60,
            "length_min": entry["estimate_min"],
            "reason": reason,
        })

    planned_total = sum(entry["estimate_min"] for entry in entries)
    over_plan_note = ""
    if planned_total > available_min:
        over_plan_note = "This plan asks for more minutes than the available window, so one task likely needs to move."

    return json.dumps({
        "summary": "Seeded AI timing advice for this persona's day.",
        "cold_start": False,
        "scheduled": scheduled,
        "over_plan_note": over_plan_note,
        "general_advice": [seed["archetype"]],
    })

def clear_workspace_data(db: Session, workspace) -> None:
    wid = _workspace_id(db, workspace)
    db.query(models.HabitCheck).filter(models.HabitCheck.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.Habit).filter(models.Habit.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.FocusSession).filter(models.FocusSession.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.Task).filter(models.Task.workspace_id == wid).delete(synchronize_session=False)
    # Goals AFTER tasks: tasks.goal_id references goals, so the children go first.
    db.query(models.Goal).filter(models.Goal.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.WorkPeriod).filter(models.WorkPeriod.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.DailyPlan).filter(models.DailyPlan.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.UserProfile).filter(models.UserProfile.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.Observation).filter(models.Observation.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.HourlyFocus).filter(models.HourlyFocus.workspace_id == wid).delete(synchronize_session=False)
    db.commit()

# Light April/May 2026 history per persona so the Trail's region browsing and
# atlas (Chunk 4) have past regions to show on the frozen June-28 demo clock.
# Day numbers only — the sessions themselves are reused from each persona's June
# `days` patterns, so past months stay persona-flavored without hand-writing them.
DEMO_PAST_MONTH_DAYS = {
    "early-morning": {"2026-05": [4, 7, 12, 18, 21, 26], "2026-04": [7, 14, 21, 28]},
    "doomscroller": {"2026-05": [6, 13, 20, 27], "2026-04": [9, 16, 23]},
    "overplanner": {"2026-05": [5, 8, 14, 19, 27], "2026-04": [8, 15, 22, 29]},
    "night-owl": {"2026-05": [7, 12, 16, 22, 29], "2026-04": [10, 17, 24]},
    "self-improver": {"2026-05": [11, 18, 25, 28], "2026-04": [6, 13, 20, 27, 30]},
}

# A saved May monthly recap per persona (the exact field set the monthly unwind
# saves/reads) so June's monthly unwind gets a real month-over-month trend and
# the May atlas tile shows its "unwound" check. April intentionally has none.
DEMO_MAY_MONTH_RECAPS = {
    "early-morning": {
        "summary": "May proved your mornings carry you — nearly every camp was pitched before noon, and the few evening tries faded fast.",
        "theme": "Mornings carry the month",
        "insights": [
            "Your before-noon blocks stayed clean almost every time you showed up.",
            "Evening sessions kept fading after the first short stretch.",
        ],
        "improvements": ["You could move review work into the late morning instead of after dinner."],
        "carry_forward": "When you plan a day, you could put the hardest block right after breakfast — May shows that's where it sticks.",
    },
    "doomscroller": {
        "summary": "May was a tug-of-war with the feed — but you caught yourself mid-scroll more than once and came back, which is the habit that matters.",
        "theme": "Learning to catch the drift",
        "insights": [
            "Most drifts started within the first ten minutes of a session.",
            "The sessions where you closed the extra tabs first ran noticeably cleaner.",
        ],
        "improvements": ["You could start each block with a site blocker on, before the first scroll gets a chance."],
        "carry_forward": "When you sit down to work, you could close every non-work tab before starting the timer — the clean starts were your best sessions.",
    },
    "overplanner": {
        "summary": "May's plans were ambitious and the work was real — the gap was between the schedule and the day, not in your focus.",
        "theme": "Big plans, honest hours",
        "insights": [
            "Days with three or fewer planned tasks matched reality far better than the packed ones.",
            "Your focus held well once a task actually started — starting late was the pattern, not drifting.",
        ],
        "improvements": ["You could plan one fewer task each day and leave a buffer between blocks."],
        "carry_forward": "When you make tomorrow's plan, you could cut the last task from the list — May says the shorter plan is the one you finish.",
    },
    "night-owl": {
        "summary": "May confirmed your rhythm runs late — the after-dark blocks were long and steady while the daytime ones stayed shallow.",
        "theme": "The night shift works",
        "insights": [
            "Your longest unbroken stretches all started after 9pm.",
            "Late-night focus stayed high, but the following mornings barely registered.",
        ],
        "improvements": ["You could protect a hard stop before it gets too late, so the next day isn't a write-off."],
        "carry_forward": "When you start a night block, you could set an end time first — the strong late hours are worth keeping, rested.",
    },
    "self-improver": {
        "summary": "May was steady, deliberate progress — a few honest camps each week and a habit of returning after every slip.",
        "theme": "Small steps, kept",
        "insights": [
            "You never missed two planned days in a row — the comeback habit is real.",
            "Shorter, more frequent sessions beat the occasional marathon for you.",
        ],
        "improvements": ["You could add one more short session on quiet weeks instead of extending the long ones."],
        "carry_forward": "When a session slips, you could schedule the makeup block for the very next morning — that's the pattern May rewarded.",
    },
}

def _seed_past_months(db: Session, workspace, seed: dict, tasks: list) -> None:
    """Seed the light April/May history: sessions only (no day work_periods or
    plans, so existing DEMO_HISTORY_DATES-keyed behavior is untouched), plus one
    saved May monthly recap row."""
    months = DEMO_PAST_MONTH_DAYS.get(seed["slug"], {})
    may_secs = {"focused": 0, "distracted": 0, "uncertain": 0, "away": 0}
    for month_key, day_nums in months.items():
        for i, day_num in enumerate(day_nums):
            day_key = f"{month_key}-{day_num:02d}"
            day_sessions = seed["days"][i % len(seed["days"])][1]
            for task_index, hour, minute, focused, distracted, uncertain, away in day_sessions:
                task = tasks[task_index % len(tasks)]
                start = _demo_dt(day_key, hour, minute)
                total_min = focused + distracted + uncertain + away
                db.add(models.FocusSession(
                    workspace_id=workspace.id,
                    task_id=task.id,
                    task_name=task.name,
                    started_at=start,
                    ended_at=start + timedelta(minutes=total_min),
                    seconds_focused=focused * 60,
                    seconds_distracted=distracted * 60,
                    seconds_uncertain=uncertain * 60,
                    seconds_away=away * 60,
                ))
                if month_key == "2026-05":
                    may_secs["focused"] += focused * 60
                    may_secs["distracted"] += distracted * 60
                    may_secs["uncertain"] += uncertain * 60
                    may_secs["away"] += away * 60

    recap = DEMO_MAY_MONTH_RECAPS.get(seed["slug"])
    if recap and any(may_secs.values()):
        db.add(models.WorkPeriod(
            workspace_id=workspace.id,
            kind="month",
            period_key="2026-05",
            ended_at=_demo_dt("2026-05-31", 21, 0),
            seconds_focused=may_secs["focused"],
            seconds_distracted=may_secs["distracted"],
            seconds_uncertain=may_secs["uncertain"],
            seconds_away=may_secs["away"],
            reflection="",
            ai_recap=json.dumps(recap),
        ))

# Earlier-June history: session days for the weeks of Mon June 8 and Mon June 15,
# so June holds three active weeks on the frozen June-28 clock. Without these the
# June monthly unwind is gated as a thin month (only one active week), the weekly
# trend has no prior weeks to compare against, and the June Trail map shows camps
# in one corner only. Sessions reuse each persona's June day patterns (like the
# April/May seeding) but DO include timeline_json, because the habit verifier's
# unbroken-25 template and the landmark backfill both read per-minute timelines.
# No day work_periods or daily plans for these days — the daily-unwind history
# window stays exactly DEMO_HISTORY_DATES.
DEMO_JUNE_WEEK_DAYS = {
    "early-morning": {"2026-06-08": [8, 9, 11, 12], "2026-06-15": [15, 16, 17, 19, 20]},
    "doomscroller": {"2026-06-08": [9, 11, 13], "2026-06-15": [16, 18, 20]},
    "overplanner": {"2026-06-08": [8, 10, 12, 13], "2026-06-15": [15, 17, 18, 20]},
    "night-owl": {"2026-06-08": [9, 10, 12, 14], "2026-06-15": [16, 17, 19, 21]},
    "self-improver": {"2026-06-08": [9, 11, 13], "2026-06-15": [15, 16, 18, 19, 20]},
}

# One saved weekly recap per prior June week (the exact field set the weekly
# unwind saves), so the June monthly unwind can fold real weekly notes and the
# month view reads "2 of 3 weeks unwound". The current week (Mon June 22) is
# deliberately NOT unwound — judges generate that one live. Pomodoro/habit ride
# along inert (recommend/propose false), matching what a healthy saved week holds.
def _inert_weekly_extras() -> dict:
    return {
        "pomodoro": {"recommend": False, "focus_min": 25, "break_min": 5, "why": ""},
        "habit": {"propose": False, "title": "", "why": "", "check": None},
    }

DEMO_JUNE_WEEK_RECAPS = {
    "early-morning": {
        "2026-06-08": {
            "summary": "Your mornings did the heavy lifting again — every clean block landed before lunch, and the evenings stayed deliberately small.",
            "theme": "Mornings set the tone",
            "insights": [
                "All four days opened with a strong pre-noon block.",
                "Evening sessions faded fast, but you kept them short instead of forcing them.",
            ],
            "improvements": ["You could move the flashcard review into the late morning once this week."],
            "next_week_focus": "Protect the 8am block on every school day.",
        },
        "2026-06-15": {
            "summary": "Five days on the trail, and the first hour kept winning — the earlier the start, the longer the focus held.",
            "theme": "Protecting the first hour",
            "insights": [
                "Your two longest focused stretches both started before 8:30am.",
                "The one late-evening block drifted within twenty minutes.",
            ],
            "improvements": [],
            "next_week_focus": "Keep the hardest task first thing and let evenings stay light.",
        },
    },
    "doomscroller": {
        "2026-06-08": {
            "summary": "The feed won a few rounds this week — most drifts opened right after a hard step, not out of boredom.",
            "theme": "The feed fought back",
            "insights": [
                "Instagram showed up within minutes of each difficult paragraph.",
                "The one session with the blocker on ran nearly twice as clean.",
            ],
            "improvements": ["You could turn the blocker on before the session starts, not after the first slip."],
            "next_week_focus": "Blocker on before every block, every time.",
        },
        "2026-06-15": {
            "summary": "Blockers first actually worked — three days showed real recovery, with shorter slips and faster returns.",
            "theme": "Blockers first",
            "insights": [
                "Sessions that started with the blocker running held their first twenty minutes.",
                "The phone on the desk was the common thread in the messier blocks.",
            ],
            "improvements": [],
            "next_week_focus": "Keep the phone out of the room and the blocker on from minute one.",
        },
    },
    "overplanner": {
        "2026-06-08": {
            "summary": "The work was real but the list was longer than the day — five planned, three moved, and the estimates were the squeeze.",
            "theme": "Five planned, three done",
            "insights": [
                "Physics and writing both ran well past their estimates.",
                "The days still felt productive because the tracked blocks were genuinely focused.",
            ],
            "improvements": ["You could drop one task from each day's plan and add a buffer after the first block."],
            "next_week_focus": "Plan one fewer task per day than feels right.",
        },
        "2026-06-15": {
            "summary": "A shorter list made a better week — plans with three tasks matched reality, and the buffer kept one long task from cascading.",
            "theme": "Shorter list, better week",
            "insights": [
                "Every three-task day closed with the plan basically met.",
                "The one packed day was the only one that ended with untouched tasks.",
            ],
            "improvements": [],
            "next_week_focus": "Keep the three-task ceiling and the mid-day buffer.",
        },
    },
    "night-owl": {
        "2026-06-08": {
            "summary": "The 5pm engine started on schedule all week — mornings idled, but the late-afternoon blocks were long and steady.",
            "theme": "The 5pm engine",
            "insights": [
                "Your strongest stretches all began after 4pm.",
                "Morning blocks worked only as small warm-ups, never as the main event.",
            ],
            "improvements": ["You could stop expecting deep work before noon and schedule it after school instead."],
            "next_week_focus": "Put the hardest work in the 4-7pm window on purpose.",
        },
        "2026-06-15": {
            "summary": "Evenings carried the week again — the creative work clicked late, and the gentle morning warm-ups kept the days from starting cold.",
            "theme": "Evenings carry it",
            "insights": [
                "The two longest focused blocks were both evening creative sessions.",
                "A ten-minute warm-up made the later deep block easier to enter.",
            ],
            "improvements": [],
            "next_week_focus": "Keep the warm-up-then-evening-deep-block shape.",
        },
    },
    "self-improver": {
        "2026-06-08": {
            "summary": "A messy week that still moved — drifts came often, but you returned every time, and that comeback is the skill being built.",
            "theme": "Messy but moving",
            "insights": [
                "Every session that opened with a written intention started cleaner.",
                "Slips happened, but none of them ended a session early.",
            ],
            "improvements": ["You could run the reset routine before every block, not just the morning one."],
            "next_week_focus": "Write the intention down before every single block.",
        },
        "2026-06-15": {
            "summary": "The recoveries got visibly faster — five days tracked, shorter drifts, and the reset routine turning into a reflex.",
            "theme": "Faster comebacks",
            "insights": [
                "Average drift length dropped noticeably from the week before.",
                "The strongest day was the one that started with the reset routine.",
            ],
            "improvements": [],
            "next_week_focus": "Keep the streak of daily written intentions alive.",
        },
    },
}

def _seed_prior_june_weeks(db: Session, workspace, seed: dict, tasks: list, extra_week_secs: dict | None = None) -> None:
    """Seed the two prior June weeks: sessions (with timelines) plus one saved
    weekly recap row per week. `extra_week_secs` folds in the done-goal task
    sessions (seeded by _seed_goals) so each week row's totals stay coherent."""
    weeks = DEMO_JUNE_WEEK_DAYS.get(seed["slug"], {})
    recaps = DEMO_JUNE_WEEK_RECAPS.get(seed["slug"], {})
    for week_key, day_nums in weeks.items():
        week_secs = {"focused": 0, "distracted": 0, "uncertain": 0, "away": 0}
        for i, day_num in enumerate(day_nums):
            day_key = f"2026-06-{day_num:02d}"
            day_sessions = seed["days"][i % len(seed["days"])][1]
            for task_index, hour, minute, focused, distracted, uncertain, away in day_sessions:
                task = tasks[task_index % len(tasks)]
                start = _demo_dt(day_key, hour, minute)
                total_min = focused + distracted + uncertain + away
                db.add(models.FocusSession(
                    workspace_id=workspace.id,
                    task_id=task.id,
                    task_name=task.name,
                    started_at=start,
                    ended_at=start + timedelta(minutes=total_min),
                    seconds_focused=focused * 60,
                    seconds_distracted=distracted * 60,
                    seconds_uncertain=uncertain * 60,
                    seconds_away=away * 60,
                    timeline_json=_timeline_json(focused, distracted, uncertain, away),
                ))
                week_secs["focused"] += focused * 60
                week_secs["distracted"] += distracted * 60
                week_secs["uncertain"] += uncertain * 60
                week_secs["away"] += away * 60

        for state, secs in ((extra_week_secs or {}).get(week_key) or {}).items():
            week_secs[state] += secs

        recap = recaps.get(week_key)
        if recap and any(week_secs.values()):
            sunday_key = f"2026-06-{int(week_key[-2:]) + 6:02d}"
            db.add(models.WorkPeriod(
                workspace_id=workspace.id,
                kind="week",
                period_key=week_key,
                ended_at=_demo_dt(sunday_key, 21, 0),
                seconds_focused=week_secs["focused"],
                seconds_distracted=week_secs["distracted"],
                seconds_uncertain=week_secs["uncertain"],
                seconds_away=week_secs["away"],
                reflection="",
                ai_recap=json.dumps({**recap, **_inert_weekly_extras()}),
            ))

# One coach-proposed AUTO habit per persona (focus-minutes 25 — every persona's
# seeded days clear 25 focused minutes). Its check rows are deliberately NOT
# seeded: the frontend verifier backfills them from the seeded June sessions on
# the judge's first habits-page visit, so the demo shows the real system, not
# hand-written data. The two phone-prone personas also get a MANUAL habit with a
# few ticked late-June days so the density dots and tick button read instantly
# on the frozen June-28 clock.
DEMO_HABIT_WHY = {
    "early-morning": "Your strong mornings carry the week — a small daily block keeps them coming.",
    "doomscroller": "On days you got one real block in, the scroll pull lost its grip.",
    "overplanner": "The days you actually sat down beat the days you only planned to.",
    "night-owl": "A daily block, whenever it lands, kept your late weeks from thinning out.",
    "self-improver": "Your steadiest weeks were the ones with a real block every day.",
}
DEMO_MANUAL_HABIT_SLUGS = {"doomscroller", "self-improver"}
DEMO_MANUAL_HABIT_DAYS = ["2026-06-23", "2026-06-25", "2026-06-26"]

# One RETIRED habit per persona so the habits page's retired section, the kept
# lifetime count, and the re-adopt flow are all visible. Framed as a coach
# proposal from the week of Mon June 1 (code coach-2026-06-01 — no collision
# with the active coach-2026-06-15 or with catalog codes) that the persona tried
# for a few days and then quietly retired. Manual on purpose: the verifier and
# the checks-sync route both skip retired/auto mismatches, so seeded history here
# can never be rewritten by the frontend. Shape: (title, why).
DEMO_RETIRED_HABITS = {
    "early-morning": ("No phone before the first morning block",
                      "You tried it for a week — mornings were already strong without it."),
    "doomscroller": ("Write down every scroll urge",
                     "Logging the urges got heavy fast; the blocker turned out to work better."),
    "overplanner": ("Rewrite tomorrow's plan before bed",
                    "A second nightly planning pass fed the overplanning instead of fixing it."),
    "night-owl": ("Start homework right after school",
                  "The 3pm start fought your rhythm; the later blocks kept winning."),
    "self-improver": ("Ten-minute evening journal",
                      "It helped, but the shorter reset routine covered the same ground."),
}
DEMO_RETIRED_HABIT_DAYS = ["2026-06-02", "2026-06-03", "2026-06-05"]

# A second ACTIVE auto habit per persona so more than one check template is live
# in the demo. Catalog entries copy code/title/why verbatim from the habits.js
# CATALOG (so the catalog page shows them as adopted); night-owl's is a coach
# proposal instead, because unbroken-25 isn't a catalog habit. created_day_key is
# June 8, so the frontend verifier backfills checks from the seeded sessions on
# first load — no check rows are seeded here, same rule as the focus-25 habit.
# Shape: (code, title, why, template, params, source).
DEMO_SECOND_AUTO_HABITS = {
    "early-morning": ("cat-before-10", "Start something before 10:00",
                      "An early first session sets the tone before the day gets loud.",
                      "session-before", {"time": "10:00"}, "catalog"),
    "doomscroller": ("cat-any-session", "Take one real focus session",
                     "Showing up is the whole habit — one session a day keeps the trail moving.",
                     "any-session", {}, "catalog"),
    "overplanner": ("cat-make-plan", "Sketch a plan for the day",
                    "Days with a rough plan wander less often.",
                    "made-a-plan", {}, "catalog"),
    "night-owl": ("coach-2026-06-08", "Hold one unbroken 25-minute stretch",
                  "Your evening blocks already run long — one unbroken stretch makes it official.",
                  "unbroken-25", {}, "coach"),
    "self-improver": ("cat-daily-unwind", "Close the day with a daily unwind",
                      "A two-minute look back is where the learning actually happens.",
                      "did-daily-unwind", {}, "catalog"),
}

def _seed_habits(db: Session, workspace, seed) -> None:
    coach = models.Habit(
        workspace_id=workspace.id,
        code="coach-2026-06-15",
        title="Complete 25 focused minutes",
        why=DEMO_HABIT_WHY.get(seed["slug"], "A small daily block keeps the trail moving."),
        kind="auto",
        check_json=json.dumps({"template": "focus-minutes", "params": {"min": 25}}),
        source="coach",
        created_day_key="2026-06-01",
    )
    db.add(coach)
    if seed["slug"] in DEMO_MANUAL_HABIT_SLUGS:
        manual = models.Habit(
            workspace_id=workspace.id,
            code="cat-phone-away",
            title="Put the phone in another room before starting",
            why="Distance beats willpower — you tick this one yourself.",
            kind="manual",
            check_json=None,
            source="catalog",
            created_day_key="2026-06-20",
        )
        db.add(manual)
        db.flush()
        for day_key in DEMO_MANUAL_HABIT_DAYS:
            db.add(models.HabitCheck(
                workspace_id=workspace.id,
                habit_id=manual.id,
                day_key=day_key,
                source="manual",
            ))

    code, title, why, template, params, source = DEMO_SECOND_AUTO_HABITS[seed["slug"]]
    db.add(models.Habit(
        workspace_id=workspace.id,
        code=code,
        title=title,
        why=why,
        kind="auto",
        check_json=json.dumps({"template": template, "params": params}),
        source=source,
        created_day_key="2026-06-08",
    ))

    retired_title, retired_why = DEMO_RETIRED_HABITS[seed["slug"]]
    retired = models.Habit(
        workspace_id=workspace.id,
        code="coach-2026-06-01",
        title=retired_title,
        why=retired_why,
        kind="manual",
        check_json=None,
        source="coach",
        status="retired",
        created_day_key="2026-06-01",
    )
    db.add(retired)
    db.flush()
    for day_key in DEMO_RETIRED_HABIT_DAYS:
        db.add(models.HabitCheck(
            workspace_id=workspace.id,
            habit_id=retired.id,
            day_key=day_key,
            source="manual",
        ))

# Persona goals (goals v1) — every judge link shows the full state set: the
# original active goal with measured June progress, one DONE goal (its work
# lives on a separate completed task with a couple of mid-June sessions, so the
# goals page shows real lifetime time), and one ARCHIVED goal. Two extras:
# doomscroller gets an active goal past its target date (the calm "past its
# target date — still open" copy) and self-improver gets an active goal with no
# tasks yet (the attach-guidance empty copy). The done-goal task is created here,
# NOT in seed["tasks"], so the historical daily plans never schedule it.
# Dict keys: title, target, status, created, and optionally done_day,
# task_indexes (into seed["tasks"]), done_task (name, desc),
# done_task_sessions [(day_key, hour, minute, f, d, u, a), ...].
DEMO_GOALS = {
    "early-morning": [
        {"title": "Ship the client project milestone", "target": "2026-07-08",
         "status": "active", "created": "2026-06-05", "task_indexes": [0, 1]},
        {"title": "Finish the biology unit review", "target": "2026-06-20",
         "status": "done", "created": "2026-06-01", "done_day": "2026-06-19",
         "done_task": ("Biology unit review packet", "Work through the full review packet."),
         "done_task_sessions": [("2026-06-10", 8, 30, 35, 5, 2, 0), ("2026-06-17", 8, 15, 40, 4, 1, 0)]},
        {"title": "Nightly chapter reading", "target": "2026-07-15",
         "status": "archived", "created": "2026-06-01"},
    ],
    "doomscroller": [
        {"title": "Finish the semester essay", "target": "2026-07-05",
         "status": "active", "created": "2026-06-05", "task_indexes": [0]},
        {"title": "Catch up on the class reading", "target": "2026-06-24",
         "status": "active", "created": "2026-06-01", "task_indexes": [3]},
        {"title": "Set up the distraction blockers", "target": "2026-06-15",
         "status": "done", "created": "2026-06-01", "done_day": "2026-06-14",
         "done_task": ("Blocker configuration", "Install and configure the site blockers."),
         "done_task_sessions": [("2026-06-11", 9, 30, 20, 8, 2, 0)]},
        {"title": "Inbox zero every day", "target": "2026-07-01",
         "status": "archived", "created": "2026-06-01"},
    ],
    "overplanner": [
        {"title": "Clear the project backlog before the trip", "target": "2026-07-12",
         "status": "active", "created": "2026-06-05", "task_indexes": [0, 1]},
        {"title": "Submit the chemistry lab portfolio", "target": "2026-06-19",
         "status": "done", "created": "2026-06-01", "done_day": "2026-06-18",
         "done_task": ("Chemistry portfolio assembly", "Collect and format the term's lab reports."),
         "done_task_sessions": [("2026-06-10", 9, 0, 45, 8, 2, 0), ("2026-06-17", 9, 15, 38, 6, 2, 0)]},
        {"title": "Reorganize every class binder", "target": "2026-07-20",
         "status": "archived", "created": "2026-06-01"},
    ],
    "night-owl": [
        {"title": "Launch the portfolio site", "target": "2026-07-10",
         "status": "active", "created": "2026-06-05", "task_indexes": [0, 1]},
        {"title": "Finish the AP Lit annotation set", "target": "2026-06-22",
         "status": "done", "created": "2026-06-01", "done_day": "2026-06-21",
         "done_task": ("Final annotation pass", "Close out the last chapters of annotations."),
         "done_task_sessions": [("2026-06-16", 17, 30, 42, 5, 2, 0)]},
        {"title": "Become a morning person", "target": "2026-07-01",
         "status": "archived", "created": "2026-06-01"},
    ],
    "self-improver": [
        {"title": "Finish the statistics course", "target": "2026-07-10",
         "status": "active", "created": "2026-06-05", "task_indexes": [0, 1]},
        {"title": "Build a two-week focus streak", "target": "2026-07-20",
         "status": "active", "created": "2026-06-05"},
        {"title": "Two weeks of daily resets", "target": "2026-06-21",
         "status": "done", "created": "2026-06-01", "done_day": "2026-06-21",
         "done_task": ("Reset routine checklist", "Design and test the daily reset checklist."),
         "done_task_sessions": [("2026-06-09", 9, 30, 22, 6, 2, 0), ("2026-06-16", 9, 30, 26, 4, 1, 0)]},
        {"title": "Read 3 books in June", "target": "2026-06-30",
         "status": "archived", "created": "2026-06-01"},
    ],
}

def _june_week_key(day_key: str) -> str:
    """Monday week key for a 2026-06-08..21 day (the two seeded prior weeks)."""
    return "2026-06-08" if int(day_key[-2:]) <= 14 else "2026-06-15"

def _seed_goals(db: Session, workspace, seed, tasks: list) -> dict:
    """Seed the persona's goals. Returns {week_key: seconds dict} for the
    done-goal task sessions, so _seed_prior_june_weeks can fold them into the
    saved weekly rows' totals."""
    extra_week_secs: dict = {}
    for entry in DEMO_GOALS.get(seed["slug"], []):
        if not tasks:
            break
        goal = models.Goal(
            workspace_id=workspace.id,
            title=entry["title"],
            target_day_key=entry["target"],
            status=entry["status"],
            created_day_key=entry["created"],
            done_day_key=entry.get("done_day"),
        )
        db.add(goal)
        db.flush()
        for index in entry.get("task_indexes", []):
            tasks[index % len(tasks)].goal_id = goal.id

        done_task = entry.get("done_task")
        if not done_task:
            continue
        name, description = done_task
        task = models.Task(
            workspace_id=workspace.id,
            name=name,
            description=description,
            completed=True,
            completed_at=_demo_dt(entry["done_day"], 20, 0),
            goal_id=goal.id,
        )
        db.add(task)
        db.flush()
        for day_key, hour, minute, focused, distracted, uncertain, away in entry.get("done_task_sessions", []):
            start = _demo_dt(day_key, hour, minute)
            total_min = focused + distracted + uncertain + away
            db.add(models.FocusSession(
                workspace_id=workspace.id,
                task_id=task.id,
                task_name=task.name,
                started_at=start,
                ended_at=start + timedelta(minutes=total_min),
                seconds_focused=focused * 60,
                seconds_distracted=distracted * 60,
                seconds_uncertain=uncertain * 60,
                seconds_away=away * 60,
                timeline_json=_timeline_json(focused, distracted, uncertain, away),
            ))
            secs = extra_week_secs.setdefault(
                _june_week_key(day_key),
                {"focused": 0, "distracted": 0, "uncertain": 0, "away": 0},
            )
            secs["focused"] += focused * 60
            secs["distracted"] += distracted * 60
            secs["uncertain"] += uncertain * 60
            secs["away"] += away * 60
    return extra_week_secs

# "Today" (the frozen June 28) starts lived-in, not blank: one small finished
# morning session plus a saved plan for the day. That makes today's donut, the
# daily unwind's Generate, plan-vs-reality, and the recommended-first highlight
# all work the moment a judge arrives — and they can still run their own live
# tracker session on top. The session's task is marked completed at the
# session's end, so Today's "Completed (1)" section shows too. Deliberately NO
# work_period row for June 28 — the day is still open for the judge to unwind.
# Times are UTC: a ~12:00Z start reads as early morning in US timezones against
# the frozen 9am demo clock (same convention as every other seeded session).
# Shape: (task_index, utc_hour, utc_minute, f, d, u, a, journal_note).
DEMO_TODAY_SESSIONS = {
    "early-morning": (0, 11, 45, 26, 3, 1, 0,
                      "First block of the day done before breakfast settled."),
    "doomscroller": (2, 12, 0, 14, 4, 1, 0,
                     "Blockers went on first thing, before the feed had a say."),
    "overplanner": (0, 11, 50, 24, 5, 1, 0,
                    "The first planned block actually started on time today."),
    "night-owl": (2, 12, 15, 12, 8, 2, 0,
                  "A shaky early warm-up — the real blocks come this evening."),
    "self-improver": (2, 12, 0, 22, 4, 1, 0,
                      "Reset routine done and the intention written before starting."),
}

# Today's saved plan per persona: (task_index, scheduled_min, estimate_min,
# difficulty). The first entry matches the finished morning session's task, so
# plan-vs-reality has a real "done" row immediately. Overplanner plans all five
# tasks into less time than available_min allows, so the saved AI advice keeps
# the over-plan note in character.
DEMO_TODAY_PLANS = {
    "early-morning": [(0, 480, 30, "hard"), (1, 540, 25, "medium"), (3, 1140, 20, "easy")],
    "doomscroller": [(2, 480, 15, "easy"), (0, 510, 30, "hard"), (1, 840, 30, "hard")],
    "overplanner": [(0, 480, 35, "hard"), (4, 525, 30, "hard"), (1, 570, 30, "medium"),
                    (3, 615, 20, "easy"), (2, 650, 25, "medium")],
    "night-owl": [(2, 495, 15, "easy"), (0, 1020, 45, "hard"), (3, 1080, 40, "medium")],
    "self-improver": [(2, 480, 15, "easy"), (0, 510, 35, "hard"), (3, 900, 25, "medium")],
}

def _seed_today(db: Session, workspace, seed, tasks: list) -> None:
    slug = seed["slug"]
    task_index, hour, minute, focused, distracted, uncertain, away, note = DEMO_TODAY_SESSIONS[slug]
    task = tasks[task_index % len(tasks)]
    start = _demo_dt(DEMO_TODAY_KEY, hour, minute)
    end = start + timedelta(minutes=focused + distracted + uncertain + away)
    db.add(models.FocusSession(
        workspace_id=workspace.id,
        task_id=task.id,
        task_name=task.name,
        started_at=start,
        ended_at=end,
        seconds_focused=focused * 60,
        seconds_distracted=distracted * 60,
        seconds_uncertain=uncertain * 60,
        seconds_away=away * 60,
        timeline_json=_timeline_json(focused, distracted, uncertain, away),
        journal_json=_journal_json(note, distracted),
        intention=f"Make visible progress on {task.name}.",
    ))
    task.completed = True
    task.completed_at = end

    entries = []
    for plan_task_index, scheduled_min, estimate_min, difficulty in DEMO_TODAY_PLANS[slug]:
        plan_task = tasks[plan_task_index % len(tasks)]
        entries.append({
            "task_id": plan_task.id,
            "name": plan_task.name,
            "estimate_min": estimate_min,
            "difficulty": difficulty,
            "scheduled_min": scheduled_min,
        })
    planned_total = sum(entry["estimate_min"] for entry in entries)
    available_min = planned_total - 30 if slug == "overplanner" else planned_total + 30
    db.add(models.DailyPlan(
        workspace_id=workspace.id,
        period_key=DEMO_TODAY_KEY,
        available_min=available_min,
        plan_json=json.dumps(entries),
        advice_json=_seed_plan_advice_json(seed, entries, available_min),
    ))

def reset_seeded_workspace(
    db: Session, slug: str, anonymous_id: str | None = None
) -> models.DemoWorkspace | None:
    seed = _seed_by_slug(slug)
    if seed is None:
        return None
    workspace_slug = _private_seeded_slug(slug, anonymous_id) if anonymous_id else slug
    workspace = get_workspace_by_slug(db, workspace_slug)
    if workspace is None:
        workspace = models.DemoWorkspace(
            slug=workspace_slug,
            display_name=seed["display_name"],
            archetype=seed["archetype"],
            workspace_type="seeded",
            seed_version=CURRENT_DEMO_SEED_VERSION,
        )
        db.add(workspace)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            workspace = get_workspace_by_slug(db, workspace_slug)
    workspace.display_name = seed["display_name"]
    workspace.archetype = seed["archetype"]
    workspace.workspace_type = "seeded"
    workspace.seed_version = CURRENT_DEMO_SEED_VERSION
    workspace.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(workspace)

    clear_workspace_data(db, workspace)

    tasks = []
    for name, description in seed["tasks"]:
        task = models.Task(workspace_id=workspace.id, name=name, description=description, completed=False)
        db.add(task)
        tasks.append(task)
    db.flush()

    db.add(models.UserProfile(workspace_id=workspace.id, about=seed["about"]))
    for text, affirmations, rejections in seed["observations"]:
        obs = models.Observation(
            workspace_id=workspace.id,
            text=text,
            affirmations=affirmations,
            rejections=rejections,
            active=(rejections - affirmations) < RETIRE_NET,
        )
        db.add(obs)

    for hour in range(24):
        pct = float(seed["hourly"].get(hour, 0.0))
        db.add(models.HourlyFocus(
            workspace_id=workspace.id,
            hour=hour,
            focus_pct=pct,
            sessions=3 if pct else 0,
        ))

    for day_index, sessions, daily_note in seed["days"]:
        day_key = DEMO_HISTORY_DATES[day_index]
        day_secs = {"focused": 0, "distracted": 0, "uncertain": 0, "away": 0}
        day_sessions = []
        for task_index, hour, minute, focused, distracted, uncertain, away in sessions:
            task = tasks[task_index % len(tasks)]
            start = _demo_dt(day_key, hour, minute)
            total_min = focused + distracted + uncertain + away
            end = start + timedelta(minutes=total_min)
            session = models.FocusSession(
                workspace_id=workspace.id,
                task_id=task.id,
                task_name=task.name,
                started_at=start,
                ended_at=end,
                seconds_focused=focused * 60,
                seconds_distracted=distracted * 60,
                seconds_uncertain=uncertain * 60,
                seconds_away=away * 60,
                timeline_json=_timeline_json(focused, distracted, uncertain, away),
                journal_json=_journal_json(daily_note, distracted),
                intention=f"Make visible progress on {task.name}.",
            )
            db.add(session)
            day_sessions.append(session)
            day_secs["focused"] += focused * 60
            day_secs["distracted"] += distracted * 60
            day_secs["uncertain"] += uncertain * 60
            day_secs["away"] += away * 60

        db.flush()
        plan_entries = _seed_plan_entries(seed, tasks, day_sessions)
        planned_total = sum(entry["estimate_min"] for entry in plan_entries)
        actual_total = round(sum(day_secs.values()) / 60)
        available_min = max(60, actual_total + 15)
        if seed["slug"] == "overplanner":
            available_min = max(75, actual_total + 20)
        plan_available_min = available_min if seed["slug"] == "overplanner" else max(available_min, planned_total)

        db.add(models.WorkPeriod(
            workspace_id=workspace.id,
            kind="day",
            period_key=day_key,
            ended_at=_demo_dt(day_key, 21, 0),
            seconds_focused=day_secs["focused"],
            seconds_distracted=day_secs["distracted"],
            seconds_uncertain=day_secs["uncertain"],
            seconds_away=day_secs["away"],
            reflection=f"Seeded reflection: {daily_note}",
            ai_recap="",
            plan_reality_json=_seed_plan_reality_json(day_key, plan_entries, day_sessions),
        ))
        db.add(models.DailyPlan(
            workspace_id=workspace.id,
            period_key=day_key,
            available_min=plan_available_min,
            plan_json=json.dumps(plan_entries),
            advice_json=_seed_plan_advice_json(
                seed,
                plan_entries,
                plan_available_min,
            ),
        ))

    _seed_past_months(db, workspace, seed, tasks)
    # Goals first: they return the done-goal task sessions' seconds so the prior
    # June week rows can fold them into coherent weekly totals.
    extra_week_secs = _seed_goals(db, workspace, seed, tasks)
    _seed_prior_june_weeks(db, workspace, seed, tasks, extra_week_secs)
    _seed_habits(db, workspace, seed)
    _seed_today(db, workspace, seed, tasks)

    db.commit()
    db.refresh(workspace)
    return workspace

def clear_anonymous_workspace(db: Session, anonymous_id: str) -> models.DemoWorkspace:
    workspace = ensure_anonymous_workspace(db, anonymous_id)
    clear_workspace_data(db, workspace)
    seed_hourly_focus(db, workspace)
    return workspace

def seeded_daily_unwinds(
    db: Session, slug: str, anonymous_id: str | None = None
) -> list[dict] | None:
    workspace = ensure_seeded_workspace(db, slug, anonymous_id)
    if workspace is None:
        return None
    rows = (
        db.query(models.WorkPeriod)
        .filter(
            models.WorkPeriod.workspace_id == workspace.id,
            models.WorkPeriod.kind == "day",
            models.WorkPeriod.period_key.in_(DEMO_HISTORY_DATES),
        )
        .order_by(models.WorkPeriod.period_key.asc())
        .all()
    )
    out = []
    for row in rows:
        recap = {}
        try:
            recap = json.loads(row.ai_recap or "{}")
        except Exception:
            recap = {}
        out.append({
            "period_key": row.period_key,
            "summary": (recap.get("summary") or "").strip(),
            "win": (recap.get("win") or "").strip(),
            "next_action": (recap.get("next_action") or "").strip(),
            "ai_recap": row.ai_recap or "",
            "plan_reality_json": row.plan_reality_json or "",
        })
    return out
