"""Spaced repetition helpers."""

from __future__ import annotations

from datetime import date, timedelta

from sqlmodel import Session, select

from app.catalog import get_problem_map
from app.models import Plan, PlanItem, ReviewCard
from app.schemas import ProblemOut, ReviewItemOut
from app.services.planner import get_active_plan


def upsert_review_card(
    session: Session,
    *,
    user_id: str,
    problem_id: str,
    performance: float,
) -> ReviewCard:
    card = session.exec(
        select(ReviewCard).where(
            ReviewCard.user_id == user_id,
            ReviewCard.problem_id == problem_id,
        )
    ).first()

    if card is None:
        card = ReviewCard(
            user_id=user_id,
            problem_id=problem_id,
            ease=2.5,
            interval_days=1,
            due_at=date.today() + timedelta(days=1),
            reps=0,
        )
    else:
        # quality mapped roughly from performance
        if performance >= 1.0:
            card.ease = min(3.0, card.ease + 0.1)
            card.interval_days = max(1, round(card.interval_days * card.ease))
        elif performance >= 0:
            card.interval_days = max(1, round(card.interval_days * 1.4))
        else:
            card.ease = max(1.3, card.ease - 0.2)
            card.interval_days = 1
        card.due_at = date.today() + timedelta(days=card.interval_days)
        card.reps += 1

    session.add(card)
    session.commit()
    session.refresh(card)

    _sync_review_into_plan(session, user_id=user_id, card=card)
    return card


def _sync_review_into_plan(session: Session, user_id: str, card: ReviewCard) -> None:
    plan = get_active_plan(session, user_id)
    if plan is None:
        return

    existing = session.exec(
        select(PlanItem).where(
            PlanItem.plan_id == plan.id,
            PlanItem.problem_id == card.problem_id,
            PlanItem.item_type == "review",
            PlanItem.status == "pending",
        )
    ).first()

    reason = "间隔复习：巩固已做题目，防止遗忘"
    if existing is None:
        item = PlanItem(
            plan_id=plan.id,
            problem_id=card.problem_id,
            scheduled_date=card.due_at,
            item_type="review",
            status="pending",
            reason=reason,
            sort_order=0,
        )
        session.add(item)
    else:
        existing.scheduled_date = card.due_at
        existing.reason = reason
        session.add(existing)
    session.commit()


def list_due_reviews(
    session: Session,
    *,
    user_id: str = "local",
    on: date | None = None,
) -> list[ReviewItemOut]:
    on = on or date.today()
    problem_map = get_problem_map()
    cards = session.exec(
        select(ReviewCard)
        .where(ReviewCard.user_id == user_id, ReviewCard.due_at <= on)
        .order_by(ReviewCard.due_at.asc())
    ).all()

    result: list[ReviewItemOut] = []
    for card in cards:
        problem = problem_map.get(card.problem_id)
        if problem is None:
            continue
        result.append(
            ReviewItemOut(
                problem=problem,
                due_at=card.due_at,
                interval_days=card.interval_days,
                reps=card.reps,
            )
        )
    return result
