"""用户上传文件路由 —— 抽取文本摘要 + 触发标签钩子。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from tax_compliance_radar.models.schemas import ApiResponse
from tax_compliance_radar.services.contract_extractor import (
    extract_audit_fields,
    extract_text_from_file,
)
from tax_compliance_radar.services.db import (
    ensure_profile_exists,
    insert_user_upload,
    list_user_uploads,
)
from tax_compliance_radar.services.policy_pusher import apply_hook
from tax_compliance_radar.services.tag_extractor import extract_tags_from_upload

logger = logging.getLogger(__name__)

MAX_CONTRACT_BYTES = 10 * 1024 * 1024  # 10MB 上限，合同文档一般不会超过

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])

MAX_EXCERPT_BYTES = 20 * 1024  # 20 KB 文本摘要，避免大文件占用 DB


def _profile_id(request: Request) -> str:
    pid = request.headers.get("x-profile-id") or request.query_params.get("profile_id")
    return (pid or "default").strip() or "default"


def _decode_excerpt(raw: bytes) -> str:
    """从任意文件的前 20KB 提取"看得懂的文本"作为摘要。"""
    truncated = raw[:MAX_EXCERPT_BYTES]
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            text = truncated.decode(enc)
            # 过滤不可打印
            return "".join(ch for ch in text if ch.isprintable() or ch in ("\n", "\r", "\t"))
        except UnicodeDecodeError:
            continue
    return ""


@router.post("", response_model=ApiResponse)
@router.post("/", response_model=ApiResponse)
async def api_upload_file(request: Request, file: UploadFile = File(...)) -> ApiResponse:
    profile_id = _profile_id(request)
    ensure_profile_exists(profile_id)

    raw = await file.read()
    size = len(raw)
    excerpt = _decode_excerpt(raw)
    upload_id = insert_user_upload(
        profile_id=profile_id,
        filename=file.filename or "unknown",
        size=size,
        excerpt=excerpt,
    )

    tag_deltas = extract_tags_from_upload(file.filename or "", excerpt)
    apply_hook(profile_id, tag_deltas, source="upload")

    return ApiResponse(
        data={
            "upload_id": upload_id,
            "profile_id": profile_id,
            "filename": file.filename,
            "size": size,
            "tag_deltas": tag_deltas,
        }
    )


@router.get("", response_model=ApiResponse)
@router.get("/", response_model=ApiResponse)
def api_list_uploads(request: Request) -> ApiResponse:
    profile_id = _profile_id(request)
    return ApiResponse(data=list_user_uploads(profile_id))


@router.post("/contract-extract", response_model=ApiResponse)
async def api_contract_extract(file: UploadFile = File(...)) -> ApiResponse:
    """从上传的合同文件中抽取表单字段（不落库、不写画像标签）。"""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(raw) > MAX_CONTRACT_BYTES:
        raise HTTPException(status_code=413, detail="文件过大，请压缩至 10MB 以内")

    try:
        text = extract_text_from_file(file.filename or "", raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("合同文本抽取失败")
        raise HTTPException(status_code=500, detail=f"合同文件解析失败：{exc}") from exc

    try:
        extracted = await extract_audit_fields(text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("合同字段抽取失败")
        raise HTTPException(status_code=500, detail="AI 抽取服务暂不可用，请稍后重试") from exc

    excerpt_preview = text[:800]
    return ApiResponse(
        data={
            "filename": file.filename,
            "size": len(raw),
            "excerpt_preview": excerpt_preview,
            **extracted,
        }
    )
