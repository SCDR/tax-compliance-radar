from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from tax_compliance_radar.config import settings
from tax_compliance_radar.models.schemas import AuditRequest, QAAnswer
from tax_compliance_radar.services.llm_providers import get_llm_provider
from tax_compliance_radar.services.retrieval_service import (
    RetrievalResult,
    build_context_prompt,
    get_source_references,
)


QA_SYSTEM_PROMPT = """
你是专业的泰国VAT合规助手，必须严格遵守以下规则：

【核心原则 - 违反即幻觉，一票否决】
1. 只依据给定的【检索到的相关法规】内容回答，绝对不能编造法规或提供不确定的信息
2. 如果检索结果显示"未检索到相关合规信息"或"暂无相关合规信息"，必须如实告知用户，不能臆测
3. 所有回答必须引用具体法规来源，禁止使用"根据相关法规"等模糊表述
4. 禁止回答与泰国VAT合规无关的问题

【输出结构 - 严格JSON格式，包含以下7个字段】
- regulation_base: 列出引用的具体法规名称及来源（如"泰国VAT注册规则（https://...）"）
- core_rules: 提炼核心合规规则，用简洁清晰的中文表述
- compliance_suggestion: 具体可行的合规建议，至少2-3条
- risk_warning: 不遵守规则的具体风险后果
- operation_guide: 操作指引，分步骤说明
- original_link: 引用法规的原文链接，多个链接用分号分隔
- disclaimer: 固定免责声明文本

【防幻觉机制】
- 任何内容如果在检索法规中不存在，请在对应字段填写"暂无相关信息"
- 如果整体无相关信息，所有字段统一填写"暂无相关合规信息"
- 禁止使用"根据相关规定"、"可能"、"大概"等模糊词汇
""".strip()


AUDIT_ENHANCEMENT_PROMPT = """
你是专业的泰国VAT合规审核官，必须基于提供的业务信息、风险点和检索到的法规内容生成增强型审核报告。

【核心原则 - 必须严格遵守】
1. 专业建议必须基于【检索到的相关法规】内容，并明确标注法规来源
2. 通用建议可以基于合规最佳实践，但不得编造具体法规名称、编号或发布日期
3. 两类建议必须明确区分：专业建议（有来源）、通用建议（无具体法规引用）

【输出格式 - 严格JSON格式】
{{
    "professional_suggestions": [
        "基于《[法规名称]》：[专业建议内容，引用具体法规]"
    ],
    "general_suggestions": [
        "[通用合规建议，不涉及具体法规编号，例如：尽早完成申报、保留完整交易记录等]"
    ],
    "attachment_guide": "需要准备的材料清单和流程指引说明"
}}

【重要约束】
1. professional_suggestions 中的每条建议必须引用检索到的具体法规名称
2. 如果没有检索到相关法规，professional_suggestions 返回空数组
3. general_suggestions 必须是不涉及具体法规编号的通用合规最佳实践
4. professional_suggestions + general_suggestions 总共至少4条建议
5. 语言必须专业、严谨、客观
6. 禁止编造不存在的法规名称、发布日期、章节编号
7. 禁止使用"根据相关规定"等模糊表述
""".strip()


@dataclass(frozen=True)
class LLMResult:
    model: str
    content: str


def _chat_with_fallback(system: str, user: str) -> tuple[str, str]:
    """带降级策略的LLM调用

    使用Provider工厂获取配置指定的LLM后端
    """
    provider = get_llm_provider()
    return provider.chat_with_fallback(system, user)


async def _achat_with_fallback(system: str, user: str) -> tuple[str, str]:
    """异步调用带降级"""
    provider = get_llm_provider()
    return await provider.achat_with_fallback(system, user)


def _extract_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise


def _normalize_text_field(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    return str(value)


def generate_qa_answer_with_rag(
    query_text: str, retrieval_result: RetrievalResult
) -> QAAnswer:
    """基于RAG检索结果生成QA回答"""
    context = build_context_prompt(retrieval_result)

    user_prompt = f"""
用户问题：{query_text}

{context}

请基于以上检索到的法规内容，按照要求的JSON格式回答问题。
如果没有相关法规内容，请如实填写"暂无相关合规信息"。
""".strip()

    _, content = _chat_with_fallback(QA_SYSTEM_PROMPT, user_prompt)
    payload = _extract_json(content)

    for field in [
        "regulation_base",
        "core_rules",
        "compliance_suggestion",
        "risk_warning",
        "operation_guide",
        "original_link",
        "disclaimer",
    ]:
        payload[field] = _normalize_text_field(payload.get(field, "暂无相关信息"))

    if not retrieval_result.below_threshold and retrieval_result.documents:
        sources = get_source_references(retrieval_result)
        if sources:
            payload["regulation_base"] = (
                payload["regulation_base"] + "\n引用来源: " + "; ".join(sources)
            )

    if "disclaimer" not in payload or not payload["disclaimer"]:
        payload["disclaimer"] = "本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。"

    return QAAnswer.model_validate(payload)


def generate_qa_answer(query_text: str) -> QAAnswer:
    """兼容旧接口 - 不推荐使用，请使用 generate_qa_answer_with_rag"""
    system_prompt = (
        "你是泰国VAT合规助手。只能依据给定事实回答，禁止编造法规。"
        "请严格输出JSON，字段为 regulation_base, core_rules, compliance_suggestion,"
        " risk_warning, operation_guide, original_link, disclaimer。"
        "答案必须是中文。"
    )
    user_prompt = f"""
用户问题：{query_text}

请返回符合字段要求的JSON答案。
""".strip()
    _, content = _chat_with_fallback(system_prompt, user_prompt)
    payload = _extract_json(content)
    for field in [
        "regulation_base",
        "core_rules",
        "compliance_suggestion",
        "risk_warning",
        "operation_guide",
        "original_link",
        "disclaimer",
    ]:
        payload[field] = _normalize_text_field(payload.get(field, "暂无相关信息"))
    if "disclaimer" not in payload or not payload["disclaimer"]:
        payload["disclaimer"] = "本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。"
    return QAAnswer.model_validate(payload)


def generate_audit_enhancement(
    business: AuditRequest, risks: list[Any], retrieval_result: Any | None = None
) -> dict[str, Any]:
    """基于业务信息、风险点和RAG检索结果生成增强型审核建议"""
    risk_descriptions = [
        f"{r.risk_level}: {r.risk_desc}" for r in risks
    ]

    # 构建法规上下文
    if retrieval_result and not retrieval_result.below_threshold and retrieval_result.documents:
        regulation_parts = []
        for doc in retrieval_result.documents:
            regulation_parts.append(f"- 《{doc.doc_name}》: {doc.content[:150]}...")
        regulation_context = "\n".join(regulation_parts)
    else:
        regulation_context = "未检索到相关法规，仅提供通用合规建议。"

    user_prompt = f"""
业务信息：
- 目标市场：{business.target_market}
- 业务类型：{business.business_type}
- 年预估销售额：{business.annual_sales:,} 泰铢
- 入驻平台：{', '.join(business.platforms) if business.platforms else '无'}

已识别风险点：
{chr(10).join(risk_descriptions)}

检索到的相关法规：
{regulation_context}

请基于以上信息按照要求的JSON格式生成审核建议。
professional_suggestions 必须引用检索到的具体法规名称。
general_suggestions 提供不涉及具体法规的通用合规最佳实践。
""".strip()

    _, content = _chat_with_fallback(AUDIT_ENHANCEMENT_PROMPT, user_prompt)
    result = _extract_json(content)

    # 向后兼容：合并为 suggestions 字段供现有代码使用
    professional = result.get("professional_suggestions", [])
    general = result.get("general_suggestions", [])
    result["suggestions"] = professional + general

    if not result["suggestions"]:
        result["suggestions"] = [
            "在开展泰国业务前完成VAT注册准备工作",
            "聘请当地税务代理处理月度申报事宜",
            "留存所有平台订单数据和申报凭证至少5年",
            "每季度进行一次合规自查，确保申报数据准确",
        ]

    if "attachment_guide" not in result:
        result["attachment_guide"] = (
            "泰国VAT注册材料清单：企业营业执照、法人身份证明、银行账户信息、"
            "注册申请表。注册流程：提交材料 -> 税务审核 -> 获取VAT号"
        )

    return result


def generate_audit_report(business: AuditRequest, risk_summary: dict[str, Any]) -> dict[str, Any]:
    """兼容旧接口 - 不推荐使用"""
    return generate_audit_enhancement(business, risk_summary.get("risks", []))


# embed_text 已移至 embedding_service.py 避免循环导入
