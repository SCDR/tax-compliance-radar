"""Ollama 本地LLM提供者 - 具体策略实现"""
from __future__ import annotations

import ollama  # type: ignore[import-not-found]

from tax_compliance_radar.config import settings
from tax_compliance_radar.services.llm_providers.base import LLMProvider
from tax_compliance_radar.services.logger import log_llm_call


class OllamaProvider(LLMProvider):
    """Ollama本地LLM提供者

    使用本地运行的Ollama服务提供LLM能力
    支持qwen3, llama3.2等本地模型
    """

    def __init__(self) -> None:
        self.base_url = settings.llm.base_url
        self.default_model = settings.llm.model
        self.temperature = settings.llm.generation_temperature
        self.max_tokens = settings.llm.generation_num_predict
        self.format = settings.llm.generation_format

    def _get_client(self) -> ollama.Client:
        """获取同步客户端"""
        return ollama.Client(host=self.base_url)

    def _get_async_client(self) -> ollama.AsyncClient:
        """获取异步客户端"""
        return ollama.AsyncClient(host=self.base_url)

    @log_llm_call
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> str:
        """同步生成文本

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model: 可选，覆盖默认模型

        Returns:
            生成的文本内容
        """
        use_model = model or self.default_model
        response = self._get_client().generate(
            model=use_model,
            prompt=f"{system_prompt}\n\n{user_prompt}",
            format=self.format,
            options={
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        )
        return response["response"]

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
        use_model = model or self.default_model
        response = await self._get_async_client().generate(
            model=use_model,
            prompt=f"{system_prompt}\n\n{user_prompt}",
            format=self.format,
            options={
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        )
        return response["response"]
