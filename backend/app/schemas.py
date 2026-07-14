from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


Language = Literal[
    "python",
    "java",
    "cpp",
    "c",
    "csharp",
    "go",
    "javascript",
    "typescript",
    "mysql",
    "rust",
    "kotlin",
    "swift",
    "php",
    "ruby",
]
Level = Literal["beginner", "easy", "medium", "advanced"]
Goal = Literal["campus", "social", "foundation", "contest", "database"]
AttemptResult = Literal["solved_solo", "solved_hint", "solved_solution", "failed"]
FeltDifficulty = Literal["too_easy", "ok", "hard", "very_hard"]


class OnboardingRequest(BaseModel):
    language: Language = "python"
    level: Level = "easy"
    goal: Goal = "campus"
    daily_minutes: int = Field(default=60, ge=20, le=240)
    horizon_days: int = Field(default=60, ge=14, le=180)
    weak_tags: list[str] = Field(default_factory=list)


class ProblemOut(BaseModel):
    id: str
    number: int
    frontend_id: str = ""
    title: str
    title_zh: Optional[str] = None
    difficulty: str
    difficulty_zh: str = ""
    tags: list[str]
    tags_zh: list[str] = Field(default_factory=list)
    est_minutes: int
    is_template: bool
    stage: str
    stage_zh: str = ""
    url: str
    url_en: Optional[str] = None
    priority: int
    paid_only: bool = False
    source: str = "leetcode"
    completed: bool = False
    completed_result: Optional[str] = None
    completed_result_zh: str = ""
    completed_at: Optional[datetime] = None


class TodayItemOut(BaseModel):
    plan_item_id: int
    problem: ProblemOut
    item_type: str
    item_type_zh: str = ""
    status: str
    status_zh: str = ""
    reason: str
    scheduled_date: date


class TodayDoneItemOut(BaseModel):
    attempt_id: int
    plan_item_id: Optional[int] = None
    problem: ProblemOut
    result: str
    result_zh: str = ""
    felt_difficulty: str
    felt_difficulty_zh: str = ""
    minutes_spent: int
    created_at: datetime
    can_undo: bool = True


class TodayResponse(BaseModel):
    date: date
    onboarded: bool
    daily_minutes: int
    items: list[TodayItemOut]
    done_items: list[TodayDoneItemOut] = Field(default_factory=list)
    total_est_minutes: int
    remaining_est_minutes: int = 0
    spent_minutes: int = 0
    streak_days: int = 0
    message: str = ""
    source_note: str = ""


class AttemptCreate(BaseModel):
    problem_id: str
    result: AttemptResult
    felt_difficulty: FeltDifficulty
    minutes_spent: int = Field(ge=1, le=600)
    note: str = ""
    plan_item_id: Optional[int] = None


class FeedbackChangeItem(BaseModel):
    kind: str  # rating | mastery | plan | review | checkin | restore
    label: str
    detail: str = ""


class FeedbackSummary(BaseModel):
    """Structured after-effect of submit/undo so the UI can show 'what changed'."""

    rating_before: int = 1000
    rating_after: int = 1000
    rating_delta: int = 0
    mastery_before: dict[str, float] = Field(default_factory=dict)
    mastery_after: dict[str, float] = Field(default_factory=dict)
    changes: list[FeedbackChangeItem] = Field(default_factory=list)
    checked_today: bool = False
    current_streak: int = 0
    review_scheduled: bool = False


class AttemptOut(BaseModel):
    id: int
    problem_id: str
    plan_item_id: Optional[int] = None
    result: str
    felt_difficulty: str
    minutes_spent: int
    performance: float
    created_at: datetime
    mastery_updates: dict[str, float] = Field(default_factory=dict)
    summary: Optional[FeedbackSummary] = None
    message: str = ""


class UndoAttemptOut(BaseModel):
    attempt_id: int
    problem_id: str
    restored_plan_item_id: Optional[int] = None
    mastery_updates: dict[str, float] = Field(default_factory=dict)
    summary: Optional[FeedbackSummary] = None
    message: str = ""


class SkipRequest(BaseModel):
    plan_item_id: int
    to_date: Optional[date] = None


class AddTodayRequest(BaseModel):
    problem_ids: list[str] = Field(min_length=1)
    date: Optional[date] = None


class AddTodayResponse(BaseModel):
    items: list["PlanItemOut"] = Field(default_factory=list)
    added: int = 0
    skipped_existing: int = 0
    skipped_invalid: int = 0
    message: str = ""


class ProfileOut(BaseModel):
    id: str
    language: str
    language_label: str = ""
    level: str
    level_label: str = ""
    level_criteria: str = ""
    goal: str
    goal_label: str = ""
    daily_minutes: int
    horizon_days: int
    weak_tags: list[str]
    weak_tags_zh: list[str] = Field(default_factory=list)
    rating: int
    onboarded: bool


class PlanItemOut(BaseModel):
    id: int
    problem_id: str
    title: str
    title_zh: Optional[str] = None
    difficulty: str
    difficulty_zh: str = ""
    scheduled_date: date
    item_type: str
    item_type_zh: str = ""
    status: str
    status_zh: str = ""
    reason: str
    stage: str
    stage_zh: str = ""
    url: str
    tags_zh: list[str] = Field(default_factory=list)


class PlanOut(BaseModel):
    id: int
    status: str
    start_date: date
    horizon_days: int
    total_items: int
    done_items: int
    items: list[PlanItemOut]


class SkillOut(BaseModel):
    tag: str
    tag_zh: str
    mastery: float
    attempts: int
    solo_ac: int


class StatsOut(BaseModel):
    rating: int
    total_attempts: int
    solo_ac_rate: float
    completed_problems: int
    skills: list[SkillOut]
    weak_top: list[str]
    weak_top_zh: list[str] = Field(default_factory=list)
    message: str = ""


class CheckinDayOut(BaseModel):
    date: date
    checked: bool
    attempts: int = 0
    minutes_spent: int = 0
    is_today: bool = False


class CheckinOut(BaseModel):
    year: int
    month: int
    days: list[CheckinDayOut] = Field(default_factory=list)
    checked_dates: list[date] = Field(default_factory=list)
    current_streak: int = 0
    longest_streak: int = 0
    total_checkin_days: int = 0
    month_checkin_days: int = 0
    checked_today: bool = False
    message: str = ""


class ReviewItemOut(BaseModel):
    problem: ProblemOut
    due_at: date
    interval_days: int
    reps: int


class HealthOut(BaseModel):
    status: str
    app: str
    problems_loaded: int


class MetaOut(BaseModel):
    app_name: str
    source_note: str
    languages: list[dict[str, str]]
    levels: list[dict[str, str]]
    goals: list[dict[str, str]]
    stages: list[dict[str, str]]
    tags: list[dict[str, str]]
    difficulties: list[dict[str, str]]
    catalog: dict
