"""
外部LLM API适配器 - 支持火山引擎Claude / OpenAI 兼容接口

使用示例配置说明：
1. 火山引擎(VolcEngine) Ark平台访问Anthropic Claude:
   - base_url: https://ark.cn-beijing.volces.com/api/v3
   - model: ep-20250101000000-xxxxx/claude-3-5-sonnet-20241022
   - 在火山引擎控制台创建推理接入点获取
"""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, AsyncOpenAI

from tax_compliance_radar.config import settings


def _client() -> OpenAI:
    """创建OpenAI兼容客户端"""
    return OpenAI(
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
    )


def _async_client() -> AsyncOpenAI:
    """创建异步OpenAI兼容客户端"""
    return AsyncOpenAI(
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
    )


# 默认超时时间（秒）
DEFAULT_TIMEOUT = 30


def _generate(model: str, system: str, user: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """调用外部LLM生成内容

    Args:
        model: 模型名称（火山引擎为推理接入点ID/模型名）
        system: 系统提示词
        user: 用户提示词
        timeout: 请求超时时间（秒）

    Returns:
        生成的文本内容
    """
    response = _client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=settings.llm.generation_temperature,
        max_tokens=settings.llm.generation_num_predict,
        response_format={"type": "json_object"},
        timeout=timeout,
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM 返回空内容")
    return content


async def _agenerate(model: str, system: str, user: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """异步调用外部LLM生成内容

    Args:
        model: 模型名称
        system: 系统提示词
        user: 用户提示词
        timeout: 请求超时时间（秒）
    """
    response = await _async_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=settings.llm.generation_temperature,
        max_tokens=settings.llm.generation_num_predict,
        response_format={"type": "json_object"},
        timeout=timeout,
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM 返回空内容")
    return content


def _chat_with_fallback(system: str, user: str) -> tuple[str, str]:
    """调用LLM带降级策略

    优先使用主模型，失败后尝试备选模型
    """
    candidates = (settings.llm.model, *settings.llm.fallback_models)
    last_error: Exception | None = None
    for model in candidates:
        try:
            return model, _generate(model, system, user)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"外部LLM调用失败: {last_error}") from last_error


async def _achat_with_fallback(system: str, user: str) -> tuple[str, str]:
    """异步调用LLM带降级策略"""
    candidates = (settings.llm.model, *settings.llm.fallback_models)
    last_error: Exception | None = None
    for model in candidates:
        try:
            return model, await _agenerate(model, system, user)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"外部LLM异步调用失败: {last_error}") from last_error
