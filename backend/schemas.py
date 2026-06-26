import json
from pydantic import BaseModel, Field, StrictInt, field_serializer, field_validator
from datetime import datetime, timezone
from typing import Literal, Optional


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
    intention: str = ''


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
    intention: Optional[str] = None


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
    intention: Optional[str] = ''

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
    plan_reality_json: Optional[str] = None


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
    plan_reality_json: Optional[str] = ''

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
    plan_reality_summary: Optional[str] = None    # deterministic plan-vs-reality line, if available


class DailyUnwindResponse(BaseModel):
    summary: str = ''
    plan_echo: str = ''             # short echo of planned vs actual, computed from provided plan summary
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


class PlanEntry(BaseModel):
    task_id: int
    name: str = ''                       # snapshot, so a later task-delete doesn't blank the plan
    estimate_min: int = Field(0, ge=0)
    difficulty: Literal['easy', 'medium', 'hard'] = 'medium'
    # User-placed start time, minutes from local midnight (0-1439). None = unscheduled (in
    # the tray). Named scheduled_min — NOT start_min — to stay distinct from
    # ScheduledBlock.start_min, which is a minute-within-hour.
    scheduled_min: Optional[StrictInt] = Field(None, ge=0, le=1439)


class DailyPlanUpsert(BaseModel):
    period_key: str = Field(..., min_length=1)   # local YYYY-MM-DD (frontend-computed)
    # None = "leave as-is" on upsert so a plan-only save and an advice-only save don't
    # clobber each other (same idiom as WorkPeriodCreate). '' on advice_json clears it.
    available_min: Optional[int] = Field(None, ge=0)
    plan_json: Optional[str] = None      # JSON list of PlanEntry
    advice_json: Optional[str] = None    # JSON advice blob (Chunk B)

    @field_validator('plan_json')
    @classmethod
    def _validate_plan_json(cls, value):
        if value is None:
            return value
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError('plan_json must be a JSON list') from exc
        if not isinstance(parsed, list):
            raise ValueError('plan_json must be a JSON list')
        for i, item in enumerate(parsed):
            if not isinstance(item, dict):
                raise ValueError(f'plan_json[{i}] must be an object')
            try:
                PlanEntry.model_validate(item)
            except Exception as exc:
                raise ValueError(f'plan_json[{i}] must match the PlanEntry schema') from exc
        return value


class DailyPlanOut(BaseModel):
    period_key: str
    available_min: int = 0
    plan_json: str = "[]"
    advice_json: Optional[str] = None

    class Config:
        from_attributes = True


class ScheduledBlock(BaseModel):
    task_id: int
    start_hour: int = 9        # 0-23 (local)
    start_min: int = 0         # 0-59
    length_min: int = 0
    reason: str = ''


class PlanAdviceRequest(BaseModel):
    period_key: Optional[str] = None        # local YYYY-MM-DD (labeling/calibration only)
    available_min: int = Field(0, ge=0)
    entries: list[PlanEntry] = []


class PlanAdviceResponse(BaseModel):
    summary: str = ''
    cold_start: bool = False        # too little hourly history to schedule by peak hours
    scheduled: list[ScheduledBlock] = []
    over_plan_note: str = ''        # set only when estimates exceed available time
    general_advice: list[str] = []  # gated: empty when patterns/profile are too thin


class PlanRealityRow(BaseModel):
    task_id: int
    name: str = ''
    planned_start_min: Optional[int] = None
    planned_estimate_min: int = 0
    actual_start_min: Optional[int] = None
    actual_total_min: int = 0
    actual_focused_min: int = 0
    start_delta_min: Optional[int] = None
    duration_delta_min: int = 0
    session_ids: list[int] = []
    status: Literal[
        'not_started',
        'on_track',
        'started_late',
        'started_early',
        'ran_short',
        'ran_long',
        'unscheduled_work',
    ] = 'not_started'


class PlanRealityReport(BaseModel):
    period_key: str
    has_plan: bool = False
    planned_total_min: int = 0
    actual_total_min: int = 0
    focused_total_min: int = 0
    rows: list[PlanRealityRow] = Field(default_factory=list)
    summary: str = ''


class PlanCalibrationItem(BaseModel):
    task_id: Optional[int] = None
    name: str = 'Overall'
    samples: int = 0
    avg_delta_min: int = 0
    avg_delta_pct: int = 0
    tendency: Literal['under', 'over', 'mixed', 'unknown'] = 'unknown'
    message: str = ''


class PlanCalibrationResponse(BaseModel):
    overall: PlanCalibrationItem = Field(default_factory=PlanCalibrationItem)
    by_task: list[PlanCalibrationItem] = Field(default_factory=list)


class PlanRescheduleRequest(BaseModel):
    period_key: Optional[str] = None
    entries: list[PlanEntry] = Field(default_factory=list)
    current_min: int = Field(..., ge=0, le=1439)
    day_end_min: int = Field(23 * 60, ge=1, le=1440)
    actual_by_task: dict[int, int] = Field(default_factory=dict)
    completed_task_ids: list[int] = Field(default_factory=list)


class PlanRescheduleResponse(BaseModel):
    summary: str = ''
    scheduled: list[ScheduledBlock] = Field(default_factory=list)
    over_plan_note: str = ''
