from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base

class DemoWorkspace(Base):
    __tablename__ = "demo_workspaces"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)
    archetype = Column(String, nullable=False, default="")
    workspace_type = Column(String, nullable=False, default="local")
    seed_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True, default='')
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Optional link to a Goal — at most one goal per task; set/cleared only by the
    # goal attach/detach routes (the DB has no FK on hosted Postgres, so those
    # routes are the integrity layer).
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    task_name = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=False)

    seconds_focused = Column(Integer, default=0)
    seconds_distracted = Column(Integer, default=0)
    seconds_uncertain = Column(Integer, default=0)
    seconds_away = Column(Integer, default=0)

    timeline_json = Column(String, default="[]")
    journal_json = Column(String, default="[]")
    intention = Column(String, nullable=True, default="")

class WorkPeriod(Base):
    """A finalized ("unwound") day or week — a snapshot of focus totals plus an
    optional reflection. Identified by (kind, period_key); one row per period."""
    __tablename__ = "work_periods"
    __table_args__ = (UniqueConstraint("workspace_id", "kind", "period_key", name="uq_workperiod_workspace_kind_key"),)

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    kind = Column(String, nullable=False)
    period_key = Column(String, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=False)

    seconds_focused = Column(Integer, default=0)
    seconds_distracted = Column(Integer, default=0)
    seconds_uncertain = Column(Integer, default=0)
    seconds_away = Column(Integer, default=0)

    reflection = Column(String, nullable=True, default="")
    ai_recap = Column(String, nullable=True, default="")
    plan_reality_json = Column(String, nullable=True, default="")

class UserProfile(Base):
    """Single-row "About me" — free-text context the user gives the AI about their
    environment, schedule, and habits. Always id=1 (single-user app)."""
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, unique=True, index=True)
    about = Column(String, nullable=False, default="")
    # Lifetime focused minutes for the Trail's league — ratcheted (only ever
    # increases), so ranks can never demote. See crud.ratchet_league.
    league_points = Column(Integer, default=0, nullable=False)

class Landmark(Base):
    """One earned Trail landmark (Chunk 5) — a lifetime milestone like "first camp"
    or "25 minutes unbroken". Insert-only: rows are never deleted or updated, so a
    landmark structurally can't be lost (the same ratchet idea as league_points).
    `day_key` is the frontend-computed local YYYY-MM-DD it was earned on — that's
    what places the cairn on the right month's map."""
    __tablename__ = "landmarks"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_landmark_workspace_code"),)

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    code = Column(String, nullable=False)
    day_key = Column(String, nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())

class Habit(Base):
    """One adopted habit (habit tracker v1). Habits come from the starter catalog
    (`source='catalog'`) or from a weekly-unwind AI proposal (`source='coach'`,
    code `coach-<week_key>` — at most one per weekly generate, so the Monday key
    is a natural dedupe id). `kind='auto'` habits carry `check_json`
    ({"template", "params"}) and are verified by the FRONTEND from session/plan
    data; `kind='manual'` habits get a daily tick from the user. Habits are
    retired, never deleted, so their check history and lifetime count survive;
    re-adopting flips the same row back to active (the unique constraint makes a
    duplicate structurally impossible). `created_day_key` is the frontend-computed
    local adoption day — auto-verification never looks earlier, so the completed
    count starts honestly at zero instead of backfilling old history."""
    __tablename__ = "habits"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_habit_workspace_code"),)

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    why = Column(String, nullable=False, default="")
    kind = Column(String, nullable=False)            # 'auto' | 'manual'
    check_json = Column(String, nullable=True)       # JSON {"template","params"} when kind='auto'
    source = Column(String, nullable=False, default="catalog")  # 'catalog' | 'coach'
    status = Column(String, nullable=False, default="active")   # 'active' | 'retired'
    created_day_key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Goal(Base):
    """One user goal (goals v1): a typed outcome ("Finish my research paper") with a
    target date and tasks attached to it (tasks.goal_id). Progress is measured, never
    guessed: focused seconds on attached tasks + days until `target_day_key`. The user
    marks it done; a passed target date is shown calmly ("past its date — still open"),
    never as a failure state. Archive is the quiet exit for abandoned goals — there is
    no delete, and reopen is allowed (subject to the active-goal cap). Day keys are
    frontend-computed local YYYY-MM-DD, like habits and landmarks."""
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    title = Column(String, nullable=False)
    target_day_key = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")   # 'active' | 'done' | 'archived'
    created_day_key = Column(String, nullable=False)
    done_day_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class HabitCheck(Base):
    """One completed day for one habit. Insert-only with one row per habit per local
    day (unique constraint), so the lifetime done count is a row count
    that only ever grows — the same ratchet idea as landmarks. `source` records
    whether the frontend verifier earned it ('auto') or the user ticked it
    ('manual'); both count the same."""
    __tablename__ = "habit_checks"
    __table_args__ = (UniqueConstraint("workspace_id", "habit_id", "day_key", name="uq_habit_check_day"),)

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False, index=True)
    day_key = Column(String, nullable=False)
    source = Column(String, nullable=False)          # 'auto' | 'manual'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Observation(Base):
    """One AI-learned focus pattern about the user (the "Pattern Memory"). Unlike
    UserProfile (which the user writes), these are built by the model: after each
    session it affirms patterns it sees again and rejects ones the session
    contradicts. The counts let a pattern firm up ("confirmed") or fade ("retired").
    The table is pre-seeded with starter hypotheses so the model has direction."""
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    text = Column(String, nullable=False)
    affirmations = Column(Integer, default=0, nullable=False)
    rejections = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

class HourlyFocus(Base):
    """A 24-row "focus by hour" profile (one row per local clock hour 0-23). Each
    row keeps a running average focus % across every session that touched that hour,
    plus how many sessions contributed. Computed deterministically from session data
    (not the AI) — see crud.update_hourly_focus. Prebooted with all 24 hours."""
    __tablename__ = "hourly_focus"

    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), primary_key=True, default=1)
    hour = Column(Integer, primary_key=True)
    focus_pct = Column(Float, default=0.0, nullable=False)
    sessions = Column(Integer, default=0, nullable=False)

class DailyPlan(Base):
    """One day's optional plan: the tasks the user chose for a local day, each with an
    estimate + difficulty, plus how much time they have. Keyed by the frontend-computed
    local date (YYYY-MM-DD) so it groups the same way analytics does. `advice_json` holds
    the AI scheduling advice (null until generated). The plan and the advice are saved by
    separate paths, so `crud.upsert_plan` preserves whichever field the caller leaves None."""
    __tablename__ = "daily_plans"
    __table_args__ = (UniqueConstraint("workspace_id", "period_key", name="uq_daily_plan_workspace_key"),)

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    period_key = Column(String, nullable=False)
    available_min = Column(Integer, default=0, nullable=False)
    plan_json = Column(String, default="[]")
    advice_json = Column(String, nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
