"""RAG检索服务 - 余弦相似度检索，来源追踪"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chromadb

from tax_compliance_radar.config import CHROMA_COLLECTION_NAME, CHROMA_PATH, settings
from tax_compliance_radar.services.embedding_service import embed_text
from tax_compliance_radar.services.logger import log_retrieval_call

SIMILARITY_THRESHOLD = settings.retrieval.similarity_threshold
TOP_K_RESULTS = settings.retrieval.top_k_results


@dataclass(frozen=True)
class RetrievedDoc:
    doc_id: str
    doc_name: str
    content: str
    similarity_score: float
    original_link: str
    chapter: str


@dataclass(frozen=True)
class RetrievalResult:
    success: bool
    message: str
    documents: list[RetrievedDoc]
    below_threshold: bool


def _get_chroma_collection() -> Any:
    """获取ChromaDB集合连接"""
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        return client.get_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        return None


@log_retrieval_call
def search_regulations(query_text: str, top_k: int = TOP_K_RESULTS) -> RetrievalResult:
    """
    搜索法规并执行边界条件:
    1. 空查询 → 返回错误
    2. 所有相似度低于阈值 → 返回"暂无相关合规信息"
    3. 有效结果 → 返回带来源的上下文
    """
    if not query_text or not query_text.strip():
        return RetrievalResult(
            success=False,
            message="查询文本不能为空",
            documents=[],
            below_threshold=False,
        )

    collection = _get_chroma_collection()
    if collection is None:
        return RetrievalResult(
            success=True,
            message="法规库正在初始化，请稍后再试",
            documents=[],
            below_threshold=True,
        )

    query_embedding = embed_text(query_text)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"] or not results["documents"][0]:
        return RetrievalResult(
            success=True,
            message="未检索到相关合规信息",
            documents=[],
            below_threshold=True,
        )

    retrieved = []
    distances = results["distances"][0]

    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], distances
    ):
        # 余弦相似度：Chroma返回 1 - cosine_similarity 作为 distance
        # 所以 cosine_similarity = 1 - distance
        similarity = 1.0 - dist
        if similarity >= SIMILARITY_THRESHOLD:
            retrieved.append(
                RetrievedDoc(
                    doc_id=meta.get("doc_id", "unknown"),
                    doc_name=meta.get("doc_name", "未知文档"),
                    content=doc,
                    similarity_score=round(similarity, 4),
                    original_link=meta.get("original_link", ""),
                    chapter=meta.get("chapter", ""),
                )
            )

    all_below_threshold = len(retrieved) == 0 and len(distances) > 0

    if all_below_threshold:
        return RetrievalResult(
            success=True,
            message="暂无相关合规信息",
            documents=[],
            below_threshold=True,
        )

    return RetrievalResult(
        success=True,
        message=f"检索到 {len(retrieved)} 条相关法规",
        documents=retrieved,
        below_threshold=False,
    )


def build_context_prompt(result: RetrievalResult) -> str:
    """构建给LLM的上下文提示"""
    if result.below_threshold:
        return """
重要提示：当前未检索到与问题相关的合规法规信息。
请明确告知用户："暂无相关合规信息"，切勿编造答案或提供不确定的内容。
"""

    if not result.documents:
        return """
重要提示：法规库中暂无内容。请明确告知用户："当前系统正在更新法规数据，请稍后再试"。
"""

    context_parts = ["\n【检索到的相关法规】\n"]
    for idx, doc in enumerate(result.documents, 1):
        context_parts.append(f"\n--- 法规 {idx} ---")
        context_parts.append(f"文件名称: {doc.doc_name}")
        context_parts.append(f"文件ID: {doc.doc_id}")
        context_parts.append(f"相似度: {doc.similarity_score}")
        context_parts.append(f"原文链接: {doc.original_link}")
        context_parts.append(f"内容摘要:\n{doc.content}\n")

    return "\n".join(context_parts)


def get_source_references(result: RetrievalResult) -> list[str]:
    """提取来源引用列表"""
    if result.below_threshold or not result.documents:
        return []
    return [f"{doc.doc_name} ({doc.original_link})" for doc in result.documents]
