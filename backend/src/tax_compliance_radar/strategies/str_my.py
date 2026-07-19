"""马来西亚 SST/VAT 策略 - 所有规则来自 YAML 配置

文件位置: data/rules/my_rules.yaml

新增/修改规则请编辑 YAML 配置文件，无需修改代码。
"""
from __future__ import annotations

from tax_compliance_radar.strategies.base import BaseAuditStrategy


class MalaysiaSSTStrategy(BaseAuditStrategy):
    """马来西亚 SST/VAT 审核策略"""

    def __init__(self):
        super().__init__("MY")


def get_strategy() -> MalaysiaSSTStrategy:
    """获取马来西亚 SST 策略实例"""
    return MalaysiaSSTStrategy()
