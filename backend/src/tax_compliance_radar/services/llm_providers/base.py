"""LLM Provider 抽象基类 - 策略模式"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple


class LLMProvider(ABC):
    """LLM提供者抽象基类

    所有具体的LLM后端实现都需要继承此类并实现抽象方法
    遵循策略模式，便于切换不同LLM提供商
    """

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
        """同步生成文本

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model: 可选，覆盖默认模型

        Returns:
            生成的文本内容
        """
        raise NotImplementedError

    @abstractmethod
    async def agenerate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> str:
        """异步生成文本

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model: 可选，覆盖默认模型

        Returns:
            生成的文本内容
        """
        raise NotImplementedError

    def chat_with_fallback(self, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
        """带降级策略的同步调用

        优先使用主模型，失败后依次尝试备选模型

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            (使用的模型名, 生成的文本内容)
        """
        from tax_compliance_radar.config import settings

        candidates = (settings.llm.model, *settings.llm.fallback_models)
        last_error: Exception | None = None
        for model in candidates:
            try:
                return model, self.generate(system_prompt, user_prompt, model)
            except Exception as exc:
                last_error = exc
        provider_name = self.__class__.__name__
        raise RuntimeError(f"{provider_name} 调用失败: {last_error}") from last_error

    async def achat_with_fallback(self, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
        """带降级策略的异步调用

        优先使用主模型，失败后依次尝试备选模型

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            (使用的模型名, 生成的文本内容)
        """
        from tax_compliance_radar.config import settings

        candidates = (settings.llm.model, *settings.llm.fallback_models)
        last_error: Exception | None = None
        for model in candidates:
            try:
                return model, await self.agenerate(system_prompt, user_prompt, model)
            except Exception as exc:
                last_error = exc
        provider_name = self.__class__.__name__
        raise RuntimeError(f"{provider_name} 异步调用失败: {last_error}") from last_error
