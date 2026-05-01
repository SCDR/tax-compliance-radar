"""LLM 增强建议生成器
基于风险点和检索到的法规生成专业合规建议
"""
from __future__ import annotations

from typing import List, Dict, Any

from tax_compliance_radar.models.schemas import SourcedRiskItem, SourcedSuggestion, SourceInfo
from tax_compliance_radar.services.llm_service import _chat_with_fallback, _extract_json
from tax_compliance_radar.services.retrieval_service import search_regulations
from tax_compliance_radar.registry import CountryRegistry


# 字段友好名称映射（与 ai_risk_detector.py 保持一致）
_FIELD_FRIENDLY_NAMES = {
    "business_type": "业务类型",
    "annual_sales": "年销售额",
    "platforms": "入驻平台",
    "product_categories": "商品类目",
    "monthly_orders": "月订单量",
    "warehousing_mode": "仓储模式",
    "has_local_entity": "本地公司主体",
    "employee_count": "员工数量",
}

# 特殊格式处理的字段
_SPECIAL_FORMAT_FIELDS = {
    "annual_sales",  # 需要加货币符号
}


def get_suggestion_prompt_template(country_code: str) -> str:
    """获取指定国家的建议生成提示词"""
    config = CountryRegistry.get(country_code)
    return f"""
你是{config.country_name}合规专家。基于以下风险点和相关法规，生成具体的合规建议。

【输出格式 - 严格JSON】
{{
    "professional_suggestions": [
        {{
            "content": "基于《[法规名称]》的专业建议内容",
            "regulation_reference": "引用的法规名称或编号"
        }}
    ],
    "general_suggestions": [
        "通用合规最佳实践建议，不涉及具体法规编号"
    ]
}}

【要求】
1. professional_suggestions 必须基于检索到的法规内容，每条都要有明确的法规引用
2. general_suggestions 是通用的最佳实践，不涉及具体法规
3. professional_suggestions + general_suggestions 总共至少4条
4. 语言必须专业、严谨、客观
5. 所有建议必须针对{config.country_name}的税务环境
""".strip()


async def generate_enhanced_suggestions_async(
    country_code: str,
    risks: List[SourcedRiskItem],
    business_data: Dict[str, Any],
) -> List[SourcedSuggestion]:
    """异步版本：基于风险点和RAG检索生成增强建议

    Args:
        country_code: 国家代码
        risks: 风险列表
        business_data: 业务数据

    Returns:
        带来源标签的建议列表
    """
    config = CountryRegistry.get(country_code)

    # 基于风险点检索相关法规
    risk_descriptions = " ".join([r.risk_desc for r in risks[:3]])
    query = f"{config.country_name} {config.tax_type} {business_data.get('business_type', '')} {risk_descriptions} 合规建议"
    retrieval_result = search_regulations(query, top_k=3)

    # 构建法规上下文
    if retrieval_result.below_threshold or not retrieval_result.documents:
        regulation_context = "无相关法规检索结果，仅生成通用建议"
    else:
        context_parts = []
        for doc in retrieval_result.documents:
            context_parts.append(f"- 《{doc.doc_name}》: {doc.content[:200]}...")
        regulation_context = "\n".join(context_parts)

    # 构建风险描述
    risk_summary = "\n".join([f"- {r.risk_level}: {r.risk_desc}" for r in risks])

    # ===== 自动格式化所有业务维度（无需硬编码）=====
    business_info_lines = []
    for key, value in business_data.items():
        # 跳过空值
        if value is None or value == "" or value == []:
            continue

        # 获取友好名称
        friendly_name = _FIELD_FRIENDLY_NAMES.get(key, key)

        # 特殊格式处理
        if key in _SPECIAL_FORMAT_FIELDS:
            if key == "annual_sales":
                display_value = f"{value:,} {config.currency_symbol}"
            else:
                display_value = str(value)
        elif isinstance(value, list):
            display_value = ", ".join(str(v) for v in value) or "无"
        elif isinstance(value, bool):
            display_value = "是" if value else "否"
        else:
            display_value = str(value)

        business_info_lines.append(f"{friendly_name}: {display_value}")

    business_info_block = "\n".join(business_info_lines)

    user_prompt = f"""
【业务信息】
{business_info_block}

【已识别风险】
{risk_summary}

【检索到的相关法规】
{regulation_context}

请基于以上信息生成合规建议，特别关注商品类目、仓储模式等特殊场景的合规要求。
"""

    try:
        _, content = _chat_with_fallback(get_suggestion_prompt_template(country_code), user_prompt)
        result = _extract_json(content)

        suggestions = []

        # 专业建议（带来源）
        for idx, s in enumerate(result.get("professional_suggestions", [])):
            suggestions.append(
                SourcedSuggestion(
                    source_info=SourceInfo(
                        country_code=country_code,
                        country_name=config.country_name,
                        source_type="ai_generated",
                    ),
                    suggestion_type="professional",
                    content=s.get("content", ""),
                )
            )

        # 通用建议
        for idx, s in enumerate(result.get("general_suggestions", [])):
            suggestions.append(
                SourcedSuggestion(
                    source_info=SourceInfo(
                        country_code=country_code,
                        country_name=config.country_name,
                        source_type="ai_generated",
                    ),
                    suggestion_type="general",
                    content=s.get("content", s) if isinstance(s, dict) else str(s),
                )
            )

        return suggestions

    except Exception as e:
        print(f"Suggestion generation failed for {country_code}: {e}")
        return []


def generate_enhanced_suggestions(
    country_code: str,
    risks: List[SourcedRiskItem],
    business_data: Dict[str, Any],
) -> List[SourcedSuggestion]:
    """同步版本：基于风险点和RAG检索生成增强建议

    注意：此函数在已有事件循环的上下文中（如FastAPI请求）会跳过LLM增强，
    直接返回空列表。请使用异步版本 aevaluate 进行完整审核。
    """
    # 检测是否已有运行的事件循环（如在FastAPI请求中）
    try:
        import asyncio
        if asyncio.get_running_loop():
            # 已有循环，暂时跳过LLM增强，防止嵌套错误
            return []
    except RuntimeError:
        pass

    # 新建循环执行
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(generate_enhanced_suggestions_async(country_code, risks, business_data))
    finally:
        loop.close()
