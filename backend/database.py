import os
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_PATH = Path(__file__).resolve().with_name("focus_buddy.db")
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DATABASE_PATH.as_posix()}"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]

_IS_SQLITE = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _IS_SQLITE else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


if _IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db():
    from . import models

    Base.metadata.create_all(bind=engine)
    if _IS_SQLITE:
        _repair_sqlite_schema()
    _prune_empty_sessions()
    _init_pattern_memory()


def _init_pattern_memory():
    """Startup maintenance for the Pattern Memory:
    - seed the starter hypotheses + 24-hour focus profile on a fresh DB (no-op once seeded),
    - one-time cleanup of the obsolete time-of-day seeds on older DBs (idempotent),
    - decay notes not touched in 30+ days (so stale habits fade)."""
    from . import crud

    db = SessionLocal()
    try:
        crud.seed_observations(db)
        crud.seed_hourly_focus(db)
        crud.cleanup_legacy_time_observations(db)
        crud.decay_stale_observations(db)
    finally:
        db.close()


def _prune_empty_sessions():
    """Remove abandoned sessions — ones opened then closed before a single tick
    was recorded (started_at == ended_at and all four second-counts are 0).
    Any session that recorded time (autosave bumped ended_at) is left untouched."""
    inspector = inspect(engine)
    if "focus_sessions" not in inspector.get_table_names():
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DELETE FROM focus_sessions
                WHERE started_at = ended_at
                  AND COALESCE(seconds_focused, 0) = 0
                  AND COALESCE(seconds_distracted, 0) = 0
                  AND COALESCE(seconds_uncertain, 0) = 0
                  AND COALESCE(seconds_away, 0) = 0
                """
            )
        )


def _repair_sqlite_schema():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    _ensure_default_workspace_row()
    if "tasks" not in table_names:
        return

    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "workspace_id" not in task_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE tasks ADD COLUMN workspace_id INTEGER NOT NULL DEFAULT 1")
            )
    if "description" not in task_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE tasks ADD COLUMN description VARCHAR DEFAULT ''")
            )
    if "completed" not in task_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE tasks ADD COLUMN completed BOOLEAN DEFAULT 0")
            )
    if "completed_at" not in task_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE tasks ADD COLUMN completed_at DATETIME")
            )

    # Add advice_json to older Chunk A daily_plans tables. `create_all` creates it
    # for fresh DBs, but SQLite needs ALTER TABLE for an existing table.
    if "daily_plans" in inspect(engine).get_table_names():
        plan_cols_before = {c["name"] for c in inspect(engine).get_columns("daily_plans")}
        if "workspace_id" not in plan_cols_before:
            _rebuild_daily_plans_with_workspace()
        plan_cols = {c["name"] for c in inspect(engine).get_columns("daily_plans")}
        if "advice_json" not in plan_cols:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE daily_plans ADD COLUMN advice_json VARCHAR")
                )

    if "focus_sessions" not in table_names:
        return

    focus_columns = {
        column["name"]: str(column["type"]).upper()
        for column in inspector.get_columns("focus_sessions")
    }
    if "workspace_id" not in focus_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE focus_sessions ADD COLUMN workspace_id INTEGER NOT NULL DEFAULT 1")
            )
        focus_columns["workspace_id"] = "INTEGER"
    second_columns = [
        "seconds_focused",
        "seconds_distracted",
        "seconds_uncertain",
        "seconds_away",
    ]
    if any(focus_columns.get(column) != "INTEGER" for column in second_columns):
        _rebuild_focus_sessions_with_integer_seconds()

    # Add journal_json to existing DBs (re-inspect in case a rebuild just ran).
    focus_cols = {c["name"] for c in inspect(engine).get_columns("focus_sessions")}
    if "journal_json" not in focus_cols:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE focus_sessions ADD COLUMN journal_json VARCHAR DEFAULT '[]'")
            )
    if "intention" not in focus_cols:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE focus_sessions ADD COLUMN intention VARCHAR DEFAULT ''")
            )

    # Add ai_recap to existing work_periods tables (stores the saved AI daily recap).
    if "work_periods" in inspect(engine).get_table_names():
        wp_cols_before = {c["name"] for c in inspect(engine).get_columns("work_periods")}
        if "workspace_id" not in wp_cols_before:
            _rebuild_work_periods_with_workspace()
        wp_cols = {c["name"] for c in inspect(engine).get_columns("work_periods")}
        if "ai_recap" not in wp_cols:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE work_periods ADD COLUMN ai_recap VARCHAR DEFAULT ''")
                )
        if "plan_reality_json" not in wp_cols:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE work_periods ADD COLUMN plan_reality_json VARCHAR DEFAULT ''")
                )

    if "user_profile" in inspect(engine).get_table_names():
        profile_cols = {c["name"] for c in inspect(engine).get_columns("user_profile")}
        if "workspace_id" not in profile_cols:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE user_profile ADD COLUMN workspace_id INTEGER NOT NULL DEFAULT 1")
                )

    if "observations" in inspect(engine).get_table_names():
        obs_cols = {c["name"] for c in inspect(engine).get_columns("observations")}
        if "workspace_id" not in obs_cols:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE observations ADD COLUMN workspace_id INTEGER NOT NULL DEFAULT 1")
                )

    if "hourly_focus" in inspect(engine).get_table_names():
        hour_cols = {c["name"] for c in inspect(engine).get_columns("hourly_focus")}
        if "workspace_id" not in hour_cols:
            _rebuild_hourly_focus_with_workspace()

def _ensure_default_workspace_row():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO demo_workspaces (
                    id, slug, display_name, archetype, workspace_type, seed_version
                ) VALUES (
                    1, 'local', 'Local workspace', 'Local development', 'local', 0
                )
                """
            )
        )


def _rebuild_daily_plans_with_workspace():
    old_cols = {c["name"] for c in inspect(engine).get_columns("daily_plans")}
    has_advice = "advice_json" in old_cols
    advice_select = "advice_json" if has_advice else "NULL"
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS daily_plans_new"))
        connection.execute(
            text(
                """
                CREATE TABLE daily_plans_new (
                    id INTEGER NOT NULL,
                    workspace_id INTEGER NOT NULL DEFAULT 1,
                    period_key VARCHAR NOT NULL,
                    available_min INTEGER NOT NULL DEFAULT 0,
                    plan_json VARCHAR,
                    advice_json VARCHAR,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    FOREIGN KEY(workspace_id) REFERENCES demo_workspaces (id),
                    UNIQUE (workspace_id, period_key)
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                INSERT INTO daily_plans_new (
                    id, workspace_id, period_key, available_min, plan_json, advice_json, created_at, updated_at
                )
                SELECT
                    id, 1, period_key, COALESCE(available_min, 0), COALESCE(plan_json, '[]'),
                    {advice_select}, created_at, updated_at
                FROM daily_plans
                """
            )
        )
        connection.execute(text("DROP TABLE daily_plans"))
        connection.execute(text("ALTER TABLE daily_plans_new RENAME TO daily_plans"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_daily_plans_id ON daily_plans (id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_daily_plans_workspace_id ON daily_plans (workspace_id)"))


def _rebuild_work_periods_with_workspace():
    old_cols = {c["name"] for c in inspect(engine).get_columns("work_periods")}
    ai_select = "COALESCE(ai_recap, '')" if "ai_recap" in old_cols else "''"
    reality_select = "COALESCE(plan_reality_json, '')" if "plan_reality_json" in old_cols else "''"
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS work_periods_new"))
        connection.execute(
            text(
                """
                CREATE TABLE work_periods_new (
                    id INTEGER NOT NULL,
                    workspace_id INTEGER NOT NULL DEFAULT 1,
                    kind VARCHAR NOT NULL,
                    period_key VARCHAR NOT NULL,
                    ended_at DATETIME NOT NULL,
                    seconds_focused INTEGER,
                    seconds_distracted INTEGER,
                    seconds_uncertain INTEGER,
                    seconds_away INTEGER,
                    reflection VARCHAR,
                    ai_recap VARCHAR,
                    plan_reality_json VARCHAR,
                    PRIMARY KEY (id),
                    FOREIGN KEY(workspace_id) REFERENCES demo_workspaces (id),
                    UNIQUE (workspace_id, kind, period_key)
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                INSERT INTO work_periods_new (
                    id, workspace_id, kind, period_key, ended_at, seconds_focused,
                    seconds_distracted, seconds_uncertain, seconds_away, reflection,
                    ai_recap, plan_reality_json
                )
                SELECT
                    id, 1, kind, period_key, ended_at, seconds_focused,
                    seconds_distracted, seconds_uncertain, seconds_away,
                    COALESCE(reflection, ''), {ai_select}, {reality_select}
                FROM work_periods
                """
            )
        )
        connection.execute(text("DROP TABLE work_periods"))
        connection.execute(text("ALTER TABLE work_periods_new RENAME TO work_periods"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_work_periods_id ON work_periods (id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_work_periods_workspace_id ON work_periods (workspace_id)"))


def _rebuild_hourly_focus_with_workspace():
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS hourly_focus_new"))
        connection.execute(
            text(
                """
                CREATE TABLE hourly_focus_new (
                    workspace_id INTEGER NOT NULL DEFAULT 1,
                    hour INTEGER NOT NULL,
                    focus_pct FLOAT NOT NULL DEFAULT 0.0,
                    sessions INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (workspace_id, hour),
                    FOREIGN KEY(workspace_id) REFERENCES demo_workspaces (id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO hourly_focus_new (workspace_id, hour, focus_pct, sessions)
                SELECT 1, hour, COALESCE(focus_pct, 0.0), COALESCE(sessions, 0)
                FROM hourly_focus
                """
            )
        )
        connection.execute(text("DROP TABLE hourly_focus"))
        connection.execute(text("ALTER TABLE hourly_focus_new RENAME TO hourly_focus"))


def _rebuild_focus_sessions_with_integer_seconds():
    # Preserve journal_json if the old table already has it (so a rebuild never
    # drops journal history). The new table always gets the column.
    old_cols = {c["name"] for c in inspect(engine).get_columns("focus_sessions")}
    has_journal = "journal_json" in old_cols
    has_intention = "intention" in old_cols
    has_workspace = "workspace_id" in old_cols
    journal_select = "COALESCE(journal_json, '[]')" if has_journal else "'[]'"
    intention_select = "COALESCE(intention, '')" if has_intention else "''"
    workspace_select = "COALESCE(workspace_id, 1)" if has_workspace else "1"
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS focus_sessions_new"))
        connection.execute(
            text(
                """
                CREATE TABLE focus_sessions_new (
                    id INTEGER NOT NULL,
                    workspace_id INTEGER NOT NULL DEFAULT 1,
                    task_id INTEGER NOT NULL,
                    task_name VARCHAR NOT NULL,
                    started_at DATETIME NOT NULL,
                    ended_at DATETIME NOT NULL,
                    seconds_focused INTEGER,
                    seconds_distracted INTEGER,
                    seconds_uncertain INTEGER,
                    seconds_away INTEGER,
                    timeline_json VARCHAR,
                    journal_json VARCHAR,
                    intention VARCHAR,
                    PRIMARY KEY (id),
                    FOREIGN KEY(workspace_id) REFERENCES demo_workspaces (id),
                    FOREIGN KEY(task_id) REFERENCES tasks (id)
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                INSERT INTO focus_sessions_new (
                    id,
                    workspace_id,
                    task_id,
                    task_name,
                    started_at,
                    ended_at,
                    seconds_focused,
                    seconds_distracted,
                    seconds_uncertain,
                    seconds_away,
                    timeline_json,
                    journal_json,
                    intention
                )
                SELECT
                    id,
                    {workspace_select},
                    task_id,
                    task_name,
                    started_at,
                    ended_at,
                    CAST(COALESCE(seconds_focused, 0) AS INTEGER),
                    CAST(COALESCE(seconds_distracted, 0) AS INTEGER),
                    CAST(COALESCE(seconds_uncertain, 0) AS INTEGER),
                    CAST(COALESCE(seconds_away, 0) AS INTEGER),
                    COALESCE(timeline_json, '[]'),
                    {journal_select},
                    {intention_select}
                FROM focus_sessions
                """
            )
        )
        connection.execute(text("DROP TABLE focus_sessions"))
        connection.execute(text("ALTER TABLE focus_sessions_new RENAME TO focus_sessions"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_focus_sessions_id ON focus_sessions (id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_focus_sessions_workspace_id ON focus_sessions (workspace_id)")
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
