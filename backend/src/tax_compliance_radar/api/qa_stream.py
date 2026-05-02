"""问答 SSE 流式响应 - 真正的逐字输出"""
from __future__ import annotations

import json
import asyncio
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from json_repair import repair_json

from tax_compliance_radar.models.schemas import QAQueryRequest, QAAnswer
from tax_compliance_radar.services.retrieval_service import search_regulations, build_context_prompt
from tax_compliance_radar.services.llm_service import QA_SYSTEM_PROMPT
from tax_compliance_radar.services.llm_providers import get_llm_provider
from tax_compliance_radar.config import settings
from tax_compliance_radar.registry import CountryRegistry
from tax_compliance_radar.services.db import insert_qa_history

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


# 存储进行中的流式任务
_active_streams: dict[str, dict] = {}


async def stream_qa_answer(query: str, country_code: str = "TH", think_mode: bool = False) -> AsyncGenerator[str, None]:
    """流式生成问答回答 - 真正的逐字输出"""
    try:
        # 第一步：检索相关法规
        yield f"event:search_start\ndata: {json.dumps({'message': '正在检索相关法规...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)

        retrieval_result = search_regulations(query, top_k=3)
        source_files = []
        if retrieval_result.documents:
            source_files = list(set([doc.doc_name for doc in retrieval_result.documents]))

        yield f"event:search_complete\ndata: {json.dumps({'sources': source_files}, ensure_ascii=False)}\n\n"
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

        yield f"event:answer_start\ndata: {json.dumps({}, ensure_ascii=False)}\n\n"

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
                yield f"event:answer_delta\ndata: {json.dumps({'delta': token, 'text': parsed.get('answer', ''), 'full_json': parsed}, ensure_ascii=False)}\n\n"
            except Exception:
                # 如果修复失败，至少推送当前的文本
                yield f"event:answer_delta\ndata: {json.dumps({'delta': token, 'text': full_json}, ensure_ascii=False)}\n\n"

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
            insert_qa_history(query, qa_answer.model_dump(), doc_ids)
        except Exception as save_error:
            print(f"[WARNING] 保存问答历史失败: {save_error}")

        yield f"event:answer_complete\ndata: {json.dumps({**final_result, 'sources': source_files, 'disclaimer': settings.disclaimer_text}, ensure_ascii=False)}\n\n"

    except Exception as e:
        yield f"event:error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def submit_qa_stream(request: QAQueryRequest):
    """提交问答查询，返回流式任务ID"""
    task_id = str(uuid.uuid4())[:8]
    _active_streams[task_id] = {
        "query": request.query_text,
        "think_mode": request.think_mode,
        "status": "ready",
    }
    return {
        "task_id": task_id,
        "message": "任务已提交，请通过 SSE 接口获取流式回答",
    }


@router.get("/stream/{task_id}")
async def stream_qa(task_id: str) -> StreamingResponse:
    """SSE 流式获取问答回答 - 真正的逐字输出"""
    if task_id not in _active_streams:
        raise HTTPException(status_code=404, detail="任务不存在")

    stream_info = _active_streams[task_id]
    query = stream_info["query"]
    think_mode = stream_info.get("think_mode", False)

    async def event_generator():
        try:
            async for chunk in stream_qa_answer(query, think_mode=think_mode):
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
