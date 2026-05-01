"""单元测试 - 规则引擎"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tax_compliance_radar.models.schemas import AuditRequest, RiskItem
from tax_compliance_radar.services.rules_engine import RulesEngine


def test_rules_engine_loads_default_rules():
    """测试规则引擎默认加载5条规则"""
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "test_rules.json"
        engine = RulesEngine(rules_path=rules_path)
        assert len(engine.rules) == 5
        rule_ids = [r.rule_id for r in engine.rules]
        assert "R001" in rule_ids
        assert "R002" in rule_ids
        assert "R003" in rule_ids
        assert "R004" in rule_ids
        assert "R005" in rule_ids


def test_rule_R001_cross_border_triggers():
    """测试R001 - 跨境电商零售触发高风险"""
    business = AuditRequest(
        target_market="泰国",
        business_type="跨境电商零售",
        annual_sales=1000000,
        platforms=[],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "test_rules.json"
        engine = RulesEngine(rules_path=rules_path)
        risks, count = engine.evaluate(business)
        assert count.high_risk >= 1
        risk_descs = [r.risk_desc for r in risks]
        assert any("跨境电商业务无注册门槛" in d for d in risk_descs)


def test_rule_R001_brand_overseas_triggers():
    """测试R001 - 品牌出海直营触发高风险"""
    business = AuditRequest(
        target_market="泰国",
        business_type="品牌出海直营",
        annual_sales=1000000,
        platforms=[],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "test_rules.json"
        engine = RulesEngine(rules_path=rules_path)
        risks, count = engine.evaluate(business)
        assert count.high_risk >= 1


def test_rule_R002_platform_triggers():
    """测试R002 - 入驻平台触发中风险"""
    business = AuditRequest(
        target_market="泰国",
        business_type="跨境电商零售",
        annual_sales=1000000,
        platforms=["Shopee"],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "test_rules.json"
        engine = RulesEngine(rules_path=rules_path)
        risks, count = engine.evaluate(business)
        assert count.medium_risk >= 1


def test_rule_R003_applies_to_all():
    """测试R003 - 2026新政适用于所有企业"""
    business = AuditRequest(
        target_market="泰国",
        business_type="跨境电商零售",
        annual_sales=100000,
        platforms=[],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "test_rules.json"
        engine = RulesEngine(rules_path=rules_path)
        risks, count = engine.evaluate(business)
        risk_descs = [r.risk_desc for r in risks]
        assert any("取消1500泰铢低值商品免税" in d for d in risk_descs)


def test_rule_R004_high_sales_threshold():
    """测试R004 - 年销售180万泰铢阈值"""
    business_below = AuditRequest(
        target_market="泰国",
        business_type="跨境电商零售",
        annual_sales=1799999,
        platforms=[],
    )
    business_above = AuditRequest(
        target_market="泰国",
        business_type="跨境电商零售",
        annual_sales=1800000,
        platforms=[],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "test_rules.json"
        engine = RulesEngine(rules_path=rules_path)

        risks_below, _ = engine.evaluate(business_below)
        risks_above, _ = engine.evaluate(business_above)

        def has_R004(risks):
            return any("年销售额超过180万" in r.risk_desc for r in risks)

        assert not has_R004(risks_below)
        assert has_R004(risks_above)


def test_rule_R005_foreign_trade_service():
    """测试R005 - 外贸综合服务企业"""
    business = AuditRequest(
        target_market="泰国",
        business_type="外贸综合服务",
        annual_sales=1000000,
        platforms=[],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "test_rules.json"
        engine = RulesEngine(rules_path=rules_path)
        risks, count = engine.evaluate(business)
        assert count.high_risk >= 1


def test_comprehensive_audit_scenario():
    """测试完整审核场景 - 跨境电商零售+500万销售额+Shopee平台"""
    business = AuditRequest(
        target_market="泰国",
        business_type="跨境电商零售",
        annual_sales=5000000,
        platforms=["Shopee", "Lazada"],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "test_rules.json"
        engine = RulesEngine(rules_path=rules_path)
        risks, count = engine.evaluate(business)

        # R001(高) + R002(中) + R003(中) + R004(高) = 高:2, 中:2
        assert count.high_risk >= 2
        assert count.medium_risk >= 2
        assert len(risks) >= 4


def test_custom_rules_file():
    """测试自定义规则文件"""
    custom_rules = {
        "version": "1.0",
        "rules": [
            {
                "rule_id": "T001",
                "description": "测试规则",
                "category": "test",
                "condition": "business.annual_sales > 0",
                "risk_template": {
                    "risk_level": "低风险",
                    "risk_desc": "测试风险描述",
                    "trigger_condition": "测试触发条件",
                    "regulation_base": "测试法规",
                    "violation_consequence": "测试后果",
                },
            }
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "custom_rules.json"
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(custom_rules, f)

        engine = RulesEngine(rules_path=rules_path)
        assert len(engine.rules) == 1
        assert engine.rules[0].rule_id == "T001"

        business = AuditRequest(
            target_market="泰国",
            business_type="跨境电商零售",
            annual_sales=100,
            platforms=[],
        )
        risks, count = engine.evaluate(business)
        assert count.low_risk == 1
