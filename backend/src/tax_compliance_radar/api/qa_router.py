import json

from fastapi import APIRouter, HTTPException, Request

from tax_compliance_radar.models.schemas import ApiResponse, QAAnswer, QAQueryData, QAQueryRequest
from tax_compliance_radar.services.db import get_connection
from tax_compliance_radar.services.policy_pusher import apply_hook
from tax_compliance_radar.services.qa_service import query_qa
from tax_compliance_radar.services.tag_extractor import extract_tags_from_qa

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


def _profile_id(request: Request) -> str:
    pid = request.headers.get("x-profile-id")
    return (pid or "default").strip() or "default"


@router.post("/query", response_model=ApiResponse)
def submit_query(payload: QAQueryRequest, request: Request) -> ApiResponse:
    query_text = payload.query_text.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="请输入您要咨询的泰国VAT合规问题")
    pid = _profile_id(request)
    result = query_qa(query_text, profile_id=pid)
    # 触发标签钩子（同步执行但兜底不抛）
    try:
        deltas = extract_tags_from_qa(
            query_text,
            result.answer_text.model_dump() if hasattr(result.answer_text, "model_dump") else result.answer_text,
            [],
        )
        apply_hook(pid, deltas, source="qa")
    except Exception as exc:  # noqa: BLE001
        print(f"[qa_router] apply_hook failed: {exc}")
    return ApiResponse(data=result)


@router.get("/history", response_model=ApiResponse)
def list_history(request: Request) -> ApiResponse:
    pid = _profile_id(request)
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT qa_id, query_text, recall_doc_ids, create_time FROM qa_history "
            "WHERE profile_id = ? ORDER BY qa_id DESC",
            (pid,),
        ).fetchall()
    data = []
    for row in rows:
        raw_ids = row["recall_doc_ids"] or ""
        sources = [s.strip() for s in raw_ids.split(",") if s.strip()]
        data.append({
            "qa_id": row["qa_id"],
            "query_text": row["query_text"],
            "create_time": row["create_time"],
            "sources": sources,
        })
    return ApiResponse(data=data)


@router.get("/history/{qa_id}", response_model=ApiResponse)
def get_history_detail(qa_id: int, request: Request) -> ApiResponse:
    pid = _profile_id(request)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT qa_id, profile_id, query_text, answer_text, recall_doc_ids, recall_snippets, recall_positions, create_time "
            "FROM qa_history WHERE qa_id = ?",
            (qa_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="问答记录不存在")
    if (row["profile_id"] or "default") != pid:
        # 不暴露"存在但无权限"，与"不存在"返回一致
        raise HTTPException(status_code=404, detail="问答记录不存在")
    answer_text = QAAnswer.model_validate(json.loads(row["answer_text"]))
    raw_ids = row["recall_doc_ids"] or ""
    sources = [s.strip() for s in raw_ids.split(",") if s.strip()]
    try:
        snippets = json.loads(row["recall_snippets"] or "{}")
        if not isinstance(snippets, dict):
            snippets = {}
    except (json.JSONDecodeError, TypeError):
        snippets = {}
    try:
        # 老历史记录可能没有 recall_positions 列或为空 —— 兼容返回 {}
        raw_pos = row["recall_positions"] if "recall_positions" in row.keys() else None
        positions = json.loads(raw_pos or "{}")
        if not isinstance(positions, dict):
            positions = {}
    except (json.JSONDecodeError, TypeError, IndexError):
        positions = {}
    data = QAQueryData(
        qa_id=row["qa_id"],
        query_text=row["query_text"],
        answer_text=answer_text,
        disclaimer="本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。",
        create_time=row["create_time"],
    )
    payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
    payload["sources"] = sources
    payload["snippets"] = snippets
    payload["positions"] = positions
    return ApiResponse(data=payload)
