"""越南 VAT 策略 - 所有规则来自 YAML 配置

文件位置: data/rules/vn_rules.yaml

新增/修改规则请编辑 YAML 配置文件，无需修改代码。
"""
from __future__ import annotations

from tax_compliance_radar.strategies.base import BaseAuditStrategy


class VietnamVATStrategy(BaseAuditStrategy):
    """越南VAT审核策略"""

    def __init__(self):
        super().__init__("VN")


def get_strategy() -> VietnamVATStrategy:
    """获取越南VAT策略实例"""
    return VietnamVATStrategy()
