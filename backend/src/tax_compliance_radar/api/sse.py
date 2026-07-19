"""SSE (Server-Sent Events) 支持 - 解决长请求超时问题"""
from __future__ import annotations

import json
import asyncio
import uuid
from typing import Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from tax_compliance_radar.models.schemas import MultiCountryAuditRequest
from tax_compliance_radar.factories import StrategyFactory
from tax_compliance_radar.config import settings
from tax_compliance_radar.services.db import insert_audit_history
from tax_compliance_radar.services.policy_pusher import apply_hook
from tax_compliance_radar.services.tag_extractor import extract_tags_from_audit

router = APIRouter(prefix="/api/v1/sse", tags=["sse"])


# 存储进行中的任务（生产环境建议使用 Redis）
_active_tasks: Dict[str, Dict[str, Any]] = {}


def sse_message(event: str, data: Any) -> str:
    """构造 SSE 消息格式"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_audit_task(task_id: str, request: MultiCountryAuditRequest, profile_id: str = "default"):
    """在后台异步执行审核任务"""
    try:
        # 创建多国审核策略
        multi_strategy = StrategyFactory.get_multi_country_strategy(
            request.selected_countries
        )

        # 执行审核
        result = await multi_strategy.aevaluate(request.business_profile)
        result_dict = result.model_dump()

        # 保存审核历史
        try:
            # 构造 business_info（兼容单/多国格式）
            business_info = {
                "business_type": request.business_profile.business_type,
                "selected_countries": request.selected_countries,
                "annual_sales": getattr(request.business_profile, "annual_sales", 0),
            }
            insert_audit_history(business_info, result_dict, profile_id=profile_id)
            # 触发标签钩子
            try:
                deltas = extract_tags_from_audit(business_info, result_dict)
                apply_hook(profile_id, deltas, source="audit")
            except Exception as hook_error:  # noqa: BLE001
                print(f"[sse] apply_hook failed: {hook_error}")
        except Exception as save_error:
            print(f"[WARNING] 保存审核历史失败: {save_error}")

        # 存储结果（策略层已注入 disclaimer）
        _active_tasks[task_id]["status"] = "completed"
        _active_tasks[task_id]["result"] = result_dict
        _active_tasks[task_id]["progress"] = 100

    except Exception as e:
        _active_tasks[task_id]["status"] = "error"
        _active_tasks[task_id]["error"] = str(e)


@router.post("/audit/submit")
async def submit_audit_sse(request: MultiCountryAuditRequest, http_request: Request):
    """提交审核任务，立即返回任务ID，后续通过 SSE 流式获取结果"""
    task_id = str(uuid.uuid4())[:8]
    profile_id = (http_request.headers.get("x-profile-id") or "default").strip() or "default"

    # 初始化任务
    _active_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "result": None,
        "error": None,
        "profile_id": profile_id,
    }

    # 启动后台任务
    asyncio.create_task(run_audit_task(task_id, request, profile_id=profile_id))

    return {
        "task_id": task_id,
        "message": "任务已提交，请通过 SSE 连接获取结果",
    }


@router.get("/audit/stream/{task_id}")
async def stream_audit_result(task_id: str) -> StreamingResponse:
    """SSE 流式获取审核结果"""
    if task_id not in _active_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator() -> AsyncGenerator[str, None]:
        # 发送开始消息
        yield sse_message("start", {
            "task_id": task_id,
            "message": "审核开始执行",
        })

        # 轮询任务状态（长轮询）
        max_wait = 120  # 最长等待 120 秒
        waited = 0

        while waited < max_wait:
            task = _active_tasks.get(task_id)
            if not task:
                yield sse_message("error", {"message": "任务不存在"})
                break

            if task["status"] == "completed":
                result = task["result"] or {}
                # 先通知前端开始接收结果分片
                yield sse_message("result_start", {
                    "message": "审核结果开始生成",
                })
                await asyncio.sleep(0.05)

                # 顶层摘要（按小片断发送，支持逐句/逐字渲染）
                overall = result.get("overall_summary", "") or ""
                if overall:
                    # 发送开始标识
                    yield sse_message("result_section", {"section": "overall_summary_start"})
                    await asyncio.sleep(0.02)
                    # 按短片断分发（每片8字符）
                    chunk_size = 8
                    for i in range(0, len(overall), chunk_size):
                        chunk = overall[i : i + chunk_size]
                        yield sse_message("result_token", {
                            "section": "overall_summary",
                            "delta": chunk,
                        })
                        await asyncio.sleep(0.02)
                    # 最后发送完整节以便前端最终替换/确认
                    yield sse_message("result_section", {
                        "section": "overall_summary",
                        "value": overall,
                    })
                    await asyncio.sleep(0.04)

                # 分国家结果逐个推送
                results_by_country = result.get("results_by_country", {}) or {}
                for country_code, country_result in results_by_country.items():
                    # 先发送国家级别结构（对象），前端渲染结构化字段
                    yield sse_message("result_section", {
                        "section": "country_result",
                        "country_code": country_code,
                        "value": country_result,
                    })
                    await asyncio.sleep(0.04)

                # 风险列表
                yield sse_message("result_section", {
                    "section": "all_risks",
                    "value": result.get("all_risks", []),
                })
                await asyncio.sleep(0.08)

                # 建议列表：按条分片推送 delta（逐字/逐句）并在每条完成后发送完整值
                suggestions = result.get("all_suggestions", []) or []
                suggestion_index = 0
                for s in suggestions:
                    full_text = s.get("content") if isinstance(s, dict) else str(s)
                    # 单条建议开始
                    yield sse_message("result_section", {
                        "section": "suggestion_start",
                        "suggestion_index": suggestion_index,
                        "source": s.get("source_info") if isinstance(s, dict) else None,
                        "metadata": {
                            "country_code": s.get("source_info", {}).get("country_code") if isinstance(s, dict) else None,
                        },
                    })
                    await asyncio.sleep(0.02)

                    # 按小片断发送 delta
                    chunk_size = 8
                    for i in range(0, len(full_text), chunk_size):
                        chunk = full_text[i : i + chunk_size]
                        yield sse_message("result_token", {
                            "section": "all_suggestions",
                            "suggestion_index": suggestion_index,
                            "delta": chunk,
                        })
                        await asyncio.sleep(0.02)

                    # 单条建议发送完成，告知前端最终值
                    yield sse_message("result_section", {
                        "section": "suggestion_complete",
                        "suggestion_index": suggestion_index,
                        "value": full_text,
                        "source": s.get("source_info") if isinstance(s, dict) else None,
                    })
                    await asyncio.sleep(0.02)
                    suggestion_index += 1

                # 免责声明/收尾信息：按片断发送
                disclaimer_text = result.get("disclaimer", settings.disclaimer_text) or ""
                chunk_size = 12
                for i in range(0, len(disclaimer_text), chunk_size):
                    chunk = disclaimer_text[i : i + chunk_size]
                    yield sse_message("result_token", {
                        "section": "disclaimer",
                        "delta": chunk,
                    })
                    await asyncio.sleep(0.02)
                yield sse_message("result_section", {
                    "section": "disclaimer",
                    "value": disclaimer_text,
                })
                await asyncio.sleep(0.02)

                yield sse_message("complete", {
                    "progress": 100,
                    "result": result,
                })
                break

            if task["status"] == "error":
                yield sse_message("error", {"message": task["error"]})
                break

            # 进行中，发送进度更新
            waited += 1
            progress = min(waited, 95)  # 模拟进度到95%
            yield sse_message("progress", {
                "progress": progress,
                "message": f"审核进行中... ({waited}s)",
            })
            await asyncio.sleep(1)
        else:
            yield sse_message("timeout", {"message": "审核超时，请减少审核国家后重试"})

        # 清理任务（延迟清理，确保前端收到结果）
        await asyncio.sleep(5)
        if task_id in _active_tasks:
            del _active_tasks[task_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
