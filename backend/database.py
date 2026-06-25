from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_PATH = Path(__file__).resolve().with_name("focus_buddy.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db():
    from . import models

    Base.metadata.create_all(bind=engine)
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
    if "tasks" not in table_names:
        return

    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
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

def _rebuild_focus_sessions_with_integer_seconds():
    # Preserve journal_json if the old table already has it (so a rebuild never
    # drops journal history). The new table always gets the column.
    old_cols = {c["name"] for c in inspect(engine).get_columns("focus_sessions")}
    has_journal = "journal_json" in old_cols
    has_intention = "intention" in old_cols
    journal_select = "COALESCE(journal_json, '[]')" if has_journal else "'[]'"
    intention_select = "COALESCE(intention, '')" if has_intention else "''"
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS focus_sessions_new"))
        connection.execute(
            text(
                """
                CREATE TABLE focus_sessions_new (
                    id INTEGER NOT NULL,
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
