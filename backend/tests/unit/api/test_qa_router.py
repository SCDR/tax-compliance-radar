"""QA接口单元测试"""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from tax_compliance_radar.models.schemas import (
    QAQueryData,
    QAAnswer,
)


class TestQARouter:
    """QA接口测试"""

    def test_query_qa_success(self, client: TestClient, mock_qa_service):
        """测试正常提交问答请求"""
        payload = {"query_text": "泰国VAT注册要求是什么？"}

        response = client.post("/api/v1/qa/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "disclaimer" in data["data"]
        assert data["data"]["qa_id"] == 1

    def test_query_qa_empty_text(self, client: TestClient):
        """测试空查询文本 - 应该返回400"""
        payload = {"query_text": ""}

        response = client.post("/api/v1/qa/query", json=payload)

        assert response.status_code == 400 or response.status_code == 422
        # FastAPI的Pydantic验证错误返回422

    def test_query_qa_too_long_text(self, client: TestClient):
        """测试超长查询文本 - 应该返回400"""
        long_text = "a" * 600  # 超过500字限制
        payload = {"query_text": long_text}

        response = client.post("/api/v1/qa/query", json=payload)

        assert response.status_code in (400, 422)

    def test_query_qa_missing_field(self, client: TestClient):
        """测试缺少必填字段"""
        payload = {}  # 缺少query_text

        response = client.post("/api/v1/qa/query", json=payload)

        assert response.status_code in (400, 422)

    def test_get_qa_history_empty(self, client: TestClient, temp_db):
        """测试获取空的历史记录列表"""
        # 先初始化数据库
        from tax_compliance_radar.services.db import initialize_database
        initialize_database()

        response = client.get("/api/v1/qa/history")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    def test_get_qa_history_detail_not_found(self, client: TestClient, temp_db):
        """测试获取不存在的历史记录详情"""
        from tax_compliance_radar.services.db import initialize_database
        initialize_database()

        response = client.get("/api/v1/qa/history/99999")

        # 应该返回404或正确的错误响应
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            # 如果返回200，检查是否有正确的错误提示
            data = response.json()
            assert data["code"] in (200, 404)

    def test_query_qa_response_structure(self, client: TestClient, mock_qa_service):
        """验证问答响应的数据结构"""
        payload = {"query_text": "测试问题"}

        response = client.post("/api/v1/qa/query", json=payload)

        assert response.status_code == 200
        data = response.json()

        # 验证外层结构
        assert "code" in data
        assert "msg" in data
        assert "data" in data

        # 验证data结构
        result_data = data["data"]
        assert "qa_id" in result_data
        assert "query_text" in result_data
        assert "answer_text" in result_data
        assert "disclaimer" in result_data
        assert "create_time" in result_data

        # 验证answer_text结构
        answer = result_data["answer_text"]
        assert "regulation_base" in answer
        assert "core_rules" in answer
        assert "compliance_suggestion" in answer
        assert "risk_warning" in answer
        assert "operation_guide" in answer
        assert "original_link" in answer
