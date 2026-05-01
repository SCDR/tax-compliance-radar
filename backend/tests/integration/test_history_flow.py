"""历史记录流程集成测试"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from tax_compliance_radar.main import app
from tax_compliance_radar.services.db import initialize_database


@pytest.fixture(autouse=True)
def setup_test_db():
    """使用临时数据库进行测试"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    original_db_path = os.environ.get("DB_PATH", "")
    os.environ["DB_PATH"] = path
    initialize_database()
    yield
    os.environ["DB_PATH"] = original_db_path
    if os.path.exists(path):
        os.unlink(path)


class TestQAHistoryFlow:
    """QA历史记录流程测试"""

    def test_empty_history(self):
        """测试空历史记录列表"""
        client = TestClient(app)
        response = client.get("/api/v1/qa/history")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    def test_history_detail_not_found(self):
        """测试获取不存在的历史记录详情"""
        client = TestClient(app)
        response = client.get("/api/v1/qa/history/99999")
        assert response.status_code == 404


class TestAuditHistoryFlow:
    """审核历史记录流程测试"""

    def test_empty_history(self):
        """测试空历史记录列表"""
        client = TestClient(app)
        response = client.get("/api/v1/audit/history")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    def test_history_detail_not_found(self):
        """测试获取不存在的历史记录详情"""
        client = TestClient(app)
        response = client.get("/api/v1/audit/history/99999")
        assert response.status_code == 404


class TestHistoryConsistency:
    """历史记录一致性测试"""

    def test_qa_history_response_structure(self):
        """测试QA历史记录响应结构"""
        client = TestClient(app)
        response = client.get("/api/v1/qa/history")
        assert response.status_code == 200
        data = response.json()

        assert "code" in data
        assert "msg" in data
        assert "data" in data

    def test_audit_history_response_structure(self):
        """测试Audit历史记录响应结构"""
        client = TestClient(app)
        response = client.get("/api/v1/audit/history")
        assert response.status_code == 200
        data = response.json()

        assert "code" in data
        assert "msg" in data
        assert "data" in data

    def test_404_response_structure(self):
        """测试404响应结构"""
        client = TestClient(app)
        response = client.get("/api/v1/qa/history/99999")
        assert response.status_code == 404
        data = response.json()

        assert "code" in data
        assert "msg" in data
        assert "error_type" in data
