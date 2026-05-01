"""来源标签装饰器 - Decorator Pattern"""
from __future__ import annotations

from functools import wraps
from typing import Any, Dict, List

from pydantic import BaseModel

from tax_compliance_radar.models.schemas import SourceInfo
from tax_compliance_radar.registry import CountryRegistry


def with_source_info(country_code: str, source_type: str = "rule"):
    """装饰器：自动为结果添加来源信息

    支持的返回类型：
    - dict：添加 source_info 键
    - Pydantic BaseModel：设置 source_info 属性
    - list：对每个元素应用
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            source_info = SourceInfo(
                country_code=country_code,
                country_name=CountryRegistry.get(country_code).country_name,
                source_type=source_type,  # type: ignore[arg-type]
            )

            # 处理不同类型的返回值
            if isinstance(result, dict):
                result["source_info"] = source_info
            elif isinstance(result, BaseModel) and hasattr(result, "source_info"):
                setattr(result, "source_info", source_info)
            elif isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        item["source_info"] = source_info
                    elif isinstance(item, BaseModel) and hasattr(item, "source_info"):
                        setattr(item, "source_info", source_info)

            return result

        return wrapper

    return decorator


def mark_ai_generated(func):
    """标记AI生成的内容"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            result["ai_generated"] = True
        return result

    return wrapper
