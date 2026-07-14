import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings
from app.constants import DIFFICULTY_ZH, STAGE_ZH, TAG_ZH_FALLBACK
from app.schemas import ProblemOut


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    path = Path(settings.problems_path)
    if not path.exists():
        raise FileNotFoundError(f"problems catalog not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def tag_zh_map() -> dict[str, str]:
    data = load_catalog()
    merged = dict(TAG_ZH_FALLBACK)
    merged.update(data.get("tag_zh") or {})
    return merged


def translate_tags(tags: list[str], tags_zh: list[str] | None = None) -> list[str]:
    if tags_zh and len(tags_zh) == len(tags):
        return tags_zh
    mapping = tag_zh_map()
    return [mapping.get(t, t) for t in tags]


def to_problem_out(item: dict[str, Any]) -> ProblemOut:
    tags = list(item.get("tags") or [])
    tags_zh = translate_tags(tags, item.get("tags_zh"))
    difficulty = item.get("difficulty") or "Medium"
    stage = item.get("stage") or "interview-mix"
    number = int(item.get("number") or 0)
    frontend_id = str(item.get("frontend_id") or (number if number else item.get("id", "")))
    return ProblemOut(
        id=item["id"],
        number=number,
        frontend_id=frontend_id,
        title=item.get("title") or "",
        title_zh=item.get("title_zh") or item.get("title"),
        difficulty=difficulty,
        difficulty_zh=DIFFICULTY_ZH.get(difficulty, difficulty),
        tags=tags,
        tags_zh=tags_zh,
        est_minutes=int(item.get("est_minutes") or 25),
        is_template=bool(item.get("is_template")),
        stage=stage,
        stage_zh=STAGE_ZH.get(stage, stage),
        url=item.get("url") or "",
        url_en=item.get("url_en"),
        priority=int(item.get("priority") or 50),
        paid_only=bool(item.get("paid_only")),
        source="leetcode",
    )


def list_problems(
    *,
    tag: str | None = None,
    difficulty: str | None = None,
    stage: str | None = None,
    q: str | None = None,
    only_free: bool = True,
    limit: int | None = None,
) -> list[ProblemOut]:
    data = load_catalog()
    results: list[ProblemOut] = []
    query = (q or "").strip().lower()
    for item in data.get("problems", []):
        if only_free and item.get("paid_only"):
            continue
        if tag and tag not in (item.get("tags") or []):
            continue
        if difficulty and item.get("difficulty") != difficulty:
            continue
        if stage and item.get("stage") != stage:
            continue
        if query:
            blob = " ".join(
                [
                    str(item.get("number") or ""),
                    str(item.get("frontend_id") or ""),
                    item.get("title") or "",
                    item.get("title_zh") or "",
                    " ".join(item.get("tags") or []),
                    " ".join(item.get("tags_zh") or []),
                ]
            ).lower()
            if query not in blob:
                continue
        results.append(to_problem_out(item))
        if limit is not None and len(results) >= limit:
            break
    return results


def get_problem_map() -> dict[str, ProblemOut]:
    # full map without search filters
    data = load_catalog()
    out: dict[str, ProblemOut] = {}
    for item in data.get("problems", []):
        if item.get("paid_only"):
            continue
        p = to_problem_out(item)
        out[p.id] = p
    return out


def get_stages() -> list[dict[str, Any]]:
    data = load_catalog()
    stages = data.get("stages") or [
        {"id": sid, "title": title, "order": i}
        for i, (sid, title) in enumerate(STAGE_ZH.items())
    ]
    return sorted(stages, key=lambda s: s.get("order", 0))


def catalog_stats() -> dict[str, Any]:
    data = load_catalog()
    problems = [p for p in data.get("problems", []) if not p.get("paid_only")]
    return {
        "total": len(problems),
        "easy": sum(1 for p in problems if p.get("difficulty") == "Easy"),
        "medium": sum(1 for p in problems if p.get("difficulty") == "Medium"),
        "hard": sum(1 for p in problems if p.get("difficulty") == "Hard"),
        "note": data.get("note") or "",
    }


def reload_catalog() -> None:
    load_catalog.cache_clear()
