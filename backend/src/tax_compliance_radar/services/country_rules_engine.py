"""按国家配置的规则引擎 - 支持从 YAML 加载规则"""
from __future__ import annotations

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from tax_compliance_radar.config import DATA_DIR
from tax_compliance_radar.models.schemas import SourcedRiskItem, SourcedSuggestion, SourceInfo


# 规则配置文件目录
RULES_DIR = DATA_DIR / "rules"


@dataclass(frozen=True)
class ComplianceRule:
    """合规规则"""
    rule_id: str
    description: str
    category: str
    condition: str
    risk_template: Dict[str, Any]

    def evaluate(
        self,
        business_data: Dict[str, Any],
        source_info: SourceInfo,
        config: Any,
    ) -> SourcedRiskItem | None:
        """评估规则是否触发

        Args:
            business_data: 业务数据（包含 business_type, annual_sales, platforms 等）
            source_info: 来源信息
            config: 国家配置（用于获取 registration_threshold 等）

        Returns:
            触发的风险项，如未触发则返回 None
        """
        try:
            # 准备 eval 环境变量 - 自动注入所有业务数据字段（支持扩展）
            eval_globals = {
                "registration_threshold": config.registration_threshold,
            }

            # 自动注入所有业务数据字段 - 无需硬编码，支持新维度自动扩展
            for key, value in business_data.items():
                eval_globals[key] = value

            # 执行条件判断
            result = eval(self.condition, eval_globals)

            if result:
                platforms_str = ", ".join(business_data.get("platforms", []))

                # 格式化风险描述
                risk_desc = self.risk_template["risk_desc"]
                if "{registration_threshold" in risk_desc:
                    risk_desc = risk_desc.format(
                        registration_threshold=config.registration_threshold
                    )

                # 格式化触发条件
                trigger_condition = self.risk_template["trigger_condition"]
                if "{}" in trigger_condition:
                    trigger_condition = trigger_condition.format(platforms_str)

                return SourcedRiskItem(
                    source_info=source_info,
                    risk_level=self.risk_template["risk_level"],
                    risk_desc=risk_desc,
                    trigger_condition=trigger_condition,
                    regulation_base=self.risk_template["regulation_base"],
                    violation_consequence=self.risk_template["violation_consequence"],
                )
        except Exception as e:
            print(f"Warning: Rule {self.rule_id} evaluation failed: {e}")
            return None

        return None


class CountryRulesEngine:
    """国家规则引擎 - 按国家加载和评估规则"""

    _cache: Dict[str, "CountryRulesEngine"] = {}  # 国家代码 -> 规则引擎实例

    def __init__(self, country_code: str):
        self.country_code = country_code
        self.rules: List[ComplianceRule] = []
        self.suggestions: List[SourcedSuggestion] = []
        self._loaded = False

    @classmethod
    def get_for_country(cls, country_code: str) -> "CountryRulesEngine":
        """获取指定国家的规则引擎实例（单例模式）"""
        if country_code not in cls._cache:
            engine = cls(country_code)
            engine.load_rules()
            cls._cache[country_code] = engine
        return cls._cache[country_code]

    def load_rules(self) -> None:
        """从 YAML 文件加载规则"""
        rules_file = RULES_DIR / f"{self.country_code.lower()}_rules.yaml"

        if not rules_file.exists():
            raise FileNotFoundError(f"Rules file not found for country {self.country_code}: {rules_file}")

        with open(rules_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 加载规则
        for rule_data in data.get("rules", []):
            self.rules.append(
                ComplianceRule(
                    rule_id=rule_data["rule_id"],
                    description=rule_data["description"],
                    category=rule_data["category"],
                    condition=rule_data["condition"],
                    risk_template=rule_data["risk_template"],
                )
            )

        # 加载建议（预先创建好 SourcedSuggestion 模板）
        # 注意：source_info 需要在 evaluate 时动态传入
        self._suggestion_templates = data.get("suggestions", [])
        self._loaded = True

    def evaluate(
        self,
        business_data: Dict[str, Any],
        source_info_factory: Any,  # 调用时传入 _make_source_info 方法
        config: Any,
    ) -> List[SourcedRiskItem]:
        """评估所有规则，返回触发的风险列表

        Args:
            business_data: 业务数据字典
            source_info_factory: 创建 SourceInfo 的工厂方法（通常是策略的 _make_source_info 方法）
            config: 国家配置

        Returns:
            触发的风险项列表（都带有来源标签）
        """
        if not self._loaded:
            self.load_rules()

        risks: List[SourcedRiskItem] = []
        for rule in self.rules:
            source_info = source_info_factory(rule.rule_id, "rule")
            risk = rule.evaluate(business_data, source_info, config)
            if risk:
                risks.append(risk)

        return risks

    def get_suggestions(
        self,
        source_info_factory: Any,
    ) -> List[SourcedSuggestion]:
        """获取建议列表

        Args:
            source_info_factory: 创建 SourceInfo 的工厂方法

        Returns:
            建议列表（都带有来源标签）
        """
        if not self._loaded:
            self.load_rules()

        suggestions: List[SourcedSuggestion] = []
        for idx, template in enumerate(self._suggestion_templates):
            source_info = source_info_factory(f"{self.country_code}_S{idx+1:03d}", "ai_generated")
            suggestions.append(
                SourcedSuggestion(
                    source_info=source_info,
                    suggestion_type=template["type"],
                    content=template["content"],
                )
            )

        return suggestions

    @classmethod
    def reload_all(cls) -> None:
        """重新加载所有规则（用于配置更新后）"""
        cls._cache.clear()

    @classmethod
    def list_available_countries(cls) -> List[str]:
        """列出所有有规则配置的国家"""
        countries = []
        if RULES_DIR.exists():
            for file in RULES_DIR.glob("*_rules.yaml"):
                country_code = file.stem.split("_")[0].upper()
                countries.append(country_code)
        return sorted(countries)
