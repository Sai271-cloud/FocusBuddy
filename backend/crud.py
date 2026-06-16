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

    db_task.completed = update.completed
    db_task.completed_at = datetime.now(timezone.utc) if update.completed else None
    db.commit()
    db.refresh(db_task)
    return db_task


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
    db.commit()
    db.refresh(db_session)
    return db_session


def get_sessions(db: Session) -> list[models.FocusSession]:
    return db.query(models.FocusSession).order_by(models.FocusSession.ended_at.desc()).all()
