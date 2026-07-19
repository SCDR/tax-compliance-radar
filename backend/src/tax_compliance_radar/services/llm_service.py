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
你是专业的税务合规助手，必须严格遵守以下规则。

【核心原则 —— 违反即幻觉，一票否决】
1. 只依据【检索到的相关法规】里给出的文档回答，绝对不能编造法规、条款号、发布日期或结论。
2. 如果检索结果显示"暂无相关合规信息"，必须如实告知用户，不得臆测。
3. 拒绝回答与税务合规无关的问题。

【回答风格】
1. 用自然、流畅的中文直接回答，不要使用强制结构化格式，读起来像专业顾问的对话。
2. 有针对性，直接回应用户的疑问；避免"根据相关规定"、"可能"、"大概"等模糊词汇。
3. 若同一问题在多份法规里有对应内容，先概括共同结论，再区分差异。

【引用来源规范】
- `regulation_base` 字段专用于列出你引用的法规，**必须、且只能**从【检索到的相关法规】里出现过的 **`文件名称`** 中挑选，逐字复制（例如"泰国VAT注册门槛"、"印尼PMK-131跨境电商"）；不要写文件路径、不要另造名字、不要翻译或改写。
- 多个引用用中文分号 `；` 分隔（前端按 `;/；` 拆分为可点击 tag）。
- 引用应精简：只列真正支撑该回答的 1–3 份主文档；如果同时引用条款文号（如 "PMK-131/2026"、"第 82/1 条"），也需先在【检索到的相关法规】中出现过。
- 若没有可引用的检索结果，`regulation_base` 留空字符串，同时在 `answer` 里如实告知"暂无相关合规信息"。

【输出格式 —— 严格 JSON】
{{
    "answer": "自然语言回答",
    "regulation_base": "引用的 doc_name，用中文分号分隔；无引用时留空",
    "original_link": "",
    "disclaimer": "本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。"
}}
""".strip()


GUIDE_SYSTEM_PROMPT = """
你是专业的跨境电商合规顾问，需要基于用户画像标签与检索到的法规内容，生成一份**可打印的合规自检清单**。

【核心原则 —— 违反即幻觉，一票否决】
1. 只能引用【检索到的相关法规】中出现过的 `doc_name` 与内容片段；绝对不得编造法规名、条款号、发布日期或阈值数字。
2. 如果某板块的证据集为空或不足以支撑任何条目，`items` 返回空数组，不要用"参考通用做法"编造事项。
3. `cost_hint` 与 `operation_hint` 只在证据里出现相关信息时填写；否则一律返回空字符串 ""，绝对不要编造网址、机构名、金额或流程。

【输出结构 —— 严格 JSON，字段一个不能少】
必须完全按照下面的 schema 返回，不要多加字段，不要少字段，不要外层包裹：

{
  "key": "funds|tax|ip|trade",
  "title": "板块中文标题",
  "items": [
    {
      "seq": "1.1",
      "title": "事项简称，8 字以内",
      "requirement": "具体要求：1-3 句，含数字/阈值/时限，语言精炼",
      "legal_basis": "法律依据：法规英文/本地文名 + 条款号（Section/§/条），来自证据集",
      "priority": 3,
      "explanation": "解释：为什么这条事项对该业务重要，2-3 句",
      "advice_and_risk": "合规建议 + 违反风险，2-3 句，先建议后风险",
      "cost_hint": "合规成本参考：金额/费率/工时；无据则留空",
      "operation_hint": "实务操作指引：办理机构/网址/步骤；无据则留空",
      "sources": [
        { "doc_id": "证据集 doc_id 原样", "doc_name": "证据集 doc_name 原样", "snippet": "支撑该事项的原文摘录，30-80 字" }
      ]
    }
  ]
}

【字段规范】
- `seq`：形如 "1.1"、"1.2"，前缀数字由外部指定（在用户提示中告知），你只需按顺序递增；
- `priority`：整数 1-3。3=必办/★★★，2=重要/★★☆，1=可选/★☆☆；
- `title`：短语，不要出现"关于/相关"等冗词；
- `requirement`：像清单里的一条硬性要求，不要复述解释；
- `legal_basis`：优先给出正式法规名与条款号，格式示例 "Revenue Code Section 85/4"、"PDPA Section 28"、"Foreign Business Act B.E. 2542 §5"；不确定条款号可给到法规名；
- `sources.doc_name` 必须逐字来自证据集里的 `doc_name`，不允许翻译或改写；
- 每个事项 sources 至少 1 条、至多 3 条；
- 如果 `include_optional=false`，`cost_hint` 与 `operation_hint` 必须留空。

【板块 items 的数量原则 —— 尽可能全面】
- 只要证据集里出现的法规、条款、时限、阈值、程序等能支撑成事项，就应当独立列为一条。
- 不设人为上限：证据充足时 15、20 条都可以；证据稀薄时可以只有 2-3 条。
- 判断标准是"证据是否支撑"，而不是"数量是否好看"。
- 相似内容合并为一条即可，但不要把不同条款、不同时限、不同责任主体强行揉成一条。
- 每条至少 1 条 sources，且 doc_name 必须来自证据集。
""".strip()


GUIDE_APPENDIX_PROMPT = """
你是专业的跨境电商合规顾问，现在需要为一份合规清单生成两张附录表：**时间节点汇总**、**法律依据速查**。

【严格约束】
1. 只能引用清单里已经出现过的法规名与事项；不要引入新的法规。
2. `deadline` 必须来自证据或事项要求中出现过的日期/周期，绝不编造。
3. `full` 与 `cn` 必须是英文缩写的准确全称与中文释义，如果拿不准，就不要列该缩写。

【输出结构 —— 严格 JSON】
{
  "appendix_timeline": [
    { "item": "事项名（对应清单中的 title）", "deadline": "时间节点，如 每月15日 / 会计年度结束后150天内", "note": "备注" }
  ],
  "appendix_glossary": [
    { "abbr": "PDPA", "full": "Personal Data Protection Act", "cn": "个人数据保护法" }
  ]
}

- `appendix_timeline`：最多 12 行，覆盖清单里最有时限性的事项；无时限事项不要放入；
- `appendix_glossary`：最多 20 行，覆盖清单中出现过的英文缩写；无缩写时返回空数组。
""".strip()


AUDIT_ENHANCEMENT_PROMPT = """
你是专业的税务合规审核官，必须基于提供的业务信息、风险点和检索到的法规内容生成增强型审核报告。

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
如果没有相关法规内容，请如实回答"抱歉，暂未检索到相关的合规信息"。
""".strip()

    _, content = _chat_with_fallback(QA_SYSTEM_PROMPT, user_prompt)
    payload = _extract_json(content)

    # 标准化必选字段
    answer = _normalize_text_field(payload.get("answer", "抱歉，暂未检索到相关的合规信息"))
    payload["regulation_base"] = _normalize_text_field(payload.get("regulation_base", "暂无相关信息"))
    payload["original_link"] = _normalize_text_field(payload.get("original_link", ""))
    payload["disclaimer"] = _normalize_text_field(
        payload.get("disclaimer", "本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。")
    )

    # 在 answer 末尾追加来源引用
    if payload["regulation_base"] and payload["regulation_base"] != "暂无相关信息":
        answer = answer + "\n\n**引用来源：**\n" + payload["regulation_base"]

    # 为向后兼容：answer 放到 core_rules 中（schema 必须字段）
    payload["core_rules"] = answer
    payload["compliance_suggestion"] = ""
    payload["risk_warning"] = ""
    payload["operation_guide"] = ""

    # 追加检索到的来源到 regulation_base
    if not retrieval_result.below_threshold and retrieval_result.documents:
        sources = get_source_references(retrieval_result)
        if sources:
            if payload["regulation_base"] and payload["regulation_base"] != "暂无相关信息":
                payload["regulation_base"] = payload["regulation_base"] + "; " + "; ".join(sources)
            else:
                payload["regulation_base"] = "; ".join(sources)

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
