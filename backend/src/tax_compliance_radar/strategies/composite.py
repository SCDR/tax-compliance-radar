"""多国组合策略 - Composite Pattern + 混合风险识别（规则引擎 + AI增强）
支持:
- 规则引擎同步执行（快速）
- AI风险检测异步并行执行（优化多国场景等待时间）
- 结果缓存机制
- 配置驱动的默认值管理（自动消除 None 歧义）
"""
from __future__ import annotations

import asyncio
from typing import List, Dict, Any

from tax_compliance_radar.models.schemas import (
    MultiCountryAuditReport,
    CountryAuditResult,
    SourcedRiskItem,
    SourcedSuggestion,
    BusinessProfile,
)
from tax_compliance_radar.strategies.base import BaseAuditStrategy
from tax_compliance_radar.services.ai_risk_detector import (
    detect_additional_risks_for_country,
    parallel_detect_risks_for_countries,
)
from tax_compliance_radar.services.suggestion_generator import generate_enhanced_suggestions_async
from tax_compliance_radar.field_config import get_field_default


class MultiCountryAuditStrategy:
    """多国组合审核策略 - 混合模式：规则引擎 + AI 增强

    审核流程（每个国家独立执行）：
    1. 🔧 **规则引擎** → 确定性风险（高/中风险），来自 YAML 配置
    2. 🤖 **AI增强检测** → 基于 RAG 的潜在边缘风险（低风险）
    3. ✨ **LLM增强建议** → 结合法规检索生成专业建议

    所有结果都保留原始来源标签（哪个国家/来源类型）
    """

    def __init__(self, strategies: List[BaseAuditStrategy]):
        self.strategies = strategies

    def evaluate(self, business_profile: BusinessProfile) -> MultiCountryAuditReport:
        """执行多国组合审核（同步版本）

        Args:
            business_profile: 统一的业务信息

        Returns:
            多国组合审核报告，所有结果都保留原始来源标签
        """
        # 同步版本使用事件循环运行异步方法
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aevaluate(business_profile))

    async def aevaluate(
        self,
        business_profile: BusinessProfile,
        use_cache: bool = True,
    ) -> MultiCountryAuditReport:
        """执行多国组合审核（异步并行版本，推荐）

        Args:
            business_profile: 统一的业务信息
            use_cache: 是否使用缓存

        Returns:
            多国组合审核报告，所有结果都保留原始来源标签
        """
        results_by_country: Dict[str, CountryAuditResult] = {}

        # ==================== 第一步：同步执行所有规则引擎（快速） ====================
        country_business_map: Dict[str, Dict[str, Any]] = {}
        rule_risks_map: Dict[str, List[SourcedRiskItem]] = {}

        for strategy in self.strategies:
            country_code = strategy.country_code
            country_business = self._extract_country_business(
                business_profile, country_code
            )
            country_business_map[country_code] = country_business
            rule_risks_map[country_code] = strategy.evaluate_rules(country_business)

        # ==================== 第二步：异步并行执行AI风险检测 + LLM建议生成 ====================
        # 并行执行：AI风险检测
        ai_risks_task = parallel_detect_risks_for_countries(
            country_business_map, use_cache=use_cache
        )
        ai_risks_map = await ai_risks_task

        # ==================== 第三步：并行生成 LLM 建议 ====================
        llm_suggestion_tasks = []
        for strategy in self.strategies:
            country_code = strategy.country_code
            rule_risks = rule_risks_map[country_code]
            ai_risks = ai_risks_map.get(country_code, [])
            all_risks = rule_risks + ai_risks
            # 为每个国家创建建议生成任务
            task = generate_enhanced_suggestions_async(
                country_code, all_risks, country_business_map[country_code]
            )
            llm_suggestion_tasks.append((country_code, task))

        # 并行执行所有建议生成
        llm_suggestions_results = await asyncio.gather(
            *[task for _, task in llm_suggestion_tasks], return_exceptions=True
        )
        llm_suggestions_map = {}
        for (country_code, _), result in zip(llm_suggestion_tasks, llm_suggestions_results):
            if not isinstance(result, Exception):
                llm_suggestions_map[country_code] = result
            else:
                llm_suggestions_map[country_code] = []

        # ==================== 第四步：合并结果 ====================
        for strategy in self.strategies:
            country_code = strategy.country_code
            rule_risks = rule_risks_map[country_code]
            ai_risks = ai_risks_map.get(country_code, [])
            all_risks = rule_risks + ai_risks
            country_business = country_business_map[country_code]

            # 基础建议来自YAML，LLM建议并行生成后合并
            yaml_suggestions = strategy.rules_engine.get_suggestions(strategy._make_source_info)
            llm_suggestions = llm_suggestions_map.get(country_code, [])

            # 去重
            seen = set()
            all_suggestions = []
            for s in yaml_suggestions + llm_suggestions:
                key = s.content[:50]
                if key not in seen:
                    seen.add(key)
                    all_suggestions.append(s)

            # 生成单个国家的结果
            country_result = CountryAuditResult(
                country_code=country_code,
                country_name=strategy.country_name,
                vat_register_assessment=self._assess_registration(
                    all_risks, strategy.config.registration_threshold
                ),
                register_deadline=self._get_deadline(all_risks),
                risks=all_risks,
                suggestions=all_suggestions,
            )
            results_by_country[country_code] = country_result

        # 扁平化：所有风险/建议混合但保留来源
        all_risks = [
            risk for result in results_by_country.values() for risk in result.risks
        ]
        all_suggestions = [
            suggestion
            for result in results_by_country.values()
            for suggestion in result.suggestions
        ]

        return MultiCountryAuditReport(
            overall_summary=self._generate_summary(results_by_country),
            results_by_country=results_by_country,
            all_risks=all_risks,
            all_suggestions=all_suggestions,
        )

    def _extract_country_business(
        self, business_profile: BusinessProfile, country_code: str
    ) -> Dict[str, Any]:
        """从全局业务信息中提取特定国家的业务信息

        🌟 自动扩展能力：
        1. 自动识别通用维度（非按国家区分）
        2. 自动识别 "xxx_by_country" 模式的多国维度
        3. 新增业务维度无需修改此函数
        4. 保留元数据：_field_set_flags 记录哪些字段被显式传递

        🤝 向后兼容保证：
        - 正常字段的值和行为完全不变
        - 无需区分的场景完全可以忽略元数据字段
        """
        result: Dict[str, Any] = {}
        # 🌟 元数据：记录每个字段是否被用户显式传递
        # 特殊字段，以下划线开头，不会与业务字段名冲突
        field_set_flags: Dict[str, bool] = {}

        # 反射遍历所有字段，自动提取所有业务维度
        # 使用 BusinessProfile.model_fields 而非实例访问（Pydantic V2 规范）
        for field_name, field_info in BusinessProfile.model_fields.items():
            # ============================================
            # 情况 A: 通用维度（没有 _by_country 后缀）
            # 如: business_type, company_size, industry 等
            # ============================================
            if not field_name.endswith("_by_country"):
                value = getattr(business_profile, field_name)
                result[field_name] = value
                # 通用维度：只要在模型中定义了就算已设置（通常都有默认值）
                field_set_flags[field_name] = value is not None
                continue

            # ============================================
            # 情况 B: 多国维度（有 _by_country 后缀）
            # 如: annual_sales_by_country, platforms_by_country 等
            # ============================================
            # 提取维度名："annual_sales_by_country" -> "annual_sales"
            dimension_name = field_name.replace("_by_country", "")

            # 获取该国家的具体值
            country_dict = getattr(business_profile, field_name)
            value = country_dict.get(country_code)

            # 🌟 先记录元数据：是否被显式传递
            field_set_flags[dimension_name] = value is not None

            # 🌟 再注入默认值（规则编写者永远不会看到 None）
            if value is None:
                value = get_field_default(dimension_name)

            result[dimension_name] = value

        # 把元数据放入结果（特殊命名，不会与业务字段冲突）
        result["_field_set_flags"] = field_set_flags

        return result

    def _assess_registration(
        self, risks: List[SourcedRiskItem], threshold: int
    ) -> str:
        """评估是否需要注册"""
        high_risk_count = sum(1 for r in risks if r.risk_level == "高风险")
        if high_risk_count > 0:
            return "必须注册"
        return "建议注册"

    def _get_deadline(self, risks: List[SourcedRiskItem]) -> str:
        """获取注册时限"""
        high_risk_count = sum(1 for r in risks if r.risk_level == "高风险")
        if high_risk_count > 0:
            return "开展业务前"
        return "建议30天内"

    def _generate_summary(self, results_by_country: Dict[str, CountryAuditResult]) -> str:
        """生成总体摘要"""
        country_count = len(results_by_country)
        total_high_risk = sum(
            1
            for result in results_by_country.values()
            for risk in result.risks
            if risk.risk_level == "高风险"
        )
        total_ai_risk = sum(
            1
            for result in results_by_country.values()
            for risk in result.risks
            if risk.source_info.source_type == "ai_generated"
        )
        countries_with_high_risk = [
            result.country_name
            for result in results_by_country.values()
            if any(r.risk_level == "高风险" for r in result.risks)
        ]

        if total_high_risk > 0:
            summary = f"在{country_count}个国家/地区共识别到{total_high_risk}个高风险事项。需要重点关注：{', '.join(countries_with_high_risk)}。"
            if total_ai_risk > 0:
                summary += f" AI额外识别到{total_ai_risk}个潜在边缘风险。"
            return summary

        if total_ai_risk > 0:
            return f"在{country_count}个国家/地区均未发现高风险事项，但AI额外识别到{total_ai_risk}个潜在边缘风险，建议关注。"

        return f"在{country_count}个国家/地区均未发现高风险事项，建议按当地法规要求正常开展业务。"
