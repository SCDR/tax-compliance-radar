# Tax Compliance Radar

税务合规雷达 MVP 的 Monorepo 项目。支持多国跨境电商税务合规智能分析。

## 当前结构

- `backend/`: FastAPI + uv + SQLite + Chroma + 多LLM提供商
- `frontend/`: React + Vite 页面骨架
- `docs/`: 需求、API 和部署文档

## ✨ 核心功能

- **智能问答 (RAG)**: 基于法规知识库的税务合规问答
- **单一国家审核**: 泰国 VAT 自动化风险评估
- **多国联合审核**: 支持泰国、越南等多国组合分析
- **历史记录管理**: 完整的审核/问答历史追溯

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
uv run python scripts/check_config.py    # 检查配置完整性
uv run python scripts/test_ollama.py      # 验证Ollama连接
uv run python scripts/test_embeddings.py  # 验证嵌入生成
uv run pytest tests/unit/api/ -q         # 运行API单元测试
```

## 模型默认配置

- **主 LLM 模型**: `qwen3:8b` (Ollama) / 支持 OpenAI 兼容 API
- **回退模型**: `llama3.2`、`qwen2.5`
- **嵌入模型**: `qwen3-embedding:0.6b`
- **向量数据库**: ChromaDB (Chroma 存储法规向量)
- **结构化输出**: 严格 JSON 格式，temperature=0.1
