"""印度尼西亚 PPh/VAT 策略 - 所有规则来自 YAML 配置

文件位置: data/rules/id_rules.yaml
"""
from __future__ import annotations

from tax_compliance_radar.strategies.base import BaseAuditStrategy


class IndonesiaPPhStrategy(BaseAuditStrategy):
    """印度尼西亚 PPh/VAT 审核策略"""

    def __init__(self):
        super().__init__("ID")


def get_strategy() -> IndonesiaPPhStrategy:
    """获取印度尼西亚 PPh 策略实例"""
    return IndonesiaPPhStrategy()
