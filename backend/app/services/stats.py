"""Stats aggregation."""

from __future__ import annotations

from sqlmodel import Session, select

from app.catalog import tag_zh_map
from app.models import Attempt, SkillStat, UserProfile
from app.schemas import SkillOut, StatsOut
from app.services.adapter import weak_tags


def get_stats(session: Session, user_id: str = "local") -> StatsOut:
    profile = session.get(UserProfile, user_id)
    rating = profile.rating if profile else 1000

    attempts = session.exec(select(Attempt).where(Attempt.user_id == user_id)).all()
    total = len(attempts)
    solo = sum(1 for a in attempts if a.result == "solved_solo")
    completed = len({a.problem_id for a in attempts if a.result != "failed"})
    solo_rate = (solo / total) if total else 0.0

    mapping = tag_zh_map()
    skills = session.exec(
        select(SkillStat).where(SkillStat.user_id == user_id).order_by(SkillStat.mastery.desc())
    ).all()
    # Honest mastery: only surface tags with real feedback. Never imply "50 = half known".
    assessed = [s for s in skills if s.attempts > 0]
    skill_out = [
        SkillOut(
            tag=s.tag,
            tag_zh=mapping.get(s.tag, s.tag),
            mastery=round(s.mastery, 1),
            attempts=s.attempts,
            solo_ac=s.solo_ac,
        )
        for s in assessed
    ]
    weak = weak_tags(session, user_id)
    weak_zh = [mapping.get(t, t) for t in weak]

    if total == 0:
        message = "还没有做题记录。标签掌握度来自你的反馈，不是力扣 AC 率；完成今日任务后这里才会有分数。"
    elif not assessed:
        message = "已有做题记录，但标签尚未形成评估，再交几次反馈即可看到掌握度。"
    elif weak_zh:
        message = f"当前更建议补强：{'、'.join(weak_zh)}。分数仅反映你提交的反馈。"
    else:
        message = "各已评估标签表现较均衡，继续保持主线节奏。"

    return StatsOut(
        rating=rating,
        total_attempts=total,
        solo_ac_rate=round(solo_rate, 3),
        completed_problems=completed,
        skills=skill_out,
        weak_top=weak,
        weak_top_zh=weak_zh,
        message=message,
    )
