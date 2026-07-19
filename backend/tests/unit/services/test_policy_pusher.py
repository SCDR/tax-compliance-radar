from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tax_compliance_radar.services import db as db_module
from tax_compliance_radar.services import policy_pusher


@pytest.fixture()
def isolated_db(monkeypatch):
    """把 DB_PATH 换成临时文件，确保测试彼此隔离。"""
    tmp = Path(tempfile.mkdtemp()) / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", tmp)
    real_get_connection = db_module.get_connection.__wrapped__ if hasattr(db_module.get_connection, "__wrapped__") else db_module.get_connection

    def _get_connection(db_path=None):
        return real_get_connection(tmp)

    monkeypatch.setattr(db_module, "get_connection", _get_connection)
    # policy_pusher / seed_profiles_news 等模块在 import 时也捕获了 get_connection 引用，
    # 保险起见也 patch 它们的引用
    from tax_compliance_radar.services import policy_pusher as pp_mod
    # pp_mod 只调用 db.xxx，不直接引用 get_connection
    db_module.initialize_database(tmp)
    yield tmp
    if tmp.exists():
        tmp.unlink()


def _iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _seed_news(tags_and_days: list[tuple[list[str], float]]) -> list[int]:
    ids = []
    for i, (tags, days_ago) in enumerate(tags_and_days):
        ids.append(
            db_module.insert_news_item(
                title=f"news-{i}",
                summary="summary",
                body="body",
                source="test",
                publish_time=_iso(days_ago),
                tags=tags,
                original_link=None,
            )
        )
    return ids


def test_effective_weight_decays_with_time(isolated_db, monkeypatch):
    db_module.upsert_profile("p1", "test", "cross", None, [])
    db_module.upsert_profile_tags("p1", {"泰国": 2.0}, source="qa")

    # 手动改 last_touch_time 到 30 天前
    thirty_days_ago = _iso(30)
    with db_module.get_connection() as conn:
        conn.execute(
            "UPDATE profile_tags SET last_touch_time=?, first_seen_time=? WHERE profile_id='p1'",
            (thirty_days_ago, thirty_days_ago),
        )
        conn.commit()

    tags = policy_pusher.compute_effective_tags("p1")
    assert len(tags) == 1
    t = tags[0]
    # exp(-30/30) ≈ 0.368
    assert 0.6 < t["effective_weight"] < 0.85
    assert t["active"]


def test_stale_tag_becomes_inactive(isolated_db):
    db_module.upsert_profile("p1", "test", "x", None, [])
    db_module.upsert_profile_tags("p1", {"泰国": 1.0}, source="qa")
    with db_module.get_connection() as conn:
        conn.execute(
            "UPDATE profile_tags SET last_touch_time=?, first_seen_time=? WHERE profile_id='p1'",
            (_iso(180), _iso(180)),
        )
        conn.commit()
    tags = policy_pusher.compute_effective_tags("p1")
    assert not tags[0]["active"]


def test_match_and_push_dedup(isolated_db):
    db_module.upsert_profile("p1", "test", "x", None, [])
    db_module.upsert_profile_tags(
        "p1",
        {"泰国": 3.0, "增值税": 2.0},
        source="qa",
    )
    _seed_news([
        (["泰国", "增值税"], 5),
        (["越南"], 3),  # 不匹配
        (["泰国", "申报"], 40),  # 匹配 1 个 + 中等新鲜度
    ])

    matches = policy_pusher.match_news_for_profile("p1", top_k=5)
    assert len(matches) == 2
    assert matches[0]["matched_tags"] == ["泰国", "增值税"]

    inserted = policy_pusher.push_news_to_profile("p1", top_k=5)
    assert len(inserted) == 2

    inserted_again = policy_pusher.push_news_to_profile("p1", top_k=5)
    assert inserted_again == []


def test_no_active_tags_no_push(isolated_db):
    db_module.upsert_profile("p1", "test", "x", None, [])
    _seed_news([(["泰国"], 2)])
    matches = policy_pusher.match_news_for_profile("p1")
    assert matches == []
    inserted = policy_pusher.push_news_to_profile("p1")
    assert inserted == []


def test_news_freshness_decay(isolated_db):
    db_module.upsert_profile("p1", "test", "x", None, [])
    db_module.upsert_profile_tags("p1", {"泰国": 5.0}, source="seed")
    ids = _seed_news([
        (["泰国"], 5),    # 新鲜度 1.0
        (["泰国"], 60),   # 新鲜度 0.6
        (["泰国"], 200),  # 新鲜度 0.3
    ])
    matches = policy_pusher.match_news_for_profile("p1", top_k=5)
    match_ids = [m["news_id"] for m in matches]
    assert match_ids == ids


def test_editorial_fallback_for_blank_profile(isolated_db):
    # 空白画像：无 profile_tags
    db_module.upsert_profile("newbie", "test", "x", None, [])
    ids = _seed_news([
        (["编辑精选", "泰国"], 3),
        (["越南"], 10),               # 非编辑精选，不应命中
        (["编辑精选", "印尼"], 40),   # 编辑精选但年代稍久
    ])
    matches = policy_pusher.match_news_for_profile("newbie", top_k=5)
    # 只应返回带"编辑精选"标签的两条，按新鲜度倒序
    match_ids = [m["news_id"] for m in matches]
    assert match_ids == [ids[0], ids[2]]
    assert all("编辑精选" in m["matched_tags"] for m in matches)


def test_editorial_fallback_when_no_tag_match(isolated_db):
    # 有标签但没匹配上任何新闻 → 兜底到编辑精选
    db_module.upsert_profile("p1", "test", "x", None, [])
    db_module.upsert_profile_tags("p1", {"未匹配主题": 3.0}, source="seed")
    _seed_news([
        (["编辑精选", "泰国"], 5),
        (["越南"], 3),
    ])
    matches = policy_pusher.match_news_for_profile("p1", top_k=5)
    assert len(matches) == 1
    assert matches[0]["matched_tags"] == ["编辑精选"]
