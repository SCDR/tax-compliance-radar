from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import os

# 加载 .env 环境变量配置
try:
    from dotenv import load_dotenv

    # 从项目根目录加载 .env 文件
    BASE_DIR = Path(__file__).resolve().parents[2]
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # 尝试从当前目录加载
        load_dotenv()
except ImportError:
    # python-dotenv 未安装时静默跳过，使用系统环境变量
    pass

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REGULATIONS_DIR = DATA_DIR / "regulations"
DB_PATH = DATA_DIR / "app.db"
CHROMA_PATH = DATA_DIR / "chroma_db"
CHROMA_COLLECTION_NAME = "thailand_vat_regulations"

DISCLAIMER_TEXT = "本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。"


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding模型独立配置

    支持与LLM模型使用不同的后端和配置
    """
    source: Literal["ollama", "volcengine", "openai"] = "ollama"
    model: str = "qwen3-embedding:0.6b"
    api_key: str = os.getenv("EMBEDDING_API_KEY", os.getenv("LLM_API_KEY", ""))
    base_url: str = os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434")
    dimensions: int = 1024

    # 便捷判断：是否与LLM使用相同后端
    @property
    def same_as_llm(self) -> bool:
        return self.source == settings.llm.source and self.base_url == settings.llm.base_url


@dataclass(frozen=True)
class LLMBackendConfig:
    """LLM生成模型配置"""
    source: Literal["ollama", "volcengine", "openai"] = os.getenv("LLM_SOURCE", "ollama")
    model: str = os.getenv("LLM_MODEL", "qwen3:8b")
    api_key: str = os.getenv("LLM_API_KEY", "")
    base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    # 火山引擎示例: base_url = "https://ark.cn-beijing.volces.com/api/v3"
    # 火山引擎模型示例: "ep-20250101000000-xxxxx/claude-3-5-sonnet-20241022"
    fallback_models: tuple[str, ...] = field(
        default_factory=lambda: tuple(os.getenv("LLM_FALLBACK_MODELS", "llama3.2,qwen2.5").split(","))
    )
    generation_format: Literal["json", ""] = "json"
    generation_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    generation_num_predict: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    generation_think: bool = False
    reasoning_effort: str = os.getenv("LLM_REASONING_EFFORT", "low")


@dataclass(frozen=True)
class RetrievalConfig:
    """RAG检索配置"""
    similarity_threshold: float = 0.5  # 提高阈值，减少不相关的结果，提升速度
    top_k_results: int = 5  # 减少召回数量，显著提升检索和后续生成速度


@dataclass(frozen=True)
class PerformanceConfig:
    """性能控制配置"""
    llm_timeout: int = 30  # LLM调用超时时间（秒）
    enable_ai_risk_detection: bool = False  # 默认关闭AI风险检测，大幅提升速度
    audit_max_retries: int = 1  # 审核流程最大重试次数
    qa_max_retries: int = 1  # 问答流程最大重试次数


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
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)
    chroma_meta: ChromaMetadataConfig = field(default_factory=ChromaMetadataConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    disclaimer_text: str = DISCLAIMER_TEXT
    debug: bool = os.getenv("TCR_ENV", "development") != "production"


settings = Settings()
