from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True, default='')
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id = Column(Integer, primary_key=True, index=True)
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
    __table_args__ = (UniqueConstraint("kind", "period_key", name="uq_workperiod_kind_key"),)

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String, nullable=False)        # "day" | "week"
    period_key = Column(String, nullable=False)  # day: local YYYY-MM-DD; week: that week's Monday
    ended_at = Column(DateTime(timezone=True), nullable=False)

    seconds_focused = Column(Integer, default=0)
    seconds_distracted = Column(Integer, default=0)
    seconds_uncertain = Column(Integer, default=0)
    seconds_away = Column(Integer, default=0)

    reflection = Column(String, nullable=True, default="")
    ai_recap = Column(String, nullable=True, default="")  # saved AI daily/weekly recap JSON/text
    plan_reality_json = Column(String, nullable=True, default="")  # saved deterministic plan-vs-reality report


class UserProfile(Base):
    """Single-row "About me" — free-text context the user gives the AI about their
    environment, schedule, and habits. Always id=1 (single-user app)."""
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    about = Column(String, nullable=False, default="")


class Observation(Base):
    """One AI-learned focus pattern about the user (the "Pattern Memory"). Unlike
    UserProfile (which the user writes), these are built by the model: after each
    session it affirms patterns it sees again and rejects ones the session
    contradicts. The counts let a pattern firm up ("confirmed") or fade ("retired").
    The table is pre-seeded with starter hypotheses so the model has direction."""
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
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

    hour = Column(Integer, primary_key=True)          # 0-23 (local)
    focus_pct = Column(Float, default=0.0, nullable=False)   # running average, 0-100
    sessions = Column(Integer, default=0, nullable=False)    # sessions that touched this hour


class DailyPlan(Base):
    """One day's optional plan: the tasks the user chose for a local day, each with an
    estimate + difficulty, plus how much time they have. Keyed by the frontend-computed
    local date (YYYY-MM-DD) so it groups the same way analytics does. `advice_json` holds
    the AI scheduling advice (null until generated). The plan and the advice are saved by
    separate paths, so `crud.upsert_plan` preserves whichever field the caller leaves None."""
    __tablename__ = "daily_plans"

    id = Column(Integer, primary_key=True, index=True)
    period_key = Column(String, nullable=False, unique=True)   # local YYYY-MM-DD (frontend-computed)
    available_min = Column(Integer, default=0, nullable=False)  # "time available today", minutes
    plan_json = Column(String, default="[]")                   # [{task_id, name, estimate_min, difficulty}]
    advice_json = Column(String, nullable=True, default=None)  # saved AI advice JSON; null until generated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
