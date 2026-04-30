from __future__ import annotations

from dataclasses import dataclass

import pytest

from tax_compliance_radar.models.schemas import AuditRequest
from tax_compliance_radar.services import llm_service


@dataclass
class FakeGenerateClient:
    response: str

    def generate(self, **kwargs):
        self.kwargs = kwargs
        return {"response": self.response}

    def embeddings(self, **kwargs):
        self.embed_kwargs = kwargs
        return {"embedding": [0.1, 0.2, 0.3]}


@pytest.fixture()
def fake_client(monkeypatch):
    client = FakeGenerateClient(
        response=(
            '{"regulation_base":"泰国VAT注册规则","core_rules":"第一笔交易前需注册",'
            '"compliance_suggestion":"先注册","risk_warning":"未注册有风险",'
            '"operation_guide":"准备材料","original_link":"https://example.com"}'
        )
    )
    monkeypatch.setattr(llm_service, "_client", lambda: client)
    return client


def test_generate_qa_answer_uses_json_payload(fake_client, test_settings, monkeypatch):
    monkeypatch.setattr(llm_service, "settings", test_settings)

    result = llm_service.generate_qa_answer("泰国VAT注册门槛是什么？")

    assert result.regulation_base == "泰国VAT注册规则"
    assert result.core_rules == "第一笔交易前需注册"
    assert fake_client.kwargs["model"] == "llama3.2"
    assert fake_client.kwargs["format"] == "json"
    assert fake_client.kwargs["options"]["num_predict"] == 128


def test_generate_audit_report_uses_test_settings(monkeypatch, test_settings):
    client = FakeGenerateClient(
        response=(
            '{"vat_register_assessment":"需注册","register_deadline":"开展业务前",'
            '"main_risks":[{"risk_level":"高风险","risk_desc":"需注册",'
            '"trigger_condition":"开展泰国业务","regulation_base":"泰国VAT规则",'
            '"violation_consequence":"可能罚款"}],'
            '"suggestions":["立即注册"],"attachment_guide":"准备材料"}'
        )
    )
    monkeypatch.setattr(llm_service, "_client", lambda: client)
    monkeypatch.setattr(llm_service, "settings", test_settings)

    payload = llm_service.generate_audit_report(
        AuditRequest(
            target_market="泰国",
            business_type="跨境电商零售",
            annual_sales=5000000,
            platforms=["Shopee"],
        ),
        {"high_risk": 1},
    )

    assert payload["vat_register_assessment"] == "需注册"
    assert payload["main_risks"][0]["risk_level"] == "高风险"
    assert client.kwargs["model"] == "llama3.2"


def test_embed_text_uses_test_client(monkeypatch, test_settings):
    client = FakeGenerateClient(response="{}")
    monkeypatch.setattr(llm_service, "_client", lambda: client)
    monkeypatch.setattr(llm_service, "settings", test_settings)

    vector = llm_service.embed_text("hello")

    assert vector == [0.1, 0.2, 0.3]
    assert client.embed_kwargs["model"] == "qwen3-embedding:0.6b"
