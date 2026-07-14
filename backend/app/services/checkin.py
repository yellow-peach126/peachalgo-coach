"""Check-in calendar derived from daily feedback attempts."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from sqlmodel import Session, select

from app.models import Attempt
from app.schemas import CheckinDayOut, CheckinOut


def _attempt_days(session: Session, user_id: str = "local") -> dict[date, dict[str, int]]:
    attempts = session.exec(select(Attempt).where(Attempt.user_id == user_id)).all()
    by_day: dict[date, dict[str, int]] = {}
    for a in attempts:
        d = a.created_at.date()
        state = by_day.setdefault(d, {"attempts": 0, "minutes_spent": 0})
        state["attempts"] += 1
        state["minutes_spent"] += max(0, int(a.minutes_spent or 0))
    return by_day


def calc_current_streak(checked: set[date], today: date | None = None) -> int:
    today = today or date.today()
    if not checked:
        return 0
    cursor = today
    if cursor not in checked:
        cursor = today - timedelta(days=1)
        if cursor not in checked:
            return 0
    streak = 0
    while cursor in checked:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def calc_longest_streak(checked: set[date]) -> int:
    if not checked:
        return 0
    days = sorted(checked)
    best = 1
    run = 1
    for i in range(1, len(days)):
        if days[i] == days[i - 1] + timedelta(days=1):
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def get_checkins(
    session: Session,
    *,
    year: int | None = None,
    month: int | None = None,
    user_id: str = "local",
) -> CheckinOut:
    today = date.today()
    year = year or today.year
    month = month or today.month
    if month < 1 or month > 12:
        raise ValueError("month must be 1-12")
    if year < 2000 or year > 2100:
        raise ValueError("year out of range")

    by_day = _attempt_days(session, user_id)
    checked = set(by_day.keys())
    current = calc_current_streak(checked, today)
    longest = calc_longest_streak(checked)
    total_days = len(checked)

    _, last_day = monthrange(year, month)
    days_out: list[CheckinDayOut] = []
    month_count = 0
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        state = by_day.get(d)
        is_checked = state is not None
        if is_checked:
            month_count += 1
        days_out.append(
            CheckinDayOut(
                date=d,
                checked=is_checked,
                attempts=state["attempts"] if state else 0,
                minutes_spent=state["minutes_spent"] if state else 0,
                is_today=d == today,
            )
        )

    checked_today = today in checked
    if total_days == 0:
        message = "还没有打卡记录。完成今日任务并提交反馈，即记为当天打卡。"
    elif checked_today:
        message = f"今天已打卡。当前连续 {current} 天，继续保持。"
    elif current > 0:
        message = f"今天还没打卡。当前连续 {current} 天，提交一次反馈就能续上。"
    else:
        message = "连续记录已中断。今天提交反馈，重新开始连续打卡。"

    return CheckinOut(
        year=year,
        month=month,
        days=days_out,
        checked_dates=sorted(checked),
        current_streak=current,
        longest_streak=longest,
        total_checkin_days=total_days,
        month_checkin_days=month_count,
        checked_today=checked_today,
        message=message,
    )
