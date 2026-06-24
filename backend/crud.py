from sqlalchemy.orm import Session
from . import models, schemas


def create_task(db: Session, task: schemas.TaskCreate) -> models.Task:
    db_task = models.Task(
        name=task.name.strip(),
        description=(task.description or "").strip(),
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task(db: Session, task_id: int) -> models.Task | None:
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def get_tasks(db: Session) -> list[models.Task]:
    return db.query(models.Task).order_by(models.Task.created_at.desc()).all()


def update_task(db: Session, db_task: models.Task, update: schemas.TaskUpdate) -> models.Task:
    from datetime import datetime, timezone

    # Partial update: only touch fields the caller actually sent.
    if update.completed is not None:
        db_task.completed = update.completed
        db_task.completed_at = datetime.now(timezone.utc) if update.completed else None
    if update.name is not None:
        db_task.name = update.name.strip()
    if update.description is not None:
        db_task.description = update.description.strip()
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, db_task: models.Task) -> None:
    # Cascade: remove the task's sessions first (FK), then the task itself.
    db.query(models.FocusSession).filter(models.FocusSession.task_id == db_task.id).delete()
    db.delete(db_task)
    db.commit()


def delete_session(db: Session, db_session: models.FocusSession) -> None:
    db.delete(db_session)
    db.commit()


def start_session(db: Session, task: models.Task) -> models.FocusSession:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    db_session = models.FocusSession(
        task_id=task.id,
        task_name=task.name,
        started_at=now,
        ended_at=now,
        seconds_focused=0,
        seconds_distracted=0,
        seconds_uncertain=0,
        seconds_away=0,
        timeline_json="[]",
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def create_session(
    db: Session,
    session: schemas.SessionCreate,
    task: models.Task,
) -> models.FocusSession:
    data = session.model_dump()
    data["task_name"] = task.name
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
    db.commit()
    db.refresh(db_session)
    return db_session


def get_sessions(db: Session) -> list[models.FocusSession]:
    return db.query(models.FocusSession).order_by(models.FocusSession.ended_at.desc()).all()


def upsert_work_period(db: Session, data: schemas.WorkPeriodCreate) -> models.WorkPeriod:
    existing = (
        db.query(models.WorkPeriod)
        .filter(models.WorkPeriod.kind == data.kind, models.WorkPeriod.period_key == data.period_key)
        .first()
    )
    if existing is None:
        existing = models.WorkPeriod(kind=data.kind, period_key=data.period_key)
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
    db.commit()
    db.refresh(existing)
    return existing


def get_work_periods(db: Session) -> list[models.WorkPeriod]:
    return db.query(models.WorkPeriod).order_by(models.WorkPeriod.ended_at.desc()).all()


def get_profile(db: Session) -> models.UserProfile:
    """The single 'About me' row (id=1), created empty on first access."""
    profile = db.get(models.UserProfile, 1)
    if profile is None:
        profile = models.UserProfile(id=1, about="")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_profile(db: Session, about: str) -> models.UserProfile:
    profile = get_profile(db)
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


def cleanup_legacy_time_observations(db: Session) -> int:
    """Remove the obsolete time-of-day seed patterns by exact text. Idempotent —
    after the first run nothing matches. Only the three known seed strings are
    targeted, so AI-made or user notes are never touched. Returns rows deleted."""
    deleted = (
        db.query(models.Observation)
        .filter(models.Observation.text.in_(LEGACY_TIME_OBSERVATIONS))
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


def decay_stale_observations(db: Session, days: int = DECAY_DAYS) -> int:
    """Erode confidence in notes not affirmed/rejected in `days`: move each stale
    note's net one step toward 0 (a confirmed note drifts back to emerging; a
    retired note can get another chance), then re-stamp updated_at so it only
    decays again after another `days` of inactivity. Reflects that habits change —
    old conclusions fade unless reinforced. Returns how many notes decayed."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    changed = 0
    for o in db.query(models.Observation).all():
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


def seed_observations(db: Session) -> None:
    """Insert the starter hypotheses, but ONLY when the table is empty. Note: if the
    user deletes every observation and the app restarts, the starters come back —
    that's acceptable (it just restores neutral direction, never resurrects a single
    pattern the user removed while others remain)."""
    if db.query(models.Observation).count() > 0:
        return
    for text in SEED_OBSERVATIONS:
        db.add(models.Observation(text=text))
    db.commit()


def list_observations(db: Session, active_only: bool = False) -> list[models.Observation]:
    q = db.query(models.Observation)
    if active_only:
        q = q.filter(models.Observation.active == True)  # noqa: E712
    return q.order_by(models.Observation.active.desc(), models.Observation.id.asc()).all()


def get_observation(db: Session, obs_id: int) -> models.Observation | None:
    return db.get(models.Observation, obs_id)


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


def create_observation(db: Session, text: str) -> models.Observation | None:
    """Add a new active pattern. Skips if the active count is already at the cap or
    a same-text active pattern already exists (cheap de-dup). Returns None if skipped."""
    clean = (text or "").strip()[:200]
    if not clean:
        return None
    active = list_observations(db, active_only=True)
    if len(active) >= MAX_ACTIVE_OBSERVATIONS:
        return None
    if any(o.text.strip().lower() == clean.lower() for o in active):
        return None
    obs = models.Observation(text=clean)
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def delete_observation(db: Session, obs: models.Observation) -> None:
    db.delete(obs)
    db.commit()


# --- Hourly focus profile (deterministic "focus by hour") -------------------

def seed_hourly_focus(db: Session) -> None:
    """Preboot all 24 hour rows (0-23) once, if the table is empty."""
    if db.query(models.HourlyFocus).count() > 0:
        return
    for h in range(24):
        db.add(models.HourlyFocus(hour=h, focus_pct=0.0, sessions=0))
    db.commit()


def get_hourly_focus(db: Session) -> list[models.HourlyFocus]:
    return db.query(models.HourlyFocus).order_by(models.HourlyFocus.hour.asc()).all()


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


def update_hourly_focus(db: Session, start_hour: int, end_hour: int, session_pct: float) -> int:
    """Fold one session's focus % into every hour it touched (running average).
    Returns how many hour rows were updated. Deterministic — no AI involved."""
    pct = max(0.0, min(100.0, float(session_pct)))
    touched = 0
    for h in _hours_in_range(start_hour, end_hour):
        row = db.get(models.HourlyFocus, h)
        if row is None:  # safety: preboot a missing hour
            row = models.HourlyFocus(hour=h, focus_pct=0.0, sessions=0)
            db.add(row)
        n = row.sessions or 0
        row.focus_pct = ((row.focus_pct or 0.0) * n + pct) / (n + 1)
        row.sessions = n + 1
        touched += 1
    db.commit()
    return touched
