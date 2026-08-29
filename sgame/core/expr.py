"""Интерпретатор выражений сценария.

Сценарий — данные, а не код: выражения считает собственный обход AST по
белому списку узлов. `eval` и `exec` не используются.
"""

import ast
import math
import operator
from collections.abc import Mapping
from typing import Any


class ExprError(ValueError):
    """Выражение недопустимо или не вычисляется."""


_ALLOWED = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.Call, ast.Attribute, ast.Name, ast.Load, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)

_FUNCS = {
    "min": min, "max": max, "abs": abs, "round": round,
    "floor": math.floor, "ceil": math.ceil,
    "clamp": lambda value, low, high: max(low, min(high, value)),
}

_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}

_CMP = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
}


def compile_expr(source: str) -> ast.Expression:
    """Разобрать выражение и убедиться, что в нём только разрешённые узлы."""
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ExprError(f"не разбирается как выражение: {source!r}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ExprError(
                f"недопустимая конструкция {type(node).__name__} в выражении {source!r}"
            )
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
            raise ExprError(f"вызывать можно только именованные функции: {source!r}")
        if isinstance(node, ast.Attribute) and not isinstance(node.value, ast.Name):
            raise ExprError(f"вложенные обращения через точку запрещены: {source!r}")
    return tree


def evaluate(source: str, context: Mapping[str, Any]) -> Any:
    """Вычислить выражение в заданном контексте."""
    return _eval(compile_expr(source).body, source, context)


def used_names(source: str) -> tuple[set[str], set[tuple[str, str]]]:
    """Какие имена и какие пары «пространство.поле» встречаются в выражении."""
    tree = compile_expr(source)
    attrs: set[tuple[str, str]] = set()
    inside_attribute: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            attrs.add((node.value.id, node.attr))
            inside_attribute.add(id(node.value))
    bare = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and id(node) not in inside_attribute
    }
    return bare, attrs


def _eval(node: ast.AST, source: str, ctx: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, str)) and not isinstance(node.value, bool):
            return node.value
        raise ExprError(f"недопустимая константа в {source!r}")

    if isinstance(node, ast.Name):
        if node.id in ctx:
            return ctx[node.id]
        if node.id in _FUNCS:
            return _FUNCS[node.id]
        raise ExprError(f"неизвестное имя {node.id!r} в выражении {source!r}")

    if isinstance(node, ast.Attribute):
        namespace = _eval(node.value, source, ctx)
        if not isinstance(namespace, Mapping) or node.attr not in namespace:
            raise ExprError(
                f"неизвестное поле {ast.unparse(node)!r} в выражении {source!r}"
            )
        return namespace[node.attr]

    if isinstance(node, ast.BinOp):
        try:
            return _BIN[type(node.op)](
                _eval(node.left, source, ctx), _eval(node.right, source, ctx)
            )
        except (TypeError, ZeroDivisionError) as exc:
            raise ExprError(f"не вычисляется: {source!r} ({exc})") from exc

    if isinstance(node, ast.UnaryOp):
        value = _eval(node.operand, source, ctx)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        return not value

    if isinstance(node, ast.BoolOp):
        values = [_eval(v, source, ctx) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)

    if isinstance(node, ast.Compare):
        left = _eval(node.left, source, ctx)
        for op, right_node in zip(node.ops, node.comparators):
            right = _eval(right_node, source, ctx)
            if not _CMP[type(op)](left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.IfExp):
        branch = node.body if _eval(node.test, source, ctx) else node.orelse
        return _eval(branch, source, ctx)

    if isinstance(node, ast.Call):
        func = _eval(node.func, source, ctx)
        if not callable(func):
            raise ExprError(f"{ast.unparse(node.func)!r} не функция: {source!r}")
        args = [_eval(a, source, ctx) for a in node.args]
        try:
            return func(*args)
        except Exception as exc:
            raise ExprError(f"ошибка вызова в {source!r}: {exc}") from exc

    raise ExprError(f"недопустимая конструкция в выражении {source!r}")
