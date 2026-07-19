from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from tax_compliance_radar.config import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vat_documents (
    doc_id TEXT PRIMARY KEY,
    doc_name TEXT NOT NULL,
    publish_org TEXT NOT NULL,
    effective_time TEXT NOT NULL,
    original_link TEXT NOT NULL,
    upload_time TEXT NOT NULL,
    is_valid INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS qa_history (
    qa_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL DEFAULT 'default',
    query_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    recall_doc_ids TEXT,
    recall_snippets TEXT,
    create_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_history (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL DEFAULT 'default',
    business_info TEXT NOT NULL,
    audit_report TEXT NOT NULL,
    high_risk_count INTEGER NOT NULL DEFAULT 0,
    medium_risk_count INTEGER NOT NULL DEFAULT 0,
    low_risk_count INTEGER NOT NULL DEFAULT 0,
    create_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_config (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    update_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    business_type TEXT,
    description TEXT,
    base_tags TEXT,
    create_time TEXT NOT NULL,
    update_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    tag_key TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'qa',
    first_seen_time TEXT NOT NULL,
    last_touch_time TEXT NOT NULL,
    UNIQUE(profile_id, tag_key)
);

CREATE TABLE IF NOT EXISTS news_items (
    news_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT,
    source TEXT,
    publish_time TEXT NOT NULL,
    tags TEXT NOT NULL,
    original_link TEXT
);

CREATE TABLE IF NOT EXISTS news_pushes (
    push_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    news_id INTEGER NOT NULL,
    match_score REAL NOT NULL DEFAULT 0,
    matched_tags TEXT,
    create_time TEXT NOT NULL,
    dismissed INTEGER NOT NULL DEFAULT 0,
    UNIQUE(profile_id, news_id)
);

CREATE TABLE IF NOT EXISTS user_uploads (
    upload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    size INTEGER NOT NULL DEFAULT 0,
    excerpt TEXT,
    create_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS guide_history (
    guide_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL DEFAULT 'default',
    countries TEXT NOT NULL,
    business_type TEXT,
    input_tags TEXT NOT NULL,
    sections TEXT NOT NULL,
    referenced_docs TEXT NOT NULL,
    include_optional INTEGER NOT NULL DEFAULT 1,
    create_time TEXT NOT NULL
);
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        # 兼容旧库：qa_history 表若缺少 recall_snippets / profile_id 列则补上
        qa_cols = {
            row[1]
            for row in connection.execute("PRAGMA table_info(qa_history)").fetchall()
        }
        if "recall_snippets" not in qa_cols:
            connection.execute("ALTER TABLE qa_history ADD COLUMN recall_snippets TEXT")
        if "recall_positions" not in qa_cols:
            # block 级定位：{filename: [{block_start, block_end}]}
            connection.execute("ALTER TABLE qa_history ADD COLUMN recall_positions TEXT")
        if "profile_id" not in qa_cols:
            connection.execute(
                "ALTER TABLE qa_history ADD COLUMN profile_id TEXT NOT NULL DEFAULT 'default'"
            )
        audit_cols = {
            row[1]
            for row in connection.execute("PRAGMA table_info(audit_history)").fetchall()
        }
        if "profile_id" not in audit_cols:
            connection.execute(
                "ALTER TABLE audit_history ADD COLUMN profile_id TEXT NOT NULL DEFAULT 'default'"
            )
        connection.execute(
            """
            INSERT OR IGNORE INTO system_config (config_key, config_value, update_time)
            VALUES (?, ?, ?)
            """,
            (
                "disclaimer_text",
                "本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。",
                utc_now_iso(),
            ),
        )
        connection.commit()


def insert_qa_history(
    query_text: str,
    answer_text: dict,
    recall_doc_ids: list[str] | None = None,
    recall_snippets: dict[str, list[str]] | None = None,
    profile_id: str = "default",
    create_time: str | None = None,
    recall_positions: dict[str, list[dict]] | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO qa_history (profile_id, query_text, answer_text, recall_doc_ids, recall_snippets, recall_positions, create_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id or "default",
                query_text,
                json.dumps(answer_text, ensure_ascii=False),
                ",".join(recall_doc_ids or []),
                json.dumps(recall_snippets or {}, ensure_ascii=False),
                json.dumps(recall_positions or {}, ensure_ascii=False),
                create_time or utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def insert_audit_history(
    business_info: dict,
    audit_report: dict,
    profile_id: str = "default",
    create_time: str | None = None,
) -> int:
    """保存审核历史记录"""
    all_risks = audit_report.get("all_risks", [])
    high_risk_count = sum(1 for r in all_risks if r.get("risk_level") == "高风险")
    medium_risk_count = sum(1 for r in all_risks if r.get("risk_level") == "中风险")
    low_risk_count = sum(1 for r in all_risks if r.get("risk_level") == "低风险")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO audit_history (
                profile_id, business_info, audit_report, high_risk_count,
                medium_risk_count, low_risk_count, create_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id or "default",
                json.dumps(business_info, ensure_ascii=False),
                json.dumps(audit_report, ensure_ascii=False),
                high_risk_count,
                medium_risk_count,
                low_risk_count,
                create_time or utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


# --------------------------------------------------------------------------- #
# 用户画像 / 标签 / 新闻推送
# --------------------------------------------------------------------------- #


def upsert_profile(
    profile_id: str,
    display_name: str,
    business_type: str | None = None,
    description: str | None = None,
    base_tags: list[str] | None = None,
) -> None:
    """创建或更新一个用户画像（idempotent）"""
    now = utc_now_iso()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_profiles (
                profile_id, display_name, business_type, description,
                base_tags, create_time, update_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET
                display_name = excluded.display_name,
                business_type = excluded.business_type,
                description = excluded.description,
                base_tags = excluded.base_tags,
                update_time = excluded.update_time
            """,
            (
                profile_id,
                display_name,
                business_type,
                description,
                json.dumps(base_tags or [], ensure_ascii=False),
                now,
                now,
            ),
        )
        connection.commit()


def ensure_profile_exists(profile_id: str) -> None:
    """确保 profile 存在，若不存在则以匿名身份创建"""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT profile_id FROM user_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        if row is None:
            now = utc_now_iso()
            connection.execute(
                """
                INSERT INTO user_profiles (
                    profile_id, display_name, business_type, description,
                    base_tags, create_time, update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    f"匿名访客 {profile_id[:6]}",
                    None,
                    "自动创建的访客画像",
                    "[]",
                    now,
                    now,
                ),
            )
            connection.commit()


def list_profiles() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT profile_id, display_name, business_type, description,
                   base_tags, create_time, update_time
            FROM user_profiles
            ORDER BY create_time ASC
            """
        ).fetchall()
    result = []
    for row in rows:
        try:
            base_tags = json.loads(row["base_tags"] or "[]")
        except (json.JSONDecodeError, TypeError):
            base_tags = []
        result.append(
            {
                "profile_id": row["profile_id"],
                "display_name": row["display_name"],
                "business_type": row["business_type"],
                "description": row["description"],
                "base_tags": base_tags,
                "create_time": row["create_time"],
                "update_time": row["update_time"],
            }
        )
    return result


def get_profile(profile_id: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT profile_id, display_name, business_type, description,
                   base_tags, create_time, update_time
            FROM user_profiles WHERE profile_id = ?
            """,
            (profile_id,),
        ).fetchone()
    if row is None:
        return None
    try:
        base_tags = json.loads(row["base_tags"] or "[]")
    except (json.JSONDecodeError, TypeError):
        base_tags = []
    return {
        "profile_id": row["profile_id"],
        "display_name": row["display_name"],
        "business_type": row["business_type"],
        "description": row["description"],
        "base_tags": base_tags,
        "create_time": row["create_time"],
        "update_time": row["update_time"],
    }


def upsert_profile_tags(
    profile_id: str,
    tag_deltas: dict[str, float],
    source: str = "qa",
) -> None:
    """对画像标签做增量更新：已存在的累加 weight，不存在的 insert。"""
    if not tag_deltas:
        return
    now = utc_now_iso()
    with get_connection() as connection:
        for tag_key, delta in tag_deltas.items():
            if not tag_key or delta <= 0:
                continue
            connection.execute(
                """
                INSERT INTO profile_tags (
                    profile_id, tag_key, weight, source,
                    first_seen_time, last_touch_time
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, tag_key) DO UPDATE SET
                    weight = weight + excluded.weight,
                    last_touch_time = excluded.last_touch_time,
                    source = excluded.source
                """,
                (profile_id, tag_key, float(delta), source, now, now),
            )
        connection.commit()


def clear_profile_tags(profile_id: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM profile_tags WHERE profile_id = ?",
            (profile_id,),
        )
        connection.commit()


def list_profile_tags(profile_id: str) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT tag_key, weight, source, first_seen_time, last_touch_time
            FROM profile_tags WHERE profile_id = ?
            ORDER BY weight DESC
            """,
            (profile_id,),
        ).fetchall()
    return [
        {
            "tag_key": row["tag_key"],
            "weight": row["weight"],
            "source": row["source"],
            "first_seen_time": row["first_seen_time"],
            "last_touch_time": row["last_touch_time"],
        }
        for row in rows
    ]


def insert_news_item(
    title: str,
    summary: str,
    body: str,
    source: str,
    publish_time: str,
    tags: list[str],
    original_link: str | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO news_items (
                title, summary, body, source, publish_time, tags, original_link
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                summary,
                body,
                source,
                publish_time,
                json.dumps(tags, ensure_ascii=False),
                original_link,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_news_items() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT news_id, title, summary, body, source, publish_time, tags, original_link
            FROM news_items ORDER BY publish_time DESC
            """
        ).fetchall()
    return [_row_to_news(row) for row in rows]


def get_news_item(news_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT news_id, title, summary, body, source, publish_time, tags, original_link
            FROM news_items WHERE news_id = ?
            """,
            (news_id,),
        ).fetchone()
    return _row_to_news(row) if row else None


def _row_to_news(row) -> dict:
    try:
        tags = json.loads(row["tags"] or "[]")
    except (json.JSONDecodeError, TypeError):
        tags = []
    return {
        "news_id": row["news_id"],
        "title": row["title"],
        "summary": row["summary"],
        "body": row["body"],
        "source": row["source"],
        "publish_time": row["publish_time"],
        "tags": tags,
        "original_link": row["original_link"],
    }


def dedupe_news_pushes() -> int:
    """清理 news_pushes 表中的历史重复记录（早期版本 UNIQUE 约束未建立时可能产生）。
    对同一 (profile_id, news_id) 只保留 push_id 最小的一条，返回删除数量。
    """
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM news_pushes
            WHERE push_id NOT IN (
                SELECT MIN(push_id)
                FROM news_pushes
                GROUP BY profile_id, news_id
            )
            """
        )
        connection.commit()
        return cursor.rowcount or 0


def dedupe_news_items() -> int:
    """按 (title, publish_time) 去重 news_items，保留 news_id 最小的一条。
    同时把关联的 news_pushes 迁移到保留的那条 news_id 上，最后清理重复。
    返回删除的重复新闻条数。
    """
    with get_connection() as connection:
        # 找到每个 (title, publish_time) 分组下保留的 news_id
        rows = connection.execute(
            """
            SELECT MIN(news_id) AS keep_id, GROUP_CONCAT(news_id) AS all_ids
            FROM news_items
            GROUP BY title, publish_time
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        removed = 0
        for row in rows:
            keep_id = row["keep_id"]
            all_ids = [int(x) for x in (row["all_ids"] or "").split(",") if x.strip()]
            dup_ids = [i for i in all_ids if i != keep_id]
            if not dup_ids:
                continue
            placeholders = ",".join("?" for _ in dup_ids)
            # 将旧 news_id 上的 push 记录改指到保留的 news_id（若已存在同 (profile,news) 则忽略）
            connection.execute(
                f"UPDATE OR IGNORE news_pushes SET news_id = ? WHERE news_id IN ({placeholders})",
                (keep_id, *dup_ids),
            )
            # 未能迁移的（因 UNIQUE 冲突）直接删掉
            connection.execute(
                f"DELETE FROM news_pushes WHERE news_id IN ({placeholders})",
                dup_ids,
            )
            # 删除重复的 news_items
            cursor = connection.execute(
                f"DELETE FROM news_items WHERE news_id IN ({placeholders})",
                dup_ids,
            )
            removed += cursor.rowcount or 0
        connection.commit()
        return removed


def clear_all_news() -> tuple[int, int]:
    """清空整个新闻库及其所有推送记录，返回 (删除的新闻数, 删除的推送数)。"""
    with get_connection() as connection:
        push_cursor = connection.execute("DELETE FROM news_pushes")
        news_cursor = connection.execute("DELETE FROM news_items")
        connection.commit()
        return (news_cursor.rowcount or 0, push_cursor.rowcount or 0)


def news_count() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS n FROM news_items").fetchone()
    return int(row["n"] or 0)


def profile_count() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS n FROM user_profiles").fetchone()
    return int(row["n"] or 0)


def insert_news_push(
    profile_id: str,
    news_id: int,
    match_score: float,
    matched_tags: list[str],
) -> int | None:
    """插入推送记录，若 (profile_id, news_id) 已存在则忽略并返回 None。"""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO news_pushes (
                profile_id, news_id, match_score, matched_tags,
                create_time, dismissed
            ) VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                profile_id,
                news_id,
                float(match_score),
                json.dumps(matched_tags, ensure_ascii=False),
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid) if cursor.lastrowid else None


def list_news_pushes(profile_id: str, limit: int = 20, include_dismissed: bool = False) -> list[dict]:
    query = """
        SELECT p.push_id, p.news_id, p.match_score, p.matched_tags,
               p.create_time, p.dismissed,
               n.title, n.summary, n.source, n.publish_time, n.tags, n.original_link
        FROM news_pushes p
        JOIN news_items n ON n.news_id = p.news_id
        WHERE p.profile_id = ?
    """
    params: list = [profile_id]
    if not include_dismissed:
        query += " AND p.dismissed = 0"
    # 稍多拉取，为 news_id 去重预留空间（防御旧数据 UNIQUE 约束建立前的重复）
    query += " ORDER BY p.create_time DESC LIMIT ?"
    params.append(max(limit * 2, limit + 10))
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    result = []
    seen_news_ids: set[int] = set()
    for row in rows:
        news_id = row["news_id"]
        if news_id in seen_news_ids:
            continue
        seen_news_ids.add(news_id)
        try:
            matched_tags = json.loads(row["matched_tags"] or "[]")
        except (json.JSONDecodeError, TypeError):
            matched_tags = []
        try:
            news_tags = json.loads(row["tags"] or "[]")
        except (json.JSONDecodeError, TypeError):
            news_tags = []
        result.append(
            {
                "push_id": row["push_id"],
                "news_id": news_id,
                "title": row["title"],
                "summary": row["summary"],
                "source": row["source"],
                "publish_time": row["publish_time"],
                "tags": news_tags,
                "original_link": row["original_link"],
                "match_score": row["match_score"],
                "matched_tags": matched_tags,
                "create_time": row["create_time"],
                "dismissed": bool(row["dismissed"]),
            }
        )
        if len(result) >= limit:
            break
    return result


def dismiss_push(push_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            "UPDATE news_pushes SET dismissed = 1 WHERE push_id = ?",
            (push_id,),
        )
        connection.commit()


def clear_news_pushes(profile_id: str) -> int:
    """删除该 profile 名下所有 news_pushes 记录，返回被删除的行数。调试用。"""
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM news_pushes WHERE profile_id = ?",
            (profile_id,),
        )
        connection.commit()
        return cursor.rowcount or 0




def insert_user_upload(profile_id: str, filename: str, size: int, excerpt: str) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO user_uploads (profile_id, filename, size, excerpt, create_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (profile_id, filename, size, excerpt, utc_now_iso()),
        )
        connection.commit()
        return int(cursor.lastrowid)


def insert_guide_history(
    profile_id: str,
    countries: list[str],
    business_type: str | None,
    input_tags: list[str],
    sections: dict,
    referenced_docs: list[str],
    include_optional: bool = True,
    create_time: str | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO guide_history (
                profile_id, countries, business_type, input_tags,
                sections, referenced_docs, include_optional, create_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id or "default",
                json.dumps(countries or [], ensure_ascii=False),
                business_type,
                json.dumps(input_tags or [], ensure_ascii=False),
                json.dumps(sections or {}, ensure_ascii=False),
                json.dumps(referenced_docs or [], ensure_ascii=False),
                1 if include_optional else 0,
                create_time or utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_guide_history(profile_id: str, limit: int = 20) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT guide_id, countries, business_type, input_tags,
                   referenced_docs, include_optional, create_time
            FROM guide_history WHERE profile_id = ?
            ORDER BY create_time DESC LIMIT ?
            """,
            (profile_id or "default", limit),
        ).fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "guide_id": row["guide_id"],
                "countries": json.loads(row["countries"] or "[]"),
                "business_type": row["business_type"],
                "input_tags": json.loads(row["input_tags"] or "[]"),
                "referenced_docs": json.loads(row["referenced_docs"] or "[]"),
                "include_optional": bool(row["include_optional"]),
                "create_time": row["create_time"],
            }
        )
    return result


def get_guide_history(guide_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT guide_id, profile_id, countries, business_type, input_tags,
                   sections, referenced_docs, include_optional, create_time
            FROM guide_history WHERE guide_id = ?
            """,
            (guide_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "guide_id": row["guide_id"],
        "profile_id": row["profile_id"],
        "countries": json.loads(row["countries"] or "[]"),
        "business_type": row["business_type"],
        "input_tags": json.loads(row["input_tags"] or "[]"),
        "sections": json.loads(row["sections"] or "{}"),
        "referenced_docs": json.loads(row["referenced_docs"] or "[]"),
        "include_optional": bool(row["include_optional"]),
        "create_time": row["create_time"],
    }


def list_user_uploads(profile_id: str) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT upload_id, filename, size, excerpt, create_time
            FROM user_uploads WHERE profile_id = ?
            ORDER BY create_time DESC
            """,
            (profile_id,),
        ).fetchall()
    return [
        {
            "upload_id": row["upload_id"],
            "filename": row["filename"],
            "size": row["size"],
            "excerpt": row["excerpt"],
            "create_time": row["create_time"],
        }
        for row in rows
    ]
