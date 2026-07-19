"""新闻库路由 —— 主要供调试面板查看全量新闻及标签。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tax_compliance_radar.models.schemas import ApiResponse
from tax_compliance_radar.services.db import (
    clear_all_news,
    dedupe_news_items,
    get_news_item,
    insert_news_item,
    list_news_items,
)

router = APIRouter(prefix="/api/v1/news", tags=["news"])


@router.get("", response_model=ApiResponse)
@router.get("/", response_model=ApiResponse)
def api_list_news() -> ApiResponse:
    return ApiResponse(data=list_news_items())


@router.get("/tags", response_model=ApiResponse)
def api_list_all_tags() -> ApiResponse:
    """返回新闻库中出现过的所有标签，按出现频次倒序 —— 供调试面板做 tag 选择器数据源。"""
    freq: dict[str, int] = {}
    for n in list_news_items():
        for t in n.get("tags") or []:
            freq[t] = freq.get(t, 0) + 1
    ordered = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return ApiResponse(data=[{"tag": t, "count": c} for t, c in ordered])


class NewsCreateBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=500)
    body: str = Field("", max_length=8000)
    source: str = Field("调试面板手动新增", max_length=100)
    publish_time: str | None = None  # ISO；缺省=当前时间
    tags: list[str] = Field(default_factory=list)
    original_link: str | None = None


@router.post("", response_model=ApiResponse)
@router.post("/", response_model=ApiResponse)
def api_create_news(payload: NewsCreateBody) -> ApiResponse:
    """调试用：向新闻库新增一条政策/新闻。"""
    tags = [t.strip() for t in (payload.tags or []) if isinstance(t, str) and t.strip()]
    if not tags:
        raise HTTPException(status_code=400, detail="至少需要一个标签，否则永远匹配不到任何画像")
    publish_time = payload.publish_time or datetime.now(timezone.utc).isoformat()
    news_id = insert_news_item(
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        body=(payload.body or "").strip(),
        source=(payload.source or "").strip() or "调试面板手动新增",
        publish_time=publish_time,
        tags=tags,
        original_link=(payload.original_link or "").strip() or None,
    )
    news = get_news_item(news_id)
    return ApiResponse(data=news)


@router.get("/{news_id}", response_model=ApiResponse)
def api_get_news(news_id: int) -> ApiResponse:
    news = get_news_item(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="新闻不存在")
    return ApiResponse(data=news)


@router.post("/rebuild", response_model=ApiResponse)
def api_rebuild_news_library() -> ApiResponse:
    """重建新闻库：清空 news_items 和 news_pushes，重新执行 seed_profiles_and_news(force=True) 播种。
    仅重置由 SEED_NEWS 定义的内置新闻，用户手动新增（无法与 seed 区分）会被一并清除。
    """
    from tax_compliance_radar.database.seed_profiles_news import seed_profiles_and_news

    removed_news, removed_pushes = clear_all_news()
    # force=True 保证 seed_profiles_and_news 会重新写入 SEED_NEWS
    seed_profiles_and_news(force=True)
    from tax_compliance_radar.services.db import news_count
    return ApiResponse(
        data={
            "removed_news": removed_news,
            "removed_pushes": removed_pushes,
            "seeded_news": news_count(),
        }
    )


@router.post("/dedupe", response_model=ApiResponse)
def api_dedupe_news_items() -> ApiResponse:
    """按 (title, publish_time) 去重现有新闻，保留 news_id 最小的一条并迁移相关推送。
    比 rebuild 温和：不会清空手动新增的数据，只删重复。"""
    removed = dedupe_news_items()
    return ApiResponse(data={"removed": removed})
