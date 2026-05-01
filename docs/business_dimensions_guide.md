# 业务维度扩展开发指南

## 概述

本系统支持**零代码侵入式**业务维度扩展，涵盖**通用维度（全局共用）**和**多国维度（按国家区分）**两类。新增业务维度只需在数据模型中定义字段，即可自动在整个合规检查链路中生效，包括：

- ✅ **通用维度自动扩展**：如企业规模、所属行业等，所有国家共用
- ✅ **多国维度自动扩展**：如销售额、平台等，每个国家可不同
- ✅ 规则引擎自动识别并可用于条件判断
- ✅ AI 风险检测提示词自动注入
- ✅ LLM 建议生成器自动感知
- ✅ 缓存键自动包含维度数据

---

## 快速添加新维度（3 步完成）

### 维度类型

系统支持两种类型的业务维度，**两者都支持自动扩展**：

| 类型 | 命名规范 | 作用域 | 示例 |
|------|----------|--------|------|
| **通用维度** | 普通字段名 | 所有国家共用 | `business_type`, `company_size`, `industry` |
| **多国维度** | `xxx_by_country` 后缀 | 每个国家可不同 | `annual_sales_by_country`, `platforms_by_country` |

---

### 步骤 1: 在 BusinessProfile 中添加字段定义

**文件**: `backend/src/tax_compliance_radar/models/schemas.py`

```python
class BusinessProfile(BaseModel):
    """跨国家通用的业务信息"""
    
    # ===== 通用维度（所有国家共用）=====
    business_type: str  # 现有通用维度
    
    # ✅ 新增通用维度（自动扩展，无需后缀）
    company_size: str = Field(
        default="",
        description="企业规模：小型/中型/大型"
    )
    industry: str = Field(
        default="",
        description="所属行业：3C电子/服饰/美妆等"
    )
    
    # ===== 多国维度（每个国家可不同）=====
    # 字段名必须遵循 xxx_by_country 命名规范
    annual_sales_by_country: Dict[str, int] = Field(
        default_factory=dict,
        description="按国家区分的年销售额"
    )
    platforms_by_country: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="按国家区分的入驻平台"
    )
    
    # ✅ 新增多国维度（自动扩展，需 _by_country 后缀）
    logistics_mode_by_country: Dict[str, str] = Field(
        default_factory=dict,
        description="按国家区分的物流模式：直邮/保税仓/本地仓"
    )
    
    payment_channel_by_country: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="按国家区分的支付渠道列表"
    )
    
    has_import_license_by_country: Dict[str, bool] = Field(
        default_factory=dict,
        description="按国家区分是否有进口许可证"
    )
    
    employee_count_by_country: Dict[str, int] = Field(
        default_factory=dict,
        description="按国家区分的本地员工数量"
    )
```

---

### 步骤 2: 在规则配置中使用新维度

**文件**: `backend/data/rules/{country_code}_rules.yaml`

在规则的 `condition` 字段中直接使用维度名（去掉 `_by_country` 后缀）。

```yaml
rules:
  # ===== 使用新维度的规则示例 =====
  
  - rule_id: TH_R008
    description: 保税仓模式关税申报要求
    category: reporting
    # 直接使用新维度字段名
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
    # 支持列表操作
    condition: "len(set(payment_channel) & {'PayPal', 'Stripe'}) > 0"
    risk_template:
      risk_level: 高风险
      risk_desc: 使用境外支付渠道需在泰国银行进行外汇交易备案
      trigger_condition: 使用 PayPal 或 Stripe 等境外支付渠道
      regulation_base: 泰国外汇管理法
      violation_consequence: 账户冻结、罚款

  - rule_id: TH_R010
    description: 无进口许可证合规风险
    category: registration
    # 支持布尔值判断
    condition: "has_import_license == False and employee_count > 10"
    risk_template:
      risk_level: 高风险
      risk_desc: 员工超过10人但无进口许可证，需尽快办理
      trigger_condition: 无进口许可证且员工数超过阈值
      regulation_base: 泰国进出口贸易法
      violation_consequence: 禁止开展自营进口业务、罚款
```

---

### 步骤 3 (可选): 添加字段友好名称映射

**文件**: 
- `backend/src/tax_compliance_radar/services/ai_risk_detector.py`
- `backend/src/tax_compliance_radar/services/suggestion_generator.py`

添加友好名称以便在 LLM 提示词中正确显示：

```python
_FIELD_FRIENDLY_NAMES = {
    # ===== 已有维度 =====
    "business_type": "业务类型",
    "annual_sales": "年销售额",
    "platforms": "入驻平台",
    
    # ===== 新增维度的友好名称 =====
    "logistics_mode": "物流模式",
    "payment_channel": "支付渠道",
    "has_import_license": "进口许可证",
    "employee_count": "员工数量",
}
```

---

## ✅ 完成！

**无需修改任何核心代码**。新维度将自动：

1. 被 `_extract_country_business` 提取到单国家业务数据
2. **自动注入配置的默认值**（消除 None 歧义）
3. 被规则引擎 `evaluate` 方法注入到 eval 环境
4. 被 AI 风险检测 `get_risk_detection_prompt` 格式化到提示词
5. 被 LLM 建议生成器自动感知并用于建议生成
6. 被缓存键生成 `_get_cache_key` 自动包含
7. **自动记录元数据** `_field_set_flags`（可选使用）

---

### 🎯 设计理念：两全其美的 None 处理

| 问题 | 解决方案 |
|------|---------|
| 无法区分 `annual_sales = 0` vs "未传递" | **元数据标记**：通过 `_field_set_flags` 特殊字段记录字段是否被显式传递 |
| 规则编写者需要写防御代码 `x is not None and x > 0` | **默认值注入**：规则编写者永远不会看到 None，只需写业务逻辑 |
| 向后兼容性 | **可选使用**：元数据字段可选使用，不影响现有规则 |

---

### 📋 可选：高级用法（区分"值为0" vs "未传递"）

**只有需要区分时才使用**，普通场景可以完全忽略：

```yaml
# ===== 普通用法（99% 场景）=====
# 简洁直观，无需关心是否传递
condition: "annual_sales > 1000000"

# ===== 高级用法（1% 特殊场景）=====
# 只有明确传递了字段，才做判断
condition: "_field_set_flags.annual_sales == True and annual_sales > 1000000"

# 针对未传递字段的特殊处理
condition: "_field_set_flags.employee_count == False"  # 员工数字段未传递
```

**元数据字段说明**：
```python
# 自动注入到每个国家的业务数据中
{
  "business_type": "跨境电商零售",
  "annual_sales": 5000000,
  "platforms": ["Shopee"],
  
  # 🌟 元数据：标记每个字段是否被用户显式传递
  "_field_set_flags": {
    "business_type": True,
    "annual_sales": True,
    "platforms": True,
    "employee_count": False,   # 这个字段用户没传
  }
}
```

**配置文件**：`backend/src/tax_compliance_radar/field_config.py`

```python
FIELD_METADATA = {
    "annual_sales": FieldMetadata(
        default_value=0,        # 未传递时自动注入 0
        field_type="int",
        description="年销售额",
    ),
    "has_local_entity": FieldMetadata(
        default_value=False,    # 未传递时自动注入 False
        field_type="bool",
    ),
    "platforms": FieldMetadata(
        default_value=[],       # 未传递时自动注入 []
        field_type="list[str]",
    ),
}
```

**规则编写者只需写**：
```yaml
# ✅ 简洁，无需 None 判断
condition: annual_sales > 1000000
condition: len(platforms) > 0
condition: has_local_entity == True
```

---

## API 请求示例

添加新维度后，前端请求格式如下：

```json
POST /api/v1/multi/audit/submit
{
  "selected_countries": ["TH", "VN"],
  "business_profile": {
    // ===== 通用维度（所有国家共用）=====
    "business_type": "跨境电商零售",
    "company_size": "中型企业",
    "industry": "3C电子产品",
    
    // ===== 多国维度（每个国家可不同）=====
    "annual_sales_by_country": {
      "TH": 5000000,
      "VN": 300000000
    },
    "platforms_by_country": {
      "TH": ["Shopee", "Lazada"],
      "VN": ["TikTok Shop"]
    },
    "logistics_mode_by_country": {
      "TH": "保税仓",
      "VN": "直邮"
    },
    "payment_channel_by_country": {
      "TH": ["PayPal", "Stripe"],
      "VN": ["COD", "Momo"]
    },
    "has_import_license_by_country": {
      "TH": false,
      "VN": true
    },
    "employee_count_by_country": {
      "TH": 25,
      "VN": 15
    }
  }
}
```

**自动提取结果**：
- 泰国规则引擎看到：`{"business_type": "跨境电商零售", "company_size": "中型企业", "industry": "3C电子产品", "annual_sales": 5000000, ...}`
- 越南规则引擎看到：`{"business_type": "跨境电商零售", "company_size": "中型企业", "industry": "3C电子产品", "annual_sales": 300000000, ...}`

---

## 测试新维度

### 运行现有测试
```bash
cd backend
uv run pytest tests/unit/test_extensible_dimensions.py -v
```

### 编写新测试

**文件**: `backend/tests/unit/test_extensible_dimensions.py`

```python
def test_new_dimension_rule():
    """测试新维度规则"""
    engine = CountryRulesEngine.get_for_country("TH")
    config = CountryRegistry.get("TH")
    
    business = {
        "business_type": "跨境电商零售",
        "annual_sales": 5000000,
        "platforms": ["Shopee"],
        "logistics_mode": "保税仓",  # 新维度
    }
    
    def make_source(rid=None, st="rule"):
        return SourceInfo(country_code="TH", country_name="泰国", 
                         regulation_id=rid, source_type=st)
    
    risks = engine.evaluate(business, make_source, config)
    triggered_rules = [r.source_info.regulation_id for r in risks]
    
    assert "TH_R008" in triggered_rules, "保税仓规则未触发"
```

---

## 支持的数据类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `str` | 字符串枚举 | `"保税仓"`, `"直邮"` |
| `int` | 整数数值 | `10000`, `25` |
| `bool` | 布尔值 | `True`, `False` |
| `List[str]` | 字符串列表 | `["PayPal", "Stripe"]` |

---

## 规则表达式语法参考

```yaml
# ===== 通用维度（所有国家共用）=====
condition: business_type == '跨境电商零售'
condition: company_size == '大型企业'
condition: industry == '3C电子产品'

# ===== 多国维度（每个国家可不同）=====
# 简单相等判断
condition: logistics_mode == '保税仓'

# 布尔值判断
condition: has_import_license == False

# 数值比较
condition: employee_count > 10
condition: annual_sales >= 1000000

# 列表包含判断
condition: "'PayPal' in payment_channel"
condition: "len(payment_channel) > 0"

# 集合交集判断
condition: "len(set(payment_channel) & {'PayPal', 'Stripe'}) > 0"

# 多条件组合（通用维度 + 多国维度混合）
condition: "business_type == '跨境电商零售' and logistics_mode == '保税仓'"
condition: "industry == '美妆' and has_import_license == False"
condition: "company_size == '大型企业' or annual_sales > 10000000"
```

---

## 最佳实践

1. **命名规范**: 字段名使用 `snake_case`，`xxx_by_country` 后缀
2. **类型明确**: 明确标注类型（`Dict[str, int]` / `Dict[str, List[str]]` 等）
3. **注释完整**: 添加清晰的 `description` 说明字段用途和可选值
4. **友好名称**: 为 AI 提示词添加中文友好名称映射
5. **规则测试**: 新增规则后编写单元测试验证触发逻辑
6. **文档同步**: 新增维度后同步更新 API 文档和前端接口定义

---

## 常见问题

### Q: 为什么我的规则没有触发？

**A**: 检查以下几点：
1. 维度名是否正确（去掉 `_by_country` 后缀）
2. YAML 规则中 condition 字段的引号是否正确（特殊字符需用双引号包裹）
3. 业务数据中是否传入了正确的值
4. 运行测试查看具体错误信息

### Q: 新维度在 AI 提示词中如何显示？

**A**: 如果配置了 `_FIELD_FRIENDLY_NAMES`，会显示友好名称；否则显示原始字段名。空值或空列表会被自动跳过。

### Q: 新增维度需要重启服务吗？

**A**: 是的，代码修改（`schemas.py`）需要重启服务。但如果只是修改 YAML 规则文件，可以调用 `CountryRulesEngine.reload_all()` 热重载。

### Q: 不同国家可以有不同的维度吗？

**A**: 可以。`BusinessProfile` 中定义的是所有国家的超集，具体某个国家可以不传特定维度的数据，不传的字段将使用默认值（空列表/0/False/空字符串）。

---

## 自动传递链路图

```
API 请求
    │
    ▼
BusinessProfile (xxx_by_country)
    │
    ▼  自动提取
MultiCountryAuditStrategy._extract_country_business
    │
    ▼  自动注入
    ├─────────────┬──────────────┐
    │             │              │
    ▼             ▼              ▼
规则引擎     AI 风险检测   LLM 建议生成
(eval)     (提示词)       (提示词)
    │             │              │
    └─────────────┴──────────────┘
    │
    ▼
风险识别结果 / 合规建议
```
