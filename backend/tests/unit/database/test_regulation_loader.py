from __future__ import annotations

from pathlib import Path

from tax_compliance_radar.database.regulation_loader import chunk_text, parse_regulation_file


def test_parse_regulation_file_with_front_matter(tmp_path: Path):
    sample = tmp_path / "sample.md"
    sample.write_text(
        """---
doc_id: test_doc
doc_name: 测试法规
publish_org: Test Org
effective_time: 2026-01-01
original_link: https://example.test/rule
chapter: registration
---

这是用于测试的法规正文。
""",
        encoding="utf-8",
    )

    parsed = parse_regulation_file(sample)

    assert parsed.doc_id == "test_doc"
    assert parsed.doc_name == "测试法规"
    assert parsed.publish_org == "Test Org"
    assert parsed.effective_time == "2026-01-01"
    assert parsed.original_link == "https://example.test/rule"
    assert parsed.chapter == "registration"
    assert "法规正文" in parsed.content


def test_chunk_text_with_overlap():
    text = "A" * 120
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)

    assert len(chunks) == 3
    assert len(chunks[0]) == 50
    assert len(chunks[1]) == 50
    assert len(chunks[2]) == 40
