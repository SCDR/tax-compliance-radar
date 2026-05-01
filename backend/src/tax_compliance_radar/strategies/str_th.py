"""泰国 VAT 策略 - 所有规则来自 YAML 配置

文件位置: data/rules/th_rules.yaml

新增/修改规则请编辑 YAML 配置文件，无需修改代码。
"""
from __future__ import annotations

from tax_compliance_radar.strategies.base import BaseAuditStrategy


class ThailandVATStrategy(BaseAuditStrategy):
    """泰国VAT审核策略

    所有规则和建议都来自 YAML 配置文件：
    backend/data/rules/th_rules.yaml
    """

    def __init__(self):
        super().__init__("TH")

    def get_qa_prompt_template(self) -> str:
        """获取泰国VAT QA系统提示词模板"""
        return f"""
你是专业的泰国VAT合规助手，必须严格遵守以下规则：

【核心原则 - 违反即幻觉，一票否决】
1. 只依据给定的【检索到的相关法规】内容回答，绝对不能编造法规或提供不确定的信息
2. 如果检索结果显示"未检索到相关合规信息"或"暂无相关合规信息"，必须如实告知用户，不能臆测
3. 所有回答必须引用具体法规来源，禁止使用"根据相关法规"等模糊表述
4. 禁止回答与泰国VAT合规无关的问题

【输出结构 - 严格JSON格式】
- regulation_base: 列出引用的具体法规名称及来源（如"泰国VAT注册规则（https://...）"）
- core_rules: 提炼核心合规规则，用简洁清晰的中文表述
- compliance_suggestion: 具体可行的合规建议
- risk_warning: 不遵守规则的具体风险后果
- operation_guide: 操作指引，分步骤说明
- original_link: 引用法规的原文链接，多个链接用分号分隔
- disclaimer: 固定免责声明文本

【重要提醒】
所有引用的法规都来自泰国，请确保回答中明确标注是针对泰国的建议。
""".strip()

    def get_audit_prompt_template(self) -> str:
        """获取泰国VAT审核增强提示词"""
        return f"""
你是专业的泰国VAT合规审核官，必须基于提供的业务信息、风险点和检索到的法规内容生成增强型审核报告。

【核心原则 - 必须严格遵守】
1. 专业建议必须基于【检索到的相关法规】内容，并明确标注法规来源
2. 通用建议可以基于合规最佳实践，但不得编造具体法规名称、编号或发布日期
3. 两类建议必须明确区分：专业建议（有来源）、通用建议（无具体法规引用）

【输出格式 - 严格JSON格式】
{{
    "professional_suggestions": [
        "基于《[法规名称]》：[专业建议内容，引用具体法规]"
    ],
    "general_suggestions": [
        "[通用合规建议，不涉及具体法规编号]"
    ],
    "attachment_guide": "需要准备的材料清单和流程指引说明"
}}

【重要约束】
1. professional_suggestions 中的每条建议必须引用检索到的具体法规名称
2. 如果没有检索到相关法规，professional_suggestions 返回空数组
3. general_suggestions 必须是不涉及具体法规编号的通用合规最佳实践
4. 所有建议都必须针对泰国VAT税务环境
""".strip()


def get_strategy() -> ThailandVATStrategy:
    """获取泰国VAT策略实例"""
    return ThailandVATStrategy()
