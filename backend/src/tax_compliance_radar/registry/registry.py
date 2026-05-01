"""国家配置注册中心 - Registry Pattern"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List

from tax_compliance_radar.registry.base import CountryConfig


class CountryRegistry:
    """国家配置注册中心

    用法:
        # 获取国家配置
        config = CountryRegistry.get("TH")

        # 列出所有支持的国家
        countries = CountryRegistry.list_all()

        # 检查国家是否支持
        if CountryRegistry.is_supported("TH"):
            ...
    """

    _configs: Dict[str, CountryConfig] = {}
    _loaded: bool = False

    @classmethod
    def _ensure_loaded(cls) -> None:
        """确保所有国家配置已加载"""
        if not cls._loaded:
            cls._load_all_countries()
            cls._loaded = True

    @classmethod
    def _load_all_countries(cls) -> None:
        """自动加载所有国家配置"""
        # 获取countries包的路径
        from tax_compliance_radar.registry import countries as countries_package
        package_path = Path(countries_package.__file__).parent

        # 遍历所有模块
        for finder, name, is_pkg in pkgutil.iter_modules([str(package_path)]):
            if not is_pkg:
                try:
                    module = importlib.import_module(
                        f"tax_compliance_radar.registry.countries.{name}"
                    )
                    # 查找模块中的CountryConfig实例
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, CountryConfig):
                            cls._configs[attr.country_code] = attr
                except Exception as e:
                    print(f"Warning: Failed to load country config from {name}: {e}")

    @classmethod
    def register(cls, config: CountryConfig) -> None:
        """手动注册国家配置"""
        cls._configs[config.country_code] = config

    @classmethod
    def get(cls, country_code: str) -> CountryConfig:
        """获取国家配置

        Raises:
            ValueError: 如果国家代码不被支持
        """
        cls._ensure_loaded()
        if country_code not in cls._configs:
            raise ValueError(f"Unsupported country: {country_code}")
        return cls._configs[country_code]

    @classmethod
    def is_supported(cls, country_code: str) -> bool:
        """检查国家是否被支持"""
        cls._ensure_loaded()
        return country_code in cls._configs

    @classmethod
    def list_all(cls) -> List[Dict[str, str]]:
        """列出所有支持的国家（用于API返回）"""
        cls._ensure_loaded()
        return [
            {
                "code": config.country_code,
                "name": config.country_name,
                "tax_type": config.tax_type,
            }
            for config in cls._configs.values()
        ]

    @classmethod
    def get_all_configs(cls) -> Dict[str, CountryConfig]:
        """获取所有国家配置"""
        cls._ensure_loaded()
        return cls._configs.copy()
