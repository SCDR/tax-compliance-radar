"""单元测试 - 安全规则表达式评估器

覆盖 SafeRuleEvaluator 的所有功能点和边界场景。
"""
from __future__ import annotations

import pytest

from tax_compliance_radar.services.safe_eval import SafeRuleEvaluator, safe_eval_rule


class TestSafeRuleEvaluatorBasic:
    """基础表达式测试"""

    @pytest.fixture
    def evaluator(self):
        """创建带测试数据的评估器"""
        return SafeRuleEvaluator(
            names={
                "business_type": "跨境电商零售",
                "annual_sales": 5000000,
                "monthly_orders": 10000,
                "platforms": ["Shopee", "Lazada", "TikTok Shop"],
                "product_categories": ["电子产品", "服饰", "美妆"],
                "warehousing_mode": "海外仓",
                "has_local_entity": False,
                "threshold": 1800000,
            }
        )

    def test_comparison_operators(self, evaluator):
        """测试所有比较运算符"""
        assert evaluator.eval("annual_sales > 1000000") is True
        assert evaluator.eval("annual_sales >= 5000000") is True
        assert evaluator.eval("monthly_orders < 20000") is True
        assert evaluator.eval("monthly_orders <= 10000") is True
        assert evaluator.eval("annual_sales == 5000000") is True
        assert evaluator.eval("annual_sales != 0") is True

    def test_logic_operators(self, evaluator):
        """测试逻辑运算符"""
        # and
        assert evaluator.eval("annual_sales > 1000000 and monthly_orders > 5000") is True
        assert evaluator.eval("annual_sales > 10000000 and monthly_orders > 5000") is False

        # or
        assert evaluator.eval("annual_sales > 10000000 or monthly_orders > 5000") is True
        assert evaluator.eval("annual_sales > 10000000 or monthly_orders > 20000") is False

        # not
        assert evaluator.eval("not has_local_entity") is True
        assert evaluator.eval("not (annual_sales > 1000000)") is False

    def test_in_operator(self, evaluator):
        """测试成员运算符 in / not in"""
        assert evaluator.eval("'Shopee' in platforms") is True
        assert evaluator.eval("'Amazon' not in platforms") is True
        assert evaluator.eval("business_type in ['跨境电商零售', '品牌出海直营']") is True
        assert evaluator.eval("business_type in ['外贸综合服务', '一般贸易']") is False

    def test_ternary_expression(self, evaluator):
        """测试三元表达式"""
        result = evaluator.eval("'高销售额' if annual_sales > 3000000 else '普通销售额'")
        assert result == "高销售额"

        result = evaluator.eval("'高销售额' if annual_sales > 10000000 else '普通销售额'")
        assert result == "普通销售额"


class TestSafeRuleEvaluatorFunctions:
    """白名单函数测试"""

    @pytest.fixture
    def evaluator(self):
        return SafeRuleEvaluator(
            names={
                "platforms": ["Shopee", "Lazada", "TikTok Shop"],
                "product_categories": ["电子产品", "服饰", "美妆"],
                "sales": [100, 200, 300],
                "empty_list": [],
            }
        )

    def test_len_function(self, evaluator):
        """测试 len() 函数"""
        assert evaluator.eval("len(platforms) == 3") is True
        assert evaluator.eval("len(empty_list) == 0") is True
        assert evaluator.eval("len(platforms) > 0") is True
        assert evaluator.eval("len(platforms) > 5") is False

    def test_any_function_with_generator(self, evaluator):
        """测试 any() + 生成器表达式"""
        # 任意平台包含 'Shop'
        assert evaluator.eval("any('Shop' in p for p in platforms)") is True
        # 任意产品是 '电子产品'
        assert evaluator.eval("any(c == '电子产品' for c in product_categories)") is True
        # 无匹配
        assert evaluator.eval("any('Amazon' in p for p in platforms)") is False

    def test_all_function_with_generator(self, evaluator):
        """测试 all() + 生成器表达式"""
        # 所有产品类目长度 > 1
        assert evaluator.eval("all(len(c) > 1 for c in product_categories)") is True
        # 所有平台都以字母开头（永远 True）
        assert evaluator.eval("all(len(p) > 0 for p in platforms)") is True
        # 存在不满足的
        assert evaluator.eval("all('Shop' in p for p in platforms)") is False  # Lazada 不包含

    def test_sum_function(self, evaluator):
        """测试 sum() 函数"""
        assert evaluator.eval("sum(sales) == 600") is True
        assert evaluator.eval("sum(sales) > 500") is True
        assert evaluator.eval("sum(empty_list) == 0") is True

    def test_max_function(self, evaluator):
        """测试 max() 函数"""
        assert evaluator.eval("max(sales) == 300") is True
        assert evaluator.eval("max(sales) > 200") is True

    def test_min_function(self, evaluator):
        """测试 min() 函数"""
        assert evaluator.eval("min(sales) == 100") is True
        assert evaluator.eval("min(sales) < 200") is True

    def test_function_combinations(self, evaluator):
        """测试函数组合使用"""
        # len + 比较
        assert evaluator.eval("len(platforms) > 2 and sum(sales) > 500") is True
        # any + len
        assert evaluator.eval("any(len(p) > 10 for p in platforms)") is True
        # all + len
        assert evaluator.eval("all(len(c) >= 2 for c in product_categories)") is True


class TestSafeRuleEvaluatorScenarios:
    """业务规则场景测试"""

    def test_cross_border_ecommerce_rules(self):
        """测试跨境电商典型规则场景"""
        data = {
            "business_type": "跨境电商零售",
            "annual_sales": 5000000,
            "platforms": ["Shopee", "TikTok Shop"],
            "product_categories": ["电子产品"],
            "registration_threshold": 1800000,
        }
        evaluator = SafeRuleEvaluator(names=data)

        # 规则 1: 跨境电商类型且销售额超过阈值 -> 高风险
        assert evaluator.eval(
            "business_type in ['跨境电商零售', '品牌出海直营'] "
            "and annual_sales >= registration_threshold"
        ) is True

        # 规则 2: 入驻 TikTok 平台 -> 专项申报
        assert evaluator.eval("any('TikTok' in p for p in platforms)") is True

        # 规则 3: 销售电子产品 -> 认证要求
        assert evaluator.eval("'电子产品' in product_categories") is True

    def test_foreign_trade_service_rules(self):
        """测试外贸综合服务规则场景"""
        data = {
            "business_type": "外贸综合服务",
            "has_local_entity": True,
            "client_count": 50,
            "annual_sales": 10000000,
        }
        evaluator = SafeRuleEvaluator(names=data)

        # 外贸综合服务类型，且无本地主体 -> 连带责任风险
        # 这里 has_local_entity=True，所以风险条件为 False
        assert evaluator.eval(
            "business_type == '外贸综合服务' and not has_local_entity"
        ) is False

    def test_platform_specific_rules(self):
        """测试平台专项规则"""
        data = {
            "platforms": ["Shopee", "Lazada", "Amazon"],
            "warehousing_mode": "第三方仓",
        }
        evaluator = SafeRuleEvaluator(names=data)

        # 多平台运营规则
        assert evaluator.eval("len(platforms) >= 3") is True

        # Amazon 平台特殊要求
        assert evaluator.eval("'Amazon' in platforms") is True

    def test_product_category_rules(self):
        """测试产品类目规则"""
        data = {
            "product_categories": ["电子产品", "食品", "化妆品"],
            "annual_sales": 2000000,
        }
        evaluator = SafeRuleEvaluator(names=data)

        # 销售高风险类目（食品/化妆品需要特殊认证）
        assert evaluator.eval(
            "any(c in ['食品', '化妆品', '医疗器械'] for c in product_categories)"
        ) is True

        # 同时销售电子产品和食品 -> 双重合规要求
        assert evaluator.eval(
            "'电子产品' in product_categories and '食品' in product_categories"
        ) is True


class TestSafeRuleEvaluatorEdgeCases:
    """边界条件测试"""

    def test_empty_list(self):
        """测试空列表"""
        evaluator = SafeRuleEvaluator(names={"items": []})
        assert evaluator.eval("len(items) == 0") is True
        assert evaluator.eval("len(items) > 0") is False
        # any 对空列表返回 False
        assert evaluator.eval("any(x > 0 for x in items)") is False
        # all 对空列表返回 True（vacuous truth）
        assert evaluator.eval("all(x > 0 for x in items)") is True

    def test_boolean_values(self):
        """测试布尔值"""
        evaluator = SafeRuleEvaluator(names={"flag_true": True, "flag_false": False})
        assert evaluator.eval("flag_true") is True
        assert evaluator.eval("flag_false") is False
        assert evaluator.eval("not flag_false") is True

    def test_zero_and_negative_values(self):
        """测试零和负值"""
        evaluator = SafeRuleEvaluator(names={"zero": 0, "negative": -100, "positive": 100})
        assert evaluator.eval("zero == 0") is True
        assert evaluator.eval("negative < 0") is True
        assert evaluator.eval("positive > 0") is True

    def test_single_element_list(self):
        """测试单元素列表"""
        evaluator = SafeRuleEvaluator(names={"items": [42]})
        assert evaluator.eval("len(items) == 1") is True
        assert evaluator.eval("any(x == 42 for x in items)") is True
        assert evaluator.eval("all(x == 42 for x in items)") is True


class TestSafeRuleEvaluatorSecurity:
    """安全测试 - 验证危险操作被阻止"""

    def test_cannot_import_modules(self):
        """验证无法导入模块"""
        evaluator = SafeRuleEvaluator()
        with pytest.raises(Exception):  # 任何类型的异常都表示阻止成功
            evaluator.eval("__import__('os')")

    def test_cannot_access_builtins(self):
        """验证无法访问内置函数"""
        evaluator = SafeRuleEvaluator()
        with pytest.raises(Exception):
            evaluator.eval("__builtins__")

    def test_cannot_call_unsafe_functions(self):
        """验证无法调用不在白名单的函数"""
        evaluator = SafeRuleEvaluator()
        with pytest.raises(Exception):
            evaluator.eval("eval('1 + 1')")

        with pytest.raises(Exception):
            evaluator.eval("exec('print(1)')")

        with pytest.raises(Exception):
            evaluator.eval("open('/etc/passwd')")

    def test_generator_with_if_condition(self):
        """测试带 if 过滤的生成器表达式"""
        evaluator = SafeRuleEvaluator(names={"numbers": [1, 2, 3, 4, 5, 6]})
        # 只对偶数求和（需要 if 过滤支持）
        assert evaluator.eval("sum(x for x in numbers if x % 2 == 0)") == 12
        # 判断是否有大于 5 的偶数
        assert evaluator.eval("any(x > 5 for x in numbers if x % 2 == 0)") is True


class TestSafeEvalRuleFunction:
    """测试 safe_eval_rule 便捷函数"""

    def test_basic_usage(self):
        """测试基本用法"""
        result = safe_eval_rule(
            "annual_sales > 1000000",
            names={"annual_sales": 5000000},
        )
        assert result is True

    def test_complex_rule(self):
        """测试复杂规则"""
        result = safe_eval_rule(
            "business_type in ['A', 'B'] and len(platforms) > 0",
            names={"business_type": "A", "platforms": ["Shopee"]},
        )
        assert result is True

    def test_returns_bool(self):
        """验证返回值总是布尔类型"""
        # 真值
        assert isinstance(safe_eval_rule("1 > 0", names={}), bool)
        # 假值
        assert isinstance(safe_eval_rule("1 < 0", names={}), bool)
