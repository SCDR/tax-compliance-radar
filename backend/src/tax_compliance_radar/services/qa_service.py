from __future__ import annotations

from datetime import datetime, timezone

from tax_compliance_radar.models.schemas import QAAnswer, QAQueryData
from tax_compliance_radar.services.db import insert_qa_history
from tax_compliance_radar.services.llm_service import generate_qa_answer
from tax_compliance_radar.services.disclaimer import get_disclaimer


def query_qa(query_text: str) -> QAQueryData:
    answer = generate_qa_answer(query_text)
    qa_id = insert_qa_history(query_text, answer.model_dump(), [])
    return QAQueryData(
        qa_id=qa_id,
        query_text=query_text,
        answer_text=answer,
        disclaimer=get_disclaimer(),
        create_time=datetime.now(timezone.utc).isoformat(),
    )
