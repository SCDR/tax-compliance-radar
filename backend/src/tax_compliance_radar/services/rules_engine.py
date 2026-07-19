"""可配置规则库框架 - 支持动态加载和扩展合规规则"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tax_compliance_radar.config import DATA_DIR, settings
from tax_compliance_radar.models.schemas import AuditRequest, RiskItem, RiskCount
from tax_compliance_radar.services.safe_eval import SafeRuleEvaluator

RULES_DB_PATH = DATA_DIR / "compliance_rules.json"


@dataclass(frozen=True)
class ComplianceRule:
    rule_id: str
    description: str
    category: str
    risk_template: RiskItem
    condition_expr: str

    def evaluate(self, business: AuditRequest) -> RiskItem | None:
        """安全地执行条件判断"""
        try:
            # 使用安全的规则评估器
            evaluator = SafeRuleEvaluator(names={"business": business})
            result = evaluator.eval(self.condition_expr)
            if result:
                return RiskItem(
                    risk_level=self.risk_template.risk_level,
                    risk_desc=self.risk_template.risk_desc,
                    trigger_condition=self._format_trigger(business),
                    regulation_base=self.risk_template.regulation_base,
                    violation_consequence=self.risk_template.violation_consequence,
                )
        except Exception:
            return None
        return None

    def _format_trigger(self, business: AuditRequest) -> str:
        """根据业务数据动态生成触发条件描述"""
        expr = self.condition_expr
        if "annual_sales" in expr and str(settings.rules.vat_registration_threshold) in expr:
            return f"年预估销售额 {business.annual_sales:,} 泰铢达到申报阈值"
        if "platforms" in expr:
            return f"入驻以下平台销售: {', '.join(business.platforms)}"
        return self.risk_template.trigger_condition


class RulesEngine:
    def __init__(self, rules_path: Path | None = None):
        self.rules: list[ComplianceRule] = []
        self._load_rules(rules_path or RULES_DB_PATH)

    def _load_rules(self, path: Path) -> None:
        """从JSON文件加载规则"""
        if not path.exists():
            self._create_default_rules(path)
            return

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for rule_data in data["rules"]:
            self.rules.append(
                ComplianceRule(
                    rule_id=rule_data["rule_id"],
                    description=rule_data["description"],
                    category=rule_data["category"],
                    condition_expr=rule_data["condition"],
                    risk_template=RiskItem(**rule_data["risk_template"]),
                )
            )

    def _create_default_rules(self, path: Path) -> None:
        """创建默认规则库"""
        default_rules = {
            "version": "1.0",
            "rules": [
                {
                    "rule_id": "R001",
                    "description": "外国企业跨境电商VAT注册义务",
                    "category": "registration",
                    "condition": "business.business_type in ['跨境电商零售', '品牌出海直营']",
                    "risk_template": {
                        "risk_level": "高风险",
                        "risk_desc": "外国企业在泰国开展跨境电商业务无注册门槛，第一笔交易前应完成VAT注册",
                        "trigger_condition": "开展泰国跨境电商业务，无论销售额多少",
                        "regulation_base": "泰国VAT注册规则与2026年新政要求",
                        "violation_consequence": "未按时注册可能面临罚款、货物被扣、平台账户受限等风险",
                    },
                },
                {
                    "rule_id": "R002",
                    "description": "平台代收代缴场景税务要求",
                    "category": "platform",
                    "condition": "len(business.platforms) > 0",
                    "risk_template": {
                        "risk_level": "中风险",
                        "risk_desc": "平台代收代缴场景下，商家仍需承担申报义务并留存完整交易数据",
                        "trigger_condition": "",
                        "regulation_base": "泰国平台代收代缴管理办法",
                        "violation_consequence": "资料缺失可能导致税费申报延误或补缴滞纳金",
                    },
                },
                {
                    "rule_id": "R003",
                    "description": "2026年取消低值商品免税政策",
                    "category": "reporting",
                    "condition": "True",
                    "risk_template": {
                        "risk_level": "中风险",
                        "risk_desc": "2026年1月起取消1500泰铢低值商品免税政策，所有跨境商品均需缴纳7% VAT",
                        "trigger_condition": "跨境销售商品至泰国，无论订单金额大小",
                        "regulation_base": "泰国2026年VAT新政第3/2025号公告",
                        "violation_consequence": "低估税费可能导致货物清关延误或产生额外罚款",
                    },
                },
                {
                    "rule_id": "R004",
                    "description": "大额销售企业合规要求",
                    "category": "reporting",
                    "condition": "business.annual_sales >= 1800000",
                    "risk_template": {
                        "risk_level": "高风险",
                        "risk_desc": "年销售额超过180万泰铢的企业需进行月度申报并接受年度审计",
                        "trigger_condition": "",
                        "regulation_base": "泰国增值税法第82/1条",
                        "violation_consequence": "未按要求申报可能产生高额罚款并影响企业信用",
                    },
                },
                {
                    "rule_id": "R005",
                    "description": "外贸综合服务企业合规要求",
                    "category": "registration",
                    "condition": "business.business_type == '外贸综合服务'",
                    "risk_template": {
                        "risk_level": "高风险",
                        "risk_desc": "外贸综合服务企业需为客户代扣代缴VAT并承担连带责任",
                        "trigger_condition": "从事外贸综合服务并代收客户款项",
                        "regulation_base": "泰国税务厅关于第三方服务机构的管理规定",
                        "violation_consequence": "代扣代缴违规可能导致企业承担连带法律责任",
                    },
                },
            ],
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_rules, f, ensure_ascii=False, indent=2)

        self._load_rules(path)

    def evaluate(self, business: AuditRequest) -> tuple[list[RiskItem], RiskCount]:
        """执行所有规则评估"""
        triggered_risks: list[RiskItem] = []

        for rule in self.rules:
            result = rule.evaluate(business)
            if result:
                triggered_risks.append(result)

        risk_count = RiskCount(
            high_risk=sum(1 for r in triggered_risks if r.risk_level == "高风险"),
            medium_risk=sum(1 for r in triggered_risks if r.risk_level == "中风险"),
            low_risk=sum(1 for r in triggered_risks if r.risk_level == "低风险"),
        )

        return triggered_risks, risk_count


_rules_engine: RulesEngine | None = None


def get_rules_engine() -> RulesEngine:
    global _rules_engine
    if _rules_engine is None:
        _rules_engine = RulesEngine()
    return _rules_engine
