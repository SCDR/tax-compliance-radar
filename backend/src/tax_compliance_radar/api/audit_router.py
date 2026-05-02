import json

from fastapi import APIRouter, HTTPException

from tax_compliance_radar.models.schemas import ApiResponse, AuditData, AuditRequest, AuditReport, RiskCount
from tax_compliance_radar.services.audit_service import submit_audit
from tax_compliance_radar.services.db import get_connection

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.post("/submit", response_model=ApiResponse)
def submit_audit_form(payload: AuditRequest) -> ApiResponse:
    result = submit_audit(payload)
    return ApiResponse(data=result)


@router.get("/history", response_model=ApiResponse)
def list_history() -> ApiResponse:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT audit_id, business_info, high_risk_count, medium_risk_count,
                   low_risk_count, create_time
            FROM audit_history
            ORDER BY audit_id DESC
            """
        ).fetchall()

    data = []
    for row in rows:
        business_info = json.loads(row["business_info"])
        # 构建摘要标题，便于区分不同历史记录
        countries = business_info.get("selected_countries", [])
        countries_str = ", ".join(countries) if countries else "未指定国家"
        summary_title = f"{business_info.get('business_type', '未知业务')} - {countries_str}"

        data.append(
            {
                "audit_id": row["audit_id"],
                "business_type": business_info.get("business_type", ""),
                "summary_title": summary_title,
                "selected_countries": countries,
                "risk_count": {
                    "high_risk": row["high_risk_count"],
                    "medium_risk": row["medium_risk_count"],
                    "low_risk": row["low_risk_count"],
                },
                "create_time": row["create_time"],
            }
        )
    return ApiResponse(data=data)


@router.get("/history/{audit_id}", response_model=ApiResponse)
def get_history_detail(audit_id: int) -> ApiResponse:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_history WHERE audit_id = ?",
            (audit_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="审核记录不存在")
    business_info = json.loads(row["business_info"])
    audit_report = json.loads(row["audit_report"])
    # 简化返回，直接使用字典无需严格 schema 验证（兼容多国格式）
    data = {
        "audit_id": row["audit_id"],
        "business_info": business_info,
        "audit_report": audit_report,
        "risk_count": {
            "high_risk": row["high_risk_count"],
            "medium_risk": row["medium_risk_count"],
            "low_risk": row["low_risk_count"],
        },
        "disclaimer": "本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。",
        "create_time": row["create_time"],
    }
    return ApiResponse(data=data)
