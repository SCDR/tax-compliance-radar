"""AI增强风险检测 - 基于RAG检索识别潜在风险点
支持:
- 同步/异步双版本调用
- 多国并行检测
- 结果缓存机制
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import Dict, Any, List

from tax_compliance_radar.models.schemas import AuditRequest, RiskItem, SourcedRiskItem, SourceInfo
from tax_compliance_radar.services.retrieval_service import search_regulations
from tax_compliance_radar.services.llm_service import _chat_with_fallback, _achat_with_fallback, _extract_json
from tax_compliance_radar.registry import CountryRegistry


# ==================== 配置与常量 ====================

# 特殊格式处理的字段
_SPECIAL_FORMAT_FIELDS = {
    "annual_sales",  # 需要加货币符号
}

# 元数据字段，不传递给 LLM
_METADATA_FIELDS = {"_field_set_flags"}


# ==================== 缓存机制 ====================
_risk_cache: Dict[str, List[SourcedRiskItem]] = {}


def _get_cache_key(country_code: str, business_data: Dict[str, Any]) -> str:
    """生成缓存键 - 自动包含所有业务维度

    🌟 自动扩展：新增业务维度无需修改此函数
    """
    key_data: Dict[str, Any] = {"country": country_code}

    # 自动遍历所有业务字段添加到缓存键
    for key, value in sorted(business_data.items()):
        if isinstance(value, list):
            key_data[key] = sorted(value) if value else []
        else:
            key_data[key] = value

    key_str = str(sorted(key_data.items()))
    return f"risk_detection:{hashlib.md5(key_str.encode()).hexdigest()}"


def get_cached_risks(country_code: str, business_data: Dict[str, Any]) -> List[SourcedRiskItem] | None:
    """获取缓存的风险检测结果"""
    key = _get_cache_key(country_code, business_data)
    return _risk_cache.get(key)


def set_cached_risks(country_code: str, business_data: Dict[str, Any], risks: List[SourcedRiskItem]):
    """缓存风险检测结果"""
    key = _get_cache_key(country_code, business_data)
    _risk_cache[key] = risks


def clear_risk_cache():
    """清空缓存（用于配置更新后）"""
    _risk_cache.clear()


# JSON 输出模板（独立定义，避免转义一次
JSON_TEMPLATE = """
[
    {{
        "risk_level": "低风险",
        "risk_desc": "具体风险描述",
        "trigger_condition": "触发条件说明",
        "regulation_base": "引用的具体法规",
        "violation_consequence": "可能的后果"
    }}
]
""".strip()


def get_risk_detection_prompt(
    country_code: str,
    business_data: Dict[str, Any],
    retrieval_result=None,
) -> str:
    """获取指定国家的风险检测提示词

    🌟 自动扩展能力：
    - 自动格式化所有业务维度字段到提示词
    - 新增业务维度无需修改此函数

    Args:
        country_code: 国家代码
        business_data: 业务数据字典
        retrieval_result: 可选，外部传入的检索结果（用于复用，减少重复检索）
    """
    config = CountryRegistry.get(country_code)
    currency_symbol = config.currency_symbol

    # ===== 自动格式化所有业务维度（无需硬编码）=====
    business_info_lines = []
    for key, value in business_data.items():
        # 跳过元数据字段和空值
        if key in _METADATA_FIELDS or value is None or value == "" or value == []:
            continue

        # 从国家配置动态获取字段友好名称
        friendly_name = key
        for field in config.business_fields:
            if field.name == key:
                friendly_name = field.label
                break

        # 特殊格式处理
        if key in _SPECIAL_FORMAT_FIELDS:
            if key == "annual_sales":
                display_value = f"{value:,} {currency_symbol}"
            else:
                display_value = str(value)
        elif isinstance(value, list):
            display_value = ", ".join(str(v) for v in value) or "无"
        elif isinstance(value, bool):
            display_value = "是" if value else "否"
        else:
            display_value = str(value)

        business_info_lines.append(f"{friendly_name}：{display_value}")

    business_info_block = "\n".join(business_info_lines)

    # 构建法规上下文（优先复用外部传入的检索结果，避免重复检索）
    if retrieval_result is None:
        # 构建检索查询（使用主要字段）
        query_parts = [
            str(business_data.get("business_type", "")),
            str(business_data.get("product_categories", "")),
            f"{business_data.get('annual_sales', 0)}",
            "VAT 风险"
        ]
        query = " ".join([p for p in query_parts if p])
        retrieval_result = search_regulations(query, top_k=2)  # 减少召回数量

    if retrieval_result.below_threshold or not retrieval_result.documents:
        regulation_context = "无相关法规检索结果"
    else:
        context_parts = []
        for doc in retrieval_result.documents:
            context_parts.append(f"- {doc.doc_name}: {doc.content[:200]}...")
        regulation_context = "\n".join(context_parts)

    return f"""
你是{config.country_name}{config.tax_type}合规风险检测专家。基于业务信息和相关法规，识别可能的潜在风险点。

【任务说明】
- 基于业务数据和检索到的相关法规
- 识别规则引擎可能遗漏的边缘场景风险
- 特别关注商品类目、仓储模式、订单规模等特殊场景
- 只添加与业务场景直接相关的真实风险
- 如果没有发现额外风险，返回空数组

【业务信息】
{business_info_block}

【相关法规检索结果】
{regulation_context}

【输出格式 - 严格JSON数组】
{JSON_TEMPLATE}

【重要约束】
- 只输出规则引擎未覆盖的潜在风险
- 如果没有发现额外风险，输出空数组 []
- 风险等级只能是"低风险"（AI识别的为潜在风险，确定性风险由规则引擎处理）
- 所有风险必须与{config.country_name}税务合规相关
- 特别关注商品类目对应的认证要求、仓储模式对应的税务义务
""".strip()


def detect_additional_risks(business: AuditRequest, retrieval_result=None) -> list[RiskItem]:
    """使用RAG + AI识别规则引擎遗漏的潜在风险（兼容旧版单国家）

    Args:
        business: 业务信息
        retrieval_result: 可选，外部传入的检索结果（用于复用，减少重复检索）
    """
    business_data = {
        "business_type": business.business_type,
        "annual_sales": business.annual_sales,
        "platforms": business.platforms,
    }
    sourced_risks = detect_additional_risks_for_country("TH", business_data)

    # 转换为旧格式
    result = []
    for risk in sourced_risks:
        result.append(RiskItem(
            risk_level=risk.risk_level,
            risk_desc=risk.risk_desc,
            trigger_condition=risk.trigger_condition,
            regulation_base=risk.regulation_base,
            violation_consequence=risk.violation_consequence,
        ))
    return result


def detect_additional_risks_for_country(
    country_code: str,
    business_data: Dict[str, Any],
) -> list[SourcedRiskItem]:
    """使用RAG + AI为指定国家识别规则引擎遗漏的潜在风险

    Args:
        country_code: 国家代码
        business_data: 业务数据字典

    Returns:
        带来源标签的风险列表
    """
    config = CountryRegistry.get(country_code)

    try:
        # 构造提示词（已包含 RAG 检索）
        user_prompt = get_risk_detection_prompt(country_code, business_data)

        _, content = _chat_with_fallback("你是合规风险检测专家", user_prompt)
        risks_data = _extract_json(content)

        if not isinstance(risks_data, list):
            return []

        result = []
        for risk in risks_data:
            risk["risk_level"] = "低风险"
            try:
                # 添加来源标签
                sourced_risk = SourcedRiskItem(
                    source_info=SourceInfo(
                        country_code=country_code,
                        country_name=config.country_name,
                        source_type="ai_generated",
                    ),
                    risk_level="低风险",
                    risk_desc=risk["risk_desc"],
                    trigger_condition=risk.get("trigger_condition", ""),
                    regulation_base=risk.get("regulation_base", ""),
                    violation_consequence=risk.get("violation_consequence", ""),
                )
                result.append(sourced_risk)
            except Exception:
                continue

        # 缓存结果
        set_cached_risks(country_code, business_data, result)
        return result
    except Exception as e:
        print(f"AI risk detection failed for {country_code}: {e}")
        return []


# ==================== 异步版本（支持并行） ====================

async def adetect_additional_risks_for_country(
    country_code: str,
    business_data: Dict[str, Any],
    use_cache: bool = True,
) -> List[SourcedRiskItem]:
    """异步版本：使用RAG + AI为指定国家识别规则引擎遗漏的潜在风险

    Args:
        country_code: 国家代码
        business_data: 业务数据字典
        use_cache: 是否使用缓存

    Returns:
        带来源标签的风险列表
    """
    # 先查缓存
    if use_cache:
        cached = get_cached_risks(country_code, business_data)
        if cached is not None:
            return cached

    config = CountryRegistry.get(country_code)

    try:
        # 构造提示词（已包含 RAG 检索）
        user_prompt = get_risk_detection_prompt(country_code, business_data)

        _, content = await _achat_with_fallback("你是合规风险检测专家", user_prompt)
        risks_data = _extract_json(content)

        if not isinstance(risks_data, list):
            return []

        result = []
        for risk in risks_data:
            risk["risk_level"] = "低风险"
            try:
                sourced_risk = SourcedRiskItem(
                    source_info=SourceInfo(
                        country_code=country_code,
                        country_name=config.country_name,
                        source_type="ai_generated",
                    ),
                    risk_level="低风险",
                    risk_desc=risk["risk_desc"],
                    trigger_condition=risk.get("trigger_condition", ""),
                    regulation_base=risk.get("regulation_base", ""),
                    violation_consequence=risk.get("violation_consequence", ""),
                )
                result.append(sourced_risk)
            except Exception:
                continue

        # 缓存结果
        set_cached_risks(country_code, business_data, result)
        return result
    except Exception as e:
        print(f"AI risk detection failed for {country_code}: {e}")
        return []


async def parallel_detect_risks_for_countries(
    countries_with_business: Dict[str, Dict[str, Any]],
    use_cache: bool = True,
) -> Dict[str, List[SourcedRiskItem]]:
    """并行检测多个国家的风险

    Args:
        countries_with_business: 国家代码 -> 业务数据 字典
        use_cache: 是否使用缓存

    Returns:
        国家代码 -> 风险列表 字典
    """
    # 创建所有检测任务
    tasks = [
        adetect_additional_risks_for_country(country_code, business_data, use_cache)
        for country_code, business_data in countries_with_business.items()
    ]

    # 并行执行
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 整理结果
    final_results = {}
    for country_code, result in zip(countries_with_business.keys(), results):
        if isinstance(result, Exception):
            print(f"Country {country_code} failed: {result}")
            final_results[country_code] = []
        else:
            final_results[country_code] = result

    return final_results
