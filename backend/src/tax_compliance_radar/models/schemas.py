from __future__ import annotations

from datetime import datetime
from typing import Literal, List, Dict

from pydantic import BaseModel, Field


# ==================== 来源标签系统 ====================
class SourceInfo(BaseModel):
    """来源信息：每个结果都必须标注来源"""
    country_code: str  # "TH", "VN", "MY"
    country_name: str  # "泰国", "越南"
    regulation_id: str | None = None  # 具体法规ID
    source_type: Literal["regulation", "rule", "ai_generated"] = "regulation"


class SourcedContent(BaseModel):
    """带来源的内容基类"""
    source_info: SourceInfo
    content: str


# ==================== 带来源的业务模型 ====================
class SourcedRiskItem(BaseModel):
    """带来源的风险项"""
    source_info: SourceInfo  # 强制包含国家来源
    risk_level: Literal["高风险", "中风险", "低风险"]
    risk_desc: str
    trigger_condition: str
    regulation_base: str
    violation_consequence: str


class SourcedSuggestion(BaseModel):
    """带来源的建议"""
    source_info: SourceInfo  # 强制包含国家来源
    suggestion_type: Literal["professional", "general"]
    content: str


class SourcedRegulation(BaseModel):
    """带来源的法规引用"""
    source_info: SourceInfo  # 强制包含国家来源
    content: str
    similarity_score: float


# ==================== 审核相关模型 ====================
class CountryAuditResult(BaseModel):
    """单个国家的审核结果"""
    country_code: str
    country_name: str
    vat_register_assessment: str
    register_deadline: str
    risks: List[SourcedRiskItem]  # 每个风险都有来源
    suggestions: List[SourcedSuggestion]  # 每个建议都有来源


class MultiCountryAuditReport(BaseModel):
    """多国组合审核报告"""
    overall_summary: str
    results_by_country: Dict[str, CountryAuditResult]  # 按国家分组
    all_risks: List[SourcedRiskItem]  # 所有风险混合但保留来源
    all_suggestions: List[SourcedSuggestion]  # 所有建议混合但保留来源


class BusinessProfile(BaseModel):
    """跨国家通用的业务信息"""
    business_type: str
    annual_sales_by_country: Dict[str, int]  # 按国家区分销售额
    platforms_by_country: Dict[str, List[str]]  # 按国家区分平台


class MultiCountryAuditRequest(BaseModel):
    """多国组合审核请求"""
    selected_countries: List[str]  # ["TH", "VN", "MY"]
    business_profile: BusinessProfile


# ==================== QA相关模型 ====================
class MultiCountryQAAnswer(BaseModel):
    """多国QA回答"""
    query_text: str
    selected_countries: List[str]
    regulations_by_country: Dict[str, List[SourcedRegulation]]  # 按国家分组法规
    core_rules: List[SourcedContent]  # 每条规则标注来源国家
    compliance_suggestion: List[SourcedContent]  # 每条建议标注来源
    risk_warning: List[SourcedContent]  # 每个风险标注来源
    operation_guide: List[SourcedContent]


class MultiCountryQARequest(BaseModel):
    """多国QA请求"""
    query_text: str = Field(..., min_length=1, max_length=500)
    selected_countries: List[str]


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
