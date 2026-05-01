"""策略基类"""
from __future__ import annotations

from abc import ABC
from typing import List, Dict, Any

from tax_compliance_radar.models.schemas import (
    SourcedRiskItem,
    SourcedSuggestion,
    SourcedRegulation,
    SourceInfo,
)
from tax_compliance_radar.registry import CountryRegistry
from tax_compliance_radar.services.country_rules_engine import CountryRulesEngine
from tax_compliance_radar.services.suggestion_generator import generate_enhanced_suggestions


class BaseAuditStrategy(ABC):
    """单国家审核策略基类

    规则评估从 YAML 配置文件加载，无需在代码中硬编码。
    新增国家只需：
    1. 在 registry/countries/ 添加配置
    2. 在 data/rules/ 添加规则配置文件
    3. 创建策略类继承此类即可
    """

    def __init__(self, country_code: str):
        self.country_code = country_code
        self.config = CountryRegistry.get(country_code)
        self.country_name = self.config.country_name
        # 加载对应国家的规则引擎
        self.rules_engine = CountryRulesEngine.get_for_country(country_code)

    def _make_source_info(
        self,
        regulation_id: str | None = None,
        source_type: str = "rule",
    ) -> SourceInfo:
        """创建来源信息"""
        return SourceInfo(
            country_code=self.country_code,
            country_name=self.country_name,
            regulation_id=regulation_id,
            source_type=source_type,  # type: ignore[arg-type]
        )

    def evaluate_rules(self, business_profile: Dict[str, Any]) -> List[SourcedRiskItem]:
        """评估合规规则，返回带来源的风险列表

        规则从 data/rules/{country_code}_rules.yaml 加载
        """
        return self.rules_engine.evaluate(
            business_profile,
            self._make_source_info,
            self.config,
        )

    def generate_suggestions(
        self, risks: List[SourcedRiskItem], business_profile: Dict[str, Any]
    ) -> List[SourcedSuggestion]:
        """生成带来源的合规建议

        建议来源:
        1. YAML 配置文件中的通用建议
        2. LLM + RAG 基于风险点生成的专业增强建议
        """
        # 1. 基础建议来自配置文件
        yaml_suggestions = self.rules_engine.get_suggestions(self._make_source_info)

        # 2. LLM 增强建议（基于风险点和法规检索）
        llm_suggestions = generate_enhanced_suggestions(
            country_code=self.country_code,
            risks=risks,
            business_data=business_profile,
        )

        # 合并并去重（简单去重：基于内容前50字符）
        seen = set()
        all_suggestions = []

        # 优先添加 YAML 配置的建议
        for s in yaml_suggestions:
            key = s.content[:50]
            if key not in seen:
                seen.add(key)
                all_suggestions.append(s)

        # 然后添加 LLM 建议
        for s in llm_suggestions:
            key = s.content[:50]
            if key not in seen:
                seen.add(key)
                all_suggestions.append(s)

        return all_suggestions

    def get_qa_prompt_template(self) -> str:
        """获取QA系统提示词模板

        子类可覆盖此方法
        """
        return f"""
你是专业的{self.country_name}税务合规助手。
请基于检索到的法规内容回答用户问题。
""".strip()

    def get_audit_prompt_template(self) -> str:
        """获取审核系统提示词模板

        子类可覆盖此方法
        """
        return f"""
你是专业的{self.country_name}税务合规审核官。
请基于提供的业务信息和风险点生成审核建议。
""".strip()

    def format_currency(self, amount: int) -> str:
        """格式化货币显示"""
        return f"{amount:,} {self.config.currency_symbol}"
