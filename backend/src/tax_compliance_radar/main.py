from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from tax_compliance_radar.api.audit_router import router as audit_router
from tax_compliance_radar.api.qa_router import router as qa_router
from tax_compliance_radar.api.countries_router import router as countries_router
from tax_compliance_radar.api.multi_audit_router import router as multi_audit_router
from tax_compliance_radar.api.regulations_router import router as regulations_router
from tax_compliance_radar.api.sse import router as sse_router
from tax_compliance_radar.api.qa_stream import router as qa_stream_router
from tax_compliance_radar.config import settings
from tax_compliance_radar.services.db import initialize_database

app = FastAPI(title=settings.app_name)


def _safe_serialize_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """安全地序列化错误详情，将异常对象转换为字符串"""
    result = []
    for err in errors:
        err_copy = dict(err)
        # 处理 ctx 中的异常对象
        if "ctx" in err_copy and err_copy["ctx"]:
            ctx_copy = {}
            for k, v in err_copy["ctx"].items():
                if isinstance(v, Exception):
                    ctx_copy[k] = str(v)
                else:
                    ctx_copy[k] = v
            err_copy["ctx"] = ctx_copy
        result.append(err_copy)
    return result


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理请求参数验证错误，返回统一格式的错误响应"""
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "msg": "参数验证失败",
            "error_type": "validation_error",
            "details": _safe_serialize_errors(exc.errors()),
        },
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """处理Pydantic验证错误，返回统一格式的错误响应"""
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "msg": "参数验证失败",
            "error_type": "validation_error",
            "details": _safe_serialize_errors(exc.errors()),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理HTTP异常，返回统一格式的错误响应"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "msg": exc.detail,
            "error_type": "http_error",
            "details": None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常，返回统一格式的错误响应"""
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "msg": "服务器内部错误",
            "error_type": "internal_server_error",
            "details": str(exc) if settings.debug else None,
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(qa_router)
app.include_router(audit_router)
app.include_router(countries_router)
app.include_router(multi_audit_router)
app.include_router(regulations_router)
app.include_router(sse_router)
app.include_router(qa_stream_router)
