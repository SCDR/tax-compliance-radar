from __future__ import annotations

from datetime import datetime
from typing import Literal, List, Dict

from pydantic import BaseModel, Field, field_validator, model_validator


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
    disclaimer: str  # 免责声明


class BusinessProfile(BaseModel):
    """跨国家通用的业务信息

    🌟 完全动态设计：
    - 所有业务字段从 YAML 配置自动加载
    - 新增字段只需修改 countries.yaml，无需修改代码
    - 自动根据配置进行类型校验和范围校验
    """
    business_type: str = Field(description="业务类型")

    # 动态字段通过 model_extra 接收，然后在根验证器中统一处理
    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_dynamic_fields(self) -> "BusinessProfile":
        """根据 YAML 配置动态验证所有业务字段"""
        from tax_compliance_radar.registry import CountryRegistry

        # 获取所有国家配置中的字段元数据（用于友好错误提示）
        field_meta = {}
        all_configs = CountryRegistry.get_all_configs()
        for config in all_configs.values():
            for field in config.business_fields:
                if field.name not in field_meta:
                    field_meta[field.name] = {
                        "label": field.label,
                        "type": field.type,
                        "required": field.required,
                        "options": field.options,
                    }

        all_field_names = list(field_meta.keys())
        expected_suffix = "_by_country"
        errors = []

        for field_name in list(self.model_dump().keys()):
            if field_name.endswith(expected_suffix) and field_name != "business_type":
                field_base_name = field_name[: -len(expected_suffix)]
                field_value = self.model_dump()[field_name]

                if field_base_name in all_field_names:
                    # 根据字段类型做基础校验
                    meta = field_meta[field_base_name]
                    friendly_name = meta["label"]

                    # number 类型校验
                    if meta["type"] == "number" and isinstance(field_value, dict):
                        for country_code, value in field_value.items():
                            if value is not None:
                                if not isinstance(value, (int, float)):
                                    errors.append(
                                        f"{friendly_name} ({country_code}) 应为有效数字"
                                    )
                                elif isinstance(value, int) and abs(value) > 9007199254740991:
                                    errors.append(
                                        f"{friendly_name} ({country_code}) 数值过大，可能导致精度丢失，请减小数值"
                                    )

        if errors:
            raise ValueError("; ".join(errors))

        return self


class MultiCountryAuditRequest(BaseModel):
    """多国组合审核请求"""
    selected_countries: List[str]  # ["TH", "VN", "MY"]
    business_profile: BusinessProfile
    think_mode: bool = Field(False, description="思考模式：开启后会进行更深入的分析")

    @field_validator("selected_countries")
    @classmethod
    def validate_selected_countries(cls, v: List[str]) -> List[str]:
        """验证至少选择一个国家"""
        from tax_compliance_radar.registry import CountryRegistry

        if not v or len(v) == 0:
            raise ValueError("至少需要选择一个国家进行审核")

        # 验证国家代码是否有效
        supported_codes = CountryRegistry.get_all_configs().keys()
        invalid_codes = [code for code in v if code not in supported_codes]
        if invalid_codes:
            raise ValueError(f"不支持的国家代码: {', '.join(invalid_codes)}。支持的国家: {', '.join(supported_codes)}")

        return v


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
    think_mode: bool = Field(False, description="思考模式：开启后会进行更深入的分析")


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
    annual_sales: int = Field(..., ge=0, le=1000000000000)  # 上限1万亿泰铢
    platforms: list[Literal["Shopee", "Lazada", "TikTok Shop"]] = Field(default_factory=list, max_length=10)


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
