"""法规文件API - 提供法规文件列表和内容查询"""

import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/regulations", tags=["regulations"])


class RegulationFile(BaseModel):
    """法规文件元数据"""
    filename: str
    title: str
    file_type: Literal["md", "pdf", "docx", "txt"]
    size: int
    modified_time: str


class RegulationContent(BaseModel):
    """法规文件内容"""
    filename: str
    title: str
    content: str
    file_type: str


# 文件名到标题的映射
FILENAME_TO_TITLE = {
    "01_vat_registration_rules.md": "泰国VAT注册规则",
    "02_low_value_goods_policy_2026.md": "低价值商品VAT政策 (2026)",
    "03_platform_withholding_rules.md": "平台代扣代缴规则",
    "04_monthly_reporting_audit.md": "月度申报与稽查要求",
}


def get_regulations_dir() -> Path:
    """获取法规目录路径"""
    # 直接使用绝对路径计算，不依赖settings.data_dir
    regulations_dir = Path(__file__).parent.parent.parent / "data" / "regulations"
    if not regulations_dir.exists():
        # 尝试备选路径（从backend目录下）
        regulations_dir = Path(__file__).parents[3] / "data" / "regulations"
    return regulations_dir


def get_file_type(filename: str) -> str:
    """获取文件类型"""
    ext = filename.lower().split(".")[-1]
    if ext in ["md", "pdf", "docx", "txt"]:
        return ext
    return "txt"


@router.get("/", response_model=list[RegulationFile])
async def list_regulations():
    """获取所有法规文件列表"""
    regulations_dir = get_regulations_dir()

    if not regulations_dir.exists():
        raise HTTPException(status_code=404, detail="法规目录不存在")

    files = []
    for file_path in sorted(regulations_dir.glob("*")):
        if file_path.is_file() and not file_path.name.startswith("."):
            stat = file_path.stat()
            files.append(
                RegulationFile(
                    filename=file_path.name,
                    title=FILENAME_TO_TITLE.get(file_path.name, file_path.name),
                    file_type=get_file_type(file_path.name),
                    size=stat.st_size,
                    modified_time=str(stat.st_mtime),
                )
            )

    return files


@router.get("/{filename}", response_model=RegulationContent)
async def get_regulation_content(filename: str):
    """获取指定法规文件的内容"""
    regulations_dir = get_regulations_dir()
    file_path = regulations_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"法规文件不存在: {filename}")

    file_type = get_file_type(filename)

    # 只读取文本类型文件
    if file_type in ["md", "txt"]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="gbk", errors="ignore")
    else:
        # PDF/DOCX等二进制文件暂时返回提示
        content = f"[此文件为 {file_type.upper()} 格式，请下载后查看]"

    return RegulationContent(
        filename=filename,
        title=FILENAME_TO_TITLE.get(filename, filename),
        content=content,
        file_type=file_type,
    )
