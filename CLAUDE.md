# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 在本仓库中工作时提供指引。

## 项目概览

Tax Compliance Radar（税务合规雷达）—— 一款 AI 驱动的多国税务合规助手。采用 Monorepo 架构，包含后端（FastAPI）与前端（React）。支持基于 RAG 的智能合规问答、多国审计分析以及流式响应。

## 架构

### 后端技术栈
- **框架**：FastAPI + uv（包管理器）
- **数据库**：SQLite（app.db），通过 SQLAlchemy ORM 访问
- **向量数据库**：ChromaDB，用于法规向量化（RAG）
- **LLM**：可插拔的 Provider 模式 —— Ollama（本地）或 OpenAI 兼容接口（远程）
- **Embedding**：模型可配置，默认 Qwen3-embedding:0.6b（1024 维）
- **流式传输**：SSE（Server-Sent Events），用于实时 Token 推送

### 关键架构分层

```
backend/src/tax_compliance_radar/
├── main.py                          # FastAPI 应用、中间件、路由注册
├── config.py                        # 环境配置、LLM 设置
├── api/
│   ├── qa_router.py                # 问答接口（/api/v1/qa/stream）
│   ├── audit_router.py             # 审计 SSE 接口（/api/v1/audit/sse）
│   ├── countries_router.py         # 多国配置（/api/v1/countries）
│   ├── regulations_router.py       # 法规检索
│   ├── sse.py                      # SSE 响应流处理逻辑
│   └── qa_stream.py                # 问答流式处理器
├── services/
│   ├── llm_service.py              # LLM 接口 + 工厂模式
│   ├── llm_providers/
│   │   ├── base.py                # BaseProvider 抽象基类
│   │   ├── ollama_provider.py     # 本地 Ollama 集成
│   │   └── openai_compatible_provider.py  # 远程 API 集成
│   ├── qa_service.py               # 基于 RAG 的问答逻辑
│   ├── audit_service.py            # 审计编排
│   ├── ai_risk_detector.py         # AI 风险评估
│   ├── embedding_service.py        # Embedding 生成
│   └── db.py                       # SQLAlchemy ORM 配置
├── database/
│   ├── regulation_loader.py       # 加载 Markdown → 分块 → Embedding
│   └── init_chroma.py             # ChromaDB 初始化
├── models/
│   └── schemas.py                 # Pydantic 模型（审计、业务字段等）
├── registry/
│   ├── base.py                    # 注册表抽象基类
│   ├── registry.py                # 国家 + 维度配置加载器
│   └── countries/                 # （已弃用 —— 现使用 YAML）
├── strategies/
│   └── composite.py               # 多国编排策略
└── factories/
    └── strategy_factory.py        # 策略实例化工厂
```

### 前端技术栈
- React + Vite
- Ant Design 组件库
- SSE 监听流式结果
- 上下文感知的动态 Slogan 系统
- PDF 导出（jspdf + html2canvas）
- Markdown 渲染：`react-markdown` + `remark-gfm`（法规原文查看 + YAML frontmatter 元数据解析）
- 图表可视化：`recharts` v3（数据看板：面积图、甜甜圈、横向条形图）
- 主题色系：**墨黑（`#0f172a` 系列灰阶）** + **暗金强调色（`#a68a5b`）** + **低饱和语义色（砖红/暗金/墨绿三档风险）**
  - 所有按钮、标签、徽章统一 **胶囊圆角（999px）**；卡片方角 14px
  - AI 生成内容以 `AIGeneratedBadge` 组件包裹显式提示

## 流式架构

### SSE 双层响应模式
```
result_section：最终确认值（数据一致性）
    └── overall_summary、country_result、all_risks、all_suggestions、disclaimer

result_token：细粒度 Token 流（实时 UX）
    └── 增量更新（8 字符块），用于逐字渲染
```

### 前端 Slogan 系统
- **基础 Slogan**：12 条通用合规提示
- **动态业务提示**：每种业务类型 3-4 条上下文提示
  - 跨境电商零售：电商相关税务影响
  - 品牌出海直营：直营复杂性（如转让定价等）
  - 外贸综合服务：外贸综合服务合规要点
- **多国加成**：选择 2 个及以上国家时追加提示

## 配置系统

### 多国注册表
位于 `backend/data/countries.yaml`：
```yaml
- code: TH
  country_name: Thailand
  flag: 🇹🇭
  tax_type: VAT
  business_fields:
    - name: monthly_turnover
      type: number
      label: "Monthly Turnover (THB)"
  compliance_dimensions:
    - registration_requirements
    - vat_filing
    - reporting_thresholds
```

启动时由 `registry.py` 加载，新增国家无需改代码。

## LLM Provider 工厂

`llm_service.py` 负责 Provider 选择：

```python
# 由配置驱动的 Provider 选择
provider = LLMFactory.create(config.LLM_PROVIDER)  # "ollama" 或 "openai"
response = provider.query(prompt, think_mode=True/False)
```

主 Provider 不可用时自动回退。

## 常用命令

### 后端（在 `backend/` 目录下执行）

**一键初始化**：
```bash
bash scripts/init_all.sh    # 创建数据目录、初始化数据库、加载法规、构建 Chroma 索引
```

**重建向量库**（新增/修改 `backend/data/regulations/*.md` 后必须执行）：
```bash
bash scripts/rebuild_vector_store.sh
# 环境变量可覆盖：CHUNK_SIZE / CHUNK_OVERLAP / SOURCE_DIR
```

脚本流程：清空 Chroma collection → 重新解析所有 markdown 的 YAML frontmatter → 分块 → 生成 embedding → 写入 Chroma；同时同步 SQLite `vat_documents` 元数据。前端引用来源通过 doc_name / doc_id / 文件名/ md stem 任一都能解析（见 `api/regulations_router.py:_resolve_filename`），所以 seed 数据里的 `recall_doc_ids` 与真实 markdown 的 `doc_name` 保持一致即可跳转。

**启动服务**：
```bash
bash scripts/start.sh       # 执行：uv run uvicorn src.tax_compliance_radar.main:app --reload --port 8000
```

**运行测试**：
```bash
uv run pytest -q                      # 全部测试
uv run pytest tests/unit/services/    # 指定目录
uv run pytest tests/integration/      # 集成测试
```

**验证外部依赖**：
```bash
uv run python scripts/test_ollama.py      # 测试 Ollama 连通性
uv run python scripts/test_embeddings.py  # 测试 Embedding 生成
```

### 前端（在 `frontend/` 目录下执行）
```bash
npm install
npm run dev          # 启动开发服务器（Vite）
npm run build        # 生产构建
npm run preview      # 预览构建
```

## 核心功能

### 1. **流式问答**

- 接口：`POST /api/v1/qa/stream` 提交任务，`GET /api/v1/qa/stream/{task_id}` 建立 SSE 连接
- SSE 事件类型：`search_start` / `search_complete`（含 `sources` + `snippets: {filename: [chunk_text, ...]}`）/ `answer_start` / `answer_delta` / `answer_complete` / `error`
- **SSE 事件行格式必须为 `event: xxx\n`（冒号后空格）**，否则 `@microsoft/fetch-event-source` 严格模式识别不出 event name
- 前端逐字淡入动画
- 可选 `think_mode` 进行更深入的分析
- 问答历史持久化 `recall_snippets`（JSON 列），支持从历史记录点击来源时精准定位到原文段落

### 2. **SSE 审计结果**

- 接口：`GET /api/v1/audit/sse/{task_id}`
- 返回：多阶段 SSE 流
  - 处理过程中的进度指示
  - 结构化风险评估的最终审计报告
  - 每条建议按 Token 流式增量渲染

### 3. **多国配置**

- 接口：`GET /api/v1/countries/configs`
- 返回：各国的动态业务字段
- 零硬编码 —— 由 YAML 驱动

### 4. **法规检索与定位**

- 接口：`GET /api/v1/regulations/{filename}`
- 支持**别名解析**：真实文件名 / doc_name（中文标题）/ doc_id / md 文件 stem 均可传入，由 `_resolve_filename` 统一映射
- 前端 `RegulationModal` 解析 YAML frontmatter 为元数据卡片；正文用 `react-markdown` + `remark-gfm` 渲染
- **来源段落聚焦**：接受 `highlight` prop（RAG 检索到的 chunk 原文），Modal 打开后自动滚动到匹配段落并暗金脉冲高亮 3.5s
  - 匹配采用多级降级：前 30 字 → 前 15 字 → 最长中文/字母数字 token
  - 手动定位滚动容器（`overflow: auto` 祖先），避免 `scrollIntoView` 在 antd Modal 内失效

### 5. **数据看板**

- 前端聚合：复用 `/qa/history`、`/audit/history`、`/countries` 三接口，无需新增后端
- Recharts 图表：近 7 日活跃 AreaChart（双系列，暗金 + 墨黑渐变）· 风险分布甜甜圈（三色）· 国家审核次数横向 BarChart · 最近问答列表
- 全部配色从组件顶部 `THEME` 常量注入，与 CSS 变量一致

### 6. **底部可折叠悬浮 dock（问答页）**

- `position: fixed` 常驻视口底部；`chatDockOpen` state 控制展开态卡片 / 折叠态右下角胶囊
- 展开态卡片头部 `position: sticky`，收起按钮始终可见；卡片 `max-height: min(dvh, vh) - 40px`，内部滚动
- 高度用 `ResizeObserver` 动态测量写入 `--chat-dock-height` CSS 变量，`.app-shell` `padding-bottom` 自适应
- QA tab 不显示独立 footer；审核 tab 显示 footer

### 7. **合同上传自动填表**

- 接口：`POST /api/v1/uploads/contract-extract`（不落库，不写画像标签）
- 后端服务：[services/contract_extractor.py](backend/src/tax_compliance_radar/services/contract_extractor.py)
  - PDF 走 `pypdf`、DOCX 走 `python-docx`、其他按 utf-8/gbk/latin-1 兜底解码
  - LLM 输出的字段按 `CountryRegistry` 中每个国家的 `business_fields` 白名单严格校验：`select` 精确匹配 options、`multiselect` 取交集、`number` 兜底做千分位/万亿单位换算
- 前端：审核表单顶部 `Upload.Dragger`（`accept=".pdf,.docx,.txt,.md"`），成功后先 `setSelectedCountries()` 触发动态字段渲染，再 `setTimeout(0)` 后 `auditForm.setFieldsValue({countries, business_type, [field_code]: value})`；低置信度字段用 `raw_hits` 弹 `notification.info` 提示人工核对
- 演示脚本：`uv run python scripts/gen_sample_contract.py` 生成 `backend/data/samples/sample_contract_TH_VN.pdf`（reportlab + `STSong-Light` CID 字体），覆盖 TH/VN 关键字段用于联调

## 数据流

1. **初始化**：
   - `scripts/load_regulations.py`：解析 Markdown → 分块 → Embedding → 存入 Chroma
   - `registry.py`：启动时加载 `countries.yaml` 配置

2. **问答流程**：
   ```
   用户提问 → 生成 Embedding → Chroma 语义检索
   → 结合上下文与来源调用 LLM → SSE Token 流 → 前端动画渲染
   ```

3. **审计流程**：
   ```
   业务档案 + 国家列表 → LLMFactory.create() → MultiCountryAuditStrategy
   → 各国并行 AI 分析 → 风险聚合 → SSE 流 → PDF 导出
   ```

## 重要说明

- **Ollama**：本地开发时须运行于 11434 端口
- **LLM 温度**：0.1，以获得确定性的结构化输出
- **Think Mode**：可选标志，会增加响应时间以换取更深入的推理
- **环境变量**：`TCR_ENV`（默认 "development"）控制日志与行为
- **流式**：所有审计 / 问答响应均采用 SSE + 增量 Token 渲染
- **免责声明**：从配置中自动追加到所有响应
- **前端缓存**：业务类型或国家选择变化时，Slogan 列表会重新计算

## 近期重大更新（最新一次会话）

1. **动态 Slogan 轮播**（前端）
   - 基于业务类型和所选国家的上下文感知 Slogan 系统
   - 每 3.5 秒自动轮换，避免相邻重复
   - 同时用于问答和审计结果的占位符

2. **SSE 流式架构**（后端）
   - 双层：`result_section`（最终）+ `result_token`（增量）
   - `result_token` 提供 8 字符块，用于实时展示
   - 支持前端细粒度动画

3. **LLM Provider 工厂**（后端）
   - 可插拔 Provider 模式（Ollama ↔ OpenAI 兼容）
   - 连接失败时自动回退
   - Think Mode 标志透传

4. **多国配置注册表**（后端）
   - 基于 YAML 的国家配置
   - 新增国家无需改代码
   - 业务字段按国家动态加载

5. **审计结果最小高度**（前端）
   - 审计卡片统一 600px 最小高度
   - 加载中布局更稳定

## 测试策略

- 单元测试：核心服务逻辑
- 集成测试：API 流程校验
- 手动测试：SSE 流、多国流程
- 外部依赖：Ollama、ChromaDB 连通性检查
