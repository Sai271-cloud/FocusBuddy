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


def _rebuild_focus_sessions_with_integer_seconds():
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
                    PRIMARY KEY (id),
                    FOREIGN KEY(task_id) REFERENCES tasks (id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
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
                    timeline_json
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
                    COALESCE(timeline_json, '[]')
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
