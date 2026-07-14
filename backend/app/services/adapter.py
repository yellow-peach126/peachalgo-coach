"""Feedback scoring and adaptive plan adjustments."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.catalog import get_problem_map, tag_zh_map
from app.models import Attempt, Plan, PlanItem, ReviewCard, SkillStat, UserProfile
from app.schemas import AttemptCreate, FeedbackChangeItem, FeedbackSummary
from app.services.checkin import calc_current_streak, _attempt_days
from app.services.planner import get_active_plan
from app.services.review import upsert_review_card


RESULT_SCORE = {
    "solved_solo": 1.5,
    "solved_hint": 0.5,
    "solved_solution": -0.5,
    "failed": -1.5,
}

FELT_SCORE = {
    "too_easy": 0.5,
    "ok": 0.0,
    "hard": -0.5,
    "very_hard": -1.0,
}


def calc_performance(
    *,
    result: str,
    felt_difficulty: str,
    minutes_spent: int,
    est_minutes: int,
) -> float:
    score = RESULT_SCORE.get(result, 0.0) + FELT_SCORE.get(felt_difficulty, 0.0)
    if est_minutes > 0:
        if minutes_spent <= 0.7 * est_minutes:
            score += 0.3
        elif minutes_spent >= 1.5 * est_minutes:
            score -= 0.3
    return max(-2.0, min(2.0, score))


def _get_or_create_skill(session: Session, user_id: str, tag: str) -> SkillStat:
    skill = session.exec(
        select(SkillStat).where(SkillStat.user_id == user_id, SkillStat.tag == tag)
    ).first()
    if skill is None:
        skill = SkillStat(user_id=user_id, tag=tag, mastery=50.0)
        session.add(skill)
        session.commit()
        session.refresh(skill)
    return skill


def update_skills(
    session: Session,
    *,
    user_id: str,
    tags: list[str],
    performance: float,
    solo: bool,
) -> dict[str, float]:
    updates: dict[str, float] = {}
    now = datetime.utcnow()
    for tag in tags:
        skill = _get_or_create_skill(session, user_id, tag)
        skill.mastery = max(0.0, min(100.0, skill.mastery + performance * 6))
        skill.attempts += 1
        if solo:
            skill.solo_ac += 1
        skill.last_seen_at = now
        session.add(skill)
        updates[tag] = round(skill.mastery, 1)
    session.commit()
    return updates


def recompute_skills_and_rating(
    session: Session,
    *,
    user_id: str,
    exclude_attempt_id: int | None = None,
) -> dict[str, float]:
    """Rebuild rating + per-tag mastery from remaining attempts (source of truth after undo)."""
    problem_map = get_problem_map()
    attempts = session.exec(
        select(Attempt).where(Attempt.user_id == user_id).order_by(Attempt.created_at.asc())
    ).all()
    remaining = [a for a in attempts if exclude_attempt_id is None or a.id != exclude_attempt_id]

    # rating from profile baseline 1000
    rating = 1000
    for a in remaining:
        rating = max(0, rating + round(a.performance * 12))

    profile = session.get(UserProfile, user_id)
    if profile is not None:
        profile.rating = rating
        profile.updated_at = datetime.utcnow()
        session.add(profile)

    # rebuild tag aggregates
    tag_state: dict[str, dict[str, float | int | datetime | None]] = {}
    for a in remaining:
        problem = problem_map.get(a.problem_id)
        if problem is None:
            continue
        for tag in problem.tags:
            state = tag_state.setdefault(
                tag,
                {"mastery": 50.0, "attempts": 0, "solo_ac": 0, "last_seen_at": None},
            )
            state["mastery"] = max(0.0, min(100.0, float(state["mastery"]) + a.performance * 6))
            state["attempts"] = int(state["attempts"]) + 1
            if a.result == "solved_solo":
                state["solo_ac"] = int(state["solo_ac"]) + 1
            state["last_seen_at"] = a.created_at

    existing = session.exec(select(SkillStat).where(SkillStat.user_id == user_id)).all()
    existing_by_tag = {s.tag: s for s in existing}
    updates: dict[str, float] = {}

    for tag, state in tag_state.items():
        skill = existing_by_tag.pop(tag, None)
        if skill is None:
            skill = SkillStat(user_id=user_id, tag=tag)
        skill.mastery = float(state["mastery"])
        skill.attempts = int(state["attempts"])
        skill.solo_ac = int(state["solo_ac"])
        skill.last_seen_at = state["last_seen_at"]  # type: ignore[assignment]
        session.add(skill)
        updates[tag] = round(skill.mastery, 1)

    # tags no longer present after undo → remove stale rows
    for stale in existing_by_tag.values():
        session.delete(stale)

    session.commit()
    return updates


def _mark_plan_item_done(session: Session, plan_item_id: int | None, problem_id: str) -> None:
    """Mark the related plan item(s) done so 学习路线 reflects completion immediately."""
    touched = False
    item = None
    if plan_item_id is not None:
        item = session.get(PlanItem, plan_item_id)
    if item is None:
        plan = get_active_plan(session)
        if plan is not None:
            item = session.exec(
                select(PlanItem).where(
                    PlanItem.plan_id == plan.id,
                    PlanItem.problem_id == problem_id,
                    PlanItem.status == "pending",
                    PlanItem.scheduled_date == date.today(),
                )
            ).first()
    if item is not None:
        item.status = "done"
        session.add(item)
        touched = True

    # Also close any other pending occurrences of the same problem in the active plan
    # (e.g. duplicate adds) so the route page stays consistent.
    plan = get_active_plan(session)
    if plan is not None:
        siblings = session.exec(
            select(PlanItem).where(
                PlanItem.plan_id == plan.id,
                PlanItem.problem_id == problem_id,
                PlanItem.status == "pending",
            )
        ).all()
        for sibling in siblings:
            if item is not None and sibling.id == item.id:
                continue
            sibling.status = "done"
            session.add(sibling)
            touched = True

    if touched:
        session.commit()


def _insert_remedial_items(
    session: Session,
    plan: Plan,
    problem_id: str,
    tags: list[str],
) -> None:
    """If user struggled, schedule an easier related pending item sooner."""
    problem_map = get_problem_map()
    current = problem_map.get(problem_id)
    if current is None:
        return

    pending = session.exec(
        select(PlanItem).where(
            PlanItem.plan_id == plan.id,
            PlanItem.status == "pending",
            PlanItem.scheduled_date > date.today(),
        )
    ).all()

    # pull one easier same-stage template earlier
    candidates = []
    for item in pending:
        p = problem_map.get(item.problem_id)
        if p is None:
            continue
        if p.stage != current.stage:
            continue
        if p.difficulty == "Easy" or p.is_template:
            candidates.append((item, p))
    if not candidates:
        return

    item, _ = sorted(candidates, key=lambda x: x[1].priority)[0]
    item.scheduled_date = date.today() + timedelta(days=1)
    item.item_type = "weak"
    item.reason = f"弱项补强：巩固 {', '.join(tags[:2]) or current.stage}"
    session.add(item)
    session.commit()


def _maybe_skip_redundant_templates(
    session: Session,
    plan: Plan,
    tags: list[str],
    performance: float,
    *,
    exclude_problem_id: str | None = None,
) -> None:
    """Delay future similar template drills — never touch remaining tasks for today."""
    if performance < 1.0:
        return
    problem_map = get_problem_map()
    pending = session.exec(
        select(PlanItem).where(
            PlanItem.plan_id == plan.id,
            PlanItem.status == "pending",
            PlanItem.item_type == "main",
            PlanItem.scheduled_date > date.today(),  # keep today's queue intact
        )
    ).all()

    moved = 0
    for item in pending:
        if exclude_problem_id and item.problem_id == exclude_problem_id:
            continue
        p = problem_map.get(item.problem_id)
        if p is None or not p.is_template:
            continue
        if not set(p.tags).intersection(tags):
            continue
        # push later templates to reduce repetition
        item.scheduled_date = item.scheduled_date + timedelta(days=5)
        item.reason = "已掌握同类模板，延后重复练习"
        session.add(item)
        moved += 1
        if moved >= 2:
            break
    if moved:
        session.commit()


def _skill_snapshot(session: Session, user_id: str, tags: list[str]) -> dict[str, float]:
    snap: dict[str, float] = {}
    for tag in tags:
        skill = session.exec(
            select(SkillStat).where(SkillStat.user_id == user_id, SkillStat.tag == tag)
        ).first()
        if skill is not None and skill.attempts > 0:
            snap[tag] = round(skill.mastery, 1)
        else:
            # Unassessed before first real attempt — do not pretend 50 is known.
            snap[tag] = None  # type: ignore[assignment]
    # Replace None with explicit absence for JSON friendliness later
    return {k: v for k, v in snap.items() if v is not None}


def _build_summary(
    *,
    rating_before: int,
    rating_after: int,
    mastery_before: dict[str, float],
    mastery_after: dict[str, float],
    plan_notes: list[str],
    review_scheduled: bool,
    checked_today: bool,
    current_streak: int,
    restored: bool = False,
) -> FeedbackSummary:
    mapping = tag_zh_map()
    changes: list[FeedbackChangeItem] = []
    delta = rating_after - rating_before
    if delta != 0:
        sign = "+" if delta > 0 else ""
        changes.append(
            FeedbackChangeItem(
                kind="rating",
                label="能力分",
                detail=f"{rating_before} → {rating_after}（{sign}{delta}）",
            )
        )
    else:
        changes.append(
            FeedbackChangeItem(
                kind="rating",
                label="能力分",
                detail=f"仍为 {rating_after}",
            )
        )

    all_tags = sorted(set(mastery_before) | set(mastery_after))
    for tag in all_tags:
        before = mastery_before.get(tag)
        after = mastery_after.get(tag)
        zh = mapping.get(tag, tag)
        if before is None and after is not None:
            changes.append(
                FeedbackChangeItem(
                    kind="mastery",
                    label=zh,
                    detail=f"未评估 → {after}",
                )
            )
        elif before is not None and after is None:
            changes.append(
                FeedbackChangeItem(
                    kind="mastery",
                    label=zh,
                    detail=f"{before} → 未评估",
                )
            )
        elif before is not None and after is not None and before != after:
            d = round(after - before, 1)
            sign = "+" if d > 0 else ""
            changes.append(
                FeedbackChangeItem(
                    kind="mastery",
                    label=zh,
                    detail=f"{before} → {after}（{sign}{d}）",
                )
            )

    for note in plan_notes:
        changes.append(FeedbackChangeItem(kind="plan", label="计划调整", detail=note))

    if review_scheduled:
        changes.append(
            FeedbackChangeItem(
                kind="review",
                label="间隔复习",
                detail="已写入复习卡片，到期会出现在今日「复习」分区",
            )
        )

    if restored:
        changes.append(
            FeedbackChangeItem(
                kind="restore",
                label="任务恢复",
                detail="题目已回到今日待做，学习路线改回待完成，题库可再选",
            )
        )

    if checked_today:
        changes.append(
            FeedbackChangeItem(
                kind="checkin",
                label="打卡",
                detail=f"今日已打卡 · 连续 {current_streak} 天",
            )
        )
    else:
        changes.append(
            FeedbackChangeItem(
                kind="checkin",
                label="打卡",
                detail="今日尚未打卡（提交反馈即记为打卡）",
            )
        )

    return FeedbackSummary(
        rating_before=rating_before,
        rating_after=rating_after,
        rating_delta=delta,
        mastery_before=mastery_before,
        mastery_after=mastery_after,
        changes=changes,
        checked_today=checked_today,
        current_streak=current_streak,
        review_scheduled=review_scheduled,
    )


def _resolve_plan_item_id(
    session: Session,
    plan_item_id: int | None,
    problem_id: str,
) -> int | None:
    item = None
    if plan_item_id is not None:
        item = session.get(PlanItem, plan_item_id)
    if item is None:
        plan = get_active_plan(session)
        if plan is None:
            return None
        item = session.exec(
            select(PlanItem).where(
                PlanItem.plan_id == plan.id,
                PlanItem.problem_id == problem_id,
                PlanItem.status == "pending",
                PlanItem.scheduled_date == date.today(),
            )
        ).first()
    return item.id if item is not None else plan_item_id


def record_attempt(
    session: Session,
    payload: AttemptCreate,
    *,
    user_id: str = "local",
) -> tuple[Attempt, dict[str, float], str, FeedbackSummary]:
    problem_map = get_problem_map()
    problem = problem_map.get(payload.problem_id)
    if problem is None:
        raise KeyError(payload.problem_id)

    performance = calc_performance(
        result=payload.result,
        felt_difficulty=payload.felt_difficulty,
        minutes_spent=payload.minutes_spent,
        est_minutes=problem.est_minutes,
    )

    resolved_plan_item_id = _resolve_plan_item_id(
        session, payload.plan_item_id, payload.problem_id
    )

    profile = session.get(UserProfile, user_id)
    if profile is None:
        profile = UserProfile(id=user_id)
        session.add(profile)
        session.commit()
        session.refresh(profile)

    rating_before = int(profile.rating or 1000)
    mastery_before = _skill_snapshot(session, user_id, problem.tags)

    attempt = Attempt(
        user_id=user_id,
        problem_id=payload.problem_id,
        plan_item_id=resolved_plan_item_id,
        result=payload.result,
        felt_difficulty=payload.felt_difficulty,
        minutes_spent=payload.minutes_spent,
        note=payload.note,
        performance=performance,
    )
    session.add(attempt)

    profile.rating = max(0, profile.rating + round(performance * 12))
    profile.updated_at = datetime.utcnow()
    session.add(profile)
    session.commit()
    session.refresh(attempt)

    mastery_updates = update_skills(
        session,
        user_id=user_id,
        tags=problem.tags,
        performance=performance,
        solo=payload.result == "solved_solo",
    )

    _mark_plan_item_done(session, resolved_plan_item_id, payload.problem_id)

    review_scheduled = False
    if payload.result != "failed":
        upsert_review_card(
            session,
            user_id=user_id,
            problem_id=payload.problem_id,
            performance=performance,
        )
        review_scheduled = True

    plan = get_active_plan(session, user_id)
    plan_notes: list[str] = []
    message = "已记录反馈，并更新掌握度。若点错可在今日已完成中撤回。"
    if plan is not None:
        if performance <= -0.7:
            _insert_remedial_items(session, plan, payload.problem_id, problem.tags)
            plan_notes.append("这题偏吃力，已安排更基础的巩固题到近两天")
            message = "这题偏吃力，已安排更基础的巩固题到近两天。点错可撤回本次反馈。"
        elif performance >= 1.0:
            _maybe_skip_redundant_templates(
                session,
                plan,
                problem.tags,
                performance,
                exclude_problem_id=payload.problem_id,
            )
            plan_notes.append("表现不错，后续几天会减少同类模板题重复（今日剩余任务保留）")
            message = "表现不错，后续几天会减少同类模板题重复（今天剩余任务保留）。点错可撤回。"
        else:
            plan_notes.append("学习路线中该题已标为完成，题库同步为已完成")

    session.refresh(profile)
    rating_after = int(profile.rating or 1000)
    mastery_after = {k: float(v) for k, v in mastery_updates.items()}
    day_map = _attempt_days(session, user_id)
    checked_today = date.today() in day_map
    streak = calc_current_streak(set(day_map.keys()))

    summary = _build_summary(
        rating_before=rating_before,
        rating_after=rating_after,
        mastery_before=mastery_before,
        mastery_after=mastery_after,
        plan_notes=plan_notes,
        review_scheduled=review_scheduled,
        checked_today=checked_today,
        current_streak=streak,
    )
    return attempt, mastery_updates, message, summary


def undo_attempt(
    session: Session,
    attempt_id: int,
    *,
    user_id: str = "local",
) -> tuple[Attempt, int | None, str, dict[str, float], FeedbackSummary]:
    """Reverse a mistaken feedback: restore plan item, skills, rating, and review side-effects."""
    attempt = session.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise KeyError(attempt_id)

    # Only allow undoing today's mistakes by default (coach workflow safety).
    if attempt.created_at.date() != date.today():
        raise ValueError("只能撤回今天的反馈")

    problem_id = attempt.problem_id
    problem = get_problem_map().get(problem_id)
    tags = list(problem.tags) if problem is not None else []

    profile = session.get(UserProfile, user_id)
    rating_before = int(profile.rating) if profile is not None else 1000
    mastery_before = _skill_snapshot(session, user_id, tags) if tags else {}

    restored_plan_item_id: int | None = None
    plan = get_active_plan(session, user_id)
    items_to_restore: list[PlanItem] = []

    if attempt.plan_item_id is not None:
        linked = session.get(PlanItem, attempt.plan_item_id)
        if linked is not None:
            items_to_restore.append(linked)

    if plan is not None:
        # Restore any done plan rows for this problem (route + today stay in sync).
        done_rows = session.exec(
            select(PlanItem).where(
                PlanItem.plan_id == plan.id,
                PlanItem.problem_id == attempt.problem_id,
                PlanItem.status == "done",
            )
        ).all()
        for row in done_rows:
            if all(row.id != existing.id for existing in items_to_restore):
                items_to_restore.append(row)

    for item in items_to_restore:
        item.status = "pending"
        item.scheduled_date = date.today()
        # Keep original coach reason clean.
        reason = item.reason or ""
        for noise in (" · 已撤回错误反馈", "· 已撤回错误反馈", "（已撤回反馈）"):
            reason = reason.replace(noise, "")
        item.reason = reason.strip(" ·") or "已撤回反馈，重新回到今日待做"
        session.add(item)
        restored_plan_item_id = restored_plan_item_id or item.id

    # If nothing was restored but problem still needs a today slot, recreate one.
    if restored_plan_item_id is None and plan is not None:
        recreated = PlanItem(
            plan_id=plan.id,
            problem_id=attempt.problem_id,
            scheduled_date=date.today(),
            item_type="main",
            status="pending",
            reason="已撤回反馈，重新回到今日待做",
            sort_order=0,
        )
        session.add(recreated)
        session.flush()
        restored_plan_item_id = recreated.id

    # Roll back review card created/updated by this non-failed attempt when possible.
    if attempt.result != "failed":
        card = session.exec(
            select(ReviewCard).where(
                ReviewCard.user_id == user_id,
                ReviewCard.problem_id == attempt.problem_id,
            )
        ).first()
        if card is not None:
            # If this was the only/first completion, drop the card; else step back one interval.
            other = session.exec(
                select(Attempt).where(
                    Attempt.user_id == user_id,
                    Attempt.problem_id == attempt.problem_id,
                    Attempt.id != attempt.id,
                    Attempt.result != "failed",
                )
            ).first()
            if other is None and card.reps <= 0:
                # Remove pending review plan items tied to this card, then delete card.
                if plan is None:
                    plan = get_active_plan(session, user_id)
                if plan is not None:
                    review_items = session.exec(
                        select(PlanItem).where(
                            PlanItem.plan_id == plan.id,
                            PlanItem.problem_id == attempt.problem_id,
                            PlanItem.item_type == "review",
                            PlanItem.status == "pending",
                        )
                    ).all()
                    for ri in review_items:
                        session.delete(ri)
                session.delete(card)
            else:
                card.reps = max(0, card.reps - 1)
                card.interval_days = max(1, round(card.interval_days / max(card.ease, 1.3)))
                card.due_at = date.today() + timedelta(days=card.interval_days)
                session.add(card)

    # Rebuild mastery/rating from remaining attempts, then delete this attempt.
    mastery_updates = recompute_skills_and_rating(
        session,
        user_id=user_id,
        exclude_attempt_id=attempt_id,
    )
    session.delete(attempt)
    session.commit()

    profile = session.get(UserProfile, user_id)
    rating_after = int(profile.rating) if profile is not None else 1000
    mastery_after = _skill_snapshot(session, user_id, tags) if tags else dict(mastery_updates)
    day_map = _attempt_days(session, user_id)
    checked_today = date.today() in day_map
    streak = calc_current_streak(set(day_map.keys()))
    summary = _build_summary(
        rating_before=rating_before,
        rating_after=rating_after,
        mastery_before=mastery_before,
        mastery_after=mastery_after,
        plan_notes=["已回滚本次反馈对计划与掌握度的影响"],
        review_scheduled=False,
        checked_today=checked_today,
        current_streak=streak,
        restored=True,
    )

    message = "已撤回本次反馈：今日任务已恢复，学习路线改回待完成，题库可再选，掌握度已同步回滚。"
    ghost = Attempt(
        id=attempt_id,
        user_id=user_id,
        problem_id=problem_id,
        plan_item_id=restored_plan_item_id,
        result="undone",
        felt_difficulty="ok",
        minutes_spent=0,
    )
    return ghost, restored_plan_item_id, message, mastery_updates, summary


def skip_plan_item(
    session: Session,
    plan_item_id: int,
    to_date: date | None = None,
) -> PlanItem:
    item = session.get(PlanItem, plan_item_id)
    if item is None:
        raise KeyError(plan_item_id)
    target = to_date or (date.today() + timedelta(days=1))
    item.scheduled_date = target
    item.status = "pending"
    item.reason = f"已改期到 {target.isoformat()}"
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def weak_tags(session: Session, user_id: str = "local", limit: int = 3) -> list[str]:
    skills = session.exec(
        select(SkillStat).where(SkillStat.user_id == user_id).order_by(SkillStat.mastery.asc())
    ).all()
    return [s.tag for s in skills[:limit] if s.attempts > 0]
