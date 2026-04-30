from __future__ import annotations

from dataclasses import dataclass

from tax_compliance_radar.models.schemas import AuditRequest, RiskCount, RiskItem


@dataclass(frozen=True)
class ComplianceAssessment:
    vat_register_assessment: str
    register_deadline: str
    main_risks: list[RiskItem]
    suggestions: list[str]
    attachment_guide: str
    risk_count: RiskCount


KNOWN_PLATFORMS = {"Shopee", "Lazada", "TikTok Shop"}


def evaluate_audit(business: AuditRequest) -> ComplianceAssessment:
    risks: list[RiskItem] = []

    risks.append(
        RiskItem(
            risk_level="高风险",
            risk_desc="外国企业在泰国开展跨境电商业务无注册门槛，第一笔交易前应完成VAT注册。",
            trigger_condition="开展泰国跨境电商业务",
            regulation_base="泰国VAT注册规则与2026年新政要求",
            violation_consequence="未按时注册可能影响税务合规并产生罚款风险。",
        )
    )

    if business.platforms:
        risks.append(
            RiskItem(
                risk_level="中风险",
                risk_desc="平台代收代缴场景下，需提前准备税务资料并核验平台税费规则。",
                trigger_condition="入驻平台销售",
                regulation_base="泰国平台代收代缴要求",
                violation_consequence="资料缺失可能导致税费申报延误。",
            )
        )

    if business.annual_sales > 0:
        risks.append(
            RiskItem(
                risk_level="低风险",
                risk_desc="需持续关注2026年新政下进口关税与7% VAT的适用范围。",
                trigger_condition="存在跨境销售额",
                regulation_base="泰国2026年VAT新政",
                violation_consequence="税费测算偏差可能影响合规判断。",
            )
        )

    suggestions = [
        "1. 在开展业务前完成VAT注册准备。",
        "2. 核验平台代收代缴规则与业务主体信息一致性。",
        "3. 留存税务申报与平台订单数据，便于后续审核。",
    ]

    return ComplianceAssessment(
        vat_register_assessment="需注册（无门槛要求）",
        register_deadline="开展业务前",
        main_risks=risks,
        suggestions=suggestions,
        attachment_guide="泰国VAT注册材料清单、注册流程指引",
        risk_count=RiskCount(
            high_risk=sum(1 for item in risks if item.risk_level == "高风险"),
            medium_risk=sum(1 for item in risks if item.risk_level == "中风险"),
            low_risk=sum(1 for item in risks if item.risk_level == "低风险"),
        ),
    )
