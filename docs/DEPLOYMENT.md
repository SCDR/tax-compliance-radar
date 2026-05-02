# 部署与运维文档

## 环境要求

- Python 3.10+
- Node.js 18+
- uv
- Ollama（本地模型服务）或可访问的 OpenAI 兼容接口

## 后端启动

### 推荐方式

```bash
cd backend
bash scripts/init_all.sh
bash scripts/start.sh
```

`init_all.sh` 会完成数据库、Chroma、法规数据与基础资源初始化。

### 常用验证

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/countries
curl http://localhost:8000/api/v1/countries/config/all
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 运行前检查

```bash
cd backend
uv run python scripts/check_config.py
uv run python scripts/test_ollama.py
uv run python scripts/test_embeddings.py
```

## 测试

```bash
cd backend
uv run pytest -q
```

## 法规文档管理

法规数据位于 `backend/data/regulations/`。更新法规后，重新执行：

```bash
cd backend
bash scripts/init_all.sh
```

## 业务维度扩展

- 新国家与字段统一配置在 `backend/data/countries.yaml`
- 前端根据 `/api/v1/countries/config/all` 动态生成表单
- 规则引擎与 LLM 提示词会自动消费新增字段

## 当前实现要点

- 问答接口使用 SSE 流式返回，前端逐字符渲染
- 审核接口支持多国组合分析、分段输出和 `result_token` 增量事件
- 前端占位区域采用动态 Slogan 轮播，QA 和审核页面均会根据上下文更新

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| TCR_ENV | `development` | 运行环境 |
| OLLAMA_HOST | `http://localhost:11434` | Ollama 地址 |
| CHROMA_PATH | `data/chroma` | Chroma 数据目录 |
| SQLITE_PATH | `data/app.db` | SQLite 数据路径 |