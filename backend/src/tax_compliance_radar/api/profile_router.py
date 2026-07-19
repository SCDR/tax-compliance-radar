"""用户画像 / 标签 / 推送相关的路由。"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from tax_compliance_radar.models.schemas import ApiResponse
from tax_compliance_radar.services.db import (
    clear_news_pushes,
    clear_profile_tags,
    dismiss_push,
    ensure_profile_exists,
    get_connection,
    get_profile,
    list_news_pushes,
    list_profile_tags,
    list_profiles,
    upsert_profile_tags,
)
from tax_compliance_radar.services.policy_pusher import (
    compute_effective_tags,
    match_news_for_profile,
    push_news_to_profile,
)
from tax_compliance_radar.services.tag_extractor import (
    extract_tags_from_audit,
    extract_tags_from_qa,
    extract_tags_from_upload,
)

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


def _profile_id_from_request(request: Request) -> str:
    pid = request.headers.get("x-profile-id") or request.query_params.get("profile_id")
    if pid:
        return pid.strip()
    return "default"


@router.get("/profiles", response_model=ApiResponse)
def api_list_profiles() -> ApiResponse:
    return ApiResponse(data=list_profiles())


@router.get("/profiles/{profile_id}", response_model=ApiResponse)
def api_get_profile(profile_id: str) -> ApiResponse:
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile 不存在")
    tags = compute_effective_tags(profile_id)
    return ApiResponse(data={**profile, "tags": tags})


@router.get("/profiles/{profile_id}/tags", response_model=ApiResponse)
def api_get_profile_tags(profile_id: str) -> ApiResponse:
    ensure_profile_exists(profile_id)
    tags = compute_effective_tags(profile_id)
    return ApiResponse(data=tags)


class RecomputeResponse(BaseModel):
    profile_id: str
    replayed_qa: int
    replayed_audits: int
    replayed_uploads: int


@router.post("/profiles/{profile_id}/recompute", response_model=ApiResponse)
def api_recompute_profile(profile_id: str) -> ApiResponse:
    """
    根据该 profile 名下的历史全量重放标签：
      1. 清空 profile_tags
      2. 遍历该 profile 名下的 qa_history / audit_history / user_uploads，
         用 tag_extractor 重新算出每次交互的标签增量并累加。
    这是"调试用"接口，帮助验证时效性衰减。
    """
    ensure_profile_exists(profile_id)
    clear_profile_tags(profile_id)

    replayed_qa = replayed_audits = replayed_uploads = 0
    with get_connection() as connection:
        # qa
        qa_rows = connection.execute(
            "SELECT query_text, answer_text, recall_doc_ids FROM qa_history "
            "WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
        for row in qa_rows:
            try:
                answer_obj: Any = json.loads(row["answer_text"] or "{}")
            except (json.JSONDecodeError, TypeError):
                answer_obj = row["answer_text"] or ""
            doc_ids = [s.strip() for s in (row["recall_doc_ids"] or "").split(",") if s.strip()]
            deltas = extract_tags_from_qa(row["query_text"] or "", answer_obj, doc_ids)
            if deltas:
                upsert_profile_tags(profile_id, deltas, source="qa")
                replayed_qa += 1

        # audit
        audit_rows = connection.execute(
            "SELECT business_info, audit_report FROM audit_history "
            "WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
        for row in audit_rows:
            try:
                business_info = json.loads(row["business_info"] or "{}")
                audit_report = json.loads(row["audit_report"] or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            deltas = extract_tags_from_audit(business_info, audit_report)
            if deltas:
                upsert_profile_tags(profile_id, deltas, source="audit")
                replayed_audits += 1

        # uploads
        upload_rows = connection.execute(
            "SELECT filename, excerpt FROM user_uploads WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
        for row in upload_rows:
            deltas = extract_tags_from_upload(row["filename"] or "", row["excerpt"] or "")
            if deltas:
                upsert_profile_tags(profile_id, deltas, source="upload")
                replayed_uploads += 1

    return ApiResponse(
        data={
            "profile_id": profile_id,
            "replayed_qa": replayed_qa,
            "replayed_audits": replayed_audits,
            "replayed_uploads": replayed_uploads,
        }
    )


# ------------- 推送 -------------


@router.get("/pushes", response_model=ApiResponse)
def api_list_pushes(request: Request, limit: int = 20) -> ApiResponse:
    profile_id = _profile_id_from_request(request)
    ensure_profile_exists(profile_id)
    pushes = list_news_pushes(profile_id, limit=limit)
    return ApiResponse(data={"profile_id": profile_id, "pushes": pushes})


class TriggerPushBody(BaseModel):
    profile_id: str | None = None
    top_k: int = 3


@router.post("/pushes/trigger", response_model=ApiResponse)
def api_trigger_push(request: Request, body: TriggerPushBody | None = None) -> ApiResponse:
    profile_id = (body and body.profile_id) or _profile_id_from_request(request)
    top_k = body.top_k if body else 3
    ensure_profile_exists(profile_id)
    inserted = push_news_to_profile(profile_id, top_k=top_k)
    matches_preview = match_news_for_profile(profile_id, top_k=top_k, include_seen=True)
    return ApiResponse(
        data={
            "profile_id": profile_id,
            "inserted": inserted,
            "preview": matches_preview,
        }
    )


@router.post("/pushes/{push_id}/dismiss", response_model=ApiResponse)
def api_dismiss_push(push_id: int) -> ApiResponse:
    dismiss_push(push_id)
    return ApiResponse(data={"push_id": push_id, "dismissed": True})


# ------------- 调试辅助 -------------


@router.post("/debug/reset-seed-profiles", response_model=ApiResponse)
def api_reset_seed_profiles() -> ApiResponse:
    """一键把所有 seed 测试画像恢复到初始状态：
    1. 清空每个 seed profile 的 profile_tags / news_pushes / qa_history / audit_history；
    2. 重新执行 seed_profiles_and_news(force=False) 覆盖 base_tags 与 seed 历史。
    仅重置 SEED_PROFILES 中定义的画像，用户自建的浏览器画像不受影响。
    news_items 表**不清空**（重建新闻库请用「重建新闻库」按钮），
    避免重复重置时把新闻库塞满重复数据。
    """
    from tax_compliance_radar.database.seed_profiles_news import (
        SEED_PROFILES,
        seed_profiles_and_news,
    )

    reset_details: list[dict] = []
    # 单事务内完成所有清理，避免与 clear_profile_tags/clear_news_pushes 内部各开
    # connection 造成 "database is locked" 死锁
    with get_connection() as connection:
        for p in SEED_PROFILES:
            pid = p["profile_id"]
            # 计数
            cleared_tags_row = connection.execute(
                "SELECT COUNT(*) AS n FROM profile_tags WHERE profile_id = ?", (pid,),
            ).fetchone()
            cleared_tags = int(cleared_tags_row["n"] if cleared_tags_row else 0)

            # 逐表 DELETE（同一 connection）
            connection.execute("DELETE FROM profile_tags WHERE profile_id = ?", (pid,))
            push_cur = connection.execute("DELETE FROM news_pushes WHERE profile_id = ?", (pid,))
            qa_cur = connection.execute("DELETE FROM qa_history WHERE profile_id = ?", (pid,))
            audit_cur = connection.execute("DELETE FROM audit_history WHERE profile_id = ?", (pid,))

            reset_details.append(
                {
                    "profile_id": pid,
                    "display_name": p["display_name"],
                    "cleared_tags": cleared_tags,
                    "cleared_pushes": push_cur.rowcount or 0,
                    "cleared_qa": qa_cur.rowcount or 0,
                    "cleared_audits": audit_cur.rowcount or 0,
                }
            )
        connection.commit()

    # 事务已完成，此刻数据库空闲，seed_profiles_and_news 可以正常开新连接
    # force=False：新闻表不动（避免累加），QA/audit 因上面已清空会走"从零播种"分支
    seed_profiles_and_news(force=False)

    return ApiResponse(
        data={
            "reset_count": len(reset_details),
            "profiles": reset_details,
        }
    )


@router.get("/debug/summary", response_model=ApiResponse)
def api_debug_summary(request: Request) -> ApiResponse:
    """调试面板用：一次拉齐 profile + tags + pushes + top news 候选。"""
    profile_id = _profile_id_from_request(request)
    ensure_profile_exists(profile_id)
    profile = get_profile(profile_id)
    tags = compute_effective_tags(profile_id)
    pushes = list_news_pushes(profile_id, limit=20)
    preview = match_news_for_profile(profile_id, top_k=10, include_seen=True)
    return ApiResponse(
        data={
            "profile": profile,
            "tags": tags,
            "pushes": pushes,
            "match_preview": preview,
            "raw_tags": list_profile_tags(profile_id),
        }
    )
