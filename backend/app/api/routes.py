from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.catalog import (
    catalog_stats,
    get_problem_map,
    get_stages,
    list_problems,
    load_catalog,
    tag_zh_map,
)
from app.config import settings
from app.constants import (
    APP_NAME,
    DIFFICULTY_ZH,
    GOALS,
    ITEM_TYPE_ZH,
    LANGUAGES,
    LEVELS,
    SOURCE_NOTE,
    STAGE_ZH,
)
from app.db import get_session
from app.models import Attempt, PlanItem, UserProfile
from app.schemas import (
    AddTodayRequest,
    AddTodayResponse,
    RemoveTodayRequest,
    RemoveTodayResponse,
    AttemptCreate,
    AttemptOut,
    CheckinOut,
    HealthOut,
    MetaOut,
    OnboardingRequest,
    PlanItemOut,
    PlanOut,
    ProblemOut,
    ProfileOut,
    ReviewItemOut,
    SkipRequest,
    StatsOut,
    TodayDoneItemOut,
    TodayItemOut,
    TodayResponse,
    UndoAttemptOut,
)
from app.services.adapter import record_attempt, skip_plan_item, undo_attempt
from app.services.checkin import get_checkins
from app.services.planner import (
    add_problems_to_today,
    create_plan_from_onboarding,
    get_active_plan,
    remove_problems_from_today,
    repair_withdrawn_roadmap_items,
)
from app.services.review import list_due_reviews
from app.services.stats import get_stats

router = APIRouter(prefix="/api")

STATUS_ZH = {
    "pending": "待完成",
    "done": "已完成",
    "skipped": "已跳过",
}

RESULT_ZH = {
    "solved_solo": "独立通过",
    "solved_hint": "看提示后通过",
    "solved_solution": "看题解后通过",
    "failed": "未完成",
}

FELT_ZH = {
    "too_easy": "太简单",
    "ok": "刚好",
    "hard": "偏难",
    "very_hard": "很难",
}


def _lang_label(language: str) -> str:
    for item in LANGUAGES:
        if item["id"] == language:
            return item["label"]
    return language


def _level_meta(level: str) -> tuple[str, str]:
    for item in LEVELS:
        if item["id"] == level:
            return item["label"], item["criteria"]
    return level, ""


def _goal_label(goal: str) -> str:
    for item in GOALS:
        if item["id"] == goal:
            return item["label"]
    return goal


def _profile_out(profile: UserProfile | None) -> ProfileOut:
    if profile is None:
        return ProfileOut(
            id="local",
            language="python",
            language_label="Python",
            level="easy",
            level_label="能做简单题",
            level_criteria="",
            goal="campus",
            goal_label="校招面试",
            daily_minutes=60,
            horizon_days=60,
            weak_tags=[],
            weak_tags_zh=[],
            rating=1000,
            onboarded=False,
        )
    try:
        weak = json.loads(profile.weak_tags_json or "[]")
    except json.JSONDecodeError:
        weak = []
    mapping = tag_zh_map()
    level_label, level_criteria = _level_meta(profile.level)
    return ProfileOut(
        id=profile.id,
        language=profile.language,
        language_label=_lang_label(profile.language),
        level=profile.level,
        level_label=level_label,
        level_criteria=level_criteria,
        goal=profile.goal,
        goal_label=_goal_label(profile.goal),
        daily_minutes=profile.daily_minutes,
        horizon_days=profile.horizon_days,
        weak_tags=weak,
        weak_tags_zh=[mapping.get(t, t) for t in weak],
        rating=profile.rating,
        onboarded=profile.onboarded,
    )


def _plan_item_out(item: PlanItem, problem: ProblemOut | None) -> PlanItemOut:
    return PlanItemOut(
        id=item.id,
        problem_id=item.problem_id,
        title=problem.title if problem else item.problem_id,
        title_zh=problem.title_zh if problem else None,
        difficulty=problem.difficulty if problem else "Unknown",
        difficulty_zh=(
            problem.difficulty_zh
            if problem
            else DIFFICULTY_ZH.get("Unknown", "未知")
        ),
        scheduled_date=item.scheduled_date,
        item_type=item.item_type,
        item_type_zh=ITEM_TYPE_ZH.get(item.item_type, item.item_type),
        status=item.status,
        status_zh=STATUS_ZH.get(item.status, item.status),
        reason=item.reason,
        stage=problem.stage if problem else "",
        stage_zh=problem.stage_zh if problem else "",
        url=problem.url if problem else "",
        tags_zh=problem.tags_zh if problem else [],
    )


@router.get("/ready")
def ready() -> dict[str, str]:
    """Lightweight liveness probe for desktop launcher (no catalog I/O)."""
    return {"status": "ok"}


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    try:
        stats = catalog_stats()
        loaded = int(stats["total"])
    except Exception:
        loaded = -1
    return HealthOut(status="ok", app=APP_NAME, problems_loaded=loaded)


@router.get("/meta", response_model=MetaOut)
def meta() -> MetaOut:
    mapping = tag_zh_map()
    stages = [
        {"id": s["id"], "title": s.get("title") or STAGE_ZH.get(s["id"], s["id"])}
        for s in get_stages()
    ]
    # popular tags first
    popular = [
        "array",
        "string",
        "hash-table",
        "dynamic-programming",
        "greedy",
        "binary-search",
        "two-pointers",
        "sliding-window",
        "tree",
        "binary-tree",
        "linked-list",
        "stack",
        "graph",
        "backtracking",
        "math",
        "database",
    ]
    tags = [{"id": t, "label": mapping.get(t, t)} for t in popular if t in mapping]
    for slug, zh in sorted(mapping.items(), key=lambda x: x[1]):
        if slug not in popular:
            tags.append({"id": slug, "label": zh})
    return MetaOut(
        app_name=APP_NAME,
        source_note=SOURCE_NOTE,
        languages=LANGUAGES,
        levels=LEVELS,
        goals=GOALS,
        stages=stages,
        tags=tags,
        difficulties=[
            {"id": "Easy", "label": "简单"},
            {"id": "Medium", "label": "中等"},
            {"id": "Hard", "label": "困难"},
        ],
        catalog=catalog_stats(),
    )


@router.get("/profile", response_model=ProfileOut)
def profile(session: Session = Depends(get_session)) -> ProfileOut:
    return _profile_out(session.get(UserProfile, "local"))


@router.post("/onboarding", response_model=ProfileOut)
def onboarding(
    payload: OnboardingRequest,
    session: Session = Depends(get_session),
) -> ProfileOut:
    profile, _, _ = create_plan_from_onboarding(session, payload)
    return _profile_out(profile)


@router.get("/today", response_model=TodayResponse)
def today(session: Session = Depends(get_session)) -> TodayResponse:
    profile = session.get(UserProfile, "local")
    if profile is None or not profile.onboarded:
        return TodayResponse(
            date=date.today(),
            onboarded=False,
            daily_minutes=60,
            items=[],
            done_items=[],
            total_est_minutes=0,
            remaining_est_minutes=0,
            spent_minutes=0,
            message="请先完成入门设置，生成你的学习路线。",
            source_note=SOURCE_NOTE,
        )

    plan = get_active_plan(session)
    if plan is None:
        return TodayResponse(
            date=date.today(),
            onboarded=True,
            daily_minutes=profile.daily_minutes,
            items=[],
            done_items=[],
            total_est_minutes=0,
            remaining_est_minutes=0,
            spent_minutes=0,
            message="还没有有效计划，请重新完成设置。",
            source_note=SOURCE_NOTE,
        )

    problem_map = get_problem_map()
    items = session.exec(
        select(PlanItem)
        .where(
            PlanItem.plan_id == plan.id,
            PlanItem.scheduled_date == date.today(),
            PlanItem.status == "pending",
        )
        .order_by(PlanItem.item_type.desc(), PlanItem.sort_order.asc())
    ).all()

    out_items: list[TodayItemOut] = []
    remaining = 0
    for item in items:
        problem = problem_map.get(item.problem_id)
        if problem is None:
            continue
        remaining += problem.est_minutes
        out_items.append(
            TodayItemOut(
                plan_item_id=item.id,
                problem=problem,
                item_type=item.item_type,
                item_type_zh=ITEM_TYPE_ZH.get(item.item_type, item.item_type),
                status=item.status,
                status_zh=STATUS_ZH.get(item.status, item.status),
                reason=item.reason,
                scheduled_date=item.scheduled_date,
            )
        )

    # Today's completed attempts (for spent minutes + undo)
    day_start = datetime_combine_today()
    attempts_today = session.exec(
        select(Attempt)
        .where(Attempt.user_id == "local", Attempt.created_at >= day_start)
        .order_by(Attempt.created_at.desc())
    ).all()

    spent = 0
    done_out: list[TodayDoneItemOut] = []
    for a in attempts_today:
        spent += max(0, int(a.minutes_spent or 0))
        problem = problem_map.get(a.problem_id)
        if problem is None:
            continue
        done_out.append(
            TodayDoneItemOut(
                attempt_id=a.id,
                plan_item_id=a.plan_item_id,
                problem=problem,
                result=a.result,
                result_zh=RESULT_ZH.get(a.result, a.result),
                felt_difficulty=a.felt_difficulty,
                felt_difficulty_zh=FELT_ZH.get(a.felt_difficulty, a.felt_difficulty),
                minutes_spent=a.minutes_spent,
                created_at=a.created_at,
                can_undo=a.created_at.date() == date.today(),
            )
        )

    total_est = remaining + spent
    streak = _calc_streak(session)
    if not out_items and not done_out:
        message = "今天没有待做题，可从题库自行添加，或查看学习路线。"
    elif not out_items and done_out:
        message = f"今日待做已清空。已完成 {len(done_out)} 题，累计用时 {spent} 分钟。"
    else:
        message = (
            f"今日待做 {len(out_items)} 题（剩余约 {remaining} 分钟），"
            f"已用时 {spent} 分钟。"
        )

    return TodayResponse(
        date=date.today(),
        onboarded=True,
        daily_minutes=profile.daily_minutes,
        items=out_items,
        done_items=done_out,
        total_est_minutes=total_est,
        remaining_est_minutes=remaining,
        spent_minutes=spent,
        streak_days=streak,
        message=message,
        source_note=SOURCE_NOTE,
    )


def datetime_combine_today():
    from datetime import datetime, time

    return datetime.combine(date.today(), time.min)


def _calc_streak(session: Session, user_id: str = "local") -> int:
    from app.services.checkin import calc_current_streak, _attempt_days

    return calc_current_streak(set(_attempt_days(session, user_id).keys()))


@router.post("/attempts", response_model=AttemptOut)
def create_attempt(
    payload: AttemptCreate,
    session: Session = Depends(get_session),
) -> AttemptOut:
    try:
        attempt, mastery, message, summary = record_attempt(session, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="题目不存在或为付费题") from None
    return AttemptOut(
        id=attempt.id,
        problem_id=attempt.problem_id,
        plan_item_id=attempt.plan_item_id,
        result=attempt.result,
        felt_difficulty=attempt.felt_difficulty,
        minutes_spent=attempt.minutes_spent,
        performance=attempt.performance,
        created_at=attempt.created_at,
        mastery_updates=mastery,
        summary=summary,
        message=message,
    )


@router.post("/attempts/{attempt_id}/undo", response_model=UndoAttemptOut)
def undo_attempt_route(
    attempt_id: int,
    session: Session = Depends(get_session),
) -> UndoAttemptOut:
    try:
        attempt, restored_id, message, mastery, summary = undo_attempt(session, attempt_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="反馈记录不存在") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return UndoAttemptOut(
        attempt_id=attempt_id,
        problem_id=attempt.problem_id,
        restored_plan_item_id=restored_id,
        mastery_updates=mastery,
        summary=summary,
        message=message,
    )


@router.post("/today/skip", response_model=PlanItemOut)
def skip_today_item(
    payload: SkipRequest,
    session: Session = Depends(get_session),
) -> PlanItemOut:
    try:
        item = skip_plan_item(session, payload.plan_item_id, payload.to_date)
    except KeyError:
        raise HTTPException(status_code=404, detail="任务项不存在") from None
    problem = get_problem_map().get(item.problem_id)
    return _plan_item_out(item, problem)


@router.post("/today/add", response_model=AddTodayResponse)
def add_today(
    payload: AddTodayRequest,
    session: Session = Depends(get_session),
) -> AddTodayResponse:
    profile = session.get(UserProfile, "local")
    if profile is None or not profile.onboarded:
        raise HTTPException(status_code=400, detail="请先完成入门设置")
    try:
        result = add_problems_to_today(session, payload.problem_ids, on=payload.date)
    except RuntimeError:
        raise HTTPException(status_code=400, detail="当前没有有效计划，请重新设置") from None
    problem_map = get_problem_map()
    items = [_plan_item_out(i, problem_map.get(i.problem_id)) for i in result["items"]]
    parts = [f"已加入今日 {result['added']} 题"]
    if result["skipped_existing"]:
        parts.append(f"已在今日队列跳过 {result['skipped_existing']} 题")
    if result["skipped_invalid"]:
        parts.append(f"无效/付费题跳过 {result['skipped_invalid']} 题")
    return AddTodayResponse(
        items=items,
        added=result["added"],
        skipped_existing=result["skipped_existing"],
        skipped_invalid=result["skipped_invalid"],
        message="，".join(parts) + "。",
    )


@router.post("/today/remove", response_model=RemoveTodayResponse)
def remove_today(
    payload: RemoveTodayRequest,
    session: Session = Depends(get_session),
) -> RemoveTodayResponse:
    profile = session.get(UserProfile, "local")
    if profile is None or not profile.onboarded:
        raise HTTPException(status_code=400, detail="请先完成入门设置")
    if not payload.problem_ids and not payload.plan_item_ids:
        raise HTTPException(status_code=400, detail="请指定要撤回的题目")
    try:
        result = remove_problems_from_today(
            session,
            problem_ids=payload.problem_ids,
            plan_item_ids=payload.plan_item_ids,
            on=payload.date,
        )
    except RuntimeError:
        raise HTTPException(status_code=400, detail="当前没有有效计划，请重新设置") from None
    removed = int(result["removed"])
    skipped = int(result["skipped"])
    skipped_roadmap = int(result.get("skipped_roadmap") or 0)
    if removed == 0 and skipped_roadmap:
        message = (
            "这些题来自学习路线，不能在题库里撤回。"
            "路线题会保留在今日任务与学习路线中；只有你从题库自行添加的题可以撤回。"
        )
    elif removed == 0:
        message = "没有可撤回的今日自选题（可能已完成、不在今日，或属于学习路线）。"
    else:
        message = f"已从今日撤回 {removed} 道自选题。"
        if skipped_roadmap:
            message += f" 另有 {skipped_roadmap} 道路线题已跳过（未改动学习路线）。"
        elif skipped:
            message += f" 跳过 {skipped} 项。"
    return RemoveTodayResponse(removed=removed, skipped=skipped, message=message)


@router.get("/plan", response_model=PlanOut)
def get_plan(session: Session = Depends(get_session)) -> PlanOut:
    plan = get_active_plan(session)
    if plan is None:
        raise HTTPException(status_code=404, detail="暂无学习计划，请先完成设置")
    problem_map = get_problem_map()
    items = session.exec(
        select(PlanItem)
        .where(PlanItem.plan_id == plan.id)
        .order_by(PlanItem.scheduled_date, PlanItem.sort_order)
    ).all()
    out: list[PlanItemOut] = []
    done = 0
    for item in items:
        if item.status == "done":
            done += 1
        out.append(_plan_item_out(item, problem_map.get(item.problem_id)))
    return PlanOut(
        id=plan.id,
        status=plan.status,
        start_date=plan.start_date,
        horizon_days=plan.horizon_days,
        total_items=len(out),
        done_items=done,
        items=out,
    )


@router.post("/plan/regenerate", response_model=ProfileOut)
def regenerate_plan(
    payload: OnboardingRequest,
    session: Session = Depends(get_session),
) -> ProfileOut:
    profile, _, _ = create_plan_from_onboarding(session, payload)
    return _profile_out(profile)


@router.get("/stats", response_model=StatsOut)
def stats(session: Session = Depends(get_session)) -> StatsOut:
    return get_stats(session)


@router.get("/checkins", response_model=CheckinOut)
def checkins(
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    session: Session = Depends(get_session),
) -> CheckinOut:
    try:
        return get_checkins(session, year=year, month=month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/review", response_model=list[ReviewItemOut])
def review(session: Session = Depends(get_session)) -> list[ReviewItemOut]:
    return list_due_reviews(session)


@router.get("/problems", response_model=list[ProblemOut])
def problems(
    tag: Optional[str] = None,
    difficulty: Optional[str] = None,
    stage: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[ProblemOut]:
    items = list_problems(tag=tag, difficulty=difficulty, stage=stage, q=q, limit=limit)
    attempts = session.exec(
        select(Attempt)
        .where(Attempt.user_id == "local")
        .order_by(Attempt.created_at.desc())
    ).all()
    # latest attempt per problem
    latest: dict[str, Attempt] = {}
    for a in attempts:
        if a.problem_id not in latest:
            latest[a.problem_id] = a

    # Repair accidental roadmap reschedules from older withdraw logic (once per request is cheap).
    repair_withdrawn_roadmap_items(session)

    # Pending items scheduled for today → show as "已加入今日" in bank.
    # Prefer custom (user-picked) over roadmap when both exist for same problem.
    today_pending: dict[str, PlanItem] = {}
    plan = get_active_plan(session)
    if plan is not None:
        pending_today = session.exec(
            select(PlanItem).where(
                PlanItem.plan_id == plan.id,
                PlanItem.scheduled_date == date.today(),
                PlanItem.status == "pending",
            )
        ).all()
        for item in pending_today:
            prev = today_pending.get(item.problem_id)
            if prev is None or (prev.item_type != "custom" and item.item_type == "custom"):
                today_pending[item.problem_id] = item

    for p in items:
        a = latest.get(p.id)
        if a is not None:
            p.completed = True
            p.completed_result = a.result
            p.completed_result_zh = RESULT_ZH.get(a.result, a.result)
            p.completed_at = a.created_at
        today_item = today_pending.get(p.id)
        if today_item is not None and not p.completed:
            p.in_today = True
            p.today_plan_item_id = today_item.id
            p.today_item_type = today_item.item_type
            p.can_withdraw_today = today_item.item_type == "custom"
    return items


@router.get("/export")
def export_data(session: Session = Depends(get_session)) -> dict[str, Any]:
    profile = session.get(UserProfile, "local")
    attempts = session.exec(select(Attempt).where(Attempt.user_id == "local")).all()
    plan = get_active_plan(session)
    items = []
    if plan is not None:
        items = session.exec(select(PlanItem).where(PlanItem.plan_id == plan.id)).all()
    return {
        "version": 1,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "profile": _profile_out(profile).model_dump(mode="json"),
        "attempts": [
            {
                "problem_id": a.problem_id,
                "result": a.result,
                "felt_difficulty": a.felt_difficulty,
                "minutes_spent": a.minutes_spent,
                "note": a.note,
                "performance": a.performance,
                "created_at": a.created_at.isoformat(),
                "plan_item_id": a.plan_item_id,
            }
            for a in attempts
        ],
        "plan_items": [
            {
                "problem_id": i.problem_id,
                "scheduled_date": i.scheduled_date.isoformat(),
                "item_type": i.item_type,
                "status": i.status,
                "reason": i.reason,
                "sort_order": i.sort_order,
            }
            for i in items
        ],
        "source_note": SOURCE_NOTE,
    }


@router.post("/import")
def import_data(
    payload: dict[str, Any],
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Restore local coach data from a previously exported JSON blob."""
    from datetime import datetime as dt

    from app.models import Plan, ReviewCard, SkillStat
    from app.services.adapter import recompute_skills_and_rating

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="导入数据格式无效")

    profile_data = payload.get("profile") or {}
    attempts_data = payload.get("attempts") or []
    plan_items_data = payload.get("plan_items") or []
    if not isinstance(attempts_data, list) or not isinstance(plan_items_data, list):
        raise HTTPException(status_code=400, detail="导入数据缺少 attempts / plan_items")

    # Clear local learning state (keep schema).
    for model in (Attempt, PlanItem, Plan, SkillStat, ReviewCard):
        rows = session.exec(select(model)).all()
        for row in rows:
            session.delete(row)
    session.commit()

    # Profile
    profile = session.get(UserProfile, "local")
    if profile is None:
        profile = UserProfile(id="local")
    profile.language = str(profile_data.get("language") or "python")
    profile.level = str(profile_data.get("level") or "easy")
    profile.goal = str(profile_data.get("goal") or "campus")
    profile.daily_minutes = int(profile_data.get("daily_minutes") or 60)
    profile.horizon_days = int(profile_data.get("horizon_days") or 60)
    weak = profile_data.get("weak_tags") or []
    profile.weak_tags_json = json.dumps(weak, ensure_ascii=False)
    profile.rating = int(profile_data.get("rating") or 1000)
    profile.onboarded = bool(profile_data.get("onboarded", True))
    profile.updated_at = dt.utcnow()
    session.add(profile)
    session.commit()

    # Plan shell
    plan = Plan(
        user_id="local",
        status="active",
        start_date=date.today(),
        horizon_days=profile.horizon_days,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)

    restored_items = 0
    for raw in plan_items_data:
        if not isinstance(raw, dict) or not raw.get("problem_id"):
            continue
        try:
            sched = date.fromisoformat(str(raw.get("scheduled_date") or date.today().isoformat()))
        except ValueError:
            sched = date.today()
        item = PlanItem(
            plan_id=plan.id,
            problem_id=str(raw["problem_id"]),
            scheduled_date=sched,
            item_type=str(raw.get("item_type") or "main"),
            status=str(raw.get("status") or "pending"),
            reason=str(raw.get("reason") or ""),
            sort_order=int(raw.get("sort_order") or 0),
        )
        session.add(item)
        restored_items += 1
    session.commit()

    restored_attempts = 0
    for raw in attempts_data:
        if not isinstance(raw, dict) or not raw.get("problem_id"):
            continue
        created = dt.utcnow()
        if raw.get("created_at"):
            try:
                created = dt.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
            except ValueError:
                created = dt.utcnow()
        attempt = Attempt(
            user_id="local",
            problem_id=str(raw["problem_id"]),
            plan_item_id=None,
            result=str(raw.get("result") or "solved_solo"),
            felt_difficulty=str(raw.get("felt_difficulty") or "ok"),
            minutes_spent=int(raw.get("minutes_spent") or 20),
            note=str(raw.get("note") or ""),
            performance=float(raw.get("performance") or 0.0),
            created_at=created,
        )
        session.add(attempt)
        restored_attempts += 1
    session.commit()

    recompute_skills_and_rating(session, user_id="local")

    return {
        "ok": True,
        "restored_attempts": restored_attempts,
        "restored_plan_items": restored_items,
        "message": f"已从备份恢复：{restored_attempts} 条反馈、{restored_items} 条计划项。掌握度已重算。",
    }


@router.post("/reset")
def reset_local_data(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Wipe local learning data. Irreversible — UI must confirm first."""
    from app.models import Plan, ReviewCard, SkillStat

    counts = {"attempts": 0, "plan_items": 0, "plans": 0, "skills": 0, "reviews": 0}
    for key, model in (
        ("attempts", Attempt),
        ("plan_items", PlanItem),
        ("plans", Plan),
        ("skills", SkillStat),
        ("reviews", ReviewCard),
    ):
        rows = session.exec(select(model)).all()
        counts[key] = len(rows)
        for row in rows:
            session.delete(row)

    profile = session.get(UserProfile, "local")
    if profile is not None:
        profile.onboarded = False
        profile.rating = 1000
        profile.weak_tags_json = "[]"
        profile.updated_at = datetime.utcnow()
        session.add(profile)
    session.commit()

    return {
        "ok": True,
        "cleared": counts,
        "message": "本机学习数据已清空。请重新完成设置以生成路线。",
    }
