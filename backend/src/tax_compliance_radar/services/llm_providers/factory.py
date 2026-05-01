"""LLM Provider 工厂类

根据配置自动创建对应的LLM Provider实例
遵循工厂模式，解耦创建和使用
"""
from __future__ import annotations

from typing import Dict, Type

from tax_compliance_radar.config import settings
from tax_compliance_radar.services.llm_providers.base import LLMProvider


class LLMProviderFactory:
    """LLM Provider工厂

    负责根据配置创建对应的LLM Provider实例
    支持动态注册新Provider
    """

    _providers: Dict[str, Type[LLMProvider]] = {}

    @classmethod
    def register(cls, source_type: str, provider_class: Type[LLMProvider]) -> None:
        """注册新的LLM Provider类型

        Args:
            source_type: Provider类型标识（如 "ollama", "volcengine"）
            provider_class: Provider实现类
        """
        cls._providers[source_type] = provider_class

    @classmethod
    def create(cls, source_type: str | None = None) -> LLMProvider:
        """创建LLM Provider实例

        Args:
            source_type: 可选，指定Provider类型，默认使用配置中的值

        Returns:
            LLM Provider实例

        Raises:
            ValueError: 不支持的Provider类型
        """
        use_source = source_type or settings.llm.source

        if use_source not in cls._providers:
            raise ValueError(
                f"不支持的LLM Provider类型: {use_source}, "
                f"支持的类型: {list(cls._providers.keys())}"
            )

        provider_class = cls._providers[use_source]
        return provider_class()


# 注册内置Provider
from tax_compliance_radar.services.llm_providers.ollama_provider import OllamaProvider
from tax_compliance_radar.services.llm_providers.openai_compatible_provider import (
    OpenAICompatibleProvider,
)

LLMProviderFactory.register("ollama", OllamaProvider)
LLMProviderFactory.register("volcengine", OpenAICompatibleProvider)
LLMProviderFactory.register("openai", OpenAICompatibleProvider)


# 便捷函数：获取默认LLM Provider
def get_llm_provider() -> LLMProvider:
    """获取配置指定的LLM Provider实例

    Returns:
        LLM Provider实例
    """
    return LLMProviderFactory.create()
