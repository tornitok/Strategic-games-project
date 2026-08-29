"""Загрузка YAML с запоминанием номеров строк.

Нужна, чтобы ошибка сценария указывала на строку файла, а не на путь внутри
структуры данных: преподаватель правит текст, а не дерево объектов.
"""

from typing import Any

import yaml

LINE_KEY = "__line__"


class _LineLoader(yaml.SafeLoader):
    pass


def _mapping_with_line(loader: _LineLoader, node: yaml.MappingNode) -> dict:
    mapping = loader.construct_mapping(node, deep=True)
    mapping[LINE_KEY] = node.start_mark.line + 1
    return mapping


_LineLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_with_line
)


def load_with_lines(text: str) -> tuple[Any, dict[str, int]]:
    """Разобрать YAML и вернуть данные плюс карту «путь → строка»."""
    raw = yaml.load(text, Loader=_LineLoader)
    lines: dict[str, int] = {}
    cleaned = _strip(raw, (), lines)
    return cleaned, lines


def _strip(node: Any, path: tuple[str, ...], lines: dict[str, int]) -> Any:
    if isinstance(node, dict):
        line = node.pop(LINE_KEY, None)
        if line is not None:
            lines[".".join(path)] = line
        return {k: _strip(v, path + (str(k),), lines) for k, v in node.items()}
    if isinstance(node, list):
        return [_strip(v, path + (str(i),), lines) for i, v in enumerate(node)]
    return node


def line_for(lines: dict[str, int], path: tuple[Any, ...]) -> int | None:
    """Ближайшая известная строка для пути: сам путь или его родитель."""
    parts = [str(p) for p in path]
    while parts:
        candidate = lines.get(".".join(parts))
        if candidate is not None:
            return candidate
        parts.pop()
    return lines.get("")
