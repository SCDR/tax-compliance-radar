"""标签抽取器 —— 基于关键词规则，从 QA/审核/上传的文本中提取用户画像标签。

标签使用自然中文短语，直接可读（例如 "泰国"、"增值税"、"跨境电商"、"注册门槛"），
方便前端展示与用户理解。同一含义的多种表达（中英大小写、别名）归一到同一个标签。
"""

from __future__ import annotations

from typing import Iterable

# 关键词 → 标签 的规则表。每条规则：(关键词, 中文标签, 权重增量)
COUNTRY_KEYWORDS: list[tuple[str, str, float]] = [
    ("泰国", "泰国", 1.0),
    ("thailand", "泰国", 1.0),
    ("thai", "泰国", 0.6),
    ("越南", "越南", 1.0),
    ("vietnam", "越南", 1.0),
    ("印尼", "印尼", 1.0),
    ("印度尼西亚", "印尼", 1.0),
    ("indonesia", "印尼", 1.0),
    ("马来西亚", "马来西亚", 1.0),
    ("malaysia", "马来西亚", 1.0),
    ("新加坡", "新加坡", 1.0),
    ("singapore", "新加坡", 1.0),
    ("菲律宾", "菲律宾", 1.0),
    ("philippines", "菲律宾", 1.0),
]

TAX_KEYWORDS: list[tuple[str, str, float]] = [
    ("vat", "增值税", 1.0),
    ("增值税", "增值税", 1.0),
    ("gst", "商品与服务税", 1.0),
    ("商品与服务税", "商品与服务税", 1.0),
    ("sst", "销售与服务税", 1.0),
    ("销售与服务税", "销售与服务税", 1.0),
    ("企业所得税", "企业所得税", 1.0),
    ("所得税", "所得税", 0.7),
    ("预扣税", "预扣税", 1.0),
    ("withholding", "预扣税", 1.0),
    ("关税", "关税", 0.9),
    ("customs duty", "关税", 0.9),
    ("印花税", "印花税", 0.8),
]

TOPIC_KEYWORDS: list[tuple[str, str, float]] = [
    ("注册门槛", "注册门槛", 1.0),
    ("门槛", "注册门槛", 0.5),
    ("registration threshold", "注册门槛", 1.0),
    ("申报", "申报", 0.8),
    ("filing", "申报", 0.8),
    ("电子发票", "电子发票", 1.0),
    ("e-invoice", "电子发票", 1.0),
    ("e-tax invoice", "电子发票", 1.0),
    ("发票", "发票", 0.7),
    ("invoice", "发票", 0.7),
    ("代扣代缴", "代扣代缴", 1.0),
    ("退税", "退税", 0.9),
    ("refund", "退税", 0.9),
    ("处罚", "处罚", 0.7),
    ("罚款", "处罚", 0.8),
    ("penalty", "处罚", 0.7),
    ("跨境", "跨境", 0.6),
    ("cross-border", "跨境", 0.6),
    ("数字服务税", "数字服务税", 1.0),
    ("digital services tax", "数字服务税", 1.0),
    ("低值免税", "低值免税政策", 1.0),
    ("de minimis", "低值免税政策", 1.0),
]

INDUSTRY_KEYWORDS: list[tuple[str, str, float]] = [
    ("跨境电商", "跨境电商", 1.2),
    ("cross-border e-commerce", "跨境电商", 1.2),
    ("cross-border ecommerce", "跨境电商", 1.2),
    ("品牌出海", "品牌出海", 1.2),
    ("brand overseas", "品牌出海", 1.0),
    ("dtc", "品牌出海", 0.8),
    ("外贸综合服务", "外贸综合服务", 1.2),
    ("外贸", "外贸综合服务", 0.6),
    ("零售", "零售", 0.6),
    ("saas", "SaaS", 1.0),
    ("digital service", "数字服务", 1.0),
    ("数字服务", "数字服务", 1.0),
]

CHANNEL_KEYWORDS: list[tuple[str, str, float]] = [
    ("amazon", "亚马逊", 0.9),
    ("亚马逊", "亚马逊", 0.9),
    ("shopee", "Shopee", 0.9),
    ("lazada", "Lazada", 0.9),
    ("tiktok", "TikTok Shop", 0.9),
    ("tokopedia", "Tokopedia", 0.8),
    ("独立站", "独立站", 0.8),
]

ALL_RULES: list[list[tuple[str, str, float]]] = [
    COUNTRY_KEYWORDS,
    TAX_KEYWORDS,
    TOPIC_KEYWORDS,
    INDUSTRY_KEYWORDS,
    CHANNEL_KEYWORDS,
]


def _extract_from_text(text: str) -> dict[str, float]:
    """遍历所有规则，返回 tag → 权重增量。多次命中同一标签累加。"""
    if not text:
        return {}
    lowered = text.lower()
    deltas: dict[str, float] = {}
    for rule_group in ALL_RULES:
        for keyword, tag_key, weight in rule_group:
            key_lower = keyword.lower()
            if not key_lower:
                continue
            occurrences = lowered.count(key_lower)
            if occurrences > 0:
                delta = weight * (1 + 0.3 * (occurrences - 1))
                deltas[tag_key] = deltas.get(tag_key, 0.0) + delta
    return deltas


def _merge(dst: dict[str, float], src: dict[str, float]) -> None:
    for k, v in src.items():
        dst[k] = dst.get(k, 0.0) + v


# 结构化字段国家码 → 中文名 的兜底映射
COUNTRY_CODE_TO_NAME = {
    "TH": "泰国",
    "VN": "越南",
    "ID": "印尼",
    "MY": "马来西亚",
    "SG": "新加坡",
    "PH": "菲律宾",
}


def extract_tags_from_qa(
    query: str,
    answer_text: str | dict | None = None,
    doc_ids: Iterable[str] | None = None,
) -> dict[str, float]:
    """从 QA 提问 + 答案 + 命中的文档名中抽取标签增量。"""
    deltas: dict[str, float] = {}
    _merge(deltas, _extract_from_text(query or ""))
    if isinstance(answer_text, dict):
        answer_str = " ".join(
            str(answer_text.get(k, ""))
            for k in ("core_rules", "compliance_suggestion", "risk_warning", "operation_guide")
        )
        for tag, w in _extract_from_text(answer_str).items():
            deltas[tag] = deltas.get(tag, 0.0) + w * 0.4
    elif isinstance(answer_text, str):
        for tag, w in _extract_from_text(answer_text).items():
            deltas[tag] = deltas.get(tag, 0.0) + w * 0.4
    for doc_id in doc_ids or []:
        for tag, w in _extract_from_text(str(doc_id)).items():
            deltas[tag] = deltas.get(tag, 0.0) + w * 0.3
    return deltas


def extract_tags_from_audit(
    business_info: dict,
    audit_report: dict | None = None,
) -> dict[str, float]:
    """从审计业务信息 + 报告中抽取标签增量。"""
    deltas: dict[str, float] = {}

    business_type = str(business_info.get("business_type") or "")
    if business_type:
        _merge(deltas, _extract_from_text(business_type))

    selected_countries = business_info.get("selected_countries") or []
    if isinstance(selected_countries, list):
        for code in selected_countries:
            if isinstance(code, str) and code:
                name = COUNTRY_CODE_TO_NAME.get(code.upper(), code)
                deltas[name] = deltas.get(name, 0.0) + 1.5

    target_market = business_info.get("target_market")
    if isinstance(target_market, str):
        _merge(deltas, _extract_from_text(target_market))

    annual_sales = business_info.get("annual_sales")
    try:
        annual_sales_num = float(annual_sales) if annual_sales is not None else 0.0
    except (TypeError, ValueError):
        annual_sales_num = 0.0
    if annual_sales_num >= 1_800_000:
        deltas["已达注册门槛"] = deltas.get("已达注册门槛", 0.0) + 1.5
    elif annual_sales_num > 0:
        deltas["未达注册门槛"] = deltas.get("未达注册门槛", 0.0) + 0.8

    import json as _json

    try:
        blob = _json.dumps(business_info, ensure_ascii=False)
    except Exception:
        blob = str(business_info)
    for tag, w in _extract_from_text(blob).items():
        deltas[tag] = deltas.get(tag, 0.0) + w * 0.5

    if audit_report:
        risks_text_parts = []
        for r in audit_report.get("all_risks", []) or []:
            if isinstance(r, dict):
                risks_text_parts.append(str(r.get("description", "")))
                risks_text_parts.append(str(r.get("risk_point", "")))
        for tag, w in _extract_from_text(" ".join(risks_text_parts)).items():
            deltas[tag] = deltas.get(tag, 0.0) + w * 0.3

    return deltas


def extract_tags_from_upload(filename: str, excerpt: str) -> dict[str, float]:
    """从上传文件的文件名 + 内容摘要抽取标签增量。"""
    deltas: dict[str, float] = {}
    _merge(deltas, _extract_from_text(filename or ""))
    _merge(deltas, _extract_from_text(excerpt or ""))
    return deltas
