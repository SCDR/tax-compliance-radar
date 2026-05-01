from __future__ import annotations

from datetime import datetime, timezone

from tax_compliance_radar.models.schemas import QAAnswer, QAQueryData
from tax_compliance_radar.services.db import insert_qa_history
from tax_compliance_radar.services.llm_service import generate_qa_answer_with_rag
from tax_compliance_radar.services.disclaimer import get_disclaimer
from tax_compliance_radar.services.retrieval_service import search_regulations


def query_qa(query_text: str) -> QAQueryData:
    """
    完整RAG QA工作流：
    1. 相似度0.7检索法规
    2. 低于阈值：返回标准化"无信息"响应
    3. 基于上下文生成答案
    4. 存储召回文档ID用于审计追踪
    """
    retrieval_result = search_regulations(query_text)

    if retrieval_result.below_threshold:
        answer = QAAnswer(
            regulation_base="暂无相关合规信息",
            core_rules="暂无相关合规信息",
            compliance_suggestion="建议您咨询专业税务顾问获取准确信息",
            risk_warning="暂无相关合规信息",
            operation_guide="暂无相关合规信息",
            original_link="",
        )
        doc_ids = []
    else:
        answer = generate_qa_answer_with_rag(query_text, retrieval_result)
        doc_ids = [doc.doc_id for doc in retrieval_result.documents]

    qa_id = insert_qa_history(query_text, answer.model_dump(), doc_ids)

    return QAQueryData(
        qa_id=qa_id,
        query_text=query_text,
        answer_text=answer,
        disclaimer=get_disclaimer(),
        create_time=datetime.now(timezone.utc).isoformat(),
    )
