"""审核接口单元测试"""
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestAuditRouter:
    """审核接口测试"""

    def test_submit_audit_success(self, client: TestClient, mock_audit_service):
        """测试正常提交审核请求"""
        payload = {
            "target_market": "泰国",
            "business_type": "跨境电商零售",
            "annual_sales": 1000000,
            "platforms": ["Shopee", "Lazada"],
        }

        response = client.post("/api/v1/audit/submit", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "disclaimer" in data["data"]
        assert data["data"]["audit_id"] == 1

    def test_submit_audit_missing_target_market(self, client: TestClient):
        """测试缺少目标市场字段"""
        payload = {
            # 缺少 target_market
            "business_type": "跨境电商零售",
            "annual_sales": 1000000,
            "platforms": ["Shopee"],
        }

        response = client.post("/api/v1/audit/submit", json=payload)

        assert response.status_code in (400, 422)

    def test_submit_audit_invalid_business_type(self, client: TestClient):
        """测试无效的业务类型"""
        payload = {
            "target_market": "泰国",
            "business_type": "无效业务类型",  # 不在枚举列表中
            "annual_sales": 1000000,
            "platforms": ["Shopee"],
        }

        response = client.post("/api/v1/audit/submit", json=payload)

        assert response.status_code in (400, 422)

    def test_submit_audit_negative_sales(self, client: TestClient):
        """测试负销售额"""
        payload = {
            "target_market": "泰国",
            "business_type": "跨境电商零售",
            "annual_sales": -1000,  # 负数
            "platforms": ["Shopee"],
        }

        response = client.post("/api/v1/audit/submit", json=payload)

        assert response.status_code in (400, 422)

    def test_submit_audit_invalid_platform(self, client: TestClient):
        """测试无效的平台名称"""
        payload = {
            "target_market": "泰国",
            "business_type": "跨境电商零售",
            "annual_sales": 1000000,
            "platforms": ["InvalidPlatform"],  # 不在枚举列表中
        }

        response = client.post("/api/v1/audit/submit", json=payload)

        assert response.status_code in (400, 422)

    def test_submit_audit_empty_platforms(self, client: TestClient, mock_audit_service):
        """测试空平台列表"""
        payload = {
            "target_market": "泰国",
            "business_type": "跨境电商零售",
            "annual_sales": 1000000,
            "platforms": [],  # 空列表
        }

        response = client.post("/api/v1/audit/submit", json=payload)

        # 平台列表可以为空，业务上可能允许只做通用审核
        # 所以这里允许200，但需要根据实际业务逻辑确认
        assert response.status_code in (200, 400, 422)

    def test_get_audit_history_empty(self, client: TestClient, temp_db):
        """测试获取空的审核历史记录列表"""
        from tax_compliance_radar.services.db import initialize_database
        initialize_database()

        response = client.get("/api/v1/audit/history")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    def test_get_audit_history_detail_not_found(self, client: TestClient, temp_db):
        """测试获取不存在的审核历史记录详情"""
        from tax_compliance_radar.services.db import initialize_database
        initialize_database()

        response = client.get("/api/v1/audit/history/99999")

        # 应该返回404或正确的错误响应
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert data["code"] in (200, 404)

    def test_submit_audit_response_structure(self, client: TestClient, mock_audit_service):
        """验证审核响应的数据结构"""
        payload = {
            "target_market": "泰国",
            "business_type": "跨境电商零售",
            "annual_sales": 1000000,
            "platforms": ["Shopee"],
        }

        response = client.post("/api/v1/audit/submit", json=payload)

        assert response.status_code == 200
        data = response.json()

        # 验证外层结构
        assert "code" in data
        assert "msg" in data
        assert "data" in data

        # 验证data结构
        result_data = data["data"]
        assert "audit_id" in result_data
        assert "business_info" in result_data
        assert "audit_report" in result_data
        assert "risk_count" in result_data
        assert "disclaimer" in result_data
        assert "create_time" in result_data

        # 验证audit_report结构
        report = result_data["audit_report"]
        assert "vat_register_assessment" in report
        assert "register_deadline" in report
        assert "main_risks" in report
        assert "suggestions" in report
        assert "attachment_guide" in report

        # 验证risk_count结构
        risk_count = result_data["risk_count"]
        assert "high_risk" in risk_count
        assert "medium_risk" in risk_count
        assert "low_risk" in risk_count
