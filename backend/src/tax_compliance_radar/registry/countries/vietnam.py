"""越南VAT配置 - 骨架"""
from tax_compliance_radar.registry.base import CountryConfig

# 越南VAT配置实例
VIETNAM_CONFIG = CountryConfig(
    country_code="VN",
    country_name="越南",
    currency="VND",
    currency_symbol="越南盾",
    tax_type="VAT",
    tax_rate=10.0,
    registration_threshold=200000000,  # 2亿越南盾
    language="zh",
    business_types=["跨境电商零售", "品牌出海直营"],
    platforms=["Shopee", "Lazada", "TikTok Shop"],
)
