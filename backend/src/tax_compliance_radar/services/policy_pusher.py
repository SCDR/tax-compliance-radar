"""政策/新闻推送引擎。

- 标签时效性：读取时对每个 profile_tag 做指数衰减 exp(-Δdays / HALF_LIFE_DAYS)。
- 匹配打分：新闻 tags 与 profile active_tags 的交集权重之和 * 新闻新鲜度因子。
- 去重：已存在的 (profile_id, news_id) push 记录不重复插入。
- 冷启动兜底：画像无激活标签或匹配为空时，回退到"编辑精选"（带 EDITORIAL_TAG 标签的新闻）。
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable

from tax_compliance_radar.services.db import (
    ensure_profile_exists,
    insert_news_push,
    list_news_items,
    list_news_pushes,
    list_profile_tags,
)

# 参数
HALF_LIFE_DAYS = 30.0
TAG_MIN_WEIGHT = 0.15
TOP_K_DEFAULT = 3
EDITORIAL_TAG = "编辑精选"


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        # sqlite 里存的是 utc_now_iso() 生成的带 tz 字符串
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _days_between(now: datetime, ts: datetime) -> float:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (now - ts).total_seconds() / 86400.0)


def compute_effective_tags(
    profile_id: str,
    *,
    now: datetime | None = None,
    min_weight: float = TAG_MIN_WEIGHT,
) -> list[dict]:
    """返回 [{tag_key, raw_weight, effective_weight, age_days, source, last_touch_time}]，按 effective_weight 降序。"""
    now = now or datetime.now(timezone.utc)
    raw_tags = list_profile_tags(profile_id)
    result: list[dict] = []
    for tag in raw_tags:
        ts = _parse_iso(tag["last_touch_time"])
        age_days = _days_between(now, ts) if ts else 999.0
        decay = math.exp(-age_days / HALF_LIFE_DAYS)
        effective = float(tag["weight"]) * decay
        result.append(
            {
                "tag_key": tag["tag_key"],
                "raw_weight": float(tag["weight"]),
                "effective_weight": effective,
                "age_days": age_days,
                "source": tag["source"],
                "last_touch_time": tag["last_touch_time"],
                "active": effective >= min_weight,
            }
        )
    result.sort(key=lambda x: x["effective_weight"], reverse=True)
    return result


def _news_freshness(publish_time: str | None, now: datetime) -> float:
    ts = _parse_iso(publish_time)
    if ts is None:
        return 0.3
    age = _days_between(now, ts)
    if age <= 30:
        return 1.0
    if age <= 90:
        return 0.6
    return 0.3


def match_news_for_profile(
    profile_id: str,
    top_k: int = TOP_K_DEFAULT,
    *,
    include_seen: bool = False,
) -> list[dict]:
    """根据画像挑选 top_k 条新闻，返回带 score / matched_tags 的候选列表。

    冷启动兜底：若画像无激活标签或没有匹配新闻，则回退到"编辑精选"
    （tags 中含 EDITORIAL_TAG 的新闻），按新鲜度排序。
    """
    now = datetime.now(timezone.utc)
    active_tags = {
        t["tag_key"]: t["effective_weight"]
        for t in compute_effective_tags(profile_id, now=now)
        if t["active"]
    }

    news_items = list_news_items()
    if not news_items:
        return []

    seen_news_ids: set[int] = set()
    if not include_seen:
        seen_news_ids = {p["news_id"] for p in list_news_pushes(profile_id, limit=1000, include_dismissed=True)}

    candidates: list[dict] = []
    if active_tags:
        for news in news_items:
            if news["news_id"] in seen_news_ids:
                continue
            news_tags = news.get("tags") or []
            matched = [t for t in news_tags if t in active_tags]
            if not matched:
                continue
            base_score = sum(active_tags[t] for t in matched)
            freshness = _news_freshness(news.get("publish_time"), now)
            score = base_score * freshness
            candidates.append(
                {
                    **news,
                    "match_score": score,
                    "matched_tags": matched,
                    "freshness": freshness,
                }
            )
        candidates.sort(key=lambda c: c["match_score"], reverse=True)

    # 冷启动 / 无匹配 兜底：编辑精选
    if not candidates:
        for news in news_items:
            if news["news_id"] in seen_news_ids:
                continue
            news_tags = news.get("tags") or []
            if EDITORIAL_TAG not in news_tags:
                continue
            freshness = _news_freshness(news.get("publish_time"), now)
            candidates.append(
                {
                    **news,
                    "match_score": freshness,        # 冷启动分值 = 新鲜度
                    "matched_tags": [EDITORIAL_TAG],
                    "freshness": freshness,
                    "editorial": True,
                }
            )
        candidates.sort(key=lambda c: c["match_score"], reverse=True)

    return candidates[:top_k]


def push_news_to_profile(profile_id: str, top_k: int = TOP_K_DEFAULT) -> list[dict]:
    """为 profile 挑选并落库推送记录，返回新插入的推送列表。"""
    ensure_profile_exists(profile_id)
    matches = match_news_for_profile(profile_id, top_k=top_k, include_seen=False)
    inserted: list[dict] = []
    for m in matches:
        push_id = insert_news_push(
            profile_id=profile_id,
            news_id=m["news_id"],
            match_score=m["match_score"],
            matched_tags=m["matched_tags"],
        )
        if push_id is not None:
            inserted.append({**m, "push_id": push_id})
    return inserted


def safe_push_async(profile_id: str, top_k: int = TOP_K_DEFAULT) -> None:
    """后台任务用的安全包装：任何异常都吞掉，仅打印日志。"""
    try:
        push_news_to_profile(profile_id, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        print(f"[policy_pusher] push failed for profile={profile_id}: {exc}")


def apply_hook(
    profile_id: str,
    tag_deltas: dict[str, float],
    source: str,
) -> None:
    """qa/audit/upload 钩子统一入口：写入标签增量 + 触发一轮推送。"""
    from tax_compliance_radar.services.db import upsert_profile_tags

    try:
        ensure_profile_exists(profile_id)
        if tag_deltas:
            upsert_profile_tags(profile_id, tag_deltas, source=source)
        push_news_to_profile(profile_id, top_k=TOP_K_DEFAULT)
    except Exception as exc:  # noqa: BLE001
        print(f"[policy_pusher] hook apply failed profile={profile_id} source={source}: {exc}")


def top_active_tag_keys(profile_id: str, top_n: int = 10) -> list[str]:
    return [
        t["tag_key"]
        for t in compute_effective_tags(profile_id)[:top_n]
        if t["active"]
    ]


__all__ = [
    "HALF_LIFE_DAYS",
    "TAG_MIN_WEIGHT",
    "compute_effective_tags",
    "match_news_for_profile",
    "push_news_to_profile",
    "safe_push_async",
    "apply_hook",
    "top_active_tag_keys",
]

# 便于类型提示的静默使用
_ = Iterable
