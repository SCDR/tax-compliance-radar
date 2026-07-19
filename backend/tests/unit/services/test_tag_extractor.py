from __future__ import annotations

from tax_compliance_radar.services.tag_extractor import (
    extract_tags_from_audit,
    extract_tags_from_qa,
    extract_tags_from_upload,
)


def test_qa_extract_country_and_tax_tags():
    deltas = extract_tags_from_qa("泰国 VAT 注册门槛是多少？", None, [])
    assert deltas.get("泰国", 0) > 0
    assert deltas.get("增值税", 0) > 0
    assert deltas.get("注册门槛", 0) > 0


def test_qa_answer_contributes_smaller_weight():
    only_query = extract_tags_from_qa("跨境电商问题", None, [])
    with_answer = extract_tags_from_qa(
        "跨境电商问题",
        {"core_rules": "越南 VAT 电子发票", "compliance_suggestion": ""},
        [],
    )
    assert "越南" in with_answer
    assert with_answer["越南"] < 1.0  # 答案的贡献被打了 0.4 折
    assert only_query.get("跨境电商", 0) > 0


def test_qa_multi_hit_accumulates():
    single = extract_tags_from_qa("泰国 VAT", None, [])
    triple = extract_tags_from_qa("泰国 VAT 泰国 VAT 泰国 VAT", None, [])
    assert triple["泰国"] > single["泰国"]


def test_audit_structured_fields():
    business = {
        "business_type": "跨境电商零售",
        "selected_countries": ["TH", "VN"],
        "annual_sales": 2_500_000,
        "extra": "使用 Shopee 平台，需要开电子发票",
    }
    deltas = extract_tags_from_audit(business, {})
    assert deltas.get("泰国", 0) >= 1.5
    assert deltas.get("越南", 0) >= 1.5
    assert deltas.get("跨境电商", 0) > 0
    assert deltas.get("已达注册门槛", 0) > 0
    assert deltas.get("Shopee", 0) > 0
    assert deltas.get("电子发票", 0) > 0


def test_upload_extraction():
    deltas = extract_tags_from_upload(
        "invoice_thai_vat.pdf",
        "This document describes the Thailand VAT filing requirements.",
    )
    assert deltas.get("泰国", 0) > 0
    assert deltas.get("增值税", 0) > 0
    assert deltas.get("申报", 0) > 0


def test_empty_inputs_return_empty():
    assert extract_tags_from_qa("", None, []) == {}
    assert extract_tags_from_upload("", "") == {}
