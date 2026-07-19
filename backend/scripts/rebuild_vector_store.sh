#!/usr/bin/env bash
# 重建 Chroma 向量库 —— 用于新增/修改 backend/data/regulations/*.md 后同步索引。
#
# 使用场景：
#   1. 新增一份 markdown 法规文档；
#   2. 修改已有 markdown 的正文；
#   3. Chroma 索引损坏或迁移到新机器。
#
# 该脚本会：
#   - `--reset` 清空现有 collection；
#   - 重新解析所有 markdown 的 YAML frontmatter；
#   - 按 chunk_size / chunk_overlap 切块；
#   - 用配置好的 embedding provider 生成向量并写入 Chroma。
#
# SQLite 中 vat_documents 表也会同步刷新（每次插入前 idempotent 更新 doc 元数据）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"

CHUNK_SIZE=${CHUNK_SIZE:-512}
CHUNK_OVERLAP=${CHUNK_OVERLAP:-50}
SOURCE_DIR=${SOURCE_DIR:-data/regulations}

# 关闭 Chroma 匿名 telemetry，避免 posthog SDK 版本不兼容打印的无害告警
export ANONYMIZED_TELEMETRY=False

echo "[rebuild] source_dir=${SOURCE_DIR} chunk=${CHUNK_SIZE}/${CHUNK_OVERLAP}"
uv run python scripts/load_regulations.py \
    --source-dir "${SOURCE_DIR}" \
    --chunk-size "${CHUNK_SIZE}" \
    --chunk-overlap "${CHUNK_OVERLAP}" \
    --reset

echo "[rebuild] Chroma 索引重建完成。若前端已开启，需要刷新页面以生效。"
