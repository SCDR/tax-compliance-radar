# API 文档

## 统一响应结构

所有成功响应使用统一格式：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

## 统一错误响应结构

### 参数验证错误 (400)

```json
{
  "code": 400,
  "msg": "参数验证失败",
  "error_type": "validation_error",
  "details": [
    {
      "type": "value_error",
      "loc": ["body", "selected_countries"],
      "msg": "至少需要选择一个国家进行审核",
      "ctx": {}
    }
  ]
}
```

---

## 1. 健康检查接口

### GET /api/v1/health

检查服务状态。

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "status": "ok"
  }
}
```

---

## 2. 问答接口（单国家）

### POST /api/v1/qa/query

提交税务合规问题，获取基于法规知识库的智能回答。

**请求**：
```json
{
  "query_text": "泰国对外国企业注册VAT有什么要求？"
}
```

**字段说明**：

| 字段名 | 类型 | 必填 | 长度限制 | 说明 |
|--------|------|------|----------|------|
|`query_text`|string|✅|1-500字符|问题内容|

### GET /api/v1/qa/history

获取问答历史列表。

### GET /api/v1/qa/history/{qa_id}

获取单条问答详情。

---

## 3. 审核接口

### 3.1 单国家审核（向后兼容）

#### POST /api/v1/audit/submit

提交单一国家的业务信息进行合规风险评估。

**请求**：
```json
{
  "target_market": "泰国",
  "business_type": "跨境电商零售",
  "annual_sales": 5000000,
  "platforms": ["Shopee", "Lazada"]
}
```

**字段说明**：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `target_market` | string | ✅ | 目标市场，目前支持「泰国」 |
| `business_type` | string | ✅ | 业务类型 |
| `annual_sales` | number | ✅ | 年预计销售额（泰铢） |
| `platforms` | Array[string] | ✅ | 入驻平台列表 |

### GET /api/v1/audit/history

获取审核历史列表。

### GET /api/v1/audit/history/{audit_id}

获取单条审核详情。

---

### 3.2 多国组合审核 ✨

#### POST /api/v1/multi/audit/submit

同时审核多个国家/地区的合规风险。

**请求**：
```json
{
  "selected_countries": ["TH", "VN"],
  "business_profile": {
    "business_type": "跨境电商零售",

    "annual_sales_by_country": {
      "TH": 5000000,
      "VN": 300000000
    },
    "platforms_by_country": {
      "TH": ["Shopee", "Lazada"],
      "VN": ["TikTok Shop"]
    },
    "product_categories_by_country": {
      "TH": ["电子产品", "服饰"],
      "VN": ["美妆"]
    },
    "monthly_orders_by_country": {
      "TH": 10000,
      "VN": 8000
    },
    "warehousing_mode_by_country": {
      "TH": "本地仓",
      "VN": "直邮"
    },
    "has_local_entity_by_country": {
      "TH": false,
      "VN": true
    }
  }
}
```

**字段说明**：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `selected_countries` | Array[string] | ✅ | 要审核的国家代码列表，至少1个 |
| `business_type` | string | ✅ | 业务类型，所有国家共用 |
| `*_by_country` | object | ➖ | 按国家代码区分的业务维度 |

> 💡 **可选维度说明**：所有 `*_by_country` 字段都是可选的。
> - 未传递的字段将自动使用配置的默认值
> - 数值字段验证：`annual_sales_by_country` ≥ 0，`monthly_orders_by_country` ≥ 0

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "overall_summary": "在2个国家/地区共识别到2个高风险事项。需要重点关注：泰国。",
    "results_by_country": {
      "TH": {
        "country_code": "TH",
        "country_name": "泰国",
        "vat_register_assessment": "必须注册",
        "register_deadline": "开展业务前",
        "risks": [
          {
            "source_info": {
              "country_code": "TH",
              "country_name": "泰国",
              "regulation_id": "TH_R001",
              "source_type": "rule"
            },
            "risk_level": "高风险",
            "risk_desc": "外国企业在泰国开展跨境电商业务无注册门槛，第一笔交易前应完成VAT注册",
            "trigger_condition": "开展泰国跨境电商业务，无论销售额多少",
            "regulation_base": "泰国VAT注册规则与2026年新政要求",
            "violation_consequence": "未按时注册可能面临罚款、货物被扣、平台账户受限等风险"
          }
        ],
        "suggestions": [
          {
            "source_info": {
              "country_code": "TH",
              "country_name": "泰国",
              "regulation_id": "TH_S001",
              "source_type": "ai_generated"
            },
            "suggestion_type": "general",
            "content": "在开展泰国业务前完成VAT注册准备工作"
          }
        ]
      },
      "VN": {
        "country_code": "VN",
        "country_name": "越南",
        "vat_register_assessment": "建议注册",
        "register_deadline": "建议30天内",
        "risks": [],
        "suggestions": []
      }
    },
    "all_risks": [],
    "all_suggestions": []
  }
}
```

---

## 4. 国家元数据接口 ✨

### GET /api/v1/countries

获取所有支持的国家/地区列表。

**响应**：
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "countries": [
      {
        "code": "TH",
        "name": "泰国",
        "tax_type": "VAT"
      },
      {
        "code": "VN",
        "name": "越南",
        "tax_type": "VAT"
      }
    ]
  }
}
```

### GET /api/v1/countries/{country_code}

获取指定国家的详细信息。

---

## 附录：支持的国家代码

| 代码 | 国家/地区 | 税种 |
|------|----------|------|
| TH | 泰国 | VAT |
| VN | 越南 | VAT |

---

## 附录：HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 参数验证失败 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
