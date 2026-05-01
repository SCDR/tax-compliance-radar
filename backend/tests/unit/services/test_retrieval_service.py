"""单元测试 - RAG检索服务"""
from __future__ import annotations

import pytest

from tax_compliance_radar.services import retrieval_service


def test_search_regulations_empty_query():
    """测试空查询返回错误"""
    result = retrieval_service.search_regulations("")
    assert result.success is False
    assert "不能为空" in result.message


def test_search_regulations_whitespace_query():
    """测试仅空白字符查询"""
    result = retrieval_service.search_regulations("   \n  ")
    assert result.success is False


def test_build_context_prompt_below_threshold():
    """测试低于阈值时的上下文提示"""
    result = retrieval_service.RetrievalResult(
        success=True,
        message="暂无相关合规信息",
        documents=[],
        below_threshold=True,
    )
    context = retrieval_service.build_context_prompt(result)
    assert "未检索到与问题相关的合规法规信息" in context
    assert "暂无相关合规信息" in context


def test_build_context_prompt_no_documents():
    """测试无文档时的上下文提示"""
    result = retrieval_service.RetrievalResult(
        success=True,
        message="法规库正在初始化",
        documents=[],
        below_threshold=True,
    )
    context = retrieval_service.build_context_prompt(result)
    assert "未检索到与问题相关的合规法规信息" in context


def test_build_context_prompt_with_documents():
    """测试有文档时构建的上下文"""
    docs = [
        retrieval_service.RetrievedDoc(
            doc_id="test_001",
            doc_name="测试法规",
            content="这是测试法规内容",
            similarity_score=0.85,
            original_link="https://test.com/1",
            chapter="测试章节",
        )
    ]
    result = retrieval_service.RetrievalResult(
        success=True,
        message="OK",
        documents=docs,
        below_threshold=False,
    )
    context = retrieval_service.build_context_prompt(result)
    assert "测试法规" in context
    assert "test_001" in context
    assert "0.85" in context


def test_get_source_references_empty():
    """测试无文档时的来源引用"""
    result = retrieval_service.RetrievalResult(
        success=True,
        message="",
        documents=[],
        below_threshold=True,
    )
    refs = retrieval_service.get_source_references(result)
    assert refs == []


def test_get_source_references_with_docs():
    """测试有文档时的来源引用提取"""
    docs = [
        retrieval_service.RetrievedDoc(
            doc_id="d1",
            doc_name="法规1",
            content="...",
            similarity_score=0.8,
            original_link="https://link1.com",
            chapter="",
        ),
        retrieval_service.RetrievedDoc(
            doc_id="d2",
            doc_name="法规2",
            content="...",
            similarity_score=0.75,
            original_link="https://link2.com",
            chapter="",
        ),
    ]
    result = retrieval_service.RetrievalResult(
        success=True,
        message="OK",
        documents=docs,
        below_threshold=False,
    )
    refs = retrieval_service.get_source_references(result)
    assert len(refs) == 2
    assert "法规1" in refs[0]
    assert "法规2" in refs[1]
    assert "link1" in refs[0]
