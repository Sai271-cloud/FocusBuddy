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
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, unique=True, index=True)
    about = Column(String, nullable=False, default="")
    league_points = Column(Integer, default=0, nullable=False)

class Landmark(Base):
    __tablename__ = "landmarks"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_landmark_workspace_code"),)

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    code = Column(String, nullable=False)
    day_key = Column(String, nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())

class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_habit_workspace_code"),)

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    why = Column(String, nullable=False, default="")
    kind = Column(String, nullable=False)
    check_json = Column(String, nullable=True)
    source = Column(String, nullable=False, default="catalog")
    status = Column(String, nullable=False, default="active")
    created_day_key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    title = Column(String, nullable=False)
    target_day_key = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_day_key = Column(String, nullable=False)
    done_day_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class HabitCheck(Base):
    __tablename__ = "habit_checks"
    __table_args__ = (UniqueConstraint("workspace_id", "habit_id", "day_key", name="uq_habit_check_day"),)

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), nullable=False, default=1, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False, index=True)
    day_key = Column(String, nullable=False)
    source = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Observation(Base):
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
    __tablename__ = "hourly_focus"

    workspace_id = Column(Integer, ForeignKey("demo_workspaces.id"), primary_key=True, default=1)
    hour = Column(Integer, primary_key=True)
    focus_pct = Column(Float, default=0.0, nullable=False)
    sessions = Column(Integer, default=0, nullable=False)

class DailyPlan(Base):
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
