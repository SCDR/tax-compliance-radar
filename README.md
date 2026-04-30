# Tax Compliance Radar

税务合规雷达 MVP 的 Monorepo 项目。

## 当前结构
- `backend/`: FastAPI + uv + SQLite + Chroma 初始化脚本
- `frontend/`: React + Vite 页面骨架
- `docs/`: 需求、API 和部署文档

## 快速启动

后端：

```bash
cd backend
bash scripts/init_all.sh
bash scripts/start.sh
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 快速验证

```bash
cd backend
uv run python scripts/test_ollama.py
uv run python scripts/test_embeddings.py
uv run pytest -q
```

## 模型默认配置
- 主模型：`qwen3:8b`
- 回退模型：`llama3.2`、`qwen2.5`
- 嵌入模型：`qwen3-embedding:0.6b`
