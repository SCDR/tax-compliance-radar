import json

from fastapi import APIRouter, HTTPException

from tax_compliance_radar.models.schemas import ApiResponse, QAAnswer, QAQueryData, QAQueryRequest
from tax_compliance_radar.services.db import get_connection
from tax_compliance_radar.services.qa_service import query_qa

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


@router.post("/query", response_model=ApiResponse)
def submit_query(payload: QAQueryRequest) -> ApiResponse:
    query_text = payload.query_text.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="请输入您要咨询的泰国VAT合规问题")
    result = query_qa(query_text)
    return ApiResponse(data=result)


@router.get("/history", response_model=ApiResponse)
def list_history() -> ApiResponse:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT qa_id, query_text, create_time FROM qa_history ORDER BY qa_id DESC"
        ).fetchall()
    data = [dict(row) for row in rows]
    return ApiResponse(data=data)


@router.get("/history/{qa_id}", response_model=ApiResponse)
def get_history_detail(qa_id: int) -> ApiResponse:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT qa_id, query_text, answer_text, recall_doc_ids, create_time FROM qa_history WHERE qa_id = ?",
            (qa_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="问答记录不存在")
    answer_text = QAAnswer.model_validate(json.loads(row["answer_text"]))
    data = QAQueryData(
        qa_id=row["qa_id"],
        query_text=row["query_text"],
        answer_text=answer_text,
        disclaimer="本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。",
        create_time=row["create_time"],
    )
    return ApiResponse(data=data)
