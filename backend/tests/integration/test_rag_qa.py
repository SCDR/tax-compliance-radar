"""集成测试 - QA RAG完整链路"""
from __future__ import annotations

import pytest

from tax_compliance_radar.services.qa_service import query_qa


@pytest.mark.integration
@pytest.mark.requires_ollama
def test_qa_rag_full_flow():
    """测试QA RAG完整链路：检索 -> 生成结构化回答"""
    result = query_qa("泰国VAT注册门槛是什么？")

    assert result.query_text == "泰国VAT注册门槛是什么？"
    assert result.answer_text is not None
    assert result.create_time is not None
    assert result.disclaimer is not None

    # 验证结构化字段存在 (即使未检索到也会返回标准结构)
    answer = result.answer_text
    assert hasattr(answer, "regulation_base")
    assert hasattr(answer, "core_rules")
    assert hasattr(answer, "compliance_suggestion")
    assert hasattr(answer, "risk_warning")
    assert hasattr(answer, "operation_guide")
    assert hasattr(answer, "original_link")

    # 打印实际结果便于人工验证
    print(f"\n=== QA RAG 集成测试结果 ===")
    print(f"法规依据: {answer.regulation_base}")
    print(f"核心规则: {answer.core_rules}")
    print(f"合规建议: {answer.compliance_suggestion}")
    print(f"风险提示: {answer.risk_warning}")
    print(f"操作指引: {answer.operation_guide}")
