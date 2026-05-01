# 国家规则配置说明

## 概览

所有国家的合规规则都存储在独立的 YAML 配置文件中，无需修改代码即可添加/修改规则。

## 文件命名规范

```
{country_code}_rules.yaml
```

示例：
- `th_rules.yaml` - 泰国规则
- `vn_rules.yaml` - 越南规则
- `my_rules.yaml` - 马来西亚规则

## YAML 文件结构

```yaml
# 国家基础信息
country_code: TH
country_name: 泰国
version: 1.0
description: 泰国跨境电商 VAT 合规审核规则

# 审核规则列表
rules:
  - rule_id: TH_R001
    description: 规则描述
    category: registration  # 分类: registration/platform/reporting
    condition: "业务判断条件（Python 表达式）"
    risk_template:
      risk_level: 高风险  # 高风险/中风险/低风险
      risk_desc: 风险描述（可包含模板变量，如 {registration_threshold}）
      trigger_condition: 触发条件描述
      regulation_base: 法规依据
      violation_consequence: 违规后果

# 默认建议列表
suggestions:
  - type: general  # general/professional
    content: 建议内容
```

## 支持的模板变量

在 `risk_desc` 和 `trigger_condition` 中可使用以下模板变量：

| 变量 | 说明 |
|------|------|
| `{registration_threshold}` | 国家注册阈值（金额） |
| `{}` | 位置占位符，会被平台列表字符串替换 |

## 条件表达式（condition）

`condition` 字段是有效的 Python 表达式，可用以下变量：

| 变量 | 类型 | 说明 |
|------|------|------|
| `business_type` | str | 业务类型（'跨境电商零售', '品牌出海直营' 等） |
| `annual_sales` | int | 年销售额（本币） |
| `platforms` | list | 入驻平台列表 |
| `registration_threshold` | int | 国家注册阈值 |

## 条件表达式示例

```yaml
# 业务类型判断
condition: "business_type in ['跨境电商零售', '品牌出海直营']"

# 销售额判断
condition: "annual_sales >= registration_threshold"

# 平台判断
condition: "len(platforms) > 0"

# 组合条件
condition: "annual_sales >= registration_threshold and len(platforms) > 0"

# 始终触发
condition: "True"
```

## 添加新国家的完整步骤

### 1. 添加国家配置

创建 `src/tax_compliance_radar/registry/countries/{country_code}.py`：

```python
from tax_compliance_radar.registry.base import CountryConfig

{COUNTRY}_CONFIG = CountryConfig(
    country_code="XX",
    country_name="国家名称",
    currency="XXX",
    currency_symbol="货币符号",
    tax_type="VAT",
    tax_rate=7.0,
    registration_threshold=1000000,
    language="zh",
    business_types=["跨境电商零售", "品牌出海直营"],
    platforms=["Shopee", "Lazada"],
)
```

### 2. 添加规则配置文件

创建 `data/rules/{country_code}_rules.yaml`

### 3. 添加策略类

创建 `src/tax_compliance_radar/strategies/str_{country_code}.py`：

```python
from tax_compliance_radar.strategies.base import BaseAuditStrategy

class CountryVATStrategy(BaseAuditStrategy):
    def __init__(self):
        super().__init__("XX")

def get_strategy() -> CountryVATStrategy:
    return CountryVATStrategy()
```

### 4. 测试验证

```bash
# 验证规则加载
uv run python -c "
from tax_compliance_radar.strategies.str_xx import CountryVATStrategy
strategy = CountryVATStrategy()
print(f'规则数: {len(strategy.rules_engine.rules)}')
"
```

## 热更新规则

修改 YAML 文件后，可以调用以下方法重新加载规则而无需重启服务：

```python
from tax_compliance_radar.services.country_rules_engine import CountryRulesEngine

CountryRulesEngine.reload_all()
```

## 查看现有规则

```bash
# 列出所有有规则配置的国家
uv run python -c "
from tax_compliance_radar.services.country_rules_engine import CountryRulesEngine
print(CountryRulesEngine.list_available_countries())
"
```
