from __future__ import annotations

from datetime import datetime, timezone

from tax_compliance_radar.models.schemas import AuditData, AuditRequest, AuditReport, RiskCount
from tax_compliance_radar.config import settings
from tax_compliance_radar.services.rules_engine import get_rules_engine
from tax_compliance_radar.services.ai_risk_detector import detect_additional_risks
from tax_compliance_radar.services.retrieval_service import search_regulations
from tax_compliance_radar.services.db import get_connection
from tax_compliance_radar.services.disclaimer import get_disclaimer
from tax_compliance_radar.services.llm_service import generate_audit_enhancement


def submit_audit(business: AuditRequest, enable_ai_detection: bool | None = None) -> AuditData:
    """
    混合审核流程：
    1. 可配置规则引擎 → 确定性风险（高/中风险）
    2. RAG检索相关法规 → 为建议生成提供依据
    3. AI增强检测（可选） → 潜在边缘风险（低风险，基于RAG）
    4. RAG增强建议生成 → 专业建议（带来源）+ 通用建议

    Args:
        business: 业务信息
        enable_ai_detection: 是否启用AI风险检测（较慢，默认False）
    """
    rules_engine = get_rules_engine()
    rule_risks, risk_count = rules_engine.evaluate(business)

    # RAG检索：获取与业务场景相关的法规（1次检索，后续复用）
    query = f"泰国 VAT {business.business_type} {business.annual_sales} 跨境电商 合规要求"
    retrieval_result = search_regulations(query, top_k=2)  # 减少召回数量，提升速度

    # AI增强检测（可选）：可配置是否启用，降低延迟
    use_ai_detection = enable_ai_detection if enable_ai_detection is not None else settings.performance.enable_ai_risk_detection
    if use_ai_detection:
        ai_risks = detect_additional_risks(business, retrieval_result)  # 共享检索结果
    else:
        ai_risks = []
    all_risks = rule_risks + ai_risks

    updated_risk_count = RiskCount(
        high_risk=risk_count.high_risk,
        medium_risk=risk_count.medium_risk,
        low_risk=risk_count.low_risk + len(ai_risks),
    )

    # RAG增强生成建议：专业建议带来源，通用建议来自最佳实践
    enhanced = generate_audit_enhancement(business, all_risks, retrieval_result)

    has_high_risk = any(r.risk_level == "高风险" for r in all_risks)

    report = AuditReport(
        vat_register_assessment="必须注册" if has_high_risk else "建议注册",
        register_deadline="开展业务前" if has_high_risk else "建议30天内",
        main_risks=all_risks,
        suggestions=enhanced.get("suggestions", []),
        attachment_guide=enhanced.get("attachment_guide", ""),
    )

    create_time = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO audit_history (
                business_info, audit_report,
                high_risk_count, medium_risk_count, low_risk_count, create_time
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                business.model_dump_json(),
                report.model_dump_json(),
                updated_risk_count.high_risk,
                updated_risk_count.medium_risk,
                updated_risk_count.low_risk,
                create_time,
            ),
        )
        connection.commit()
        audit_id = int(cursor.lastrowid)

    return AuditData(
        audit_id=audit_id,
        business_info=business,
        audit_report=report,
        risk_count=updated_risk_count,
        disclaimer=get_disclaimer(),
        create_time=create_time,
    )
