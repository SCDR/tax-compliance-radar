from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import ollama  # type: ignore[import-not-found]

from tax_compliance_radar.config import settings
from tax_compliance_radar.models.schemas import AuditRequest, QAAnswer


VAT_KNOWLEDGE_SNIPPETS = """
已知可用法规事实：
1. 外国企业在泰国开展跨境电商业务，无注册门槛，第一笔交易前应完成VAT注册。
2. 2026年1月起，取消1500泰铢低值商品免税政策，跨境商品适用进口关税与7% VAT。
3. Shopee、Lazada、TikTok Shop 等平台交易场景，需要关注平台代收代缴情形下的税务要求。
4. 所有输出必须附带免责声明：本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。
""".strip()


@dataclass(frozen=True)
class LLMResult:
    model: str
    content: str


def _client() -> ollama.Client:
    return ollama.Client(host=settings.llm.base_url)


def _generate(model: str, system: str, user: str) -> str:
    response = _client().generate(
        model=model,
        prompt=f"{system}\n\n{user}",
        format=settings.llm.generation_format,
        options={
            "temperature": settings.llm.generation_temperature,
            "num_predict": settings.llm.generation_num_predict,
        },
    )
    return response["response"]


def _chat_with_fallback(system: str, user: str) -> tuple[str, str]:
    candidates = (settings.llm.model, *settings.llm.fallback_models)
    last_error: Exception | None = None
    for model in candidates:
        try:
            return model, _generate(model, system, user)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(f"Ollama 调用失败: {last_error}") from last_error


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


def generate_qa_answer(query_text: str) -> QAAnswer:
    system_prompt = (
        "你是泰国VAT合规助手。只能依据给定事实回答，禁止编造法规。"
        "请严格输出JSON，字段为 regulation_base, core_rules, compliance_suggestion,"
        " risk_warning, operation_guide, original_link。"
        "答案必须是中文，且包含免责声明要求。"
    )
    user_prompt = f"""
用户问题：{query_text}

参考事实：
{VAT_KNOWLEDGE_SNIPPETS}

请返回符合字段要求的JSON答案。
""".strip()
    _, content = _chat_with_fallback(system_prompt, user_prompt)
    payload = _extract_json(content)
    payload["core_rules"] = _normalize_text_field(payload.get("core_rules", ""))
    payload["regulation_base"] = _normalize_text_field(payload.get("regulation_base", ""))
    payload["compliance_suggestion"] = _normalize_text_field(payload.get("compliance_suggestion", ""))
    payload["risk_warning"] = _normalize_text_field(payload.get("risk_warning", ""))
    payload["operation_guide"] = _normalize_text_field(payload.get("operation_guide", ""))
    payload["original_link"] = _normalize_text_field(payload.get("original_link", ""))
    return QAAnswer.model_validate(payload)


def generate_audit_report(business: AuditRequest, risk_summary: dict[str, Any]) -> dict[str, Any]:
    system_prompt = (
        "你是泰国VAT合规审核助手。只能依据给定事实生成结构化审核报告，禁止编造。"
        "请严格输出JSON，字段为 vat_register_assessment, register_deadline, main_risks, suggestions, attachment_guide。"
        "main_risks 必须是数组，每个元素包含 risk_level, risk_desc, trigger_condition, regulation_base, violation_consequence。"
    )
    user_prompt = f"""
业务信息：{business.model_dump_json(ensure_ascii=False)}
风险摘要：{json.dumps(risk_summary, ensure_ascii=False)}

参考事实：
{VAT_KNOWLEDGE_SNIPPETS}

请返回符合字段要求的JSON报告。
""".strip()
    _, content = _chat_with_fallback(system_prompt, user_prompt)
    return _extract_json(content)


def embed_text(text: str) -> list[float]:
    response = _client().embeddings(model=settings.llm.embedding_model, prompt=text)
    return response["embedding"]
