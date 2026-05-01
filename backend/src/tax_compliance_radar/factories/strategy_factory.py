"""策略工厂 - Factory Pattern + Auto Discovery"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import List, Dict, Type

from tax_compliance_radar.registry import CountryRegistry
from tax_compliance_radar.strategies import __path__ as strategies_path
from tax_compliance_radar.strategies.base import BaseAuditStrategy
from tax_compliance_radar.strategies.composite import MultiCountryAuditStrategy


class StrategyFactory:
    """策略工厂 - 自动扫描注册策略

    自动扫描 strategies 目录下所有 str_*.py 策略文件，无需手动注册。
    新增国家只需创建 strategies/str_xx.py 文件即可自动发现。
    """

    _strategy_registry: Dict[str, Type[BaseAuditStrategy]] = {}
    _discovered: bool = False

    @classmethod
    def _ensure_discovered(cls) -> None:
        """确保所有策略已被自动扫描发现"""
        if cls._discovered:
            return

        # 扫描 strategies 目录下所有 str_ 开头的模块
        strategies_package_path = Path(strategies_path[0])
        for _, module_name, _ in pkgutil.iter_modules([str(strategies_package_path)]):
            if module_name.startswith("str_"):
                try:
                    module = importlib.import_module(
                        f"tax_compliance_radar.strategies.{module_name}"
                    )
                    if hasattr(module, "get_strategy"):
                        strategy = module.get_strategy()
                        country_code = strategy.country_code
                        cls._strategy_registry[country_code] = type(strategy)
                except Exception as e:
                    print(f"Warning: Failed to load strategy {module_name}: {e}")

        cls._discovered = True

    @classmethod
    def register_strategy(
        cls, country_code: str, strategy_class: Type[BaseAuditStrategy]
    ) -> None:
        """注册国家策略"""
        cls._strategy_registry[country_code] = strategy_class

    @classmethod
    def get_audit_strategy(cls, country_code: str) -> BaseAuditStrategy:
        """获取单个国家的审核策略

        Raises:
            ValueError: 如果国家代码不被支持或策略未找到
        """
        cls._ensure_discovered()

        if not CountryRegistry.is_supported(country_code):
            raise ValueError(f"Unsupported country: {country_code}")

        strategy_class = cls._strategy_registry.get(country_code)

        if strategy_class is None:
            raise ValueError(
                f"No strategy found for country: {country_code}. "
                f"Please implement strategy for this country first."
            )

        return strategy_class()

    @classmethod
    def get_multi_country_strategy(
        cls, country_codes: List[str]
    ) -> MultiCountryAuditStrategy:
        """获取多国组合审核策略

        Args:
            country_codes: 国家代码列表，例如 ["TH", "VN"]

        Returns:
            MultiCountryAuditStrategy 实例
        """
        strategies = [cls.get_audit_strategy(code) for code in country_codes]
        return MultiCountryAuditStrategy(strategies)

    @classmethod
    def get_supported_countries(cls) -> List[str]:
        """获取所有有策略实现的国家"""
        return list(cls._strategy_registry.keys())
