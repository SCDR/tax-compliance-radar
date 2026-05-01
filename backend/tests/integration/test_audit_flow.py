"""集成测试 - 混合审核完整链路"""
from __future__ import annotations

import pytest

from tax_compliance_radar.models.schemas import AuditRequest
from tax_compliance_radar.services.audit_service import submit_audit


@pytest.mark.integration
@pytest.mark.requires_ollama
def test_audit_full_flow():
    """测试混合审核完整链路：规则引擎 -> AI增强检测 -> 报告生成"""
    business = AuditRequest(
        target_market="泰国",
        business_type="跨境电商零售",
        annual_sales=5000000,
        platforms=["Shopee", "Lazada"],
    )

    result = submit_audit(business)

    # 验证返回结构
    assert result.business_info == business
    assert result.audit_report is not None
    assert result.disclaimer is not None
    assert result.create_time is not None

    # 验证风险统计
    risk_count = result.risk_count
    assert risk_count.high_risk >= 2  # R001+R004 至少2个高风险
    assert risk_count.medium_risk >= 2  # R002+R003 至少2个中风险

    # 验证报告内容
    report = result.audit_report
    assert report.vat_register_assessment is not None
    assert report.register_deadline is not None
    assert len(report.main_risks) >= 4  # 规则引擎4个 + AI补充0个或以上
    assert len(report.suggestions) >= 3
    assert report.attachment_guide is not None

    # 打印实际结果便于人工验证
    print(f"\n=== 混合审核集成测试结果 ===")
    print(f"注册评估: {report.vat_register_assessment}")
    print(f"注册时限: {report.register_deadline}")
    print(f"风险总数: {len(report.main_risks)} (高:{risk_count.high_risk}, 中:{risk_count.medium_risk}, 低:{risk_count.low_risk})")
    print(f"\n风险清单:")
    for risk in report.main_risks:
        print(f"  [{risk.risk_level}] {risk.risk_desc[:40]}...")

    # 区分展示：专业建议 vs 通用建议
    print(f"\n【建议分类说明】")
    print(f"  注：当前向量库为空，仅返回通用建议（无编造法规引用）")
    print(f"\n所有建议:")
    for i, s in enumerate(report.suggestions, 1):
        print(f"  {i}. {s[:80]}...")
    print(f"\n附件指引: {report.attachment_guide[:60]}...")
