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
    query_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    recall_doc_ids TEXT,
    create_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_history (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
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


def insert_qa_history(query_text: str, answer_text: dict, recall_doc_ids: list[str] | None = None) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO qa_history (query_text, answer_text, recall_doc_ids, create_time)
            VALUES (?, ?, ?, ?)
            """,
            (
                query_text,
                json.dumps(answer_text, ensure_ascii=False),
                ",".join(recall_doc_ids or []),
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def insert_audit_history(business_info: dict, audit_report: dict) -> int:
    """保存审核历史记录"""
    all_risks = audit_report.get("all_risks", [])
    high_risk_count = sum(1 for r in all_risks if r.get("risk_level") == "高风险")
    medium_risk_count = sum(1 for r in all_risks if r.get("risk_level") == "中风险")
    low_risk_count = sum(1 for r in all_risks if r.get("risk_level") == "低风险")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO audit_history (
                business_info, audit_report, high_risk_count,
                medium_risk_count, low_risk_count, create_time
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                json.dumps(business_info, ensure_ascii=False),
                json.dumps(audit_report, ensure_ascii=False),
                high_risk_count,
                medium_risk_count,
                low_risk_count,
                utc_now_iso(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
