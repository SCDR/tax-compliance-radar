"""国家配置基类"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from tax_compliance_radar.config import REGULATIONS_DIR


@dataclass(frozen=True)
class CountryConfig:
    """国家配置基类 - 所有国家配置都继承此类"""
    country_code: str  # "TH", "VN", "MY"
    country_name: str  # "泰国", "越南"
    currency: str  # "THB", "VND", "MYR"
    currency_symbol: str  # "泰铢", "越南盾", "马币"
    tax_type: str  # "VAT", "GST"
    tax_rate: float  # 7.0, 10.0, 6.0
    registration_threshold: int  # 注册阈值（本币）
    language: str  # "zh", "en"
    business_types: List[str]  # 支持的业务类型
    platforms: List[str]  # 支持的平台列表

    @property
    def collection_name(self) -> str:
        """Chroma collection 名称"""
        return f"{self.country_code.lower()}_{self.tax_type.lower()}_regulations"

    @property
    def regulations_dir(self) -> Path:
        """法规文档路径"""
        return REGULATIONS_DIR / self.country_code.upper()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于API返回"""
        return {
            "country_code": self.country_code,
            "country_name": self.country_name,
            "currency": self.currency,
            "currency_symbol": self.currency_symbol,
            "tax_type": self.tax_type,
            "tax_rate": self.tax_rate,
            "registration_threshold": self.registration_threshold,
            "language": self.language,
            "business_types": self.business_types,
            "platforms": self.platforms,
        }
