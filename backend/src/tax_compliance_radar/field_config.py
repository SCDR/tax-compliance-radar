"""
业务字段元数据配置

集中管理所有业务维度的：
- 默认值
- 数据类型
- 是否必填
- 说明文档

规则编写者无需关心 None 判断，系统自动注入默认值。
"""
from typing import Any, Dict, Optional


class FieldMetadata:
    """字段元数据"""

    def __init__(
        self,
        name: str,
        field_type: str,
        default_value: Any,
        required: bool = False,
        description: str = "",
    ):
        self.name = name
        self.field_type = field_type  # str, int, bool, list[str]
        self.default_value = default_value
        self.required = required
        self.description = description


# ============================================
# 所有业务字段的元数据配置
# ============================================
FIELD_METADATA: Dict[str, FieldMetadata] = {
    # ===== 通用维度 =====
    "business_type": FieldMetadata(
        name="business_type",
        field_type="str",
        default_value="",
        required=True,
        description="业务类型",
    ),
    "company_size": FieldMetadata(
        name="company_size",
        field_type="str",
        default_value="",
        required=False,
        description="企业规模",
    ),
    "industry": FieldMetadata(
        name="industry",
        field_type="str",
        default_value="",
        required=False,
        description="所属行业",
    ),

    # ===== 多国维度 =====
    "annual_sales": FieldMetadata(
        name="annual_sales",
        field_type="int",
        default_value=0,
        required=False,
        description="年销售额（当地货币）",
    ),
    "monthly_orders": FieldMetadata(
        name="monthly_orders",
        field_type="int",
        default_value=0,
        required=False,
        description="月均订单量",
    ),
    "employee_count": FieldMetadata(
        name="employee_count",
        field_type="int",
        default_value=0,
        required=False,
        description="员工数量",
    ),
    "platforms": FieldMetadata(
        name="platforms",
        field_type="list[str]",
        default_value=[],
        required=False,
        description="入驻平台列表",
    ),
    "product_categories": FieldMetadata(
        name="product_categories",
        field_type="list[str]",
        default_value=[],
        required=False,
        description="商品类目列表",
    ),
    "warehousing_mode": FieldMetadata(
        name="warehousing_mode",
        field_type="str",
        default_value="",
        required=False,
        description="仓储模式",
    ),
    "has_local_entity": FieldMetadata(
        name="has_local_entity",
        field_type="bool",
        default_value=False,
        required=False,
        description="是否有本地公司主体",
    ),
}


def get_field_default(field_name: str) -> Any:
    """获取字段的默认值"""
    if field_name in FIELD_METADATA:
        return FIELD_METADATA[field_name].default_value
    # 未知字段，根据常见类型推断默认值
    if field_name.endswith("_count") or field_name.endswith("_sales") or field_name.endswith("_orders"):
        return 0
    if field_name.endswith("s") and not field_name.endswith("ss"):  # 复数形式通常是列表
        return []
    if field_name.startswith("has_") or field_name.startswith("is_"):
        return False
    return ""


def get_all_field_names() -> list:
    """获取所有已配置的字段名"""
    return list(FIELD_METADATA.keys())
