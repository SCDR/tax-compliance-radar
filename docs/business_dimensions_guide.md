# 业务维度扩展开发指南

## 概述

本系统已升级为**完全 YAML 配置驱动**的零代码扩展方案。新增国家、新增业务字段，**无需修改任何 Python 代码**，只需修改配置文件即可自动生效。

整个合规检查链路自动支持：

- ✅ **前端表单动态渲染**
- ✅ **规则引擎自动识别**
- ✅ **AI 风险检测提示词自动注入**
- ✅ **LLM 建议生成器自动感知**
- ✅ **缓存键自动包含维度数据**

---

## 快速开始

### 新增业务字段（1 步完成）

编辑 `backend/data/countries.yaml`，在 `business_fields` 数组中添加新字段：

```yaml
countries:
  - code: TH
    name: 泰国
    # ... 其他配置
    business_fields:
      # ===== 已有字段 =====
      - name: annual_sales
        label: 年预计销售额
        type: number
        required: true
        placeholder: 请输入年销售额（泰铢）
      
      # ===== ✅ 新增字段 =====
      - name: logistics_mode
        label: 物流模式
        type: select          # 下拉单选
        options: ["直邮", "保税仓", "本地仓", "第三方"]
      
      - name: payment_channel
        label: 支付渠道
        type: multiselect     # 下拉多选
        options: ["PayPal", "Stripe", "COD", "银行转账"]
      
      - name: import_license_type
        label: 进口许可证类型
        type: select
        options: ["API", "NPIK", "无"]
      
      - name: local_employee_count
        label: 本地员工数量
        type: number
        placeholder: 请输入本地员工数量
        min_value: 0
```

**保存即生效！** 重启服务后：
1. 前端表单自动出现新字段
2. 规则引擎可直接使用 `logistics_mode` / `payment_channel` 等字段
3. LLM 提示词自动包含新字段

---

### 新增国家（1 步完成）

在 `backend/data/countries.yaml` 中添加完整的国家配置：

```yaml
countries:
  # ... 已有国家
  - code: SG
    name: 新加坡
    currency: SGD
    currency_symbol: 新加坡元
    tax_type: GST
    tax_rate: 9.0
    registration_threshold: 1000000
    language: zh
    flag: 🇸🇬
    business_types: ["跨境电商零售", "品牌出海直营"]
    platforms: ["Shopee", "Lazada", "Amazon"]
    business_fields:
      - name: annual_sales
        label: 年预计销售额
        type: number
        required: true
        placeholder: 请输入年销售额（新加坡元）
      - name: platforms
        label: 入驻平台
        type: multiselect
        options: ["Shopee", "Lazada", "Amazon"]
      - name: has_gst_registration
        label: 是否已GST注册
        type: select
        options: ["是", "否", "办理中"]
      - name: import_declaration_mode
        label: 进口申报模式
        type: select
        options: ["自主申报", "代理申报", "保税仓申报"]
```

重启服务即可生效，前端可选国家列表自动更新。

---

## 字段类型说明

| 类型 | 说明 | 前端渲染 | 必填配置 |
|------|------|----------|----------|
| `number` | 数字输入 | InputNumber 组件 | `required: true/false` |
| `select` | 单选下拉 | Select 组件 | 需配置 `options` 数组 |
| `multiselect` | 多选下拉 | Select 组件（mode=multiple） | 需配置 `options` 数组 |
| `text` | 文本输入 | Input 组件 | `placeholder` 可选 |

### 完整字段配置示例

```yaml
business_fields:
  # ===== number 类型 =====
  - name: annual_sales
    label: 年预计销售额           # 前端显示标签
    type: number                 # 字段类型
    required: true               # 是否必填
    placeholder: 请输入年销售额   # 占位提示
    min_value: 0                 # 最小值（前端校验）
    max_value: 1000000000000     # 最大值（前端校验）
  
  # ===== select 类型 =====
  - name: warehousing_mode
    label: 仓储模式
    type: select
    options: ["本地仓", "海外仓", "直邮"]  # 选项列表
  
  # ===== multiselect 类型 =====
  - name: product_categories
    label: 商品类目
    type: multiselect
    options: ["电子产品", "服饰", "美妆", "家居", "食品"]
```

---

## 在规则中使用新字段

编辑 `backend/data/rules/{country_code}_rules.yaml`，直接使用字段名：

```yaml
rules:
  # ===== 使用新字段的规则示例 =====
  - rule_id: TH_R008
    description: 保税仓模式关税申报要求
    category: reporting
    # 直接使用新字段名
    condition: "logistics_mode == '保税仓'"
    risk_template:
      risk_level: 中风险
      risk_desc: 保税仓模式需按月进行关税申报并留存完整的入库出库记录
      trigger_condition: 使用保税仓物流模式
      regulation_base: 泰国海关保税仓库监管规定 B.E. 2560
      violation_consequence: 海关稽查风险、货物扣押

  - rule_id: TH_R009
    description: 第三方支付渠道备案要求
    category: compliance
    # 列表包含判断
    condition: "'PayPal' in payment_channel or 'Stripe' in payment_channel"
    risk_template:
      risk_level: 高风险
      risk_desc: 使用境外支付渠道需在泰国银行进行外汇交易备案
      trigger_condition: 使用 PayPal 或 Stripe 等境外支付渠道
      regulation_base: 泰国外汇管理法
      violation_consequence: 账户冻结、罚款

  - rule_id: TH_R010
    description: 无进口许可证合规风险
    category: registration
    # 多条件组合
    condition: "import_license_type == '无' and local_employee_count > 10"
    risk_template:
      risk_level: 高风险
      risk_desc: 员工超过10人但无进口许可证，需尽快办理
      trigger_condition: 无进口许可证且员工数超过阈值
      regulation_base: 泰国进出口贸易法
      violation_consequence: 禁止开展自营进口业务、罚款
```

---

## API 请求格式

新增字段后，前端请求自动适配，格式如下：

```json
POST /api/v1/multi/audit/submit
{
  "selected_countries": ["TH", "VN"],
  "business_profile": {
    "business_type": "跨境电商零售",
    
    // ===== 通用字段 =====
    "annual_sales_by_country": {
      "TH": 5000000,
      "VN": 300000000
    },
    
    // ===== 新增字段自动支持 =====
    "logistics_mode_by_country": {
      "TH": "保税仓",
      "VN": "直邮"
    },
    "payment_channel_by_country": {
      "TH": ["PayPal", "Stripe"],
      "VN": ["COD", "Momo"]
    },
    "import_license_type_by_country": {
      "TH": "无",
      "VN": "API"
    },
    "local_employee_count_by_country": {
      "TH": 25,
      "VN": 15
    }
  }
}
```

---

## 🎯 设计理念：全链路自动感知

### 数据流转图

```
YAML 配置文件 (countries.yaml)
    │
    ▼ 服务启动时加载
  CountryRegistry
    │
    ├─────────────────────────────────────────┐
    │                                         ▼
    │                              GET /countries/config/all
    │                                         │
    │                                         ▼
    │                                    前端 App
    │                                         │
    │                                    动态表单渲染
    │                                         │
    │                                         ▼
    │                              用户提交审核请求
    │                                         │
    ▼                                         ▼
  后端接收 → BusinessProfile → _extract_country_business
                                                    │
                                                    ▼
                ┌──────────────────┬──────────────────┬──────────────────┐
                │                  │                  │                  │
                ▼                  ▼                  ▼                  ▼
            规则引擎         AI 风险检测       LLM 建议生成       缓存键生成
            (evaluate)      (提示词注入)       (提示词注入)       (自动包含)
                │                  │                  │                  │
                └──────────────────┴──────────────────┴──────────────────┘
                                          │
                                          ▼
                                    合规审核报告
```

### 核心机制

1. **动态字段校验**：`BusinessProfile` 使用 Pydantic `model_config = {"extra": "allow"}` 支持任意字段
2. **自动提取逻辑**：`_extract_country_business` 遍历 `model_dump()` 结果，自动识别所有 `xxx_by_country` 字段
3. **配置驱动渲染**：前端根据 `/countries/config/all` 返回的配置动态渲染表单
4. **LLM 友好名称**：从国家配置的 `label` 动态获取，无需硬编码

---

## 旧方案迁移指南

如果之前使用的是修改 `schemas.py` 的方式，请按以下步骤迁移到新方案：

### 迁移步骤

1. **删除代码中的字段定义**：从 `BusinessProfile` 中移除手动定义的字段
2. **移到 YAML 配置**：将字段定义添加到 `countries.yaml` 的 `business_fields` 中
3. **删除友好名称映射**：`_FIELD_FRIENDLY_NAMES` 字典不再需要，系统自动从 `label` 读取

### 迁移前后对比

| 项目 | 旧方案 | 新方案 |
|------|--------|--------|
| 新增字段位置 | `schemas.py` + Python 代码 | `countries.yaml` |
| 友好名称 | 硬编码 `_FIELD_FRIENDLY_NAMES` | 配置中的 `label` |
| 前端表单 | 需手动修改 React 代码 | 自动动态渲染 |
| 生效方式 | 代码修改 + 重启 | 修改配置 + 重启 |

---

## 最佳实践

1. **字段命名统一**：使用 `snake_case` 命名，多国字段自动以 `_by_country` 传递
2. **配置完整**：为每个字段提供清晰的 `label` 和 `placeholder`
3. **选项明确**：`select`/`multiselect` 类型必须提供 `options` 数组
4. **规则测试**：新增规则后编写单元测试验证触发逻辑
5. **配置复用**：相同字段在多个国家使用时，可复制配置避免重复输入

---

## 常见问题

### Q: 为什么新增字段没有出现在前端？

**A**: 检查以下几点：
1. 是否已重启后端服务（配置在启动时加载）
2. 前端是否调用了 `/countries/config/all` 获取最新配置
3. 浏览器是否有缓存，刷新页面试试

### Q: 规则没有触发？

**A**: 检查：
1. 规则中的字段名是否与配置中的 `name` 一致（去掉 `_by_country`）
2. YAML 规则的 `condition` 字段引号是否正确
3. 业务数据中是否传入了正确的值

### Q: 不同国家可以有不同的字段吗？

**A**: 完全可以！每个国家有独立的 `business_fields` 配置，前端根据选中国家动态显示对应字段。

### Q: LLM 能识别新字段吗？

**A**: 是的。系统从国家配置的 `label` 字段自动获取友好名称，注入到 LLM 提示词中，无需额外配置。

---

## 后端 API 说明

### 获取所有国家配置

```
GET /api/v1/countries/config/all
```

返回包含所有国家的完整配置，包括业务字段定义：

```json
{
  "TH": {
    "country_code": "TH",
    "country_name": "泰国",
    "currency": "THB",
    "tax_type": "VAT",
    "flag": "🇹🇭",
    "business_fields": [
      {"name": "annual_sales", "label": "年预计销售额", "type": "number", ...},
      ...
    ]
  },
  ...
}
```

前端使用此配置动态生成表单。
