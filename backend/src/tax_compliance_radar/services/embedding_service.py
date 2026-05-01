"""Embedding服务 - 独立模块避免循环导入"""
from __future__ import annotations

import ollama  # type: ignore[import-not-found]

from tax_compliance_radar.config import settings


def _client() -> ollama.Client:
    return ollama.Client(host=settings.llm.base_url)


def embed_text(text: str) -> list[float]:
    """生成文本Embedding向量"""
    response = _client().embeddings(model=settings.llm.embedding_model, prompt=text)
    return response["embedding"]
