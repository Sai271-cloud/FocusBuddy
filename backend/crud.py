import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from . import models, schemas


DEFAULT_WORKSPACE_SLUG = "local"
DEFAULT_WORKSPACE_ID = 1
CURRENT_DEMO_SEED_VERSION = 4
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
        db.commit()
        db.refresh(workspace)
    return workspace


def _workspace_id(db: Session, workspace=None) -> int:
    if workspace is None:
        return ensure_default_workspace(db).id
    if isinstance(workspace, int):
        return workspace
    return workspace.id


def get_workspace_by_slug(db: Session, slug: str) -> models.DemoWorkspace | None:
    return db.query(models.DemoWorkspace).filter(models.DemoWorkspace.slug == slug).first()


def ensure_seeded_workspace(db: Session, slug: str) -> models.DemoWorkspace | None:
    seed = _seed_by_slug(slug)
    if seed is None:
        return None
    workspace = get_workspace_by_slug(db, slug)
    if (
        workspace is None
        or workspace.workspace_type != "seeded"
        or workspace.seed_version != CURRENT_DEMO_SEED_VERSION
    ):
        workspace = reset_seeded_workspace(db, slug)
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
        db.commit()
        db.refresh(workspace)
        seed_hourly_focus(db, workspace)
    return workspace


def resolve_demo_workspace(
    db: Session,
    demo_slug: str | None = None,
    anonymous_id: str | None = None,
) -> models.DemoWorkspace | None:
    if anonymous_id:
        return ensure_anonymous_workspace(db, anonymous_id)
    if demo_slug:
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

    # Partial update: only touch fields the caller actually sent.
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
    # Cascade: remove the task's sessions first (FK), then the task itself.
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
    # None means "leave as-is" so the two save paths (reflection vs AI recap) don't
    # clobber each other; '' explicitly clears.
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


# --- Daily plan ("Today's Plan") --------------------------------------------

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
    # None means "leave as-is" so a plan-only save and an advice-only save don't clobber
    # each other (same idiom as upsert_work_period).
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


# --- Pattern Memory (AI-learned focus observations) -------------------------
# Simple counting confidence. net = affirmations - rejections.
CONFIRM_NET = 2          # net >= this  -> "confirmed"
RETIRE_NET = 2           # (rejections - affirmations) >= this -> retired (active=False)
MAX_ACTIVE_OBSERVATIONS = 20  # cap so the file can't grow without bound

# Starter hypotheses so the model has direction on what to look for. These are
# neutral guesses (0/0) the model affirms or rejects over time. (Time-of-day is NOT
# here — that's handled deterministically by the 24-hour hourly_focus profile.)
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


# The old time-of-day seeds, replaced by the deterministic hourly_focus profile.
# Existing DBs (seeded before the redesign) still hold these; we delete them once.
LEGACY_TIME_OBSERVATIONS = [
    "Focuses best in the morning",
    "Focuses best around midday",
    "Focuses best in the late afternoon or evening",
]

DECAY_DAYS = 30  # a note untouched this long loses one step of confidence


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
            continue  # already neutral — nothing to decay
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


# --- Hourly focus profile (deterministic "focus by hour") -------------------

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
        if row is None:  # safety: preboot a missing hour
            row = models.HourlyFocus(workspace_id=wid, hour=h, focus_pct=0.0, sessions=0)
            db.add(row)
        n = row.sessions or 0
        row.focus_pct = ((row.focus_pct or 0.0) * n + pct) / (n + 1)
        row.sessions = n + 1
        touched += 1
    db.commit()
    return touched


# --- Demo workspace seeding --------------------------------------------------

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
    db.query(models.FocusSession).filter(models.FocusSession.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.Task).filter(models.Task.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.WorkPeriod).filter(models.WorkPeriod.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.DailyPlan).filter(models.DailyPlan.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.UserProfile).filter(models.UserProfile.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.Observation).filter(models.Observation.workspace_id == wid).delete(synchronize_session=False)
    db.query(models.HourlyFocus).filter(models.HourlyFocus.workspace_id == wid).delete(synchronize_session=False)
    db.commit()


def reset_seeded_workspace(db: Session, slug: str) -> models.DemoWorkspace | None:
    seed = _seed_by_slug(slug)
    if seed is None:
        return None
    workspace = get_workspace_by_slug(db, slug)
    if workspace is None:
        workspace = models.DemoWorkspace(
            slug=slug,
            display_name=seed["display_name"],
            archetype=seed["archetype"],
            workspace_type="seeded",
            seed_version=CURRENT_DEMO_SEED_VERSION,
        )
        db.add(workspace)
        db.flush()
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

    db.commit()
    db.refresh(workspace)
    return workspace


def clear_anonymous_workspace(db: Session, anonymous_id: str) -> models.DemoWorkspace:
    workspace = ensure_anonymous_workspace(db, anonymous_id)
    clear_workspace_data(db, workspace)
    seed_hourly_focus(db, workspace)
    return workspace


def seeded_daily_unwinds(db: Session, slug: str) -> list[dict] | None:
    workspace = ensure_seeded_workspace(db, slug)
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
