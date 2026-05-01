"""OpenAI兼容接口提供者 - 支持火山引擎Claude、OpenAI、智谱AI等

具体支持平台：
1. 火山引擎Ark（Claude系列）: base_url = https://ark.cn-beijing.volces.com/api/v3
2. OpenAI官方: base_url = https://api.openai.com/v1
3. 智谱AI: base_url = https://open.bigmodel.cn/api/paas/v4
4. DeepSeek: base_url = https://api.deepseek.com/v1
5. 通义千问: base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
"""
from __future__ import annotations

from typing import Any

from openai import OpenAI, AsyncOpenAI

from tax_compliance_radar.config import settings
from tax_compliance_radar.services.llm_providers.base import LLMProvider
from tax_compliance_radar.services.logger import log_llm_call


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI兼容接口提供者

    支持所有兼容OpenAI API格式的LLM服务
    """

    def __init__(self) -> None:
        self.api_key = settings.llm.api_key
        self.base_url = settings.llm.base_url
        self.default_model = settings.llm.model
        self.temperature = settings.llm.generation_temperature
        self.max_tokens = settings.llm.generation_num_predict
        self.reasoning_effort = settings.llm.reasoning_effort

    def _get_client(self) -> OpenAI:
        """获取同步客户端"""
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _get_async_client(self) -> AsyncOpenAI:
        """获取异步客户端"""
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

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

        extra_options: dict[str, Any] = {}
        if self.reasoning_effort:
            extra_options["reasoning_effort"] = self.reasoning_effort

        response = self._get_client().chat.completions.create(
            model=use_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
            **extra_options,
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("LLM 返回空内容")
        return content

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

        extra_options: dict[str, Any] = {}
        if self.reasoning_effort:
            extra_options["reasoning_effort"] = self.reasoning_effort

        response = await self._get_async_client().chat.completions.create(
            model=use_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
            **extra_options,
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("LLM 返回空内容")
        return content
