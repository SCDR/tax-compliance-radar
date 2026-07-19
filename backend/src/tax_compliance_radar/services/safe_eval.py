"""安全的规则表达式评估器

基于 simpleeval 实现，仅白名单放行必要的函数和语法，
杜绝代码注入风险，同时支持规则引擎需要的所有条件判断能力。
"""
from __future__ import annotations

import ast
from typing import Any, Dict

from simpleeval import SimpleEval


class SafeRuleEvaluator(SimpleEval):
    """安全的规则表达式评估器

    支持的语法：
    - 比较运算: >, >=, <, <=, ==, !=, in, not in
    - 逻辑运算: and, or, not
    - 列表字面量: ['a', 'b', 'c']
    - 生成器表达式: any(x > 0 for x in list), all(x > 0 for x in list)
    - 三元表达式: 'A' if x > 0 else 'B'

    白名单函数:
    - len(): 计算长度
    - any(): 任意满足
    - all(): 全部满足
    - sum(): 求和
    - max(): 最大值
    - min(): 最小值
    """

    # 默认白名单函数（无副作用的纯函数）
    DEFAULT_FUNCTIONS = {
        "len": len,
        "any": any,
        "all": all,
        "sum": sum,
        "max": max,
        "min": min,
    }

    def __init__(self, names: Dict[str, Any] | None = None):
        super().__init__()
        # 启用白名单函数
        self.functions = self.DEFAULT_FUNCTIONS.copy()
        # 设置变量命名空间
        if names:
            self.names = names
        # 添加 AST 节点支持
        self._add_ast_nodes()

    def _add_ast_nodes(self) -> None:
        """添加规则引擎需要的 AST 节点支持"""
        # 列表字面量: ['a', 'b', 'c']
        self.nodes[ast.List] = self._eval_list

        # 生成器表达式: any(x > 0 for x in list)
        self.nodes[ast.GeneratorExp] = self._eval_generator

    def _eval_list(self, node: ast.List) -> list:
        """求值列表字面量"""
        return [self._eval(x) for x in node.elts]

    def _eval_generator(self, node: ast.GeneratorExp):
        """求值得生成器表达式（简化版：单循环，支持条件过滤）"""
        target = node.elt
        for_iter = node.generators[0]

        iter_val = self._eval(for_iter.iter)
        loop_var = for_iter.target.id

        for item in iter_val:
            # 设置循环变量到命名空间
            self.names[loop_var] = item

            # 检查过滤条件（如有）
            skip = False
            for if_cond in for_iter.ifs:
                if not self._eval(if_cond):
                    skip = True
                    break

            if not skip:
                yield self._eval(target)


def safe_eval_rule(
    condition_expr: str,
    names: Dict[str, Any],
) -> bool:
    """安全评估规则条件表达式

    Args:
        condition_expr: 条件表达式字符串
        names: 变量命名空间字典

    Returns:
        布尔值，表示条件是否满足

    Raises:
        任何表达式求值错误（由调用方处理）
    """
    evaluator = SafeRuleEvaluator(names=names)
    return bool(evaluator.eval(condition_expr))
