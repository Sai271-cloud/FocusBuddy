from pydantic import BaseModel, Field, field_serializer
from datetime import datetime, timezone
from typing import Optional


def _as_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ''


class TaskOut(BaseModel):
    id: int
    name: str
    description: str
    completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime

    @field_serializer('created_at', 'completed_at')
    def _ser_dt(self, dt):
        return _as_utc_iso(dt)

    class Config:
        from_attributes = True


class TaskUpdate(BaseModel):
    completed: bool


class SessionCreate(BaseModel):
    task_id: int
    task_name: str = ''
    started_at: datetime
    ended_at: datetime
    seconds_focused: int = Field(0, ge=0)
    seconds_distracted: int = Field(0, ge=0)
    seconds_uncertain: int = Field(0, ge=0)
    seconds_away: int = Field(0, ge=0)
    timeline_json: str = "[]"


class SessionStart(BaseModel):
    task_id: int


class SessionUpdate(BaseModel):
    ended_at: Optional[datetime] = None
    seconds_focused: int = Field(0, ge=0)
    seconds_distracted: int = Field(0, ge=0)
    seconds_uncertain: int = Field(0, ge=0)
    seconds_away: int = Field(0, ge=0)
    timeline_json: str = "[]"


class SessionOut(BaseModel):
    id: int
    task_id: int
    task_name: str
    started_at: datetime
    ended_at: datetime
    seconds_focused: int
    seconds_distracted: int
    seconds_uncertain: int
    seconds_away: int
    timeline_json: str

    @field_serializer('started_at', 'ended_at')
    def _ser_dt(self, dt):
        return _as_utc_iso(dt)

    class Config:
        from_attributes = True


class FocusAnalyzeRequest(BaseModel):
    frame_base64: str
    task_name: str
    description: str = ''


class FocusAnalyzeResponse(BaseModel):
    state: str
