from __future__ import annotations

from datetime import datetime, timezone

from tax_compliance_radar.models.schemas import AuditData, AuditRequest, AuditReport
from tax_compliance_radar.services.compliance_rules import evaluate_audit
from tax_compliance_radar.services.db import get_connection
from tax_compliance_radar.services.disclaimer import get_disclaimer
from tax_compliance_radar.services.llm_service import generate_audit_report


def submit_audit(business: AuditRequest) -> AuditData:
    assessment = evaluate_audit(business)
    report_payload = generate_audit_report(
        business,
        {
            "vat_register_assessment": assessment.vat_register_assessment,
            "register_deadline": assessment.register_deadline,
            "main_risks": [item.model_dump() for item in assessment.main_risks],
            "suggestions": assessment.suggestions,
            "attachment_guide": assessment.attachment_guide,
        },
    )

    report = AuditReport.model_validate(report_payload)

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
                assessment.risk_count.high_risk,
                assessment.risk_count.medium_risk,
                assessment.risk_count.low_risk,
                create_time,
            ),
        )
        connection.commit()
        audit_id = int(cursor.lastrowid)

    return AuditData(
        audit_id=audit_id,
        business_info=business,
        audit_report=report,
        risk_count=assessment.risk_count,
        disclaimer=get_disclaimer(),
        create_time=create_time,
    )
