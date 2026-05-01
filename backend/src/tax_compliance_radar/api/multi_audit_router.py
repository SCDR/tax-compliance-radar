"""多国组合审核API端点"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tax_compliance_radar.models.schemas import (
    ApiResponse,
    MultiCountryAuditRequest,
    MultiCountryAuditReport,
)
from tax_compliance_radar.factories import StrategyFactory
from tax_compliance_radar.registry import CountryRegistry

router = APIRouter(prefix="/api/v1/multi/audit", tags=["multi-audit"])


@router.post("/submit", response_model=ApiResponse)
async def submit_multi_country_audit(request: MultiCountryAuditRequest) -> ApiResponse:
    """提交多国组合合规审核

    支持同时审核多个国家/地区的合规风险，所有结果都带有明确的来源国家标签。

    Args:
        request: 包含选中国家列表和业务信息

    Returns:
        多国组合审核报告，包含：
        - 整体摘要
        - 按国家分组的详细结果
        - 所有风险混合列表（保留来源标签）
        - 所有建议混合列表（保留来源标签）
    """
    # 验证所有国家都被支持
    for code in request.selected_countries:
        if not CountryRegistry.is_supported(code):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的国家代码: {code}，请先检查支持的国家列表",
            )

    try:
        # 创建多国组合策略并执行异步并行审核
        multi_strategy = StrategyFactory.get_multi_country_strategy(
            request.selected_countries
        )
        result = await multi_strategy.aevaluate(request.business_profile)

        return ApiResponse(data=result.model_dump())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"审核失败: {str(e)}")
