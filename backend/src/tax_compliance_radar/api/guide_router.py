"""合规指南（模块四）API 路由。

提交：POST /api/v1/guide/stream → {task_id}
消费：GET  /api/v1/guide/stream/{task_id} → SSE
标签库：GET /api/v1/guide/tag-library
画像标签：GET /api/v1/guide/profile-tags
历史：GET /api/v1/guide/history、/history/{guide_id}
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from tax_compliance_radar.services.db import (
    get_guide_history,
    list_guide_history,
)
from tax_compliance_radar.services.guide_service import (
    get_profile_top_tags,
    get_tag_library,
    stream_guide,
)


router = APIRouter(prefix="/api/v1/guide", tags=["guide"])


# ----------------------------------------------------------------------------
# 提交/SSE
# ----------------------------------------------------------------------------


class GuideRequest(BaseModel):
    countries: list[str] = Field(default_factory=lambda: ["TH", "ID", "MY", "VN"])
    business_type: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    include_optional: bool = True


_active: dict[str, dict] = {}


def _profile_id(request: Request) -> str:
    pid = request.headers.get("x-profile-id")
    return (pid or "default").strip() or "default"


@router.post("/stream")
async def submit_guide(payload: GuideRequest, request: Request):
    task_id = str(uuid.uuid4())[:8]
    _active[task_id] = {
        "countries": payload.countries or ["TH", "ID", "MY", "VN"],
        "business_type": payload.business_type,
        "tags": payload.tags or [],
        "include_optional": bool(payload.include_optional),
        "profile_id": _profile_id(request),
    }
    return {"task_id": task_id, "message": "合规指南任务已提交"}


@router.get("/stream/{task_id}")
async def stream_guide_endpoint(task_id: str, request: Request) -> StreamingResponse:
    if task_id not in _active:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    info = _active[task_id]
    profile_id = (
        request.headers.get("x-profile-id")
        or request.query_params.get("profile_id")
        or info.get("profile_id")
        or "default"
    ).strip() or "default"

    async def event_gen():
        try:
            async for chunk in stream_guide(
                countries=info["countries"],
                business_type=info["business_type"],
                tags=info["tags"],
                include_optional=info["include_optional"],
                profile_id=profile_id,
            ):
                yield chunk
        finally:
            _active.pop(task_id, None)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no",
        },
    )


# ----------------------------------------------------------------------------
# 标签库 / 画像标签
# ----------------------------------------------------------------------------


@router.get("/tag-library")
def tag_library():
    return {"data": get_tag_library()}


@router.get("/profile-tags")
def profile_tags(request: Request, limit: int = 12):
    pid = _profile_id(request)
    return {"data": get_profile_top_tags(pid, limit=limit)}


# ----------------------------------------------------------------------------
# 历史
# ----------------------------------------------------------------------------


@router.get("/history")
def guide_history(request: Request, limit: int = 20):
    pid = _profile_id(request)
    return {"data": list_guide_history(pid, limit=limit)}


@router.get("/history/{guide_id}")
def guide_detail(guide_id: int):
    row = get_guide_history(guide_id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"data": row}
