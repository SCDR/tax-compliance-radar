from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import os

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REGULATIONS_DIR = DATA_DIR / "regulations"
DB_PATH = DATA_DIR / "app.db"
CHROMA_PATH = DATA_DIR / "chroma_db"
CHROMA_COLLECTION_NAME = "thailand_vat_regulations"

DISCLAIMER_TEXT = "本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。"


@dataclass(frozen=True)
class LLMBackendConfig:
    source: str = "ollama"
    model: str = "qwen3:8b"
    base_url: str = "http://localhost:11434"
    fallback_models: tuple[str, ...] = ("llama3.2", "qwen2.5")
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dimensions: int = 1024
    generation_format: Literal["json", ""] = "json"
    generation_temperature: float = 0.1
    generation_num_predict: int = 512
    generation_think: bool = False


@dataclass(frozen=True)
class RetrievalConfig:
    """RAG检索配置"""
    similarity_threshold: float = 0.55
    top_k_results: int = 3


@dataclass(frozen=True)
class RAGConfig:
    """文档分块与向量化配置"""
    chunk_size: int = 512
    chunk_overlap: int = 50


@dataclass(frozen=True)
class RulesConfig:
    """合规规则阈值配置"""
    vat_registration_threshold: int = 1800000
    low_value_goods_threshold: int = 1500


@dataclass(frozen=True)
class ChromaMetadataConfig:
    """Chroma集合元数据配置"""
    description: str = "Thailand VAT regulations index"
    language: str = "zh"
    similarity_space: str = "cosine"


@dataclass(frozen=True)
class Settings:
    api_prefix: str = "/api/v1"
    app_name: str = "Tax Compliance Radar"
    environment: str = os.getenv("TCR_ENV", "development")
    llm: LLMBackendConfig = field(default_factory=LLMBackendConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    chroma_meta: ChromaMetadataConfig = field(default_factory=ChromaMetadataConfig)
    disclaimer_text: str = DISCLAIMER_TEXT


settings = Settings()
