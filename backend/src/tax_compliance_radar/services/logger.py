"""
结构化日志服务 - 记录LLM调用、检索、API请求等关键信息

支持：
- LLM调用日志（请求、响应、耗时、token等）
- RAG检索日志
- API请求日志
- 统一的JSON格式输出
"""
from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from tax_compliance_radar.config import settings

# 类型变量用于装饰器
F = TypeVar("F", bound=Callable[..., Any])


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器，输出JSON格式日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加额外的上下文信息
        if hasattr(record, "context"):
            log_entry["context"] = record.context

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(name: str = "tax_compliance_radar") -> logging.Logger:
    """设置并返回结构化日志器

    Args:
        name: 日志器名称

    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # 使用结构化格式化器
    formatter = StructuredFormatter()
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger


# 全局日志器实例
logger = setup_logger()


def log_with_context(level: str, message: str, **context: Any) -> None:
    """带上下文的日志记录

    Args:
        level: 日志级别 (debug, info, warning, error, critical)
        message: 日志消息
        **context: 额外的上下文信息
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    record = logging.LogRecord(
        name=logger.name,
        level=log_level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    if context:
        # 转换非JSON序列化的类型
        def serialize_value(v: Any) -> Any:
            if hasattr(v, "model_dump"):
                return v.model_dump()
            if hasattr(v, "__dict__"):
                return str(v)
            return v

        context = {k: serialize_value(v) for k, v in context.items()}
        record.context = context

    logger.handle(record)


class LLMLogger:
    """LLM调用专用日志器"""

    @staticmethod
    def log_call_start(
        model: str,
        system_prompt: str,
        user_prompt: str,
        call_type: str = "generate",
    ) -> float:
        """记录LLM调用开始

        Args:
            model: 模型名称
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            call_type: 调用类型 (generate, chat, rag)

        Returns:
            开始时间戳
        """
        start_time = time.time()
        log_with_context(
            "info",
            f"LLM调用开始 - {call_type}",
            model=model,
            call_type=call_type,
            system_prompt_length=len(system_prompt),
            user_prompt_length=len(user_prompt),
            system_prompt_preview=system_prompt[:200] if len(system_prompt) > 200 else system_prompt,
            user_prompt_preview=user_prompt[:300] if len(user_prompt) > 300 else user_prompt,
            backend=settings.llm.source,
            temperature=settings.llm.generation_temperature,
            max_tokens=settings.llm.generation_num_predict,
        )
        return start_time

    @staticmethod
    def log_call_end(
        start_time: float,
        model: str,
        response: str,
        error: Optional[Exception] = None,
    ) -> None:
        """记录LLM调用结束

        Args:
            start_time: 开始时间戳
            model: 模型名称
            response: 响应内容
            error: 异常（如果有）
        """
        duration_ms = round((time.time() - start_time) * 1000, 2)

        if error:
            log_with_context(
                "error",
                f"LLM调用失败 - 耗时 {duration_ms}ms",
                model=model,
                duration_ms=duration_ms,
                error_type=type(error).__name__,
                error_message=str(error),
                traceback=traceback.format_exc(),
            )
        else:
            log_with_context(
                "info",
                f"LLM调用成功 - 耗时 {duration_ms}ms",
                model=model,
                duration_ms=duration_ms,
                response_length=len(response),
                response_preview=response[:300] if len(response) > 300 else response,
            )


class RetrievalLogger:
    """RAG检索专用日志器"""

    @staticmethod
    def log_search_start(query: str, top_k: int, threshold: float) -> float:
        """记录检索开始

        Args:
            query: 查询文本
            top_k: 返回数量
            threshold: 相似度阈值

        Returns:
            开始时间戳
        """
        start_time = time.time()
        log_with_context(
            "debug",
            "RAG检索开始",
            query=query,
            top_k=top_k,
            threshold=threshold,
            collection=settings.chroma_meta.description,
        )
        return start_time

    @staticmethod
    def log_search_end(
        start_time: float,
        query: str,
        results_count: int,
        below_threshold: bool,
        results: list[Any],
    ) -> None:
        """记录检索结束

        Args:
            start_time: 开始时间戳
            query: 查询文本
            results_count: 返回结果数量
            below_threshold: 是否低于阈值
            results: 检索结果列表
        """
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # 提取结果摘要
        result_summaries = []
        for i, doc in enumerate(results[:3]):  # 最多记录3个
            if hasattr(doc, "doc_name"):
                result_summaries.append(
                    {
                        "index": i,
                        "doc_name": doc.doc_name,
                        "similarity": getattr(doc, "similarity", None),
                        "content_preview": doc.content[:100] if hasattr(doc, "content") else "",
                    }
                )

        log_with_context(
            "info",
            f"RAG检索完成 - 找到 {results_count} 个结果",
            query=query,
            duration_ms=duration_ms,
            results_count=results_count,
            below_threshold=below_threshold,
            results_preview=result_summaries,
        )


class APILogger:
    """API请求专用日志器"""

    @staticmethod
    def log_request(endpoint: str, method: str, request_data: Any) -> float:
        """记录API请求开始

        Args:
            endpoint: 端点路径
            method: HTTP方法
            request_data: 请求数据

        Returns:
            开始时间戳
        """
        start_time = time.time()
        log_with_context(
            "info",
            f"API请求开始 - {method} {endpoint}",
            endpoint=endpoint,
            method=method,
            request_data_preview=str(request_data)[:500] if request_data else "",
        )
        return start_time

    @staticmethod
    def log_response(
        start_time: float,
        endpoint: str,
        method: str,
        status_code: int,
        success: bool,
    ) -> None:
        """记录API响应

        Args:
            start_time: 开始时间戳
            endpoint: 端点路径
            method: HTTP方法
            status_code: HTTP状态码
            success: 是否成功
        """
        duration_ms = round((time.time() - start_time) * 1000, 2)
        level = "info" if success else "error"

        log_with_context(
            level,
            f"API响应 - {method} {endpoint} - {status_code}",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            success=success,
        )


def log_llm_call(func: F) -> F:
    """LLM调用装饰器 - 自动记录调用日志

    使用示例：
        @log_llm_call
        def _generate(model: str, system: str, user: str) -> str:
            # LLM调用逻辑

    支持类方法：
        @log_llm_call
        def generate(self, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # 检测是否为类方法调用（第一个参数是self）
        is_method = len(args) > 0 and hasattr(args[0], '__class__') and hasattr(args[0], 'generate')

        if is_method:
            # 类方法: (self, system_prompt, user_prompt, model)
            model = kwargs.get("model", args[3] if len(args) > 3 else None) or args[0].default_model
            system = kwargs.get("system_prompt", args[1] if len(args) > 1 else "")
            user = kwargs.get("user_prompt", args[2] if len(args) > 2 else "")
        else:
            # 普通函数: (model, system, user)
            model = kwargs.get("model", args[0] if args else "unknown")
            system = kwargs.get("system", args[1] if len(args) > 1 else "")
            user = kwargs.get("user", args[2] if len(args) > 2 else "")

        start_time = LLMLogger.log_call_start(model, system, user, func.__name__)

        try:
            result = func(*args, **kwargs)
            LLMLogger.log_call_end(start_time, model, result)
            return result
        except Exception as e:
            LLMLogger.log_call_end(start_time, model, "", error=e)
            raise

    return wrapper  # type: ignore


def log_retrieval_call(func: F) -> F:
    """检索调用装饰器 - 自动记录检索日志"""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        query = kwargs.get("query_text", args[0] if args else "")
        top_k = kwargs.get("top_k", settings.retrieval.top_k_results)
        threshold = settings.retrieval.similarity_threshold

        start_time = RetrievalLogger.log_search_start(query, top_k, threshold)

        try:
            result = func(*args, **kwargs)
            RetrievalLogger.log_search_end(
                start_time,
                query,
                len(result.documents) if hasattr(result, "documents") else 0,
                result.below_threshold if hasattr(result, "below_threshold") else False,
                result.documents if hasattr(result, "documents") else [],
            )
            return result
        except Exception as e:
            log_with_context(
                "error",
                "RAG检索失败",
                query=query,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    return wrapper  # type: ignore


# 便捷函数
def log_info(message: str, **context: Any) -> None:
    log_with_context("info", message, **context)


def log_debug(message: str, **context: Any) -> None:
    log_with_context("debug", message, **context)


def log_warning(message: str, **context: Any) -> None:
    log_with_context("warning", message, **context)


def log_error(message: str, exception: Optional[Exception] = None, **context: Any) -> None:
    if exception:
        context["error_type"] = type(exception).__name__
        context["error_message"] = str(exception)
        context["traceback"] = traceback.format_exc()
    log_with_context("error", message, **context)
