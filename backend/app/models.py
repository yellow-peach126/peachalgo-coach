from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class UserProfile(SQLModel, table=True):
    id: str = Field(default="local", primary_key=True)
    language: str = "python"
    level: str = "easy"
    goal: str = "campus"
    daily_minutes: int = 60
    horizon_days: int = 60
    weak_tags_json: str = "[]"
    rating: int = 1000
    onboarded: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="local", index=True)
    status: str = "active"  # active | archived
    start_date: date = Field(default_factory=date.today)
    horizon_days: int = 60
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(index=True)
    problem_id: str = Field(index=True)
    scheduled_date: date = Field(index=True)
    item_type: str = "main"  # main | review | weak
    status: str = "pending"  # pending | done | skipped
    reason: str = ""
    sort_order: int = 0


class Attempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="local", index=True)
    problem_id: str = Field(index=True)
    plan_item_id: Optional[int] = Field(default=None, index=True)
    result: str
    felt_difficulty: str
    minutes_spent: int
    note: str = ""
    performance: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SkillStat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="local", index=True)
    tag: str = Field(index=True)
    mastery: float = 50.0
    attempts: int = 0
    solo_ac: int = 0
    last_seen_at: Optional[datetime] = None


class ReviewCard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="local", index=True)
    problem_id: str = Field(index=True)
    ease: float = 2.5
    interval_days: int = 1
    due_at: date = Field(default_factory=date.today)
    reps: int = 0
