# Tax Compliance Radar

Tax Compliance Radar 是一个面向多国税务合规场景的 AI 智能问答与合规审核平台，支持法规检索、流式回答、动态合规建议和历史记录追溯。

## 当前结构

- `backend/`: FastAPI + uv + SQLite + ChromaDB + LLM 提供商工厂
- `frontend/`: React + Vite + Ant Design + 动态 Slogan 轮播
- `docs/`: API、部署、需求与扩展说明

## 核心功能

- **智能问答 (RAG)**: 基于法规知识库的税务合规问答，支持引用来源展示
- **合规审核**: 多国组合审核、风险分级、结构化报告与 PDF 导出
- **流式体验**: SSE 推送、逐字符淡入、审核结果增量展示
- **动态占位符**: 根据业务类型和国家动态轮播合规 Slogan
- **历史记录**: 问答历史和审核历史可追溯

## 开发文档

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | 当前实现与开发约定 |
| [业务维度扩展指南](docs/business_dimensions_guide.md) | 新增国家/字段的配置驱动扩展流程 |
| [API 文档](docs/API_DOCS.md) | 当前接口、SSE 事件与请求示例 |
| [部署文档](docs/DEPLOYMENT.md) | 环境部署、启动与验证步骤 |
| [需求分析](docs/Requirements%20Analysis.md) | 需求基线与实现差异说明 |

## 快速启动

后端：

```bash
cd backend
bash scripts/init_all.sh
bash scripts/start.sh
```

健康检查：`http://localhost:8000/api/v1/health`

前端：

```bash
cd frontend
npm install
npm run dev
```

## 快速验证

```bash
cd backend
uv run python scripts/check_config.py
uv run python scripts/test_ollama.py
uv run python scripts/test_embeddings.py
uv run pytest -q
```

## 默认配置

- **主 LLM**: `qwen3:8b`（支持 Ollama 和 OpenAI 兼容 API）
- **嵌入模型**: `qwen3-embedding:0.6b`
- **向量数据库**: ChromaDB
- **响应模式**: SSE 流式输出 + `result_token` 增量事件
- **前端 UI**: 动态 Slogan、思考模式切换、PDF 导出

## 扩展提示

- 新国家配置放在 `backend/data/countries.yaml`
- 法规文档放在 `backend/data/regulations/`
- 动态 Slogan 可在 `frontend/src/App.jsx` 中调整