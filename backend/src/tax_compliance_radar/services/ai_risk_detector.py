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


# ==================== 缓存机制 ====================
_risk_cache: Dict[str, List[SourcedRiskItem]] = {}


def _get_cache_key(country_code: str, business_data: Dict[str, Any]) -> str:
    """生成缓存键"""
    key_data = {
        "country": country_code,
        "business_type": business_data.get("business_type"),
        "annual_sales": business_data.get("annual_sales"),
        "platforms": sorted(business_data.get("platforms", [])),
    }
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


def get_risk_detection_prompt(country_code: str, business_data: Dict[str, Any]) -> str:
    """获取指定国家的风险检测提示词"""
    config = CountryRegistry.get(country_code)
    currency_symbol = config.currency_symbol

    platforms_str = ", ".join(business_data.get("platforms", [])) or "无"

    # 构建法规上下文
    query = f"{business_data.get('business_type', '')} {business_data.get('annual_sales', 0)} VAT 风险"
    retrieval_result = search_regulations(query, top_k=3)

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
- 只添加与业务场景直接相关的真实风险
- 如果没有发现额外风险，返回空数组

【输入】
业务类型：{business_data.get('business_type', '')}
年销售额：{business_data.get('annual_sales', 0)} {currency_symbol}
入驻平台：{platforms_str}

【相关法规检索结果】
{regulation_context}

【输出格式 - 严格JSON数组】
{JSON_TEMPLATE}

【重要约束】
- 只输出规则引擎未覆盖的潜在风险
- 如果没有发现额外风险，输出空数组 []
- 风险等级只能是"低风险"（AI识别的为潜在风险，确定性风险由规则引擎处理）
- 所有风险必须与{config.country_name}税务合规相关
""".strip()


def detect_additional_risks(business: AuditRequest) -> list[RiskItem]:
    """使用RAG + AI识别规则引擎遗漏的潜在风险（兼容旧版单国家）"""
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
