"""国家配置注册中心 - 基于 YAML 配置自动加载"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List

from tax_compliance_radar.config import DATA_DIR
from tax_compliance_radar.registry.base import CountryConfig, BusinessField


class CountryRegistry:
    """国家配置注册中心

    支持两种加载方式：
    1. YAML 配置文件 (优先): backend/data/countries.yaml
    2. Python 模块 (降级): registry/countries/ 下的 Python 文件

    用法:
        # 获取国家配置
        config = CountryRegistry.get("TH")

        # 列出所有支持的国家
        countries = CountryRegistry.list_all()
    """

    _configs: Dict[str, CountryConfig] = {}
    _loaded: bool = False
    _yaml_path: Path = DATA_DIR / "countries.yaml"

    @classmethod
    def _ensure_loaded(cls) -> None:
        """确保所有国家配置已加载"""
        if not cls._loaded:
            # 优先从 YAML 加载，降级到 Python 模块
            if cls._yaml_path.exists():
                cls._load_from_yaml()
            else:
                cls._load_from_python_modules()
            cls._loaded = True

    @classmethod
    def _load_from_yaml(cls) -> None:
        """从 YAML 配置文件加载所有国家配置"""
        try:
            import yaml
        except ImportError:
            print("Warning: PyYAML not installed, falling back to Python modules")
            cls._load_from_python_modules()
            return

        with open(cls._yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for country_data in data.get("countries", []):
            # 解析业务字段
            business_fields = []
            fields_data = country_data.pop("business_fields", [])
            for field_data in fields_data:
                business_fields.append(BusinessField(**field_data))

            # YAML 字段名映射到 CountryConfig 字段名
            config = CountryConfig(
                country_code=country_data["code"],
                country_name=country_data["name"],
                currency=country_data["currency"],
                currency_symbol=country_data["currency_symbol"],
                tax_type=country_data["tax_type"],
                tax_rate=country_data["tax_rate"],
                registration_threshold=country_data["registration_threshold"],
                language=country_data["language"],
                business_types=country_data["business_types"],
                platforms=country_data["platforms"],
                flag=country_data.get("flag", "🌍"),
                business_fields=business_fields,
            )
            cls._configs[config.country_code] = config

        print(f"Loaded {len(cls._configs)} countries from YAML config")

    @classmethod
    def _load_from_python_modules(cls) -> None:
        """从 Python 模块加载国家配置（降级方案）"""
        from tax_compliance_radar.registry import countries as countries_package
        package_path = Path(countries_package.__file__).parent

        for finder, name, is_pkg in pkgutil.iter_modules([str(package_path)]):
            if not is_pkg:
                try:
                    module = importlib.import_module(
                        f"tax_compliance_radar.registry.countries.{name}"
                    )
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

    @classmethod
    def get_all_business_field_names(cls) -> List[str]:
        """获取所有国家定义的所有业务字段名（用于动态校验）"""
        cls._ensure_loaded()
        field_names = set()
        for config in cls._configs.values():
            for field in config.business_fields:
                field_names.add(field.name)
        return list(field_names)
