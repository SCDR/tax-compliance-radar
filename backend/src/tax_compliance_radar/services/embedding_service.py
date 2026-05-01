"""Embedding服务 - 支持独立配置和多后端

使用策略模式，支持与LLM不同的后端配置
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type, Dict

from tax_compliance_radar.config import settings


class EmbeddingProvider(ABC):
    """Embedding提供者抽象基类"""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """生成文本Embedding向量

        Args:
            text: 输入文本

        Returns:
            Embedding向量列表
        """
        raise NotImplementedError


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama本地Embedding提供者"""

    def __init__(self) -> None:
        import ollama  # type: ignore[import-not-found]

        self._client = ollama.Client(host=settings.embedding.base_url)
        self.model = settings.embedding.model

    def embed(self, text: str) -> list[float]:
        """生成文本Embedding向量"""
        response = self._client.embeddings(model=self.model, prompt=text)
        return response["embedding"]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """OpenAI兼容接口Embedding提供者

    支持火山引擎、OpenAI、智谱AI等兼容OpenAI Embedding接口的服务
    """

    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            api_key=settings.embedding.api_key,
            base_url=settings.embedding.base_url,
        )
        self.model = settings.embedding.model
        self.dimensions = settings.embedding.dimensions

    def embed(self, text: str) -> list[float]:
        """生成文本Embedding向量"""
        response = self._client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
        )
        return response.data[0].embedding


class EmbeddingProviderFactory:
    """Embedding Provider工厂类"""

    _providers: Dict[str, Type[EmbeddingProvider]] = {}

    @classmethod
    def register(cls, source_type: str, provider_class: Type[EmbeddingProvider]) -> None:
        """注册新的Embedding Provider类型"""
        cls._providers[source_type] = provider_class

    @classmethod
    def create(cls, source_type: str | None = None) -> EmbeddingProvider:
        """创建Embedding Provider实例"""
        use_source = source_type or settings.embedding.source

        if use_source not in cls._providers:
            raise ValueError(
                f"不支持的Embedding Provider类型: {use_source}, "
                f"支持的类型: {list(cls._providers.keys())}"
            )

        provider_class = cls._providers[use_source]
        return provider_class()


# 注册内置Provider
EmbeddingProviderFactory.register("ollama", OllamaEmbeddingProvider)
EmbeddingProviderFactory.register("volcengine", OpenAICompatibleEmbeddingProvider)
EmbeddingProviderFactory.register("openai", OpenAICompatibleEmbeddingProvider)


# 全局Provider实例（懒加载）
_provider_instance: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """获取Embedding Provider实例（单例）"""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = EmbeddingProviderFactory.create()
    return _provider_instance


def embed_text(text: str) -> list[float]:
    """生成文本Embedding向量

    这是对外的便捷函数，内部使用配置指定的Provider

    Args:
        text: 输入文本

    Returns:
        Embedding向量列表
    """
    provider = get_embedding_provider()
    return provider.embed(text)
