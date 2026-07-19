"""法规文件API - 提供法规文件列表和内容查询"""

import os
import re
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
    regulations_dir = Path(__file__).parent.parent.parent / "data" / "regulations"
    if not regulations_dir.exists():
        regulations_dir = Path(__file__).parents[3] / "data" / "regulations"
    return regulations_dir


def get_file_type(filename: str) -> str:
    ext = filename.lower().split(".")[-1]
    if ext in ["md", "pdf", "docx", "txt"]:
        return ext
    return "txt"


# 缓存：doc_name/doc_id -> 实际文件名。启动时按需构建
_alias_cache: dict[str, str] | None = None


def _extract_frontmatter_field(text: str, field: str) -> str | None:
    """从 md frontmatter 提取指定字段（doc_id / doc_name）"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        if key.strip() == field:
            return value.strip().strip("'").strip('"')
    return None


def _build_alias_cache() -> dict[str, str]:
    """扫描所有 md 文件，构建 {别名: 真实文件名} 映射"""
    cache: dict[str, str] = {}
    regulations_dir = get_regulations_dir()
    if not regulations_dir.exists():
        return cache

    # 硬编码 title
    for filename, title in FILENAME_TO_TITLE.items():
        cache.setdefault(title, filename)
        cache.setdefault(filename, filename)

    # md frontmatter
    for path in regulations_dir.glob("*.md"):
        try:
            head = path.read_text(encoding="utf-8", errors="ignore")[:4096]
        except OSError:
            continue
        doc_name = _extract_frontmatter_field(head, "doc_name")
        doc_id = _extract_frontmatter_field(head, "doc_id")
        aliases_raw = _extract_frontmatter_field(head, "aliases")
        if doc_name:
            cache.setdefault(doc_name, path.name)
        if doc_id:
            cache.setdefault(doc_id, path.name)
        if aliases_raw:
            # 支持 `alias1; alias2, alias3` 或 `[alias1, alias2]` 简易列表形式
            cleaned = aliases_raw.strip().lstrip("[").rstrip("]")
            for alias in re.split(r"[;,；，]", cleaned):
                alias = alias.strip().strip("'\"")
                if alias:
                    cache.setdefault(alias, path.name)
        cache.setdefault(path.name, path.name)
        cache.setdefault(path.stem, path.name)
    return cache


def _resolve_filename(name: str) -> str | None:
    """把任意别名（doc_name/doc_id/title/文件名）解析为真实文件名"""
    global _alias_cache
    if _alias_cache is None:
        _alias_cache = _build_alias_cache()
    return _alias_cache.get(name)


@router.get("/aliases")
async def list_aliases() -> dict[str, str]:
    """返回所有别名 → 真实文件名的映射。前端用它判断某个引用标签是否可点击。"""
    global _alias_cache
    if _alias_cache is None:
        _alias_cache = _build_alias_cache()
    return dict(_alias_cache)


@router.get("/", response_model=list[RegulationFile])
async def list_regulations():
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


@router.get("/{filename:path}", response_model=RegulationContent)
async def get_regulation_content(filename: str):
    """获取指定法规文件的内容 —— 支持真实文件名、doc_name、doc_id、title 等别名。
    使用 `:path` 转换器允许 filename 含 `/`，以便支持如 `PMK-131/2026` 这类文号别名。"""
    regulations_dir = get_regulations_dir()
    real_filename = _resolve_filename(filename) or filename
    # `real_filename` 若命中别名 → 是纯文件名；未命中 → 原样透传，需防止 `..` 逃逸
    if ".." in real_filename.split("/"):
        raise HTTPException(status_code=400, detail="非法路径")
    file_path = regulations_dir / real_filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"法规文件不存在: {filename}")

    file_type = get_file_type(real_filename)

    if file_type in ["md", "txt"]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="gbk", errors="ignore")
    else:
        content = f"[此文件为 {file_type.upper()} 格式，请下载后查看]"

    return RegulationContent(
        filename=real_filename,
        title=FILENAME_TO_TITLE.get(real_filename, _extract_frontmatter_field(content, "doc_name") or real_filename),
        content=content,
        file_type=file_type,
    )
