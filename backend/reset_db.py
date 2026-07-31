from pathlib import Path

if __package__ in {None, ""}:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from backend.database import Base, DATABASE_PATH, engine
    from backend import models
else:
    from .database import Base, DATABASE_PATH, engine
    from . import models

def reset_db():
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    Base.metadata.create_all(bind=engine)
    print(f"Reset database at {DATABASE_PATH}")

if __name__ == "__main__":
    reset_db()
