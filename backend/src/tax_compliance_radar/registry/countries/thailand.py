"""泰国VAT配置"""
from tax_compliance_radar.registry.base import CountryConfig

# 泰国VAT配置实例 - 会被自动注册
THAILAND_CONFIG = CountryConfig(
    country_code="TH",
    country_name="泰国",
    currency="THB",
    currency_symbol="泰铢",
    tax_type="VAT",
    tax_rate=7.0,
    registration_threshold=1800000,  # 180万泰铢
    language="zh",
    business_types=["跨境电商零售", "品牌出海直营", "外贸综合服务"],
    platforms=["Shopee", "Lazada", "TikTok Shop"],
)
