"""LLM Providers 模块

使用策略模式实现的多LLM后端支持

使用示例:
    from tax_compliance_radar.services.llm_providers import get_llm_provider

    provider = get_llm_provider()
    model, content = provider.chat_with_fallback(system_prompt, user_prompt)

扩展新Provider:
    1. 继承 LLMProvider 基类
    2. 实现 generate 和 agenerate 方法
    3. 使用 LLMProviderFactory.register() 注册
"""
from .base import LLMProvider
from .factory import LLMProviderFactory, get_llm_provider
from .ollama_provider import OllamaProvider
from .openai_compatible_provider import OpenAICompatibleProvider

__all__ = [
    "LLMProvider",
    "LLMProviderFactory",
    "get_llm_provider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
]
