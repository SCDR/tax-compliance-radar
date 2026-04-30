from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: object | None = None


class QAQueryRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=500)


class QAAnswer(BaseModel):
    regulation_base: str
    core_rules: str
    compliance_suggestion: str
    risk_warning: str
    operation_guide: str
    original_link: str


class QAQueryData(BaseModel):
    qa_id: int
    query_text: str
    answer_text: QAAnswer
    disclaimer: str
    create_time: str


class QAHistoryItem(BaseModel):
    qa_id: int
    query_text: str
    create_time: str


class AuditRequest(BaseModel):
    target_market: Literal["泰国"]
    business_type: Literal["跨境电商零售", "品牌出海直营", "外贸综合服务"]
    annual_sales: int = Field(..., ge=0)
    platforms: list[Literal["Shopee", "Lazada", "TikTok Shop"]] = Field(default_factory=list)


class RiskItem(BaseModel):
    risk_level: Literal["高风险", "中风险", "低风险"]
    risk_desc: str
    trigger_condition: str
    regulation_base: str
    violation_consequence: str


class AuditReport(BaseModel):
    vat_register_assessment: str
    register_deadline: str
    main_risks: list[RiskItem]
    suggestions: list[str]
    attachment_guide: str


class RiskCount(BaseModel):
    high_risk: int = 0
    medium_risk: int = 0
    low_risk: int = 0


class AuditData(BaseModel):
    audit_id: int
    business_info: AuditRequest
    audit_report: AuditReport
    risk_count: RiskCount
    disclaimer: str
    create_time: str


class AuditHistoryItem(BaseModel):
    audit_id: int
    business_type: str
    annual_sales: int
    risk_count: RiskCount
    create_time: str
