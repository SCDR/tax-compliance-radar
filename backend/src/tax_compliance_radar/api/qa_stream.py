"""问答 SSE 流式响应 - 真正的逐字输出"""
from __future__ import annotations

import json
import asyncio
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from json_repair import repair_json

from tax_compliance_radar.models.schemas import QAQueryRequest, QAAnswer
from tax_compliance_radar.services.retrieval_service import search_regulations, build_context_prompt
from tax_compliance_radar.services.llm_service import QA_SYSTEM_PROMPT
from tax_compliance_radar.services.llm_providers import get_llm_provider
from tax_compliance_radar.config import settings
from tax_compliance_radar.registry import CountryRegistry
from tax_compliance_radar.services.db import insert_qa_history
from tax_compliance_radar.services.policy_pusher import apply_hook
from tax_compliance_radar.services.tag_extractor import extract_tags_from_qa
from tax_compliance_radar.api.regulations_router import _resolve_filename

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


# 存储进行中的流式任务
_active_streams: dict[str, dict] = {}


async def stream_qa_answer(query: str, country_code: str = "TH", think_mode: bool = False, profile_id: str = "default") -> AsyncGenerator[str, None]:
    """流式生成问答回答 - 真正的逐字输出"""
    try:
        # 第一步：检索相关法规
        yield f"event: search_start\ndata: {json.dumps({'message': '正在检索相关法规...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)

        retrieval_result = search_regulations(query, top_k=3)
        source_files: list[str] = []
        source_snippets: dict[str, list[str]] = {}
        # block 级位置：{filename: [{block_start, block_end}, ...]} —— 前端按 data-block 精准定位
        source_positions: dict[str, list[dict[str, int]]] = {}
        if retrieval_result.documents:
            for doc in retrieval_result.documents:
                # 把 doc_name（中文标题）解析为真实文件名，与前端 REGULATION_TITLES 的 key 一致
                resolved = _resolve_filename(doc.doc_name) or doc.doc_name
                if resolved not in source_files:
                    source_files.append(resolved)
                snippet = (doc.content or "").strip()
                if snippet:
                    # 同时以 resolved 真实文件名与原始 doc_name（中文标题）为键存放片段，
                    # 前端无论按哪种引用形式点击都能命中 → 保证"定位原文"功能生效
                    source_snippets.setdefault(resolved, []).append(snippet)
                    if doc.doc_name and doc.doc_name != resolved:
                        source_snippets.setdefault(doc.doc_name, []).append(snippet)
                if doc.block_start >= 0:
                    pos = {"block_start": doc.block_start, "block_end": doc.block_end}
                    source_positions.setdefault(resolved, []).append(pos)
                    if doc.doc_name and doc.doc_name != resolved:
                        source_positions.setdefault(doc.doc_name, []).append(pos)

        yield f"event: search_complete\ndata: {json.dumps({'sources': source_files, 'snippets': source_snippets, 'positions': source_positions}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)

        # 第二步：构建提示词
        context = build_context_prompt(retrieval_result)
        user_prompt = f"""
用户问题：{query}

{context}

请基于以上检索到的法规内容，按照要求的JSON格式回答问题。
"""

        # 获取LLM provider并流式生成
        provider = get_llm_provider()
        reasoning_effort = "low" if think_mode else "minimal"
        _, stream = await provider.astream_with_fallback(QA_SYSTEM_PROMPT, user_prompt, reasoning_effort)

        yield f"event: answer_start\ndata: {json.dumps({}, ensure_ascii=False)}\n\n"

        # 流式接收JSON，每次都修复并推送完整结构
        full_json = ""
        async for token in stream:
            full_json += token

            # 修复当前不完整的JSON
            try:
                repaired = repair_json(full_json)
                parsed = json.loads(repaired)
                # 确保answer字段存在
                if "answer" not in parsed:
                    parsed["answer"] = ""
                # 推送给前端
                yield f"event: answer_delta\ndata: {json.dumps({'delta': token, 'text': parsed.get('answer', ''), 'full_json': parsed}, ensure_ascii=False)}\n\n"
            except Exception:
                # 如果修复失败，至少推送当前的文本
                yield f"event: answer_delta\ndata: {json.dumps({'delta': token, 'text': full_json}, ensure_ascii=False)}\n\n"

        # 最后一次修复确保完整
        try:
            repaired = repair_json(full_json)
            final_result = json.loads(repaired)
        except Exception:
            final_result = {"answer": full_json}

        # 转换为 QAAnswer 格式并保存历史
        try:
            qa_answer = QAAnswer(
                regulation_base=final_result.get("regulation_base", ", ".join(source_files)),
                core_rules=final_result.get("core_rules", final_result.get("answer", "")),
                compliance_suggestion=final_result.get("compliance_suggestion", ""),
                risk_warning=final_result.get("risk_warning", ""),
                operation_guide=final_result.get("operation_guide", ""),
                original_link=final_result.get("original_link", ""),
            )
            doc_ids = source_files
            insert_qa_history(query, qa_answer.model_dump(), doc_ids, source_snippets, profile_id=profile_id, recall_positions=source_positions)
            # 触发标签钩子（吞异常，不影响主流程）
            try:
                deltas = extract_tags_from_qa(query, qa_answer.model_dump(), doc_ids)
                apply_hook(profile_id, deltas, source="qa")
            except Exception as hook_error:  # noqa: BLE001
                print(f"[qa_stream] apply_hook failed: {hook_error}")
        except Exception as save_error:
            print(f"[WARNING] 保存问答历史失败: {save_error}")

        yield f"event: answer_complete\ndata: {json.dumps({**final_result, 'sources': source_files, 'snippets': source_snippets, 'positions': source_positions, 'disclaimer': settings.disclaimer_text}, ensure_ascii=False)}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def submit_qa_stream(request: QAQueryRequest, http_request: Request):
    """提交问答查询，返回流式任务ID"""
    task_id = str(uuid.uuid4())[:8]
    profile_id = (http_request.headers.get("x-profile-id") or "default").strip() or "default"
    _active_streams[task_id] = {
        "query": request.query_text,
        "think_mode": request.think_mode,
        "profile_id": profile_id,
        "status": "ready",
    }
    return {
        "task_id": task_id,
        "message": "任务已提交，请通过 SSE 接口获取流式回答",
    }


@router.get("/stream/{task_id}")
async def stream_qa(task_id: str, http_request: Request) -> StreamingResponse:
    """SSE 流式获取问答回答 - 真正的逐字输出"""
    if task_id not in _active_streams:
        raise HTTPException(status_code=404, detail="任务不存在")

    stream_info = _active_streams[task_id]
    query = stream_info["query"]
    think_mode = stream_info.get("think_mode", False)
    # SSE 建连时也允许通过 header 覆盖 profile_id（EventSource 不能自定义 header，
    # 因此实际会读取到 submit 时缓存的值；query param 兜底）
    profile_id = (
        http_request.headers.get("x-profile-id")
        or http_request.query_params.get("profile_id")
        or stream_info.get("profile_id")
        or "default"
    ).strip() or "default"

    async def event_generator():
        try:
            async for chunk in stream_qa_answer(query, think_mode=think_mode, profile_id=profile_id):
                yield chunk
        finally:
            # 清理任务
            if task_id in _active_streams:
                del _active_streams[task_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
