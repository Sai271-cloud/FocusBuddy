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
    completed: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None


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
    journal_json: str = "[]"


class SessionStart(BaseModel):
    task_id: int


class SessionUpdate(BaseModel):
    ended_at: Optional[datetime] = None
    seconds_focused: int = Field(0, ge=0)
    seconds_distracted: int = Field(0, ge=0)
    seconds_uncertain: int = Field(0, ge=0)
    seconds_away: int = Field(0, ge=0)
    timeline_json: str = "[]"
    journal_json: str = "[]"


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
    journal_json: str = "[]"

    @field_serializer('started_at', 'ended_at')
    def _ser_dt(self, dt):
        return _as_utc_iso(dt)

    class Config:
        from_attributes = True


class WorkPeriodCreate(BaseModel):
    kind: str = Field(..., pattern="^(day|week)$")
    period_key: str = Field(..., min_length=1)
    ended_at: datetime
    seconds_focused: int = Field(0, ge=0)
    seconds_distracted: int = Field(0, ge=0)
    seconds_uncertain: int = Field(0, ge=0)
    seconds_away: int = Field(0, ge=0)
    # None = "leave as-is" on upsert, so saving the AI recap doesn't wipe a reflection
    # and vice-versa. Pass '' to explicitly clear.
    reflection: Optional[str] = None
    ai_recap: Optional[str] = None


class WorkPeriodOut(BaseModel):
    id: int
    kind: str
    period_key: str
    ended_at: datetime
    seconds_focused: int
    seconds_distracted: int
    seconds_uncertain: int
    seconds_away: int
    reflection: Optional[str] = ''
    ai_recap: Optional[str] = ''

    @field_serializer('ended_at')
    def _ser_dt(self, dt):
        return _as_utc_iso(dt)

    class Config:
        from_attributes = True


class FocusAnalyzeRequest(BaseModel):
    frame_base64: str
    task_name: str
    description: str = ''
    current_url: Optional[str] = None
    current_title: Optional[str] = None
    explain: bool = False
    sensors: Optional[str] = None


class FocusAnalyzeResponse(BaseModel):
    state: str
    note: str = ''
    reason: str = ''


class ActivityIn(BaseModel):
    url: str
    title: Optional[str] = None


class ActivityOut(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None


class TrackingState(BaseModel):
    active: bool


class ProfileIn(BaseModel):
    about: str = ''


class ProfileOut(BaseModel):
    about: str = ''

    class Config:
        from_attributes = True


class DebriefResponse(BaseModel):
    summary: str = ''
    win: str = ''                   # one concrete thing they did well (positive reinforcement)
    patterns: list[str] = []
    suggestions: list[str] = []
    next_action: str = ''           # single highest-leverage step, implementation-intention phrased


class DailyUnwindRequest(BaseModel):
    session_ids: list[int] = []
    recent_avg_focus_pct: Optional[float] = None  # frontend-computed avg of recent days
    period_key: Optional[str] = None              # local YYYY-MM-DD, for labeling only


class DailyUnwindResponse(BaseModel):
    summary: str = ''
    win: str = ''                   # one concrete win today (positive reinforcement)
    pattern_notes: list[str] = []   # where today matched or broke the user's patterns
    advice: list[str] = []
    next_action: str = ''           # single implementation-intention step for tomorrow
    shutdown_question: str = ''     # one reflective end-of-day question (detachment ritual)


class WeeklyDay(BaseModel):
    label: str = ''                 # e.g. "Monday"
    date: Optional[str] = None      # local YYYY-MM-DD
    seconds_focused: int = 0
    seconds_distracted: int = 0
    seconds_uncertain: int = 0
    seconds_away: int = 0
    daily_recap: Optional[str] = None   # saved daily ai_recap JSON string, if the user unwound that day
    top_task: Optional[str] = None


class WeeklyUnwindRequest(BaseModel):
    week_key: Optional[str] = None      # local Monday key, for labeling + excluding from trend
    days: list[WeeklyDay] = []
    pomo_focus_min: Optional[int] = None
    pomo_break_min: Optional[int] = None
    pomo_enabled: Optional[bool] = None


class PomodoroSuggestion(BaseModel):
    recommend: bool = False
    focus_min: int = 25
    break_min: int = 5
    why: str = ''


class WeeklyUnwindResponse(BaseModel):
    summary: str = ''
    theme: str = ''                 # one-line headline for the week
    insights: list[str] = []        # most-productive day+time, trend, top tasks, distractions
    improvements: list[str] = []    # only when the AI detects a real problem (else empty)
    next_week_focus: str = ''       # one concrete forward strategy for next week
    pomodoro: PomodoroSuggestion = PomodoroSuggestion()


class ObservationOut(BaseModel):
    id: int
    text: str
    affirmations: int
    rejections: int
    active: bool
    status: str = 'emerging'  # emerging | confirmed | retired (filled by the endpoint)

    class Config:
        from_attributes = True


class LearnRequest(BaseModel):
    # Local clock hours (0-23) the session started and ended in, computed by the
    # frontend (the backend stores UTC and does no timezone math). Used to fold the
    # session's focus % into the hourly profile. Optional so the call still works
    # without them.
    start_hour: Optional[int] = Field(None, ge=0, le=23)
    end_hour: Optional[int] = Field(None, ge=0, le=23)


class LearnResult(BaseModel):
    updated: int = 0       # how many observations were affirmed/rejected/added
    hours_updated: int = 0  # how many hourly-focus rows this session touched


class HourlyFocusOut(BaseModel):
    hour: int
    focus_pct: float
    sessions: int

    class Config:
        from_attributes = True
