import os
import re
import base64
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .database import get_db, init_db
from . import crud, models, schemas

load_dotenv()

logger = logging.getLogger("focus_buddy")

init_db()

_gemini_key = os.getenv("GEMINI_API_KEY")
_client = None
if _gemini_key:
    _client = genai.Client(
        api_key=_gemini_key,
        http_options=types.HttpOptions(timeout=15_000),
    )

GEMINI_MODEL = "gemini-3.5-flash"

VALID_STATES = ["focused", "distracted", "uncertain", "away"]
_VALID_SET = set(VALID_STATES)
MAX_FRAME_BASE64_CHARS = 1_400_000
MAX_FRAME_BYTES = 1_000_000

app = FastAPI(title="Focus Buddy API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/tasks", response_model=schemas.TaskOut)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    if not task.name.strip():
        raise HTTPException(status_code=400, detail="Task name cannot be empty")
    return crud.create_task(db, task)


@app.get("/tasks", response_model=list[schemas.TaskOut])
def get_tasks(db: Session = Depends(get_db)):
    return crud.get_tasks(db)


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, update: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, task_id)
    return crud.update_task(db, task, update)


def _get_task_or_404(db: Session, task_id: int):
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/sessions", response_model=schemas.SessionOut)
def create_session(session: schemas.SessionCreate, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, session.task_id)
    return crud.create_session(db, session, task)


@app.post("/sessions/start", response_model=schemas.SessionOut)
def start_session(session: schemas.SessionStart, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, session.task_id)
    return crud.start_session(db, task)


@app.patch("/sessions/{session_id}", response_model=schemas.SessionOut)
def update_session(
    session_id: int,
    update: schemas.SessionUpdate,
    db: Session = Depends(get_db),
):
    session = db.get(models.FocusSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return crud.update_session(db, session, update)


@app.post("/sessions/{session_id}/finish", response_model=schemas.SessionOut)
def finish_session(
    session_id: int,
    update: schemas.SessionUpdate,
    db: Session = Depends(get_db),
):
    session = db.get(models.FocusSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return crud.update_session(db, session, update)


@app.get("/sessions", response_model=list[schemas.SessionOut])
def get_sessions(db: Session = Depends(get_db)):
    return crud.get_sessions(db)


def _parse_state(reply_text: str) -> str:
    text = (reply_text or "").lower()
    for word in re.findall(r"[a-z]+", text):
        if word in _VALID_SET:
            return word
    return "uncertain"


@app.post("/focus/analyze", response_model=schemas.FocusAnalyzeResponse)
def analyze_focus(request: schemas.FocusAnalyzeRequest):
    if _client is None:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not set in .env")

    if len(request.frame_base64) > MAX_FRAME_BASE64_CHARS:
        raise HTTPException(status_code=413, detail="Frame data is too large")

    try:
        image_bytes = base64.b64decode(request.frame_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 frame data")

    if len(image_bytes) > MAX_FRAME_BYTES:
        raise HTTPException(status_code=413, detail="Frame image is too large")

    detail = f'\nMore detail on the task: "{request.description}"' if request.description else ''
    prompt = f"""You are a focus detection system analyzing a single webcam frame.

The person's current task is: "{request.task_name}"{detail}

Choose the ONE state that best fits the image:
- focused: looking at their screen/task and appears engaged
- distracted: present but not engaged (looking away, on phone, talking, etc.)
- uncertain: present but their focus is genuinely unclear
- away: no person visible, or they have clearly left

Reply with ONE word only: focused, distracted, uncertain, or away."""

    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt,
            ],
        )
        return schemas.FocusAnalyzeResponse(state=_parse_state(response.text))
    except Exception:
        logger.exception("Gemini call failed")
        raise HTTPException(status_code=502, detail="Focus analysis is temporarily unavailable")
