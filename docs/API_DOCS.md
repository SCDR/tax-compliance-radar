# API 文档

本文档对应当前前后端实现，重点覆盖流式问答、多国审核、国家配置和法规检索接口。

## 统一响应结构

成功响应通常为：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

## 1. 健康检查

### GET /api/v1/health

返回服务状态。

## 2. 问答接口

### POST /api/v1/qa/stream

提交税务合规问题，创建流式问答任务。

**请求示例**：

```json
{
  "query_text": "泰国对外国企业注册 VAT 有什么要求？",
  "think_mode": false
}
```

### GET /api/v1/qa/stream/{task_id}

监听问答 SSE 流，常见事件包括：`search_start`、`search_complete`、`answer_start`、`answer_delta`、`answer_complete`。

### GET /api/v1/qa/history

获取问答历史列表。

### GET /api/v1/qa/history/{qa_id}

获取单条问答详情。

## 3. 审核接口

### POST /api/v1/audit/submit

提交多国审核任务。前端会将所选国家与业务字段组装为 `business_profile`。

**请求示例**：

```json
{
  "selected_countries": ["TH", "VN"],
  "business_profile": {
    "business_type": "跨境电商零售",
    "annual_sales_by_country": {
      "TH": 5000000,
      "VN": 300000000
    }
  },
  "think_mode": true
}
```

### POST /api/v1/sse/audit/submit

SSE 审核任务提交入口，返回 `task_id` 供前端监听。

### GET /api/v1/sse/audit/stream/{task_id}

监听审核 SSE 流，常见事件包括：`start`、`progress`、`result_start`、`result_section`、`result_token`、`complete`。

### GET /api/v1/audit/history

获取审核历史列表。

### GET /api/v1/audit/history/{audit_id}

获取单条审核详情。

## 4. 国家配置接口

### GET /api/v1/countries

返回国家基础列表，用于下拉选择。

### GET /api/v1/countries/config/all

返回完整国家配置，包括业务字段、校验信息和界面展示所需元数据。

## 5. 法规检索接口

### GET /api/v1/regulations/{filename}

返回法规 Markdown 原文，用于前端引用来源弹窗。

## 6. 多国审核请求字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `selected_countries` | Array[string] | 选中的国家代码列表 |
| `business_profile` | object | 业务基础信息，支持 `*_by_country` 动态字段 |
| `think_mode` | boolean | 是否开启思考模式 |

## 7. SSE 事件说明

### 问答流

- `search_start`: 开始检索法规
- `search_complete`: 检索完成
- `answer_start`: 开始生成回答
- `answer_delta`: 回答增量片段
- `answer_complete`: 问答完成

### 审核流

- `start`: 开始任务
- `progress`: 进度更新
- `result_start`: 开始生成审核结果
- `result_section`: 结构化结果段
- `result_token`: 增量 token
- `complete`: 完成

## 8. 备注

- 当前前端默认展示动态 Slogan 占位符，并在无结果时自动轮播。
- 审核与问答页面都支持“思考模式”开关。