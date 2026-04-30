from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
import ollama  # type: ignore[import-not-found]

from tax_compliance_radar.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PATH,
    DB_PATH,
    REGULATIONS_DIR,
    settings,
)


@dataclass(frozen=True)
class RegulationDoc:
    doc_id: str
    doc_name: str
    publish_org: str
    effective_time: str
    original_link: str
    chapter: str
    content: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_front_matter(raw_text: str) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---\n"):
        return {}, raw_text

    end_idx = raw_text.find("\n---\n", 4)
    if end_idx < 0:
        return {}, raw_text

    block = raw_text[4:end_idx]
    body = raw_text[end_idx + 5 :].strip()
    metadata: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, body


def parse_regulation_file(path: Path) -> RegulationDoc:
    raw_text = path.read_text(encoding="utf-8")
    metadata, body = _parse_front_matter(raw_text)

    doc_id = metadata.get("doc_id") or path.stem
    doc_name = metadata.get("doc_name") or path.stem
    publish_org = metadata.get("publish_org") or "待补充"
    effective_time = metadata.get("effective_time") or "待补充"
    original_link = metadata.get("original_link") or "待补充"
    chapter = metadata.get("chapter") or "general"

    normalized_body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if not normalized_body:
        raise ValueError(f"Empty regulation content: {path.name}")

    return RegulationDoc(
        doc_id=doc_id,
        doc_name=doc_name,
        publish_org=publish_org,
        effective_time=effective_time,
        original_link=original_link,
        chapter=chapter,
        content=normalized_body,
    )


def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - chunk_overlap
    return chunks


def _get_sqlite_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn


def _upsert_document_metadata(doc: RegulationDoc) -> None:
    with _get_sqlite_connection() as conn:
        conn.execute(
            """
            INSERT INTO vat_documents (
                doc_id, doc_name, publish_org, effective_time,
                original_link, upload_time, is_valid
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(doc_id) DO UPDATE SET
                doc_name = excluded.doc_name,
                publish_org = excluded.publish_org,
                effective_time = excluded.effective_time,
                original_link = excluded.original_link,
                upload_time = excluded.upload_time,
                is_valid = 1
            """,
            (
                doc.doc_id,
                doc.doc_name,
                doc.publish_org,
                doc.effective_time,
                doc.original_link,
                _utc_now_iso(),
            ),
        )
        conn.commit()


def _get_collection(reset_collection: bool = False):
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if reset_collection:
        try:
            client.delete_collection(CHROMA_COLLECTION_NAME)
        except Exception:  # noqa: BLE001
            pass

    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={
            "description": "Thailand VAT regulations index",
            "embedding_model": settings.llm.embedding_model,
            "language": "zh",
        },
    )


def _embed_batch(texts: list[str]) -> list[list[float]]:
    client = ollama.Client(host=settings.llm.base_url)
    vectors: list[list[float]] = []
    for text in texts:
        result = client.embeddings(model=settings.llm.embedding_model, prompt=text)
        vectors.append(result["embedding"])
    return vectors


def load_regulations(
    source_dir: Path = REGULATIONS_DIR,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    reset_collection: bool = False,
) -> dict[str, Any]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Regulations directory not found: {source_dir}")

    md_files = sorted(source_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No markdown files in {source_dir}")

    collection = _get_collection(reset_collection=reset_collection)

    total_docs = 0
    total_chunks = 0
    for file_path in md_files:
        doc = parse_regulation_file(file_path)
        _upsert_document_metadata(doc)

        chunks = chunk_text(doc.content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        vectors = _embed_batch(chunks)

        ids = [f"{doc.doc_id}:{idx}" for idx in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc.doc_id,
                "chunk_id": idx,
                "doc_name": doc.doc_name,
                "chapter": doc.chapter,
                "effective_time": doc.effective_time,
                "original_link": doc.original_link,
            }
            for idx in range(len(chunks))
        ]

        collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=chunks,
            metadatas=metadatas,
        )

        total_docs += 1
        total_chunks += len(chunks)

    return {
        "docs": total_docs,
        "chunks": total_chunks,
        "collection": CHROMA_COLLECTION_NAME,
        "source_dir": str(source_dir),
    }
