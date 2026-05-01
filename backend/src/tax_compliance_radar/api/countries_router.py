"""国家配置API端点"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tax_compliance_radar.models.schemas import ApiResponse
from tax_compliance_radar.registry import CountryRegistry

router = APIRouter(prefix="/api/v1/countries", tags=["countries"])


@router.get("", response_model=ApiResponse)
async def list_supported_countries() -> ApiResponse:
    """获取所有支持的国家列表"""
    countries = CountryRegistry.list_all()
    return ApiResponse(data={"countries": countries})


@router.get("/{country_code}", response_model=ApiResponse)
async def get_country_config(country_code: str) -> ApiResponse:
    """获取特定国家的配置信息"""
    try:
        config = CountryRegistry.get(country_code)
        return ApiResponse(data=config.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
