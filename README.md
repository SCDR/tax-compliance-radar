# Tax Compliance Radar

税务合规雷达 MVP 的 Monorepo 项目。

## 当前结构
- `backend/`: FastAPI + uv + SQLite + Chroma 初始化脚本
- `frontend/`: React + Vite 页面骨架
- `docs/`: 需求、API 和部署文档

## 📚 开发文档

| 文档 | 说明 |
|------|------|
| [业务维度扩展指南](docs/business_dimensions_guide.md) | 新增业务维度的完整开发流程（零代码侵入式扩展） |
| [API 文档](docs/API_DOCS.md) | 接口说明与调用示例 |
| [部署文档](docs/DEPLOYMENT.md) | 环境部署与运维指南 |
| [需求分析](docs/Requirements%20Analysis.md) | 产品需求与架构说明 |

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
