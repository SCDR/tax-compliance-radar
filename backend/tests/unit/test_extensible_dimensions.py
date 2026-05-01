#!/usr/bin/env python3
"""可扩展业务维度测试套件

验证:
1. 新增业务维度自动提取到单国家业务数据
2. 规则引擎自动识别并使用新维度
3. AI 风险检测自动感知新维度
4. 建议生成器自动感知新维度
"""

import sys
import pytest

sys.path.insert(0, 'src')

from tax_compliance_radar.models.schemas import BusinessProfile, SourceInfo
from tax_compliance_radar.factories import StrategyFactory
from tax_compliance_radar.services.country_rules_engine import CountryRulesEngine
from tax_compliance_radar.services.ai_risk_detector import get_risk_detection_prompt
from tax_compliance_radar.registry import CountryRegistry


@pytest.fixture
def sample_business_profile():
    """创建包含所有新维度的测试业务档案"""
    return BusinessProfile(
        business_type="跨境电商零售",
        annual_sales_by_country={"TH": 5000000, "VN": 300000000},
        platforms_by_country={"TH": ["Shopee", "Lazada"], "VN": ["TikTok Shop"]},
        product_categories_by_country={"TH": ["电子产品", "服饰"], "VN": ["美妆"]},
        monthly_orders_by_country={"TH": 10000, "VN": 8000},
        warehousing_mode_by_country={"TH": "海外仓", "VN": "直邮"},
        has_local_entity_by_country={"TH": False, "VN": True},
    )


@pytest.fixture
def strategy():
    """创建多国组合策略"""
    return StrategyFactory.get_multi_country_strategy(["TH", "VN"])


class TestDimensionAutoExtraction:
    """测试业务维度自动提取能力"""

    def test_general_dimension_auto_extractable(self, sample_business_profile, strategy):
        """测试通用维度自动扩展：新增通用维度无需修改代码"""
        # 验证 business_type 被自动提取（现有通用维度）
        th_business = strategy._extract_country_business(sample_business_profile, "TH")
        assert "business_type" in th_business
        assert th_business["business_type"] == "跨境电商零售"

        # 验证：通用维度在所有国家都相同
        vn_business = strategy._extract_country_business(sample_business_profile, "VN")
        assert vn_business["business_type"] == th_business["business_type"]

    def test_field_set_metadata_injected(self, sample_business_profile, strategy):
        """测试：元数据字段 _field_set_flags 自动注入"""
        th_business = strategy._extract_country_business(sample_business_profile, "TH")

        # 验证元数据字段存在
        assert "_field_set_flags" in th_business
        flags = th_business["_field_set_flags"]

        # 已传递的字段标记为 True
        assert flags["annual_sales"] == True
        assert flags["platforms"] == True
        assert flags["product_categories"] == True

    def test_distinguish_zero_vs_not_provided(self, strategy):
        """测试：区分"值为0" vs "未传递"（通过元数据）"""
        from tax_compliance_radar.models.schemas import BusinessProfile

        # 场景 A：泰国传了 annual_sales = 0，越南完全没传
        profile = BusinessProfile(
            business_type="跨境电商零售",
            annual_sales_by_country={"TH": 0},  # 泰国明确传了 0
            platforms_by_country={"TH": ["Shopee"]},
        )

        th_business = strategy._extract_country_business(profile, "TH")
        vn_business = strategy._extract_country_business(profile, "VN")

        # 两个国家看到的 annual_sales 都是 0（默认值注入）
        assert th_business["annual_sales"] == 0
        assert vn_business["annual_sales"] == 0

        # 🌟 但通过元数据可以区分：泰国是"显式传了0"，越南是"没传，用默认值"
        assert th_business["_field_set_flags"]["annual_sales"] == True  # 显式传递
        assert vn_business["_field_set_flags"]["annual_sales"] == False  # 未传递

    def test_backward_compatibility_ignoring_metadata(self, strategy):
        """测试：向后兼容 - 完全忽略元数据字段也能正常工作"""
        from tax_compliance_radar.models.schemas import BusinessProfile

        profile = BusinessProfile(
            business_type="跨境电商零售",
            annual_sales_by_country={"TH": 1000000},
            platforms_by_country={"TH": ["Shopee"]},
        )

        th_business = strategy._extract_country_business(profile, "TH")

        # 旧代码不依赖 _field_set_flags，仍然能正常工作
        assert th_business["business_type"] == "跨境电商零售"
        assert th_business["annual_sales"] == 1000000
        assert th_business["platforms"] == ["Shopee"]

        # 旧规则："annual_sales > 0" 依然有效，不需要修改
        assert th_business["annual_sales"] > 0

    def test_thailand_dimensions_extracted(self, sample_business_profile, strategy):
        """测试泰国业务维度自动提取"""
        th_business = strategy._extract_country_business(sample_business_profile, "TH")

        # 验证所有新维度被正确提取
        assert "product_categories" in th_business
        assert "monthly_orders" in th_business
        assert "warehousing_mode" in th_business
        assert "has_local_entity" in th_business

        # 验证值正确性
        assert th_business["product_categories"] == ["电子产品", "服饰"]
        assert th_business["monthly_orders"] == 10000
        assert th_business["warehousing_mode"] == "海外仓"
        assert th_business["has_local_entity"] == False

    def test_vietnam_dimensions_extracted(self, sample_business_profile, strategy):
        """测试越南业务维度自动提取"""
        vn_business = strategy._extract_country_business(sample_business_profile, "VN")

        # 验证所有新维度被正确提取
        assert vn_business["product_categories"] == ["美妆"]
        assert vn_business["monthly_orders"] == 8000
        assert vn_business["warehousing_mode"] == "直邮"
        assert vn_business["has_local_entity"] == True

    def test_default_values_for_missing_dimensions(self, strategy):
        """测试缺失维度的默认值处理"""
        empty_profile = BusinessProfile(
            business_type="跨境电商零售",
            annual_sales_by_country={},
            platforms_by_country={},
            product_categories_by_country={},
            monthly_orders_by_country={},
            warehousing_mode_by_country={},
            has_local_entity_by_country={},
        )

        th_business = strategy._extract_country_business(empty_profile, "TH")

        # 验证默认值
        assert th_business["annual_sales"] == 0
        assert th_business["platforms"] == []
        assert th_business["product_categories"] == []
        assert th_business["monthly_orders"] == 0
        assert th_business["warehousing_mode"] == ""
        assert th_business["has_local_entity"] == False


class TestRulesEngineNewDimensions:
    """测试规则引擎使用新维度的能力"""

    @pytest.fixture
    def config(self):
        return CountryRegistry.get("TH")

    @pytest.fixture
    def engine(self):
        return CountryRulesEngine.get_for_country("TH")

    def make_source(self, regulation_id=None, source_type="rule"):
        return SourceInfo(
            country_code="TH",
            country_name="泰国",
            regulation_id=regulation_id,
            source_type=source_type,
        )

    def test_electronics_category_rule_triggered(self, engine, config):
        """测试电子产品类目规则触发"""
        business = {
            "business_type": "跨境电商零售",
            "annual_sales": 5000000,
            "platforms": ["Shopee"],
            "product_categories": ["电子产品"],
            "monthly_orders": 1000,
            "warehousing_mode": "海外仓",
            "has_local_entity": True,
        }

        risks = engine.evaluate(business, self.make_source, config)
        triggered_rules = [r.source_info.regulation_id for r in risks]

        assert "TH_R005" in triggered_rules, "电子产品规则未触发"
        electronics_risk = next(
            r for r in risks if r.source_info.regulation_id == "TH_R005"
        )
        assert "NBTC 认证" in electronics_risk.risk_desc

    def test_high_volume_orders_rule_triggered(self, engine, config):
        """测试高订单量规则触发"""
        business = {
            "business_type": "跨境电商零售",
            "annual_sales": 5000000,
            "platforms": ["Shopee"],
            "product_categories": ["服饰"],
            "monthly_orders": 10000,
            "warehousing_mode": "海外仓",
            "has_local_entity": True,
        }

        risks = engine.evaluate(business, self.make_source, config)
        triggered_rules = [r.source_info.regulation_id for r in risks]

        assert "TH_R006" in triggered_rules, "高订单量规则未触发"
        high_volume_risk = next(
            r for r in risks if r.source_info.regulation_id == "TH_R006"
        )
        assert "5000单" in high_volume_risk.trigger_condition

    def test_local_warehouse_rule_triggered(self, engine, config):
        """测试本地仓储规则触发"""
        business = {
            "business_type": "跨境电商零售",
            "annual_sales": 1000000,
            "platforms": ["Lazada"],
            "product_categories": ["服饰"],
            "monthly_orders": 1000,
            "warehousing_mode": "本地仓",
            "has_local_entity": False,
        }

        risks = engine.evaluate(business, self.make_source, config)
        triggered_rules = [r.source_info.regulation_id for r in risks]

        assert "TH_R007" in triggered_rules, "本地仓储规则未触发"
        warehouse_risk = next(
            r for r in risks if r.source_info.regulation_id == "TH_R007"
        )
        assert "本地商业主体" in warehouse_risk.risk_desc

    def test_no_rules_triggered_for_low_risk_scenario(self, engine, config):
        """测试低风险场景不触发新维度规则"""
        business = {
            "business_type": "跨境电商零售",
            "annual_sales": 100000,
            "platforms": [],
            "product_categories": ["图书"],
            "monthly_orders": 100,
            "warehousing_mode": "直邮",
            "has_local_entity": True,
        }

        risks = engine.evaluate(business, self.make_source, config)
        triggered_rules = [r.source_info.regulation_id for r in risks]

        # 通用规则可能触发，但新维度特定规则不应触发
        assert "TH_R005" not in triggered_rules, "电子产品规则不应触发"


class TestAIPromptAutoDimensions:
    """测试 AI 提示词自动感知新维度"""

    def test_prompt_contains_all_dimensions(self):
        """测试提示词自动包含所有业务维度"""
        business_data = {
            "business_type": "跨境电商零售",
            "annual_sales": 5000000,
            "platforms": ["Shopee", "Lazada"],
            "product_categories": ["电子产品", "玩具"],
            "monthly_orders": 8000,
            "warehousing_mode": "本地仓",
            "has_local_entity": False,
            "employee_count": 50,
        }

        prompt = get_risk_detection_prompt("TH", business_data)

        # 提取业务信息部分
        business_section = prompt.split("【业务信息】")[1].split("【相关法规检索结果】")[0]

        # 验证所有新维度出现在提示词中
        assert "商品类目" in business_section
        assert "月订单量" in business_section
        assert "仓储模式" in business_section
        assert "本地公司主体" in business_section
        assert "员工数量" in business_section

        # 验证具体值出现
        assert "电子产品" in business_section
        assert "8000" in business_section
        assert "本地仓" in business_section

    def test_boolean_formatting(self):
        """测试布尔值格式化"""
        business_data = {
            "business_type": "跨境电商零售",
            "annual_sales": 1000000,
            "platforms": [],
            "has_local_entity": True,
        }

        prompt = get_risk_detection_prompt("TH", business_data)
        assert "是" in prompt  # True 转换为"是"

    def test_empty_list_handling(self):
        """测试空列表不显示"""
        business_data = {
            "business_type": "跨境电商零售",
            "annual_sales": 1000000,
            "platforms": [],
            "product_categories": [],
        }

        prompt = get_risk_detection_prompt("TH", business_data)
        business_section = prompt.split("【业务信息】")[1].split("【相关法规检索结果】")[0]

        # 空列表的字段应跳过
        assert "商品类目" not in business_section or "无" in business_section


class TestCacheKeyAutoDimensions:
    """测试缓存键自动包含新维度"""

    def test_cache_key_contains_product_categories(self):
        """测试缓存键包含商品类目信息"""
        from tax_compliance_radar.services.ai_risk_detector import _get_cache_key

        business_1 = {
            "business_type": "跨境电商零售",
            "annual_sales": 5000000,
            "platforms": ["Shopee"],
            "product_categories": ["电子产品"],
        }

        business_2 = {
            "business_type": "跨境电商零售",
            "annual_sales": 5000000,
            "platforms": ["Shopee"],
            "product_categories": ["服饰"],  # 不同的商品类目
        }

        key_1 = _get_cache_key("TH", business_1)
        key_2 = _get_cache_key("TH", business_2)

        # 不同的商品类目应产生不同的缓存键
        assert key_1 != key_2, "新维度变化应导致缓存键变化"

    def test_cache_key_stable_for_same_input(self):
        """测试相同输入产生相同缓存键"""
        from tax_compliance_radar.services.ai_risk_detector import _get_cache_key

        business = {
            "business_type": "跨境电商零售",
            "annual_sales": 5000000,
            "platforms": ["Shopee"],
            "product_categories": ["电子产品"],
            "monthly_orders": 10000,
            "warehousing_mode": "本地仓",
        }

        key_1 = _get_cache_key("TH", business)
        key_2 = _get_cache_key("TH", business)

        assert key_1 == key_2, "相同输入应产生相同缓存键"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
