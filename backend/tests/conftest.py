from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tax_compliance_radar import testing_config
from tax_compliance_radar.main import app


def pytest_configure(config):
    """pytest配置钩子 - 在测试开始前配置日志"""
    import sys
    from tax_compliance_radar.services.logger import StructuredFormatter

    logger = logging.getLogger("tax_compliance_radar")

    # 移除现有处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 添加结构化JSON格式化器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # 阻止日志传播到pytest的根日志处理器


@pytest.fixture(autouse=True)
def setup_test_logging():
    """确保每个测试都有正确的日志配置"""
    # pytest_configure 已经完成了主要配置
    yield
from tax_compliance_radar.models.schemas import (
    AuditReport,
    AuditData,
    QAQueryData,
    QAAnswer,
    RiskCount,
)


@pytest.fixture()
def test_settings():
    return testing_config.TEST_SETTINGS


@pytest.fixture()
def client():
    """FastAPI测试客户端"""
    return TestClient(app)


@pytest.fixture()
def mock_qa_service():
    """Mock QA服务，避免Ollama外部依赖"""
    with patch(
        "tax_compliance_radar.api.qa_router.query_qa"
    ) as mock:
        mock_answer = QAAnswer(
            regulation_base="泰国增值税法第1条",
            core_rules="外国企业在泰开展业务需注册VAT",
            compliance_suggestion="建议立即办理注册",
            risk_warning="未注册可能面临罚款",
            operation_guide="登录税务局官网提交申请",
            original_link="https://www.rd.go.th",
        )
        mock_data = QAQueryData(
            qa_id=1,
            query_text="测试问题",
            answer_text=mock_answer,
            disclaimer="本工具仅供参考",
            create_time="2026-05-01 12:00:00",
        )
        mock.return_value = mock_data
        yield mock


@pytest.fixture()
def mock_audit_service():
    """Mock Audit服务，避免Ollama外部依赖"""
    with patch(
        "tax_compliance_radar.api.audit_router.submit_audit"
    ) as mock:
        from tax_compliance_radar.models.schemas import (
            RiskItem,
            SourcedRiskItem,
        )

        risk = RiskItem(
            risk_level="高风险",
            risk_desc="取消低值免税政策",
            trigger_condition="2026年1月1日起",
            regulation_base="泰国税务局公告",
            violation_consequence="罚款",
        )
        report = AuditReport(
            vat_register_assessment="需要注册",
            register_deadline="开展业务前",
            main_risks=[risk],
            suggestions=["立即注册"],
            attachment_guide="材料清单",
        )
        from tax_compliance_radar.models.schemas import AuditRequest

        audit_data = AuditData(
            audit_id=1,
            business_info=AuditRequest(
                target_market="泰国",
                business_type="跨境电商零售",
                annual_sales=1000000,
                platforms=["Shopee"],
            ),
            audit_report=report,
            risk_count=RiskCount(high_risk=1, medium_risk=0, low_risk=0),
            disclaimer="本工具仅供参考",
            create_time="2026-05-01 12:00:00",
        )
        mock.return_value = audit_data
        yield mock


@pytest.fixture()
def temp_db():
    """使用临时SQLite数据库，隔离测试数据"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    original_db_path = os.environ.get("DB_PATH", "")
    os.environ["DB_PATH"] = path
    yield path
    os.environ["DB_PATH"] = original_db_path
    if os.path.exists(path):
        os.unlink(path)
