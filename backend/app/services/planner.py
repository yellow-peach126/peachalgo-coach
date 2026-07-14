"""Initial learning plan generation."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable
import json

from sqlmodel import Session, select

from app.catalog import get_problem_map, get_stages, list_problems
from app.constants import STAGE_ZH
from app.models import Plan, PlanItem, UserProfile
from app.schemas import OnboardingRequest, ProblemOut


LEVEL_MAX_DIFFICULTY = {
    "beginner": {"Easy"},
    "easy": {"Easy", "Medium"},
    "medium": {"Easy", "Medium", "Hard"},
    "advanced": {"Easy", "Medium", "Hard"},
}

LEVEL_START_STAGE = {
    "beginner": "array-hash",
    "easy": "array-hash",
    "medium": "two-pointers",
    "advanced": "binary-tree",
}

GOAL_TAG_BOOST = {
    "campus": {"array", "hash-table", "tree", "binary-tree", "dynamic-programming", "dfs", "bfs"},
    "social": {"array", "hash-table", "string", "two-pointers", "dynamic-programming"},
    "foundation": {"array", "string", "hash-table", "linked-list", "stack"},
    "contest": {"binary-search", "greedy", "graph", "dynamic-programming", "backtracking"},
    "database": {"database"},
}


def _allowed(problem: ProblemOut, level: str, goal: str) -> bool:
    if problem.paid_only:
        return False
    if goal == "database":
        return "database" in problem.tags or problem.stage == "database"
    if goal != "database" and problem.stage == "database":
        # SQL track only when user chooses database goal / mysql focus later via goal
        return False
    return problem.difficulty in LEVEL_MAX_DIFFICULTY.get(level, {"Easy", "Medium"})


def _score_problem(problem: ProblemOut, profile: OnboardingRequest) -> float:
    score = 1000 - problem.priority
    if problem.is_template:
        score += 40
    weak = set(profile.weak_tags)
    score += 25 * len(weak.intersection(problem.tags))
    boost = GOAL_TAG_BOOST.get(profile.goal, set())
    score += 10 * len(boost.intersection(problem.tags))
    if profile.level == "beginner" and problem.difficulty == "Easy":
        score += 20
    if profile.level == "advanced" and problem.difficulty == "Hard":
        score += 15
    if profile.language == "mysql" and ("database" in problem.tags or problem.stage == "database"):
        score += 50
    # Prefer lower numbers / classic problems slightly for stability
    if 0 < problem.number <= 300:
        score += 8
    return score


def _ordered_problems(profile: OnboardingRequest) -> list[ProblemOut]:
    stages = get_stages()
    stage_order = {s["id"]: s.get("order", 0) for s in stages}
    if profile.goal == "database" or profile.language == "mysql":
        start = "database"
    else:
        start = LEVEL_START_STAGE.get(profile.level, "array-hash")
    start_order = stage_order.get(start, 0)

    # For planning, prefer templates + early numbers first to keep plan size sane.
    # We still schedule across horizon_days; list_problems returns free problems only.
    all_candidates = [
        p
        for p in list_problems()
        if _allowed(p, profile.level, profile.goal)
        and (
            profile.goal == "database"
            or profile.language == "mysql"
            or stage_order.get(p.stage, 0) >= start_order
        )
    ]

    # Cap candidate pool for performance while keeping quality:
    # templates first, then medium-priority classics.
    templates = [p for p in all_candidates if p.is_template]
    others = [p for p in all_candidates if not p.is_template]
    others.sort(key=lambda p: (-_score_problem(p, profile), p.number))
    # keep enough for ~horizon*3 items
    need = max(profile.horizon_days * 3, 120)
    candidates = templates + others[: max(0, need - len(templates))]

    candidates.sort(
        key=lambda p: (
            stage_order.get(p.stage, 99),
            0 if p.is_template else 1,
            -_score_problem(p, profile),
            p.number,
        )
    )
    return candidates


def _pack_daily(
    problems: Iterable[ProblemOut],
    *,
    start: date,
    horizon_days: int,
    daily_minutes: int,
) -> list[tuple[date, ProblemOut, str]]:
    budget = max(30, int(daily_minutes * 0.9))
    max_per_day = 4 if daily_minutes >= 90 else 3 if daily_minutes >= 45 else 2

    queue = list(problems)
    schedule: list[tuple[date, ProblemOut, str]] = []
    idx = 0
    day = start

    while idx < len(queue) and (day - start).days < horizon_days:
        used = 0
        count = 0
        while idx < len(queue) and count < max_per_day:
            p = queue[idx]
            if count > 0 and used + p.est_minutes > budget:
                break
            schedule.append((day, p, _reason_for(p)))
            used += p.est_minutes
            count += 1
            idx += 1
        day += timedelta(days=1)

    return schedule


def _reason_for(problem: ProblemOut) -> str:
    stage = problem.stage_zh or STAGE_ZH.get(problem.stage, problem.stage)
    kind = "模板题" if problem.is_template else "巩固题"
    return f"主线推进：{stage} 阶段的{kind}"


def archive_active_plans(session: Session, user_id: str = "local") -> None:
    plans = session.exec(
        select(Plan).where(Plan.user_id == user_id, Plan.status == "active")
    ).all()
    for plan in plans:
        plan.status = "archived"
        session.add(plan)


def create_plan_from_onboarding(
    session: Session,
    payload: OnboardingRequest,
    *,
    user_id: str = "local",
) -> tuple[UserProfile, Plan, list[PlanItem]]:
    profile = session.get(UserProfile, user_id)
    if profile is None:
        profile = UserProfile(id=user_id)

    # If user chose mysql language, default goal boost toward database unless explicit contest etc.
    goal = payload.goal
    if payload.language == "mysql" and payload.goal in {"campus", "social", "foundation"}:
        goal = "database"

    profile.language = payload.language
    profile.level = payload.level
    profile.goal = goal
    profile.daily_minutes = payload.daily_minutes
    profile.horizon_days = payload.horizon_days
    profile.weak_tags_json = json.dumps(payload.weak_tags, ensure_ascii=False)
    profile.onboarded = True
    profile.updated_at = datetime.utcnow()
    session.add(profile)

    archive_active_plans(session, user_id)

    plan = Plan(
        user_id=user_id,
        status="active",
        start_date=date.today(),
        horizon_days=payload.horizon_days,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)

    ordered = _ordered_problems(
        OnboardingRequest(
            language=payload.language,
            level=payload.level,
            goal=goal,
            daily_minutes=payload.daily_minutes,
            horizon_days=payload.horizon_days,
            weak_tags=payload.weak_tags,
        )
    )
    packed = _pack_daily(
        ordered,
        start=plan.start_date,
        horizon_days=payload.horizon_days,
        daily_minutes=payload.daily_minutes,
    )

    items: list[PlanItem] = []
    for order, (scheduled_date, problem, reason) in enumerate(packed):
        item = PlanItem(
            plan_id=plan.id,
            problem_id=problem.id,
            scheduled_date=scheduled_date,
            item_type="main",
            status="pending",
            reason=reason,
            sort_order=order,
        )
        session.add(item)
        items.append(item)

    session.commit()
    for item in items:
        session.refresh(item)
    session.refresh(plan)
    session.refresh(profile)
    return profile, plan, items


def get_active_plan(session: Session, user_id: str = "local") -> Plan | None:
    return session.exec(
        select(Plan)
        .where(Plan.user_id == user_id, Plan.status == "active")
        .order_by(Plan.id.desc())
    ).first()


def add_problems_to_today(
    session: Session,
    problem_ids: list[str],
    *,
    on: date | None = None,
    user_id: str = "local",
) -> dict:
    """Add problems to today's queue.

    Returns {items, added, skipped_existing, skipped_invalid}.
    """
    on = on or date.today()
    plan = get_active_plan(session, user_id)
    if plan is None:
        raise RuntimeError("no active plan")

    problem_map = get_problem_map()
    created: list[PlanItem] = []
    existing = session.exec(
        select(PlanItem).where(
            PlanItem.plan_id == plan.id,
            PlanItem.scheduled_date == on,
            PlanItem.status == "pending",
        )
    ).all()
    existing_ids = {e.problem_id for e in existing}
    sort_base = max([e.sort_order for e in existing], default=0)

    skipped_existing = 0
    skipped_invalid = 0
    for i, pid in enumerate(problem_ids):
        if pid in existing_ids:
            skipped_existing += 1
            continue
        problem = problem_map.get(pid)
        if problem is None or problem.paid_only:
            skipped_invalid += 1
            continue
        item = PlanItem(
            plan_id=plan.id,
            problem_id=pid,
            scheduled_date=on,
            item_type="custom",
            status="pending",
            reason="自行添加：你选择加入今日任务",
            sort_order=sort_base + i + 1,
        )
        session.add(item)
        created.append(item)
        existing_ids.add(pid)

    session.commit()
    for item in created:
        session.refresh(item)
    return {
        "items": created,
        "added": len(created),
        "skipped_existing": skipped_existing,
        "skipped_invalid": skipped_invalid,
    }


def remove_problems_from_today(
    session: Session,
    *,
    problem_ids: list[str] | None = None,
    plan_item_ids: list[int] | None = None,
    on: date | None = None,
    user_id: str = "local",
) -> dict:
    """Withdraw *bank-added* problems from today's pending queue.

    Only ``item_type == "custom"`` items can be withdrawn. Roadmap items
    (main / review / weak) are never deleted or rescheduled here — they
    stay on the learning path and remain on today's task list.
    """
    on = on or date.today()
    plan = get_active_plan(session, user_id)
    if plan is None:
        raise RuntimeError("no active plan")

    problem_ids = problem_ids or []
    plan_item_ids = plan_item_ids or []

    candidates: list[PlanItem] = []
    if plan_item_ids:
        for pid in plan_item_ids:
            item = session.get(PlanItem, pid)
            if item is not None and item.plan_id == plan.id:
                candidates.append(item)

    if problem_ids:
        rows = session.exec(
            select(PlanItem).where(
                PlanItem.plan_id == plan.id,
                PlanItem.problem_id.in_(problem_ids),  # type: ignore[attr-defined]
                PlanItem.scheduled_date == on,
                PlanItem.status == "pending",
            )
        ).all()
        for row in rows:
            if all(row.id != c.id for c in candidates):
                candidates.append(row)

    removed = 0
    skipped = 0
    skipped_roadmap = 0
    for item in candidates:
        if item.status != "pending" or item.scheduled_date != on:
            skipped += 1
            continue
        # Only user-picked bank adds may be withdrawn from today.
        if item.item_type != "custom":
            skipped_roadmap += 1
            skipped += 1
            continue
        session.delete(item)
        removed += 1

    session.commit()
    return {
        "removed": removed,
        "skipped": skipped,
        "skipped_roadmap": skipped_roadmap,
    }


def repair_withdrawn_roadmap_items(
    session: Session,
    *,
    user_id: str = "local",
    on: date | None = None,
) -> int:
    """Undo accidental roadmap reschedules from the old withdraw behavior.

    Restores main/review/weak items that were pushed to tomorrow with the
    ``已从今日撤回选择`` marker back onto ``on`` (default: today).
    """
    on = on or date.today()
    plan = get_active_plan(session, user_id)
    if plan is None:
        return 0
    marker = "已从今日撤回选择"
    rows = session.exec(
        select(PlanItem).where(
            PlanItem.plan_id == plan.id,
            PlanItem.status == "pending",
            PlanItem.item_type != "custom",
        )
    ).all()
    fixed = 0
    for item in rows:
        reason = item.reason or ""
        if marker not in reason:
            continue
        item.reason = (
            reason.replace(" · " + marker, "")
            .replace(marker, "")
            .strip(" ·")
        )
        # Only pull back one day if it was deferred by the old withdraw path.
        if item.scheduled_date == on + timedelta(days=1):
            item.scheduled_date = on
        session.add(item)
        fixed += 1
    if fixed:
        session.commit()
    return fixed
