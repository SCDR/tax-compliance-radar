# 部署与运维文档

## 环境要求
- Python 3.10+
- Node.js 18+
- uv (Python 包管理器)
- Ollama（本地已安装模型）

## 后端启动

### 标准启动方式

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

### 服务启动后验证

1. 检查健康状态：
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

2. 检查支持的国家列表：
   ```bash
   curl http://localhost:8000/api/v1/countries
   ```

3. 测试多国审核接口：
   ```bash
   curl -X POST http://localhost:8000/api/v1/multi/audit/submit \
     -H "Content-Type: application/json" \
     -d '{"selected_countries": ["TH", "VN"], "business_profile": {"business_type": "跨境电商零售", "annual_sales_by_country": {"TH": 5000000}}}'
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

## 运行测试套件

```bash
cd backend

# 所有测试
uv run pytest -v

# 指定测试目录
uv run pytest tests/unit/services/ -v

# 业务维度扩展相关测试
uv run pytest tests/unit/test_extensible_dimensions.py -v
```

---

## 法规文档管理

### 占位法规文档用于开发与测试

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

### 真实法规文档就绪后的替换流程

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
   uv run pytest -q
   ```

5. 手工抽查 3 个问题，确认返回可追溯到真实法规片段。

---

## 业务维度扩展指南

新增业务字段时，参考：

- **[业务维度扩展指南](business_dimensions_guide.md)** - 完整的新增维度流程文档

### 快速添加新维度摘要

1. **在 `BusinessProfile` 模型中添加字段**：
   - 通用维度：普通字段名（如 `company_size`）
   - 多国维度：`xxx_by_country` 后缀（如 `annual_sales_by_country`）

2. **在 `field_config.py` 中配置默认值**（可选）：
   ```python
   "company_size": FieldMetadata(
       default_value="",
       field_type="str",
       description="企业规模"
   )
   ```

3. **在规则配置中使用**（`data/rules/{country}_rules.yaml`）：
   ```yaml
   condition: "company_size == '大型企业'"
   ```

4. **无需修改任何核心代码** ✨

---

## 架构说明

### 核心模块

| 模块 | 说明 | 路径 |
|------|------|------|
| 策略工厂 | 创建单国家/多国审核策略 | `tax_compliance_radar/factories/` |
| 规则引擎 | 基于 YAML 配置的合规规则评估 | `tax_compliance_radar/services/country_rules_engine.py` |
| AI 风险检测 | 基于 LLM + RAG 的边缘风险识别 | `tax_compliance_radar/services/ai_risk_detector.py` |
| 建议生成 | LLM 增强的合规建议生成 | `tax_compliance_radar/services/suggestion_generator.py` |
| 字段配置 | 业务维度元数据与默认值管理 | `tax_compliance_radar/field_config.py` |

### 多国组合审核架构

```
API 请求 (MultiCountryAuditRequest)
    │
    ▼
MultiCountryAuditStrategy (Composite 模式)
    ├─ ThailandAuditStrategy
    │   ├─ RulesEngine (YAML 规则)
    │   ├─ AIRiskDetection (LLM + RAG)
    │   └─ SuggestionGenerator
    └─ VietnamAuditStrategy
        ├─ RulesEngine
        ├─ AIRiskDetection
        └─ SuggestionGenerator
```

---

## 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| TCR_ENV | `development` | 运行环境：development / staging / production |
| OLLAMA_HOST | `http://localhost:11434` | Ollama 服务地址 |
| CHROMA_PATH | `data/chroma` | ChromaDB 数据目录 |
| SQLITE_PATH | `data/app.db` | SQLite 数据库路径 |
