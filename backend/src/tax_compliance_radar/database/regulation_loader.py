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


def _clean_markdown(text: str) -> str:
    """清理Markdown标记，保留纯文本语义"""
    # 移除标题标记 (#, ##, ###, ...)
    cleaned = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 移除加粗/斜体标记
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
    # 移除列表标记
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
    # 移除行首的空格
    cleaned = re.sub(r"^\s+", "", cleaned, flags=re.MULTILINE)
    # 压缩多余的空行
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def chunk_text(text: str, chunk_size: int | None = None, chunk_overlap: int | None = None) -> list[str]:
    """兼容旧调用：只返回 chunk 文本数组。新逻辑走 chunk_document。"""
    return [c["text"] for c in chunk_document(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)]


def _is_boilerplate_block(block: str) -> bool:
    """判断一个 block 是否是"引用样板"，比如
       `> 关联主文档：[[...]]`、`> 参考：[[...]]`。
    这些内容在 citation 类文档里很常见，把它们纳入 embedding 会把整个 chunk
    拉向"关联文档"语义，检索命中的却不是真正的正文条款。
    索引时跳过，但仍保留在原始 markdown 中，前端渲染依然可见。
    """
    text = block.strip()
    if not text:
        return True
    # 以 > 开头的引用块且包含 wiki 链接或"关联"字样
    if text.startswith(">") and re.search(r"关联|\[\[[^\]]+\]\]", text):
        return True
    return False


def split_blocks(body: str) -> list[str]:
    """按空行把 markdown 正文切成 block 数组（保留原始 markdown 标记）。
    这个切分**必须与前端完全一致** —— 前端 RegulationModal 会以同样的 `/\n{2,}/` 切分并给每个 block
    挂 `data-block="N"` 属性，检索命中时靠 block 索引精准定位，不再依赖字符串模糊匹配。
    """
    return [b.strip() for b in re.split(r"\n{2,}", body) if b.strip()]


def chunk_document(
    body: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict[str, Any]]:
    """按 block 聚合成 chunk，每个 chunk 记录首个 block 的索引 —— 用于原文精准定位。

    返回：[{ "text": 用于 embedding 的清洗后文本, "block_start": 首块索引, "block_end": 末块索引 }]
    - chunk_size 用于控制单个 chunk 的最大字符数（近似上限，单块超长时不硬切）
    - chunk_overlap 用非负字符数控制两 chunk 之间的 block 级重叠
    """
    chunk_size = chunk_size if chunk_size is not None else settings.rag.chunk_size
    chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.rag.chunk_overlap
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    blocks = split_blocks(body)
    if not blocks:
        return []

    # 为 embedding 准备清洗后的 block 文本（剥掉 markdown 标记，语义更纯）
    # 样板 block（`> 关联主文档：[[...]]` 等）在此清空，避免拉偏 embedding；
    # 位置索引仍占位，保证前端 data-block 与后端 block_start 完全对齐。
    clean_blocks = [
        "" if _is_boilerplate_block(b) else _clean_markdown(b) for b in blocks
    ]

    chunks: list[dict[str, Any]] = []
    n = len(blocks)
    i = 0
    while i < n:
        start_idx = i
        current: list[str] = []
        size = 0
        while i < n:
            piece = clean_blocks[i]
            if not piece:
                i += 1
                continue
            # 至少收一个 block；后续 block 加入若会超过 chunk_size 就停
            if current and size + len(piece) + 2 > chunk_size:
                break
            current.append(piece)
            size += len(piece) + 2
            i += 1
        if not current:
            # 全空 block 尾部保护
            break
        end_idx = i - 1
        chunks.append(
            {
                "text": "\n\n".join(current).strip(),
                "block_start": start_idx,
                "block_end": end_idx,
            }
        )

        # overlap：从末尾往回回退若干 block，作为下一 chunk 起点
        if i >= n:
            break
        overlap_chars = 0
        j = end_idx
        while j > start_idx and overlap_chars < chunk_overlap:
            overlap_chars += len(clean_blocks[j])
            j -= 1
        # 至少推进 1 个 block，避免死循环
        i = max(j + 1, start_idx + 1)

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
            "description": settings.chroma_meta.description,
            "embedding_model": settings.embedding.model,
            "language": settings.chroma_meta.language,
            "hnsw:space": settings.chroma_meta.similarity_space,
        },
    )


def _embed_batch(texts: list[str]) -> list[list[float]]:
    client = ollama.Client(host=settings.embedding.base_url)
    vectors: list[list[float]] = []
    for text in texts:
        result = client.embeddings(model=settings.embedding.model, prompt=text)
        vectors.append(result["embedding"])
    return vectors


def load_regulations(
    source_dir: Path = REGULATIONS_DIR,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    reset_collection: bool = False,
) -> dict[str, Any]:
    chunk_size = chunk_size if chunk_size is not None else settings.rag.chunk_size
    chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.rag.chunk_overlap
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

        chunks_meta = chunk_document(doc.content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = [c["text"] for c in chunks_meta]
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
                # block 级定位信息 —— 与前端 split_blocks 保持完全一致
                "block_start": chunks_meta[idx]["block_start"],
                "block_end": chunks_meta[idx]["block_end"],
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
