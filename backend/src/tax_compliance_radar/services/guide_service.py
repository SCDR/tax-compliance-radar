"""合规指南（模块四）服务层。

以画像标签 + 用户勾选/自由输入 + 锁定国家/业务类型为输入，按四板块
（资金合规 / 税务 / 知识产权 / 贸易与海关）分块检索法规，交给 LLM
生成结构化的自检清单（sources 强制来自证据集），最后附 2 张附录。
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from json_repair import repair_json

from tax_compliance_radar.api.regulations_router import _resolve_filename
from tax_compliance_radar.services.db import (
    insert_guide_history,
    list_profile_tags,
)
from tax_compliance_radar.services.llm_providers import get_llm_provider
from tax_compliance_radar.services.llm_service import (
    GUIDE_APPENDIX_PROMPT,
    GUIDE_SYSTEM_PROMPT,
)
from tax_compliance_radar.services.retrieval_service import (
    RetrievedDoc,
    search_regulations,
)
from tax_compliance_radar.services.tag_extractor import (
    CHANNEL_KEYWORDS,
    COUNTRY_KEYWORDS,
    INDUSTRY_KEYWORDS,
    TAX_KEYWORDS,
    TOPIC_KEYWORDS,
)


# ----------------------------------------------------------------------------
# 常量：四板块 & 关键词
# ----------------------------------------------------------------------------

COUNTRY_CN = {
    "TH": "泰国",
    "ID": "印尼",
    "MY": "马来西亚",
    "VN": "越南",
    "SG": "新加坡",
    "PH": "菲律宾",
    "CN": "中国",
}

SECTIONS: list[dict[str, Any]] = [
    {
        "key": "funds",
        "title": "资金合规",
        "keywords": [
            "外汇管制", "跨境汇款", "结汇", "支付牌照", "反洗钱",
            "利润汇出", "股息汇出", "资金池", "预扣税",
        ],
    },
    {
        "key": "tax",
        "title": "税务",
        "keywords": [
            "VAT", "GST", "增值税", "注册门槛", "申报周期",
            "代扣代缴", "转让定价", "e-invoice", "电子发票",
            "所得税", "预扣税",
        ],
    },
    {
        "key": "ip",
        "title": "知识产权",
        "keywords": [
            "商标", "版权", "著作权", "专利", "马德里协定",
            "撤三", "平台品牌备案", "海关知识产权保护",
        ],
    },
    {
        "key": "trade",
        "title": "贸易与海关",
        "keywords": [
            "进出口许可", "HS编码", "原产地", "关税", "清关",
            "CIQ", "CE认证", "CCC认证", "低值免税",
        ],
    },
]


def _tag_library() -> dict[str, list[str]]:
    """把 tag_extractor 里的五组词表暴露为可选的"标签库"（去重、保留中文标签）。"""

    def _uniq_labels(rules: list[tuple[str, str, float]]) -> list[str]:
        seen: list[str] = []
        for _, label, _ in rules:
            if label not in seen:
                seen.append(label)
        return seen

    return {
        "country": _uniq_labels(COUNTRY_KEYWORDS),
        "tax": _uniq_labels(TAX_KEYWORDS),
        "topic": _uniq_labels(TOPIC_KEYWORDS),
        "industry": _uniq_labels(INDUSTRY_KEYWORDS),
        "channel": _uniq_labels(CHANNEL_KEYWORDS),
    }


def get_tag_library() -> dict[str, list[str]]:
    """路由层可调用：返回预置标签库分组。"""
    return _tag_library()


def get_profile_top_tags(profile_id: str, limit: int = 12) -> list[dict[str, Any]]:
    """从 profile_tags 拉取该画像 TopN 权重标签。"""
    tags = list_profile_tags(profile_id)
    return [
        {"tag_key": t["tag_key"], "weight": round(float(t["weight"]), 3)}
        for t in tags[:limit]
    ]


# ----------------------------------------------------------------------------
# 检索：每板块按 country×业务×板块关键词×用户标签 拼查询，多轮 search_regulations
# ----------------------------------------------------------------------------


def _build_queries(
    countries: list[str],
    business_type: str | None,
    tags: list[str],
    section_keywords: list[str],
) -> list[str]:
    """构造该板块的检索 query 列表。尽可能覆盖全部板块关键词与用户标签,让 LLM 拿到最广的证据面。"""
    countries_cn = [COUNTRY_CN.get(c, c) for c in countries] or ["泰国", "印尼", "马来西亚", "越南"]
    bt = business_type or "跨境电商"
    tag_str = "、".join(tags[:8]) if tags else ""

    queries: list[str] = []
    kws = section_keywords or [""]
    # 每国家 × 每个板块关键词各一条 query,不再截断到 top3
    for country in countries_cn:
        for kw in kws:
            q = f"{country} {bt} {kw} {tag_str}".strip()
            queries.append(q)
    # 追加"国家 × 单个用户标签"轮次,让用户强关注点能拉出对应法规
    for country in countries_cn:
        for tag in tags[:6]:
            queries.append(f"{country} {bt} {tag}".strip())
    return queries


def _collect_evidence(
    countries: list[str],
    business_type: str | None,
    tags: list[str],
    section: dict[str, Any],
    top_k: int = 8,
) -> list[RetrievedDoc]:
    """对该板块跑多轮检索，按 doc_id 去重后返回证据文档列表。"""
    seen: dict[str, RetrievedDoc] = {}
    for query in _build_queries(countries, business_type, tags, section["keywords"]):
        result = search_regulations(query, top_k=top_k)
        if result.below_threshold or not result.documents:
            continue
        for doc in result.documents:
            # 相似度较高者胜出
            existing = seen.get(doc.doc_id)
            if existing is None or doc.similarity_score > existing.similarity_score:
                seen[doc.doc_id] = doc
    return list(seen.values())


def _format_evidence_for_llm(evidence: list[RetrievedDoc]) -> str:
    if not evidence:
        return "【本板块证据集为空】未检索到相关法规，请返回 items: [] 。"
    parts = ["\n【本板块检索到的相关法规（证据集）】\n"]
    for idx, doc in enumerate(evidence, 1):
        parts.append(f"\n--- 证据 {idx} ---")
        parts.append(f"doc_id: {doc.doc_id}")
        parts.append(f"doc_name: {doc.doc_name}")
        parts.append(f"chapter: {doc.chapter}")
        parts.append(f"content:\n{doc.content}\n")
    return "\n".join(parts)


# ----------------------------------------------------------------------------
# SSE 事件生成
# ----------------------------------------------------------------------------


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _repair(json_text: str) -> dict:
    try:
        return json.loads(json_text)
    except Exception:
        try:
            return json.loads(repair_json(json_text))
        except Exception:
            return {}


async def stream_guide(
    countries: list[str],
    business_type: str | None,
    tags: list[str],
    include_optional: bool,
    profile_id: str = "default",
) -> AsyncGenerator[str, None]:
    """SSE 主流：progress -> result_section×4 -> result_section(appendix_timeline/glossary) -> complete。"""
    try:
        # 1. 标签归一化：profile TopN + 用户输入 合并
        profile_tags = [t["tag_key"] for t in get_profile_top_tags(profile_id, limit=10)]
        merged_tags: list[str] = []
        for tg in [*profile_tags, *tags]:
            if tg and tg not in merged_tags:
                merged_tags.append(tg)

        yield _sse(
            "progress",
            {"stage": "retrieving", "message": "正在按四板块检索法规...", "percent": 5},
        )

        provider = get_llm_provider()

        all_sections: list[dict] = []
        all_doc_ids: list[str] = []
        seq_prefix_map = {"funds": 1, "tax": 2, "ip": 3, "trade": 4}

        for i, section in enumerate(SECTIONS):
            section_key = section["key"]
            section_title = section["title"]
            percent_base = 10 + i * 20

            yield _sse(
                "progress",
                {
                    "stage": f"section_start:{section_key}",
                    "message": f"开始生成 {section_title} 事项...",
                    "percent": percent_base,
                },
            )

            # 检索证据
            evidence = _collect_evidence(countries, business_type, merged_tags, section)
            for doc in evidence:
                if doc.doc_id not in all_doc_ids:
                    all_doc_ids.append(doc.doc_id)

            # 若无证据 → 直接空 items
            if not evidence:
                section_payload = {
                    "key": section_key,
                    "title": section_title,
                    "items": [],
                }
                all_sections.append(section_payload)
                yield _sse(
                    "result_section",
                    {"section": section_key, "value": section_payload},
                )
                yield _sse(
                    "progress",
                    {
                        "stage": "section_complete",
                        "section": section_key,
                        "message": f"{section_title} 无匹配法规，跳过",
                        "percent": percent_base + 15,
                    },
                )
                continue

            # 组装 LLM 用户提示词
            evidence_text = _format_evidence_for_llm(evidence)
            countries_display = "、".join(COUNTRY_CN.get(c, c) for c in countries)
            tags_display = "、".join(merged_tags) if merged_tags else "（无）"
            optional_hint = (
                "本次请填写 cost_hint 与 operation_hint（有据则填、无据留空）。"
                if include_optional
                else "本次 include_optional=false，cost_hint 与 operation_hint 必须一律留空。"
            )
            seq_prefix = seq_prefix_map[section_key]

            user_prompt = f"""
【任务】为「{section_title}」板块生成合规自检清单事项。

【锁定上下文】
- 目标国家：{countries_display}
- 业务类型：{business_type or "跨境电商"}
- 用户画像 + 关注标签：{tags_display}
- 板块关键词：{"、".join(section['keywords'])}

【序号规则】
每个 item 的 `seq` 使用 "{seq_prefix}.1"、"{seq_prefix}.2"、"{seq_prefix}.3" 递增。

【成本与实务指引】
{optional_hint}

{evidence_text}

请严格按 GUIDE_SYSTEM_PROMPT 指定的 JSON schema 输出，key = "{section_key}"，title = "{section_title}"。
""".strip()

            # 调 LLM 生成该板块
            try:
                _, stream = await provider.astream_with_fallback(
                    GUIDE_SYSTEM_PROMPT, user_prompt, reasoning_effort="minimal"
                )
                full_json = ""
                async for token in stream:
                    full_json += token
                parsed = _repair(full_json)
            except Exception as gen_error:  # noqa: BLE001
                parsed = {}
                print(f"[guide_service] section {section_key} generation failed: {gen_error}")

            # 结构化清洗
            items = parsed.get("items") or []
            cleaned_items: list[dict] = []
            valid_doc_names = {d.doc_name for d in evidence}
            valid_doc_ids = {d.doc_id for d in evidence}
            for idx, item in enumerate(items, 1):
                if not isinstance(item, dict):
                    continue
                sources_raw = item.get("sources") or []
                sources: list[dict] = []
                for s in sources_raw:
                    if not isinstance(s, dict):
                        continue
                    doc_name = str(s.get("doc_name") or "").strip()
                    doc_id = str(s.get("doc_id") or "").strip()
                    if doc_name in valid_doc_names or doc_id in valid_doc_ids:
                        sources.append(
                            {
                                "doc_id": doc_id,
                                "doc_name": doc_name,
                                "filename": _resolve_filename(doc_name) or doc_name,
                                "snippet": str(s.get("snippet") or "")[:200],
                            }
                        )
                # 必须至少 1 条有效来源，否则丢弃这条事项
                if not sources:
                    continue
                priority = item.get("priority")
                try:
                    priority = max(1, min(3, int(priority)))
                except (TypeError, ValueError):
                    priority = 2
                cleaned_items.append(
                    {
                        "seq": str(item.get("seq") or f"{seq_prefix}.{idx}"),
                        "title": str(item.get("title") or "")[:32],
                        "requirement": str(item.get("requirement") or ""),
                        "legal_basis": str(item.get("legal_basis") or ""),
                        "priority": priority,
                        "explanation": str(item.get("explanation") or ""),
                        "advice_and_risk": str(item.get("advice_and_risk") or ""),
                        "cost_hint": str(item.get("cost_hint") or "") if include_optional else "",
                        "operation_hint": str(item.get("operation_hint") or "") if include_optional else "",
                        "sources": sources,
                    }
                )

            section_payload = {
                "key": section_key,
                "title": section_title,
                "items": cleaned_items,
            }
            all_sections.append(section_payload)

            yield _sse(
                "result_section",
                {"section": section_key, "value": section_payload},
            )
            yield _sse(
                "progress",
                {
                    "stage": "section_complete",
                    "section": section_key,
                    "message": f"{section_title} 已生成 {len(cleaned_items)} 条事项",
                    "percent": percent_base + 18,
                },
            )
            await asyncio.sleep(0.05)

        # 附录
        yield _sse(
            "progress",
            {"stage": "appendix", "message": "正在生成附录（时间节点/术语速查）...", "percent": 92},
        )

        appendix_timeline: list[dict] = []
        appendix_glossary: list[dict] = []
        try:
            appendix_input = {
                "sections": [
                    {
                        "key": s["key"],
                        "title": s["title"],
                        "items": [
                            {
                                "title": it["title"],
                                "requirement": it["requirement"],
                                "legal_basis": it["legal_basis"],
                            }
                            for it in s["items"]
                        ],
                    }
                    for s in all_sections
                ]
            }
            _, content = await provider.achat_with_fallback(
                GUIDE_APPENDIX_PROMPT,
                f"清单如下：\n{json.dumps(appendix_input, ensure_ascii=False)}\n请生成 appendix_timeline 与 appendix_glossary。",
            )
            appendix_parsed = _repair(content)
            appendix_timeline = [
                {
                    "item": str(x.get("item") or ""),
                    "deadline": str(x.get("deadline") or ""),
                    "note": str(x.get("note") or ""),
                }
                for x in (appendix_parsed.get("appendix_timeline") or [])
                if isinstance(x, dict)
            ]
            appendix_glossary = [
                {
                    "abbr": str(x.get("abbr") or ""),
                    "full": str(x.get("full") or ""),
                    "cn": str(x.get("cn") or ""),
                }
                for x in (appendix_parsed.get("appendix_glossary") or [])
                if isinstance(x, dict)
            ]
        except Exception as ax_error:  # noqa: BLE001
            print(f"[guide_service] appendix failed: {ax_error}")

        yield _sse(
            "result_section",
            {"section": "appendix_timeline", "value": appendix_timeline},
        )
        yield _sse(
            "result_section",
            {"section": "appendix_glossary", "value": appendix_glossary},
        )

        # 落库
        guide_payload = {
            "sections": all_sections,
            "appendix_timeline": appendix_timeline,
            "appendix_glossary": appendix_glossary,
            "input": {
                "countries": countries,
                "business_type": business_type,
                "tags": merged_tags,
                "include_optional": include_optional,
            },
        }
        try:
            guide_id = insert_guide_history(
                profile_id=profile_id,
                countries=countries,
                business_type=business_type,
                input_tags=merged_tags,
                sections=guide_payload,
                referenced_docs=all_doc_ids,
                include_optional=include_optional,
            )
        except Exception as save_error:  # noqa: BLE001
            print(f"[guide_service] insert_guide_history failed: {save_error}")
            guide_id = None

        yield _sse(
            "complete",
            {
                "guide_id": guide_id,
                "referenced_docs": all_doc_ids,
                "tags_used": merged_tags,
            },
        )

    except Exception as e:  # noqa: BLE001
        yield _sse("error", {"message": str(e)})
