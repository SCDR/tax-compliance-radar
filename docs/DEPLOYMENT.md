# 本地部署与启动（Day1）

## 环境要求
- Python 3.10+
- Node.js 18+
- uv
- Ollama（本地已安装模型）

## 后端启动

```bash
cd backend
uv sync
uv run python -m tax_compliance_radar.database.init_db
uv run python -m tax_compliance_radar.database.init_chroma
uv run uvicorn tax_compliance_radar.main:app --host 0.0.0.0 --port 8000 --reload
```

或使用脚本：

```bash
cd backend
bash scripts/init_all.sh
bash scripts/start.sh
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 连通性测试（快速）

```bash
cd backend
uv run python scripts/test_ollama.py
uv run python scripts/test_embeddings.py
```

## 占位法规文档用于开发与测试

占位文档目录：
- `backend/data/regulations/`

初始化时会自动把占位文档写入 SQLite 与 Chroma：

```bash
cd backend
bash scripts/init_all.sh
```

也可以单独加载：

```bash
cd backend
uv run python scripts/load_regulations.py --reset
```

## 真实法规文档就绪后的替换流程

1. 按当前占位文档格式准备真实文档（保留 front matter 字段）：
- `doc_id`
- `doc_name`
- `publish_org`
- `effective_time`
- `original_link`
- `chapter`

2. 用真实文档覆盖 `backend/data/regulations/*.md`。

3. 重新初始化并重建向量集合：

```bash
cd backend
uv run python -m tax_compliance_radar.database.init_db
uv run python -m tax_compliance_radar.database.init_chroma
uv run python scripts/load_regulations.py --reset
```

4. 验证加载结果：

```bash
cd backend
uv run python scripts/test_embeddings.py
uv run --extra dev pytest -q
```

5. 手工抽查 3 个问题，确认返回可追溯到真实法规片段。
