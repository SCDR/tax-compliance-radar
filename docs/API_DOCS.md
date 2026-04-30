# API 文档（Day1 骨架版）

统一响应结构：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

## 1. 问答接口

### POST /api/v1/qa/query
请求：
```json
{
  "query_text": "泰国对外国企业注册VAT有什么要求？"
}
```

### GET /api/v1/qa/history
获取问答历史列表。

### GET /api/v1/qa/history/{qa_id}
获取单条问答详情。

## 2. 审核接口

### POST /api/v1/audit/submit
请求：
```json
{
  "target_market": "泰国",
  "business_type": "跨境电商零售",
  "annual_sales": 5000000,
  "platforms": ["Shopee", "Lazada"]
}
```

### GET /api/v1/audit/history
获取审核历史列表。

### GET /api/v1/audit/history/{audit_id}
获取单条审核详情。

## 3. 健康检查

### GET /api/v1/health
返回：
```json
{
  "status": "ok"
}
```
