# Движок стратегических игр, этап 1 — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Довести до состояния «можно провести пару»: детерминированное ядро правил, декларативный сценарий с валидатором, три веб-экрана для hot-seat игры, шаблонный нарратив, эталонная игра и собранное `.app`.

**Architecture:** Ядро — чистые функции без ввода-вывода: `resolve(spec, state, orders, ...) -> (state', события)`. Сессия хранится как журнал приказов, состояние получается пересчётом журнала — отсюда откат и воспроизводимость. Веб (FastAPI + Jinja2) и нарратив — адаптеры вокруг ядра, зависимости направлены только внутрь.

**Tech Stack:** Python 3.11+, pydantic v2, PyYAML, FastAPI, Uvicorn, Jinja2, pytest, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-08-29-strategic-game-engine-design.md`

## Global Constraints

- Python 3.11 или новее.
- Только чистый Python в зависимостях: `pydantic>=2`, `pyyaml`, `fastapi`, `uvicorn`, `jinja2`, `python-multipart`. Ничего скомпилированного — иначе сломается сборка `.app`.
- `eval` и `exec` не используются нигде в проекте. Выражения сценария считает собственный интерпретатор на белом списке узлов AST.
- Зависимости слоёв строго направлены внутрь: `web` → `session` → `core`; `narrate` зависит только от `core`. Ядро не импортирует FastAPI, не читает файлы, не ходит в сеть.
- Глобальный `random` не используется. Каждый бросок берётся из потока `Random(blake2b(f"{seed}|{round}|{roll_id}").digest())`.
- Весь текст интерфейса и все сообщения об ошибках — на русском языке.
- Данные пользователя — только в `~/Library/Application Support/StrategicGame/`. Внутрь пакета ничего не пишется.
- Ресурсы (шаблоны, статика, сценарии) читаются через `importlib.resources`, не через `__file__` и не по относительным путям.
- Расчёт раунда для 6 команд — меньше секунды.
- Каждая задача заканчивается коммитом. Тест пишется раньше кода.

---

## Карта файлов

| Файл | Ответственность |
|---|---|
| `pyproject.toml` | Пакет `sgame`, зависимости, точка входа `sgame` |
| `sgame/core/errors.py` | `Problem`, `ScenarioError` — единый формат ошибок сценария |
| `sgame/core/expr.py` | Интерпретатор выражений на белом списке узлов AST |
| `sgame/core/yamlsrc.py` | Загрузка YAML с картой «путь → номер строки» |
| `sgame/core/spec.py` | Pydantic-модели сценария, `load_scenario` |
| `sgame/core/validate.py` | Шесть классов смысловых проверок сценария |
| `sgame/core/state.py` | `GameState` (неизменяемое), `StateBuilder` (рабочая копия) |
| `sgame/core/rng.py` | Детерминированные потоки случайности |
| `sgame/core/events.py` | `Delta`, `Event`, аудитория события |
| `sgame/core/orders.py` | `Order`, `DealOffer` |
| `sgame/core/phases.py` | Восемь фаз раунда, каждая — отдельная функция |
| `sgame/core/scoring.py` | Подсчёт очков и проверка конца игры |
| `sgame/core/resolve.py` | Склейка фаз в `resolve()` |
| `sgame/session/paths.py` | Пользовательские директории |
| `sgame/session/journal.py` | Формат журнала, чтение и запись |
| `sgame/session/replay.py` | Пересчёт журнала в состояние, откат раунда |
| `sgame/narrate/view.py` | Фильтрация событий и состояния по зрителю |
| `sgame/narrate/templates.py` | Шаблонный нарратив |
| `sgame/web/app.py` | Сборка приложения, запуск, открытие браузера |
| `sgame/web/routes/host.py` | Пульт ведущего |
| `sgame/web/routes/team.py` | Экран команды |
| `sgame/web/routes/screen.py` | Проектор |
| `sgame/web/templates/*.html` | Jinja2-шаблоны |
| `sgame/scenarios/meridian.yaml` | Эталонная игра |
| `sgame/cli.py` | `sgame run`, `sgame validate` |
| `packaging/sgame.spec`, `packaging/ИНСТРУКЦИЯ.md` | Сборка `.app` и памятка получателю |

---

## Task 1: Каркас проекта и интерпретатор выражений

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `sgame/__init__.py`, `sgame/core/__init__.py`, `sgame/core/errors.py`, `sgame/core/expr.py`
- Test: `tests/test_expr.py`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `Problem(line: int | None, message: str)` — датакласс, `str(problem)` даёт `"строка N: текст"`, при `line is None` — просто текст
  - `ScenarioError(Exception)` с полем `problems: list[Problem]`
  - `ExprError(ValueError)`
  - `compile_expr(source: str) -> ast.Expression` — проверяет допустимость, кидает `ExprError`
  - `evaluate(source: str, context: Mapping[str, Any]) -> float | bool`

- [ ] **Step 1: Инициализировать репозиторий и структуру**

```bash
cd "/Users/klim/Desktop/Strategic games project"
git init
mkdir -p sgame/core sgame/session sgame/narrate sgame/web/routes sgame/web/templates sgame/scenarios tests packaging
touch sgame/__init__.py sgame/core/__init__.py sgame/session/__init__.py sgame/narrate/__init__.py sgame/web/__init__.py sgame/web/routes/__init__.py
touch tests/__init__.py   # чтобы тесты могли импортировать друг у друга общий сценарий
printf '__pycache__/\n*.pyc\n.venv/\nbuild/\ndist/\n.pytest_cache/\n' > .gitignore
```

- [ ] **Step 2: Написать `pyproject.toml`**

```toml
[project]
name = "sgame"
version = "0.1.0"
description = "Движок текстовых стратегических игр для учебных занятий"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "pyyaml>=6",
    "fastapi>=0.110",
    "uvicorn>=0.29",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27", "pyinstaller>=6.5"]

[project.scripts]
sgame = "sgame.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["sgame*"]

[tool.setuptools.package-data]
sgame = ["web/templates/*.html", "web/static/*", "scenarios/*.yaml"]
```

Установить: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`

- [ ] **Step 3: Написать падающий тест `tests/test_expr.py`**

```python
import pytest
from sgame.core.expr import ExprError, evaluate


def test_arithmetic():
    assert evaluate("2 + 2 * 3", {}) == 8


def test_namespace_attribute():
    assert evaluate("self.army * 0.5", {"self": {"army": 60}}) == 30.0


def test_functions():
    assert evaluate("clamp(120, 0, 100)", {}) == 100
    assert evaluate("min(3, 5) + max(1, 2)", {}) == 5


def test_comparison_and_logic():
    assert evaluate("self.intel >= 10 and round < 5", {"self": {"intel": 40}, "round": 2}) is True


def test_ternary():
    assert evaluate("10 if world.tension > 50 else 1", {"world": {"tension": 70}}) == 10


def test_context_callable():
    ctx = {"rel": lambda a, b: -20}
    assert evaluate('rel("astoria", "borea")', ctx) == -20


def test_rejects_import():
    with pytest.raises(ExprError):
        evaluate("__import__('os').listdir('.')", {})


def test_rejects_lambda():
    with pytest.raises(ExprError):
        evaluate("(lambda: 1)()", {})


def test_rejects_subscript():
    with pytest.raises(ExprError):
        evaluate("self['army']", {"self": {"army": 1}})


def test_unknown_name_message_names_it():
    with pytest.raises(ExprError) as exc:
        evaluate("self.cyberdef + 1", {"self": {"army": 1}})
    assert "cyberdef" in str(exc.value)


def test_syntax_error_is_expr_error():
    with pytest.raises(ExprError):
        evaluate("2 +", {})
```

- [ ] **Step 4: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_expr.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sgame.core.expr'`

- [ ] **Step 5: Написать `sgame/core/errors.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    """Одна ошибка в сценарии, привязанная к строке файла."""

    message: str
    line: int | None = None

    def __str__(self) -> str:
        return f"строка {self.line}: {self.message}" if self.line else self.message


class ScenarioError(Exception):
    """Сценарий не удалось загрузить или он не прошёл проверки."""

    def __init__(self, problems: list[Problem]) -> None:
        self.problems = problems
        super().__init__("; ".join(str(p) for p in problems))
```

- [ ] **Step 6: Написать `sgame/core/expr.py`**

```python
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
```

- [ ] **Step 7: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_expr.py -v`
Expected: PASS, 11 тестов

- [ ] **Step 8: Коммит**

```bash
git add pyproject.toml .gitignore sgame tests docs
git commit -m "feat: каркас проекта и интерпретатор выражений сценария"
```

---

## Task 2: Схема сценария и загрузчик с номерами строк

**Files:**
- Create: `sgame/core/yamlsrc.py`, `sgame/core/spec.py`
- Test: `tests/test_spec.py`

**Interfaces:**
- Consumes: `Problem`, `ScenarioError` из `core/errors.py`
- Produces:
  - `load_with_lines(text: str) -> tuple[Any, dict[str, int]]` — данные и карта «путь вида `actions.2.cost` → номер строки»
  - Модели: `TrackSpec`, `WorldTrackSpec`, `GoalSpec`, `FactionSpec`, `EffectSpec`, `RiskOutcome`, `ActionSpec`, `DealSpec`, `EventSpec`, `EndSpec`, `MetaSpec`, `RelationsSpec`, `ScenarioSpec`
  - `ScenarioSpec.action(action_id: str) -> ActionSpec | None`, `.faction(faction_id: str) -> FactionSpec | None`
  - `load_scenario(path: Path) -> ScenarioSpec` — кидает `ScenarioError`
  - `parse_scenario(text: str) -> ScenarioSpec` — то же для строки, используется в тестах

- [ ] **Step 1: Написать падающий тест `tests/test_spec.py`**

```python
import pytest
from sgame.core.errors import ScenarioError
from sgame.core.spec import parse_scenario

MINIMAL = """
schema_version: 1
meta: { id: t, title: "Тест", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100, visibility: public }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 50 } }
  - { id: b, title: "Б", start: { budget: 50 } }
actions:
  - id: grow
    title: "Рост"
    cost: { budget: 10 }
    effects:
      - { self: budget, delta: "5" }
end:
  when: "round > meta.rounds"
  scoring: "self.budget"
"""


def test_loads_minimal_scenario():
    spec = parse_scenario(MINIMAL)
    assert spec.meta.rounds == 3
    assert spec.action("grow").ap == 1
    assert spec.faction("b").title == "Б"


def test_effect_self_alias_is_readable():
    spec = parse_scenario(MINIMAL)
    effect = spec.action("grow").effects[0]
    assert effect.self_track == "budget"
    assert effect.delta == "5"


def test_unknown_field_is_rejected_with_line():
    text = MINIMAL.replace('title: "Рост"', 'title: "Рост"\n    цена: 5')
    with pytest.raises(ScenarioError) as exc:
        parse_scenario(text)
    assert exc.value.problems[0].line is not None


def test_missing_required_field_reports_path():
    text = MINIMAL.replace("rounds: 3, ", "")
    with pytest.raises(ScenarioError) as exc:
        parse_scenario(text)
    assert "rounds" in str(exc.value)


def test_future_schema_version_rejected():
    text = MINIMAL.replace("schema_version: 1", "schema_version: 99")
    with pytest.raises(ScenarioError) as exc:
        parse_scenario(text)
    assert "99" in str(exc.value)
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_spec.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sgame.core.spec'`

- [ ] **Step 3: Написать `sgame/core/yamlsrc.py`**

```python
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
```

- [ ] **Step 4: Написать `sgame/core/spec.py`**

```python
"""Схема сценария: то, что преподаватель пишет в YAML."""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import Problem, ScenarioError
from .yamlsrc import line_for, load_with_lines

SCHEMA_VERSION = 1


class Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class MetaSpec(Base):
    id: str
    title: str
    rounds: int = Field(ge=1)
    action_points: int = Field(ge=1)


class TrackSpec(Base):
    title: str
    min: float
    max: float
    visibility: Literal["public", "private"] = "public"


class WorldTrackSpec(Base):
    title: str
    min: float
    max: float
    start: float


class GoalSpec(Base):
    id: str
    title: str
    when: str
    score: float


class FactionSpec(Base):
    id: str
    title: str
    start: dict[str, float]
    briefing: str = ""
    goals: list[GoalSpec] = []


class EffectSpec(Base):
    """Ровно одна форма адресации плюс обязательная дельта."""

    self_track: str | None = Field(default=None, alias="self")
    target: str | None = None
    world: str | None = None
    all: str | None = None
    relation: list[str] | None = None
    delta: str


class RiskOutcome(Base):
    p: float = Field(ge=0, le=1)
    title: str = ""
    effects: list[EffectSpec] = []


class ActionSpec(Base):
    id: str
    title: str
    description: str = ""
    ap: int = Field(default=1, ge=1)
    cost: dict[str, float] = {}
    requires: str | None = None
    target: Literal["none", "faction"] = "none"
    visibility: Literal["open", "secret"] = "open"
    reveal_chance: float = Field(default=0.0, ge=0, le=1)
    countered_by: list[str] = []
    counter_multiplier: float = Field(default=0.0, ge=0, le=1)
    effects: list[EffectSpec] = []
    risk: list[RiskOutcome] = []


class DealSpec(Base):
    id: str
    title: str
    kind: Literal["resource", "status"]
    track: str | None = None
    duration: int | None = None


class EventSpec(Base):
    id: str
    when: str
    title: str
    text: str = ""
    once: bool = False
    effects: list[EffectSpec] = []


class RelationPair(Base):
    a: str
    b: str
    value: float


class RelationsSpec(Base):
    default: float = 0
    pairs: list[RelationPair] = []


class EndSpec(Base):
    when: str
    scoring: str


class ScenarioSpec(Base):
    schema_version: int
    meta: MetaSpec
    tracks: dict[str, TrackSpec]
    world: dict[str, WorldTrackSpec] = {}
    factions: list[FactionSpec]
    relations: RelationsSpec = RelationsSpec()
    actions: list[ActionSpec]
    deals: list[DealSpec] = []
    world_dynamics: list[EffectSpec] = []
    events: list[EventSpec] = []
    end: EndSpec

    def action(self, action_id: str) -> ActionSpec | None:
        return next((a for a in self.actions if a.id == action_id), None)

    def faction(self, faction_id: str) -> FactionSpec | None:
        return next((f for f in self.factions if f.id == faction_id), None)

    def deal(self, deal_id: str) -> DealSpec | None:
        return next((d for d in self.deals if d.id == deal_id), None)


def parse_scenario(text: str) -> ScenarioSpec:
    data, lines = load_with_lines(text)
    if not isinstance(data, dict):
        raise ScenarioError([Problem("файл сценария должен быть отображением ключ-значение")])

    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ScenarioError([
            Problem(
                f"версия схемы {version!r} не поддерживается, нужна {SCHEMA_VERSION}",
                line_for(lines, ("schema_version",)),
            )
        ])

    try:
        return ScenarioSpec.model_validate(data)
    except ValidationError as exc:
        raise ScenarioError(
            [
                Problem(
                    f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}",
                    line_for(lines, err["loc"]),
                )
                for err in exc.errors()
            ]
        ) from exc


def load_scenario(path: Path) -> ScenarioSpec:
    return parse_scenario(Path(path).read_text(encoding="utf-8"))


def scenario_lines(text: str) -> dict[str, int]:
    """Карта «путь → строка» для того же текста: нужна валидатору."""
    _, lines = load_with_lines(text)
    return lines


def scenario_data(text: str) -> Any:
    data, _ = load_with_lines(text)
    return data
```

- [ ] **Step 5: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_spec.py -v`
Expected: PASS, 5 тестов

- [ ] **Step 6: Коммит**

```bash
git add sgame/core/yamlsrc.py sgame/core/spec.py tests/test_spec.py
git commit -m "feat: схема сценария и загрузчик с номерами строк"
```

---

## Task 3: Валидатор сценария и команда `sgame validate`

Шесть классов проверок из спеки в конкретной формулировке: (1) ссылки на неизвестные треки, стороны и действия; (2) сумма вероятностей в `risk` не равна единице; (3) выражение не разбирается; (4) выражение обращается к неизвестному имени — сюда же попадают цели с несуществующим треком; (5) стартовое значение вне границ трека или трек в `start` не описан; (6) действие числится в собственном `countered_by`.

**Files:**
- Create: `sgame/core/validate.py`, `sgame/cli.py`
- Modify: `sgame/core/expr.py` (добавить `used_names`)
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `ScenarioSpec`, `scenario_lines`, `Problem`, `compile_expr`
- Produces:
  - `used_names(source: str) -> tuple[set[str], set[tuple[str, str]]]` — голые имена и пары `(пространство, поле)`
  - `validate_scenario(spec: ScenarioSpec, lines: dict[str, int]) -> list[Problem]`
  - `sgame validate <файл>` — печатает `файл:строка: сообщение`, код возврата 1 при ошибках

- [ ] **Step 1: Написать падающий тест `tests/test_validate.py`**

```python
from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.validate import validate_scenario

BASE = """
schema_version: 1
meta: { id: t, title: "Тест", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 50 } }
  - { id: b, title: "Б", start: { budget: 50 } }
actions:
  - id: grow
    title: "Рост"
    cost: { budget: 10 }
    effects:
      - { self: budget, delta: "5" }
end:
  when: "round > meta.rounds"
  scoring: "self.budget"
"""


def problems_for(text):
    spec = parse_scenario(text)
    return validate_scenario(spec, scenario_lines(text))


def test_clean_scenario_has_no_problems():
    assert problems_for(BASE) == []


def test_unknown_track_in_effect():
    text = BASE.replace("{ self: budget, delta: \"5\" }", "{ self: cyberdef, delta: \"5\" }")
    problems = problems_for(text)
    assert any("cyberdef" in p.message for p in problems)
    assert all(p.line is not None for p in problems)


def test_risk_probabilities_must_sum_to_one():
    text = BASE.replace(
        '    effects:\n      - { self: budget, delta: "5" }',
        '    risk:\n      - { p: 0.5, effects: [ { self: budget, delta: "5" } ] }\n'
        '      - { p: 0.2, effects: [ { self: budget, delta: "1" } ] }',
    )
    assert any("вероятност" in p.message for p in problems_for(text))


def test_broken_expression_syntax():
    text = BASE.replace('delta: "5"', 'delta: "5 +"')
    assert any("не разбирается" in p.message for p in problems_for(text))


def test_unknown_name_in_expression():
    text = BASE.replace('scoring: "self.budget"', 'scoring: "self.reputation"')
    assert any("reputation" in p.message for p in problems_for(text))


def test_start_value_out_of_bounds():
    text = BASE.replace("start: { budget: 50 } }\n  - { id: b", "start: { budget: 500 } }\n  - { id: b")
    assert any("500" in p.message or "границ" in p.message for p in problems_for(text))


def test_action_counters_itself():
    text = BASE.replace('    cost: { budget: 10 }', '    cost: { budget: 10 }\n    countered_by: [ grow ]')
    assert any("само" in p.message for p in problems_for(text))
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_validate.py -v`
Expected: FAIL — нет модуля `sgame.core.validate`

- [ ] **Step 3: Добавить `used_names` в `sgame/core/expr.py`**

```python
def used_names(source: str) -> tuple[set[str], set[tuple[str, str]]]:
    """Какие имена и какие пары «пространство.поле» встречаются в выражении."""
    tree = compile_expr(source)
    bare: set[str] = set()
    attrs: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            attrs.add((node.value.id, node.attr))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            parent_attr = any(node is a.value for a in ast.walk(tree)
                              if isinstance(a, ast.Attribute))
            if not parent_attr:
                bare.add(node.id)
    return bare, attrs
```

- [ ] **Step 4: Написать `sgame/core/validate.py`**

```python
"""Смысловые проверки сценария поверх схемы.

Схема отвечает за форму (типы, обязательные поля), этот модуль — за смысл:
ссылки, вероятности, выражения, границы.
"""

from .errors import Problem
from .expr import ExprError, used_names
from .spec import EffectSpec, ScenarioSpec
from .yamlsrc import line_for

_FUNC_NAMES = {"min", "max", "abs", "round", "floor", "ceil", "clamp", "rel"}


def validate_scenario(spec: ScenarioSpec, lines: dict[str, int]) -> list[Problem]:
    problems: list[Problem] = []
    tracks = set(spec.tracks)
    world_tracks = set(spec.world)
    factions = {f.id for f in spec.factions}
    actions = {a.id for a in spec.actions}

    def at(*path):
        return line_for(lines, path)

    def check_effects(effects: list[EffectSpec], path: tuple, where: str) -> None:
        for i, effect in enumerate(effects):
            line = at(*path, i)
            for name in (effect.self_track, effect.target, effect.all):
                if name is not None and name not in tracks:
                    problems.append(Problem(f"{where}: неизвестный трек {name!r}", line))
            if effect.world is not None and effect.world not in world_tracks:
                problems.append(
                    Problem(f"{where}: неизвестный мировой трек {effect.world!r}", line)
                )
            if effect.relation is not None and len(effect.relation) != 2:
                problems.append(
                    Problem(f"{where}: relation должен задавать ровно две стороны", line)
                )
            check_expression(effect.delta, f"{where}: delta", line)

    def check_expression(source: str, where: str, line: int | None) -> None:
        try:
            bare, attrs = used_names(source)
        except ExprError as exc:
            problems.append(Problem(f"{where}: {exc}", line))
            return
        for name in bare:
            if name not in {"round"} | _FUNC_NAMES:
                problems.append(Problem(f"{where}: неизвестное имя {name!r}", line))
        for namespace, field in attrs:
            if namespace in {"self", "target", "all"}:
                if field not in tracks:
                    problems.append(
                        Problem(f"{where}: неизвестный трек {namespace}.{field}", line)
                    )
            elif namespace == "world":
                if field not in world_tracks:
                    problems.append(
                        Problem(f"{where}: неизвестный мировой трек world.{field}", line)
                    )
            elif namespace == "meta":
                if field != "rounds":
                    problems.append(Problem(f"{where}: у meta есть только rounds", line))
            else:
                problems.append(
                    Problem(f"{where}: неизвестное пространство имён {namespace!r}", line)
                )

    for i, faction in enumerate(spec.factions):
        line = at("factions", i)
        for name, value in faction.start.items():
            if name not in tracks:
                problems.append(
                    Problem(f"сторона {faction.id!r}: неизвестный трек {name!r}", line)
                )
                continue
            track = spec.tracks[name]
            if not track.min <= value <= track.max:
                problems.append(
                    Problem(
                        f"сторона {faction.id!r}: начальное значение {value} для {name!r} "
                        f"вне границ {track.min}–{track.max}",
                        line,
                    )
                )
        for missing in tracks - set(faction.start):
            problems.append(
                Problem(f"сторона {faction.id!r}: не задано начальное значение {missing!r}", line)
            )
        for j, goal in enumerate(faction.goals):
            check_expression(goal.when, f"цель {goal.id!r}", at("factions", i, "goals", j))

    for i, action in enumerate(spec.actions):
        line = at("actions", i)
        where = f"действие {action.id!r}"
        for name in action.cost:
            if name not in tracks:
                problems.append(Problem(f"{where}: неизвестный трек в стоимости {name!r}", line))
        if action.requires:
            check_expression(action.requires, f"{where}: requires", line)
        for counter in action.countered_by:
            if counter == action.id:
                problems.append(Problem(f"{where}: действие гасит само себя", line))
            elif counter not in actions:
                problems.append(Problem(f"{where}: неизвестное контрдействие {counter!r}", line))
        check_effects(action.effects, ("actions", i, "effects"), where)
        if action.risk:
            total = sum(outcome.p for outcome in action.risk)
            if abs(total - 1.0) > 1e-6:
                problems.append(
                    Problem(f"{where}: сумма вероятностей исходов {total}, должна быть 1", line)
                )
            for j, outcome in enumerate(action.risk):
                check_effects(outcome.effects, ("actions", i, "risk", j, "effects"), where)

    for i, deal in enumerate(spec.deals):
        line = at("deals", i)
        if deal.kind == "resource" and deal.track not in tracks:
            problems.append(Problem(f"сделка {deal.id!r}: неизвестный трек {deal.track!r}", line))
        if deal.kind == "status" and not deal.duration:
            problems.append(Problem(f"сделка {deal.id!r}: у статуса должен быть duration", line))

    for i, event in enumerate(spec.events):
        line = at("events", i)
        check_expression(event.when, f"событие {event.id!r}: when", line)
        check_effects(event.effects, ("events", i, "effects"), f"событие {event.id!r}")

    check_effects(spec.world_dynamics, ("world_dynamics",), "world_dynamics")
    check_expression(spec.end.when, "end.when", at("end"))
    check_expression(spec.end.scoring, "end.scoring", at("end"))

    unknown_factions = {p.a for p in spec.relations.pairs} | {p.b for p in spec.relations.pairs}
    for name in unknown_factions - factions:
        problems.append(Problem(f"relations: неизвестная сторона {name!r}", at("relations")))

    return problems
```

- [ ] **Step 5: Написать `sgame/cli.py`**

```python
"""Точка входа: sgame run | validate."""

import argparse
import sys
from pathlib import Path

from .core.errors import ScenarioError
from .core.spec import load_scenario, scenario_lines
from .core.validate import validate_scenario


def _validate(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    try:
        spec = load_scenario(path)
    except ScenarioError as exc:
        for problem in exc.problems:
            print(f"{path.name}:{problem.line or 0}: {problem.message}")
        return 1

    problems = validate_scenario(spec, scenario_lines(text))
    for problem in problems:
        print(f"{path.name}:{problem.line or 0}: {problem.message}")
    if problems:
        print(f"Найдено проблем: {len(problems)}")
        return 1
    print(f"{path.name}: сценарий в порядке")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sgame", description="Движок стратегических игр")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate", help="проверить файл сценария")
    validate_cmd.add_argument("path", type=Path)

    run_cmd = sub.add_parser("run", help="запустить приложение")
    run_cmd.add_argument("--port", type=int, default=0)
    run_cmd.add_argument("--no-browser", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "validate":
        return _validate(args.path)

    from .web.app import serve

    serve(port=args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Заглушка `sgame/web/app.py` появится в задаче 12; до неё команда `run` не вызывается.

- [ ] **Step 6: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_validate.py -v`
Expected: PASS, 7 тестов

- [ ] **Step 7: Коммит**

```bash
git add sgame/core/validate.py sgame/core/expr.py sgame/cli.py tests/test_validate.py
git commit -m "feat: валидатор сценария и команда sgame validate"
```

---

## Task 4: Случайность, события и приказы

**Files:**
- Create: `sgame/core/rng.py`, `sgame/core/events.py`, `sgame/core/orders.py`
- Test: `tests/test_rng.py`, `tests/test_events.py`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `stream(seed: int, round_no: int, roll_id: str) -> random.Random`
  - `choose(rng, weights: Sequence[float]) -> int`
  - `happens(rng, chance: float) -> bool`
  - `Delta(scope, who, track, amount, clamped)` и `Delta.describe() -> str`
  - `Event(kind, title, actor, target, detail, deltas, audience, roll)`
  - `Audience = Literal["public", "actor", "actor_and_target", "host"]`
  - `Order(action: str, target: str | None, intent: str)`
  - `DealOffer(id: str, deal: str, sender: str, receiver: str, amount: float | None)`

- [ ] **Step 1: Написать падающий тест `tests/test_rng.py`**

```python
from sgame.core.rng import choose, happens, stream


def test_same_key_gives_same_numbers():
    a = stream(42, 3, "astoria:1:cyber_op").random()
    b = stream(42, 3, "astoria:1:cyber_op").random()
    assert a == b


def test_different_roll_ids_are_independent():
    a = stream(42, 3, "astoria:1:cyber_op").random()
    b = stream(42, 3, "borea:1:cyber_op").random()
    assert a != b


def test_choose_respects_weights_at_boundaries():
    class Fixed:
        def __init__(self, value):
            self.value = value

        def random(self):
            return self.value

    assert choose(Fixed(0.0), [0.5, 0.3, 0.2]) == 0
    assert choose(Fixed(0.6), [0.5, 0.3, 0.2]) == 1
    assert choose(Fixed(0.99), [0.5, 0.3, 0.2]) == 2


def test_happens_never_and_always():
    rng = stream(1, 1, "x")
    assert happens(rng, 0.0) is False
    assert happens(rng, 1.0) is True
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_rng.py -v`
Expected: FAIL — нет модуля `sgame.core.rng`

- [ ] **Step 3: Написать `sgame/core/rng.py`**

```python
"""Детерминированные потоки случайности.

Глобальный генератор не используется: каждый бросок получает собственный
поток, выведенный из ключа партии, номера раунда и идентификатора броска.
Поэтому порядок вычислений не влияет на результат, а пересчёт журнала
воспроизводит те же исходы.
"""

import random
from collections.abc import Sequence
from hashlib import blake2b


def stream(seed: int, round_no: int, roll_id: str) -> random.Random:
    key = f"{seed}|{round_no}|{roll_id}".encode("utf-8")
    return random.Random(blake2b(key, digest_size=16).digest())


def choose(rng, weights: Sequence[float]) -> int:
    """Индекс исхода по накопленным вероятностям."""
    point = rng.random() * sum(weights)
    total = 0.0
    for index, weight in enumerate(weights):
        total += weight
        if point < total:
            return index
    return len(weights) - 1


def happens(rng, chance: float) -> bool:
    if chance <= 0:
        return False
    if chance >= 1:
        return True
    return rng.random() < chance
```

- [ ] **Step 4: Написать падающий тест `tests/test_events.py`**

```python
from sgame.core.events import Delta, Event


def test_delta_describes_itself_in_russian():
    delta = Delta(scope="faction", who="astoria", track="Бюджет", amount=-15)
    assert delta.describe() == "Бюджет −15"


def test_clamped_delta_is_marked():
    delta = Delta(scope="faction", who="a", track="ВС", amount=10, clamped=True)
    assert "предел" in delta.describe()


def test_event_defaults_to_public():
    event = Event(kind="action", title="Мобилизация")
    assert event.audience == "public"


def test_event_is_hashable_and_frozen():
    event = Event(kind="action", title="Мобилизация", deltas=())
    assert hash(event)
```

- [ ] **Step 5: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_events.py -v`
Expected: FAIL — нет модуля `sgame.core.events`

- [ ] **Step 6: Написать `sgame/core/events.py` и `sgame/core/orders.py`**

```python
# sgame/core/events.py
"""Что произошло за раунд и кому это видно."""

from dataclasses import dataclass, field
from typing import Literal

Audience = Literal["public", "actor", "actor_and_target", "host"]


@dataclass(frozen=True)
class Delta:
    """Одно изменение числа с указанием, упёрлось ли оно в границу."""

    scope: Literal["faction", "world", "relation"]
    who: str
    track: str
    amount: float
    clamped: bool = False

    def describe(self) -> str:
        sign = "+" if self.amount >= 0 else "−"
        body = f"{self.track} {sign}{abs(self.amount):g}"
        return f"{body} (предел)" if self.clamped else body


@dataclass(frozen=True)
class Event:
    kind: str
    title: str
    actor: str | None = None
    target: str | None = None
    detail: str = ""
    deltas: tuple[Delta, ...] = field(default=())
    audience: Audience = "public"
    roll: str | None = None
```

```python
# sgame/core/orders.py
"""Ввод команд: приказы и предложения сделок."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    action: str
    target: str | None = None
    intent: str = ""


@dataclass(frozen=True)
class DealOffer:
    id: str
    deal: str
    sender: str
    receiver: str
    amount: float | None = None
```

- [ ] **Step 7: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_rng.py tests/test_events.py -v`
Expected: PASS, 8 тестов

- [ ] **Step 8: Коммит**

```bash
git add sgame/core/rng.py sgame/core/events.py sgame/core/orders.py tests/test_rng.py tests/test_events.py
git commit -m "feat: детерминированная случайность, события и приказы"
```

---

## Task 5: Состояние игры и рабочая копия

**Files:**
- Create: `sgame/core/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `ScenarioSpec`, `Delta`, `DealOffer`
- Produces:
  - `Status(deal: str, a: str, b: str, until: int)`
  - `GameState(round, tracks, world, relations, statuses, pending_offers, fired_events, finished)` — неизменяемое
  - `initial_state(spec) -> GameState`
  - `pair_key(a, b) -> tuple[str, str]`
  - `StateBuilder(spec, state)` с методами `add_track`, `add_world`, `add_relation`, `track`, `context`, `build`

- [ ] **Step 1: Написать падающий тест `tests/test_state.py`**

```python
from sgame.core.spec import parse_scenario
from sgame.core.state import StateBuilder, initial_state, pair_key

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
  army:   { title: "ВС", min: 0, max: 50 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 50, army: 10 } }
  - { id: b, title: "Б", start: { budget: 50, army: 10 } }
relations:
  default: 0
  pairs: [ { a: a, b: b, value: -20 } ]
actions:
  - { id: noop, title: "Ничего", effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
""")


def test_initial_state_reads_scenario():
    state = initial_state(SPEC)
    assert state.round == 1
    assert state.tracks["a"]["budget"] == 50
    assert state.world["tension"] == 10
    assert state.relations[pair_key("a", "b")] == -20


def test_builder_clamps_at_upper_bound():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    delta = builder.add_track("a", "army", 100)
    assert builder.track("a", "army") == 50
    assert delta.amount == 40
    assert delta.clamped is True


def test_builder_clamps_at_lower_bound():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    delta = builder.add_track("a", "budget", -80)
    assert builder.track("a", "budget") == 0
    assert delta.clamped is True


def test_builder_does_not_mutate_source_state():
    state = initial_state(SPEC)
    builder = StateBuilder(SPEC, state)
    builder.add_track("a", "budget", -10)
    assert state.tracks["a"]["budget"] == 50


def test_relations_are_symmetric():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.add_relation("b", "a", 5)
    assert builder.relation("a", "b") == -15


def test_context_exposes_namespaces():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    ctx = builder.context(actor="a", target="b")
    assert ctx["self"]["budget"] == 50
    assert ctx["target"]["army"] == 10
    assert ctx["world"]["tension"] == 10
    assert ctx["meta"]["rounds"] == 3
    assert ctx["rel"]("a", "b") == -20
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_state.py -v`
Expected: FAIL — нет модуля `sgame.core.state`

- [ ] **Step 3: Написать `sgame/core/state.py`**

```python
"""Состояние партии и рабочая копия для расчёта раунда.

`GameState` неизменяемо и всегда является результатом свёртки журнала.
Фазы раунда работают с `StateBuilder` — рабочей копией, которая знает
границы треков и сама зажимает значения.
"""

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any

from .events import Delta
from .orders import DealOffer
from .spec import ScenarioSpec


def pair_key(a: str, b: str) -> tuple[str, str]:
    """Ключ отношения не зависит от порядка сторон."""
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True)
class Status:
    deal: str
    a: str
    b: str
    until: int


@dataclass(frozen=True)
class GameState:
    round: int
    tracks: dict[str, dict[str, float]]
    world: dict[str, float]
    relations: dict[tuple[str, str], float]
    statuses: tuple[Status, ...] = ()
    pending_offers: tuple[DealOffer, ...] = ()
    fired_events: frozenset[str] = field(default=frozenset())
    finished: bool = False


def initial_state(spec: ScenarioSpec) -> GameState:
    tracks = {f.id: dict(f.start) for f in spec.factions}
    world = {name: track.start for name, track in spec.world.items()}
    relations: dict[tuple[str, str], float] = {}
    ids = [f.id for f in spec.factions]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            relations[pair_key(a, b)] = spec.relations.default
    for pair in spec.relations.pairs:
        relations[pair_key(pair.a, pair.b)] = pair.value
    return GameState(round=1, tracks=tracks, world=world, relations=relations)


class StateBuilder:
    """Рабочая копия состояния на время расчёта одного раунда."""

    def __init__(self, spec: ScenarioSpec, state: GameState) -> None:
        self.spec = spec
        self.round = state.round
        self._tracks = deepcopy(state.tracks)
        self._world = dict(state.world)
        self._relations = dict(state.relations)
        self.statuses = list(state.statuses)
        self.pending_offers = list(state.pending_offers)
        self.fired_events = set(state.fired_events)

    def track(self, faction: str, name: str) -> float:
        return self._tracks[faction][name]

    def world_track(self, name: str) -> float:
        return self._world[name]

    def relation(self, a: str, b: str) -> float:
        return self._relations.get(pair_key(a, b), self.spec.relations.default)

    def add_track(self, faction: str, name: str, amount: float) -> Delta:
        track = self.spec.tracks[name]
        before = self._tracks[faction][name]
        after = min(track.max, max(track.min, before + amount))
        self._tracks[faction][name] = after
        return Delta(
            scope="faction", who=faction, track=track.title,
            amount=after - before, clamped=(after - before) != amount,
        )

    def add_world(self, name: str, amount: float) -> Delta:
        track = self.spec.world[name]
        before = self._world[name]
        after = min(track.max, max(track.min, before + amount))
        self._world[name] = after
        return Delta(
            scope="world", who="", track=track.title,
            amount=after - before, clamped=(after - before) != amount,
        )

    def add_relation(self, a: str, b: str, amount: float) -> Delta:
        key = pair_key(a, b)
        before = self._relations.get(key, self.spec.relations.default)
        after = min(100.0, max(-100.0, before + amount))
        self._relations[key] = after
        return Delta(
            scope="relation", who=f"{key[0]}↔{key[1]}", track="Отношения",
            amount=after - before, clamped=(after - before) != amount,
        )

    def context(self, actor: str | None = None, target: str | None = None) -> dict[str, Any]:
        """Контекст для вычисления выражений сценария."""
        return {
            "self": dict(self._tracks[actor]) if actor else {},
            "target": dict(self._tracks[target]) if target else {},
            "world": dict(self._world),
            "round": self.round,
            "meta": {"rounds": self.spec.meta.rounds},
            "rel": self.relation,
        }

    def build(self, *, round_no: int, finished: bool = False) -> GameState:
        return GameState(
            round=round_no,
            tracks=deepcopy(self._tracks),
            world=dict(self._world),
            relations=dict(self._relations),
            statuses=tuple(self.statuses),
            pending_offers=tuple(self.pending_offers),
            fired_events=frozenset(self.fired_events),
            finished=finished,
        )
```

- [ ] **Step 4: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_state.py -v`
Expected: PASS, 6 тестов

- [ ] **Step 5: Коммит**

```bash
git add sgame/core/state.py tests/test_state.py
git commit -m "feat: состояние партии и рабочая копия с зажимом границ"
```

---

## Task 6: Фазы 1–2 — валидация приказов и оплата

**Files:**
- Create: `sgame/core/phases.py`
- Test: `tests/test_phases_validate.py`

**Interfaces:**
- Consumes: `ScenarioSpec`, `StateBuilder`, `Order`, `Event`, `evaluate`
- Produces:
  - `Accepted(faction: str, index: int, order: Order, action: ActionSpec)`
  - `phase_validate(spec, builder, orders) -> tuple[list[Accepted], list[Event]]`
  - `phase_pay(spec, builder, accepted) -> list[Event]`
  - `apply_effect(spec, builder, effect, actor, target, multiplier) -> list[Delta]`

- [ ] **Step 1: Написать падающий тест `tests/test_phases_validate.py`**

```python
from sgame.core.orders import Order
from sgame.core.phases import phase_pay, phase_validate
from sgame.core.spec import parse_scenario
from sgame.core.state import StateBuilder, initial_state

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 30, intel: 5 } }
  - { id: b, title: "Б", start: { budget: 30, intel: 5 } }
actions:
  - { id: cheap, title: "Дёшево", cost: { budget: 10 }, effects: [] }
  - { id: pricey, title: "Дорого", cost: { budget: 25 }, effects: [] }
  - { id: gated, title: "Условное", requires: "self.intel >= 10", effects: [] }
  - { id: strike, title: "Удар", target: faction, effects: [] }
  - { id: heavy, title: "Тяжёлое", ap: 2, effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
""")


def builder():
    return StateBuilder(SPEC, initial_state(SPEC))


def test_accepts_valid_order():
    accepted, events = phase_validate(SPEC, builder(), {"a": [Order(action="cheap")]})
    assert len(accepted) == 1
    assert events == []


def test_rejects_unknown_action():
    accepted, events = phase_validate(SPEC, builder(), {"a": [Order(action="nope")]})
    assert accepted == []
    assert events[0].kind == "order_rejected"
    assert events[0].audience == "actor"
    assert "nope" in events[0].detail


def test_rejects_when_requires_is_false():
    _, events = phase_validate(SPEC, builder(), {"a": [Order(action="gated")]})
    assert "условие" in events[0].detail


def test_rejects_when_action_points_exhausted():
    orders = {"a": [Order(action="heavy"), Order(action="cheap")]}
    accepted, events = phase_validate(SPEC, builder(), orders)
    assert [x.order.action for x in accepted] == ["heavy"]
    assert "очк" in events[0].detail


def test_rejects_unaffordable_second_order():
    orders = {"a": [Order(action="pricey"), Order(action="cheap")]}
    accepted, events = phase_validate(SPEC, builder(), orders)
    assert [x.order.action for x in accepted] == ["pricey"]
    assert "хватает" in events[0].detail


def test_rejects_targeted_action_without_target():
    _, events = phase_validate(SPEC, builder(), {"a": [Order(action="strike")]})
    assert "цель" in events[0].detail


def test_rejects_targeting_self():
    _, events = phase_validate(SPEC, builder(), {"a": [Order(action="strike", target="a")]})
    assert "себя" in events[0].detail


def test_payment_subtracts_cost():
    work = builder()
    accepted, _ = phase_validate(SPEC, work, {"a": [Order(action="cheap")]})
    events = phase_pay(SPEC, work, accepted)
    assert work.track("a", "budget") == 20
    assert events[0].audience == "actor"
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_phases_validate.py -v`
Expected: FAIL — нет модуля `sgame.core.phases`

- [ ] **Step 3: Написать `sgame/core/phases.py` — начало модуля, фазы 1 и 2**

```python
"""Восемь фаз разрешения раунда.

Порядок фаз фиксирован: он и делает результат объяснимым для студентов.
Каждая фаза — функция, принимающая рабочую копию состояния и возвращающая
список событий.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .events import Delta, Event
from .expr import evaluate
from .orders import Order
from .spec import ActionSpec, EffectSpec, ScenarioSpec
from .state import StateBuilder


@dataclass(frozen=True)
class Accepted:
    faction: str
    index: int
    order: Order
    action: ActionSpec

    @property
    def roll_id(self) -> str:
        return f"{self.faction}:{self.index}:{self.action.id}"


def _reject(faction: str, order: Order, reason: str) -> Event:
    return Event(
        kind="order_rejected",
        title="Приказ отклонён",
        actor=faction,
        detail=f"{order.action}: {reason}",
        audience="actor",
    )


def phase_validate(
    spec: ScenarioSpec,
    builder: StateBuilder,
    orders: Mapping[str, Sequence[Order]],
) -> tuple[list[Accepted], list[Event]]:
    """Фаза 1. Отсеять приказы, которые нельзя исполнить, с указанием причины."""
    accepted: list[Accepted] = []
    events: list[Event] = []
    known_factions = {f.id for f in spec.factions}

    for faction in sorted(orders):
        points_left = spec.meta.action_points
        reserved: dict[str, float] = {}

        for index, order in enumerate(orders[faction]):
            action = spec.action(order.action)
            if action is None:
                events.append(_reject(faction, order, f"неизвестное действие {order.action!r}"))
                continue
            if action.ap > points_left:
                events.append(_reject(faction, order, "не хватает очков действий"))
                continue
            if action.target == "faction":
                if not order.target:
                    events.append(_reject(faction, order, "не выбрана цель"))
                    continue
                if order.target == faction:
                    events.append(_reject(faction, order, "нельзя направить действие на себя"))
                    continue
                if order.target not in known_factions:
                    events.append(_reject(faction, order, f"неизвестная цель {order.target!r}"))
                    continue
            if action.requires:
                context = builder.context(actor=faction, target=order.target)
                if not evaluate(action.requires, context):
                    events.append(_reject(faction, order, f"не выполнено условие: {action.requires}"))
                    continue

            shortfall = next(
                (
                    name
                    for name, amount in action.cost.items()
                    if builder.track(faction, name) - reserved.get(name, 0.0) < amount
                ),
                None,
            )
            if shortfall is not None:
                events.append(
                    _reject(faction, order, f"не хватает ресурса «{spec.tracks[shortfall].title}»")
                )
                continue

            for name, amount in action.cost.items():
                reserved[name] = reserved.get(name, 0.0) + amount
            points_left -= action.ap
            accepted.append(Accepted(faction=faction, index=index, order=order, action=action))

    return accepted, events


def phase_pay(spec: ScenarioSpec, builder: StateBuilder, accepted: Sequence[Accepted]) -> list[Event]:
    """Фаза 2. Списать стоимость принятых приказов."""
    events: list[Event] = []
    for item in accepted:
        if not item.action.cost:
            continue
        deltas = tuple(
            builder.add_track(item.faction, name, -amount)
            for name, amount in sorted(item.action.cost.items())
        )
        events.append(
            Event(
                kind="cost",
                title=f"Затраты: {item.action.title}",
                actor=item.faction,
                deltas=deltas,
                audience="actor",
            )
        )
    return events


def apply_effect(
    spec: ScenarioSpec,
    builder: StateBuilder,
    effect: EffectSpec,
    actor: str | None,
    target: str | None,
    multiplier: float = 1.0,
) -> list[Delta]:
    """Применить один эффект. Форма `all` считается отдельно для каждой стороны."""
    if effect.all is not None:
        deltas = []
        for faction in spec.factions:
            amount = evaluate(effect.delta, builder.context(actor=faction.id, target=target))
            deltas.append(builder.add_track(faction.id, effect.all, amount * multiplier))
        return deltas

    amount = evaluate(effect.delta, builder.context(actor=actor, target=target)) * multiplier

    if effect.self_track is not None:
        return [builder.add_track(actor, effect.self_track, amount)]
    if effect.target is not None:
        return [builder.add_track(target, effect.target, amount)]
    if effect.world is not None:
        return [builder.add_world(effect.world, amount)]
    if effect.relation is not None:
        names = {"self": actor, "target": target}
        first, second = (names.get(n, n) for n in effect.relation)
        return [builder.add_relation(first, second, amount)]
    return []
```

- [ ] **Step 4: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_phases_validate.py -v`
Expected: PASS, 8 тестов

- [ ] **Step 5: Коммит**

```bash
git add sgame/core/phases.py tests/test_phases_validate.py
git commit -m "feat: фазы валидации приказов и оплаты"
```

---

## Task 7: Фазы 3–5 — сделки, противодействия, эффекты и броски

**Files:**
- Modify: `sgame/core/phases.py`
- Test: `tests/test_phases_effects.py`

**Interfaces:**
- Consumes: `Accepted`, `apply_effect`, `stream`, `choose`, `happens`, `DealOffer`, `Status`
- Produces:
  - `phase_deals(spec, builder, offers, responses) -> list[Event]`
  - `phase_counters(spec, accepted) -> dict[tuple[str, int], float]`
  - `phase_effects(spec, builder, accepted, multipliers, seed) -> list[Event]`

- [ ] **Step 1: Написать падающий тест `tests/test_phases_effects.py`**

```python
from sgame.core.orders import DealOffer, Order
from sgame.core.phases import (
    phase_counters, phase_deals, phase_effects, phase_validate,
)
from sgame.core.spec import parse_scenario
from sgame.core.state import Status, StateBuilder, initial_state

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 5, action_points: 3 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 200 }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 100, intel: 50 } }
  - { id: b, title: "Б", start: { budget: 100, intel: 50 } }
actions:
  - id: open_hit
    title: "Открытый удар"
    target: faction
    countered_by: [ shield ]
    effects:
      - { target: budget, delta: "-20" }
      - { world: tension, delta: "5" }
  - id: shield
    title: "Щит"
    counter_multiplier: 0.25
    effects: []
  - id: covert
    title: "Тайная операция"
    target: faction
    visibility: secret
    reveal_chance: 1.0
    effects: [ { target: budget, delta: "-10" } ]
  - id: gamble
    title: "Риск"
    risk:
      - { p: 1.0, title: "успех", effects: [ { self: budget, delta: "10" } ] }
deals:
  - { id: transfer, title: "Передача", kind: resource, track: budget }
  - { id: pact, title: "Пакт", kind: status, duration: 2 }
end: { when: "round > meta.rounds", scoring: "self.budget" }
""")


def prepared(orders):
    builder = StateBuilder(SPEC, initial_state(SPEC))
    accepted, _ = phase_validate(SPEC, builder, orders)
    return builder, accepted


def test_counter_reduces_effect():
    builder, accepted = prepared({
        "a": [Order(action="open_hit", target="b")],
        "b": [Order(action="shield")],
    })
    multipliers = phase_counters(SPEC, accepted)
    phase_effects(SPEC, builder, accepted, multipliers, seed=1)
    assert builder.track("b", "budget") == 95


def test_without_counter_full_effect():
    builder, accepted = prepared({"a": [Order(action="open_hit", target="b")]})
    phase_effects(SPEC, builder, accepted, phase_counters(SPEC, accepted), seed=1)
    assert builder.track("b", "budget") == 80


def test_secret_action_is_private_until_revealed():
    builder, accepted = prepared({"a": [Order(action="covert", target="b")]})
    events = phase_effects(SPEC, builder, accepted, {}, seed=1)
    assert events[0].audience == "actor_and_target"


def test_risk_outcome_is_recorded():
    builder, accepted = prepared({"a": [Order(action="gamble")]})
    events = phase_effects(SPEC, builder, accepted, {}, seed=7)
    assert events[0].roll == "успех"
    assert builder.track("a", "budget") == 110


def test_resource_deal_moves_value_when_accepted():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.pending_offers = [DealOffer(id="o1", deal="transfer", sender="a", receiver="b", amount=30)]
    phase_deals(SPEC, builder, offers=[], responses={"o1": True})
    assert builder.track("a", "budget") == 70
    assert builder.track("b", "budget") == 130


def test_rejected_deal_changes_nothing():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.pending_offers = [DealOffer(id="o1", deal="transfer", sender="a", receiver="b", amount=30)]
    phase_deals(SPEC, builder, offers=[], responses={"o1": False})
    assert builder.track("a", "budget") == 100


def test_status_deal_sets_expiry():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.pending_offers = [DealOffer(id="o2", deal="pact", sender="a", receiver="b")]
    phase_deals(SPEC, builder, offers=[], responses={"o2": True})
    assert builder.statuses == [Status(deal="pact", a="a", b="b", until=3)]


def test_expired_status_is_removed():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.round = 4
    builder.statuses = [Status(deal="pact", a="a", b="b", until=3)]
    events = phase_deals(SPEC, builder, offers=[], responses={})
    assert builder.statuses == []
    assert any(e.kind == "status_expired" for e in events)


def test_new_offers_become_pending():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    offer = DealOffer(id="o3", deal="pact", sender="a", receiver="b")
    phase_deals(SPEC, builder, offers=[offer], responses={})
    assert builder.pending_offers == [offer]
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_phases_effects.py -v`
Expected: FAIL — в `phases` нет `phase_deals`

- [ ] **Step 3: Дописать фазы 3–5 в `sgame/core/phases.py`**

Добавить импорты `from .orders import DealOffer, Order`, `from .rng import choose, happens, stream`, `from .state import Status, StateBuilder` и следующие функции:

```python
def phase_deals(
    spec: ScenarioSpec,
    builder: StateBuilder,
    offers: Sequence[DealOffer],
    responses: Mapping[str, bool],
) -> list[Event]:
    """Фаза 3. Ответы на прошлые предложения, истечение статусов, новые предложения."""
    events: list[Event] = []

    for offer in builder.pending_offers:
        deal = spec.deal(offer.deal)
        if deal is None:
            continue
        if not responses.get(offer.id, False):
            events.append(
                Event(
                    kind="deal_rejected",
                    title=f"Отклонено: {deal.title}",
                    actor=offer.sender,
                    target=offer.receiver,
                    audience="actor_and_target",
                )
            )
            continue

        if deal.kind == "resource":
            amount = offer.amount or 0.0
            deltas = (
                builder.add_track(offer.sender, deal.track, -amount),
                builder.add_track(offer.receiver, deal.track, amount),
            )
            events.append(
                Event(
                    kind="deal_done",
                    title=f"Исполнено: {deal.title}",
                    actor=offer.sender,
                    target=offer.receiver,
                    deltas=deltas,
                    audience="public",
                )
            )
        else:
            builder.statuses.append(
                Status(
                    deal=deal.id,
                    a=offer.sender,
                    b=offer.receiver,
                    until=builder.round + (deal.duration or 1),
                )
            )
            events.append(
                Event(
                    kind="deal_done",
                    title=f"Заключено: {deal.title}",
                    actor=offer.sender,
                    target=offer.receiver,
                    audience="public",
                )
            )

    still_active = []
    for status in builder.statuses:
        if status.until <= builder.round:
            deal = spec.deal(status.deal)
            events.append(
                Event(
                    kind="status_expired",
                    title=f"Истекло: {deal.title if deal else status.deal}",
                    actor=status.a,
                    target=status.b,
                    audience="public",
                )
            )
        else:
            still_active.append(status)
    builder.statuses = still_active

    builder.pending_offers = list(offers)
    for offer in offers:
        deal = spec.deal(offer.deal)
        events.append(
            Event(
                kind="deal_offered",
                title=f"Предложено: {deal.title if deal else offer.deal}",
                actor=offer.sender,
                target=offer.receiver,
                detail="ответ ожидается в следующем раунде",
                audience="actor_and_target",
            )
        )
    return events


def phase_counters(spec: ScenarioSpec, accepted: Sequence[Accepted]) -> dict[tuple[str, int], float]:
    """Фаза 4. Множитель эффекта для каждого приказа, который встретил контрдействие."""
    by_faction: dict[str, set[str]] = {}
    for item in accepted:
        by_faction.setdefault(item.faction, set()).add(item.action.id)

    multipliers: dict[tuple[str, int], float] = {}
    for item in accepted:
        if not item.action.countered_by or not item.order.target:
            continue
        defences = by_faction.get(item.order.target, set()) & set(item.action.countered_by)
        if not defences:
            continue
        multipliers[(item.faction, item.index)] = min(
            spec.action(name).counter_multiplier for name in defences
        )
    return multipliers


def phase_effects(
    spec: ScenarioSpec,
    builder: StateBuilder,
    accepted: Sequence[Accepted],
    multipliers: Mapping[tuple[str, int], float],
    seed: int,
) -> list[Event]:
    """Фаза 5. Броски и применение эффектов.

    Бросок делается всегда, даже если действие погашено контрдействием:
    иначе очередь обращений к генератору зависела бы от чужих приказов.
    """
    events: list[Event] = []

    for item in accepted:
        effects = item.action.effects
        roll_title = None
        if item.action.risk:
            rng = stream(seed, builder.round, item.roll_id)
            index = choose(rng, [outcome.p for outcome in item.action.risk])
            outcome = item.action.risk[index]
            effects = outcome.effects
            roll_title = outcome.title or f"исход {index + 1}"

        multiplier = multipliers.get((item.faction, item.index), 1.0)
        deltas: list[Delta] = []
        for effect in effects:
            deltas.extend(
                apply_effect(spec, builder, effect, item.faction, item.order.target, multiplier)
            )

        audience = "public"
        if item.action.visibility == "secret":
            audience = "actor"
            if item.order.target and item.action.reveal_chance:
                revealed = happens(
                    stream(seed, builder.round, item.roll_id + ":reveal"),
                    item.action.reveal_chance,
                )
                if revealed:
                    audience = "actor_and_target"

        detail = item.action.description
        if multiplier < 1.0:
            detail = (detail + " " if detail else "") + "Действие встретило противодействие."

        events.append(
            Event(
                kind="action",
                title=item.action.title,
                actor=item.faction,
                target=item.order.target,
                detail=detail.strip(),
                deltas=tuple(deltas),
                audience=audience,
                roll=roll_title,
            )
        )

        if multiplier < 1.0:
            events.append(
                Event(
                    kind="counter",
                    title=f"Противодействие: {item.action.title}",
                    actor=item.order.target,
                    target=item.faction,
                    audience="actor_and_target",
                )
            )

    return events
```

- [ ] **Step 4: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_phases_effects.py -v`
Expected: PASS, 9 тестов

- [ ] **Step 5: Коммит**

```bash
git add sgame/core/phases.py tests/test_phases_effects.py
git commit -m "feat: фазы сделок, противодействий и применения эффектов"
```

---

## Task 8: Фазы 6–8, подсчёт очков и `resolve()`

**Files:**
- Modify: `sgame/core/phases.py`
- Create: `sgame/core/scoring.py`, `sgame/core/resolve.py`
- Test: `tests/test_resolve.py`

**Interfaces:**
- Consumes: все фазы, `initial_state`
- Produces:
  - `phase_world(spec, builder) -> list[Event]`
  - `phase_events(spec, builder) -> list[Event]`
  - `phase_end(spec, builder) -> tuple[bool, list[Event]]`
  - `score(spec, state, faction) -> tuple[float, list[tuple[str, float]]]` — итог и расшифровка
  - `RoundResult(state: GameState, events: tuple[Event, ...])`
  - `resolve(spec, state, orders, offers, responses, seed) -> RoundResult`

- [ ] **Step 1: Написать падающий тест `tests/test_resolve.py`**

```python
from sgame.core.orders import Order
from sgame.core.resolve import resolve
from sgame.core.scoring import score
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 2, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 200 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 50 }
factions:
  - id: a
    title: "А"
    start: { budget: 100 }
    goals: [ { id: calm, title: "Мир", when: "world.tension < 55", score: 10 } ]
  - { id: b, title: "Б", start: { budget: 100 } }
actions:
  - { id: escalate, title: "Эскалация", effects: [ { world: tension, delta: "10" } ] }
world_dynamics:
  - { all: budget, delta: "5" }
events:
  - id: shock
    when: "world.tension > 55"
    title: "Шок"
    once: true
    effects: [ { all: budget, delta: "-20" } ]
end: { when: "round > meta.rounds", scoring: "self.budget * 0.1" }
""")


def test_world_dynamics_apply_to_everyone():
    result = resolve(SPEC, initial_state(SPEC), {}, [], {}, seed=1)
    assert result.state.tracks["a"]["budget"] == 105
    assert result.state.tracks["b"]["budget"] == 105


def test_triggered_event_fires_once():
    state = initial_state(SPEC)
    first = resolve(SPEC, state, {"a": [Order(action="escalate")]}, [], {}, seed=1)
    assert "shock" in first.state.fired_events
    assert first.state.tracks["b"]["budget"] == 85
    second = resolve(SPEC, first.state, {}, [], {}, seed=1)
    assert second.state.tracks["b"]["budget"] == 90


def test_round_advances_and_game_ends():
    state = initial_state(SPEC)
    state = resolve(SPEC, state, {}, [], {}, seed=1).state
    assert state.round == 2
    assert state.finished is False
    state = resolve(SPEC, state, {}, [], {}, seed=1).state
    assert state.finished is True


def test_scoring_includes_goals():
    state = initial_state(SPEC)
    total, breakdown = score(SPEC, state, "a")
    assert total == 100 * 0.1 + 10
    assert ("Мир", 10) in breakdown


def test_order_of_factions_does_not_change_outcome():
    orders_one = {"a": [Order(action="escalate")], "b": [Order(action="escalate")]}
    orders_two = {"b": [Order(action="escalate")], "a": [Order(action="escalate")]}
    first = resolve(SPEC, initial_state(SPEC), orders_one, [], {}, seed=3)
    second = resolve(SPEC, initial_state(SPEC), orders_two, [], {}, seed=3)
    assert first.state.tracks == second.state.tracks
    assert first.state.world == second.state.world
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_resolve.py -v`
Expected: FAIL — нет модуля `sgame.core.resolve`

- [ ] **Step 3: Дописать фазы 6–8 в `sgame/core/phases.py`**

```python
def phase_world(spec: ScenarioSpec, builder: StateBuilder) -> list[Event]:
    """Фаза 6. Динамика мира: то, что происходит независимо от команд."""
    deltas: list[Delta] = []
    for effect in spec.world_dynamics:
        deltas.extend(apply_effect(spec, builder, effect, actor=None, target=None))
    if not deltas:
        return []
    return [
        Event(kind="world", title="Обстановка", deltas=tuple(deltas), audience="public")
    ]


def phase_events(spec: ScenarioSpec, builder: StateBuilder) -> list[Event]:
    """Фаза 7. Плановые и триггерные события сценария."""
    events: list[Event] = []
    for scenario_event in spec.events:
        if scenario_event.once and scenario_event.id in builder.fired_events:
            continue
        if not evaluate(scenario_event.when, builder.context()):
            continue
        deltas: list[Delta] = []
        for effect in scenario_event.effects:
            deltas.extend(apply_effect(spec, builder, effect, actor=None, target=None))
        builder.fired_events.add(scenario_event.id)
        events.append(
            Event(
                kind="scenario_event",
                title=scenario_event.title,
                detail=scenario_event.text,
                deltas=tuple(deltas),
                audience="public",
            )
        )
    return events


def phase_end(spec: ScenarioSpec, builder: StateBuilder) -> tuple[bool, list[Event]]:
    """Фаза 8. Проверка условия окончания. Раунд уже прожит, поэтому проверяем следующий."""
    context = builder.context()
    context["round"] = builder.round + 1
    finished = bool(evaluate(spec.end.when, context))
    if not finished:
        return False, []
    return True, [Event(kind="end", title="Игра окончена", audience="public")]
```

- [ ] **Step 4: Написать `sgame/core/scoring.py`**

```python
"""Подсчёт итогов партии."""

from .expr import evaluate
from .spec import ScenarioSpec
from .state import GameState


def _context(spec: ScenarioSpec, state: GameState, faction: str) -> dict:
    return {
        "self": dict(state.tracks[faction]),
        "target": {},
        "world": dict(state.world),
        "round": state.round,
        "meta": {"rounds": spec.meta.rounds},
        "rel": lambda a, b: state.relations.get(tuple(sorted((a, b))), spec.relations.default),
    }


def score(spec: ScenarioSpec, state: GameState, faction: str) -> tuple[float, list[tuple[str, float]]]:
    """Итоговый счёт стороны и его расшифровка по слагаемым."""
    context = _context(spec, state, faction)
    base = float(evaluate(spec.end.scoring, context))
    breakdown: list[tuple[str, float]] = [("Базовый счёт", round(base, 2))]

    spec_faction = spec.faction(faction)
    total = base
    if spec_faction:
        for goal in spec_faction.goals:
            if evaluate(goal.when, context):
                total += goal.score
                breakdown.append((goal.title, goal.score))
    return round(total, 2), breakdown
```

- [ ] **Step 5: Написать `sgame/core/resolve.py`**

```python
"""Склейка фаз в один расчёт раунда."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .events import Event
from .orders import DealOffer, Order
from .phases import (
    phase_counters, phase_deals, phase_effects, phase_end,
    phase_events, phase_pay, phase_validate, phase_world,
)
from .spec import ScenarioSpec
from .state import GameState, StateBuilder


@dataclass(frozen=True)
class RoundResult:
    state: GameState
    events: tuple[Event, ...]


def resolve(
    spec: ScenarioSpec,
    state: GameState,
    orders: Mapping[str, Sequence[Order]],
    offers: Sequence[DealOffer],
    responses: Mapping[str, bool],
    seed: int,
) -> RoundResult:
    """Чистая функция раунда: состояние и приказы на входе, новое состояние на выходе."""
    builder = StateBuilder(spec, state)
    events: list[Event] = []

    accepted, rejected = phase_validate(spec, builder, orders)
    events.extend(rejected)
    events.extend(phase_pay(spec, builder, accepted))
    events.extend(phase_deals(spec, builder, offers, responses))
    multipliers = phase_counters(spec, accepted)
    events.extend(phase_effects(spec, builder, accepted, multipliers, seed))
    events.extend(phase_world(spec, builder))
    events.extend(phase_events(spec, builder))
    finished, end_events = phase_end(spec, builder)
    events.extend(end_events)

    return RoundResult(
        state=builder.build(round_no=state.round + 1, finished=finished),
        events=tuple(events),
    )
```

- [ ] **Step 6: Прогнать все тесты ядра**

Run: `.venv/bin/pytest tests -v`
Expected: PASS, все тесты

- [ ] **Step 7: Коммит**

```bash
git add sgame/core/phases.py sgame/core/scoring.py sgame/core/resolve.py tests/test_resolve.py
git commit -m "feat: динамика мира, события, подсчёт очков и resolve()"
```

---

## Task 9: Журнал сессии и пользовательские директории

Уточнение к спеке: журнал хранит **и** идентификатор сценария с его sha256, **и** полный текст сценария. Тогда файл партии самодостаточен (его можно переслать), а хеш позволяет заметить, что сценарий на диске с тех пор изменился.

**Files:**
- Create: `sgame/session/paths.py`, `sgame/session/journal.py`
- Test: `tests/test_journal.py`

**Interfaces:**
- Consumes: `Order`, `DealOffer`, `ScenarioSpec`
- Produces:
  - `data_dir() -> Path`, `sessions_dir() -> Path`, `scenarios_dir() -> Path`, `config_path() -> Path`
  - `builtin_scenarios() -> dict[str, str]` — идентификатор → текст встроенного сценария
  - `TeamSlot(faction, team, code)`, `RoundRecord(n, orders, offers, responses, narration, resolved_at)`
  - `Journal(format, scenario_id, scenario_sha256, scenario_text, seed, created_at, teams, rounds)`
  - `new_journal(scenario_id, scenario_text, teams, seed) -> Journal`
  - `save(path, journal)`, `load(path) -> Journal`

- [ ] **Step 1: Написать падающий тест `tests/test_journal.py`**

```python
from sgame.core.orders import DealOffer, Order
from sgame.session import journal as J
from sgame.session.paths import data_dir, sessions_dir

SCENARIO_TEXT = "schema_version: 1\n"


def test_data_dir_follows_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    assert data_dir() == tmp_path
    assert sessions_dir().exists()


def test_new_journal_records_hash_and_teams():
    journal = J.new_journal(
        scenario_id="t",
        scenario_text=SCENARIO_TEXT,
        teams=[J.TeamSlot(faction="a", team="Команда 1", code="1234")],
        seed=7,
    )
    assert journal.seed == 7
    assert len(journal.scenario_sha256) == 64
    assert journal.rounds == []


def test_roundtrip_preserves_orders_and_offers(tmp_path):
    journal = J.new_journal("t", SCENARIO_TEXT, [J.TeamSlot("a", "Команда 1", "1234")], 7)
    journal.rounds.append(
        J.RoundRecord(
            n=1,
            orders={"a": [Order(action="grow", target="b", intent="растём")]},
            offers=[DealOffer(id="o1", deal="pact", sender="a", receiver="b", amount=None)],
            responses={"o0": True},
            narration={"public": "текст", "private": {"a": "своё"}},
            resolved_at="2026-09-01T10:00:00",
        )
    )
    path = tmp_path / "s.json"
    J.save(path, journal)
    loaded = J.load(path)
    assert loaded.rounds[0].orders["a"][0].intent == "растём"
    assert loaded.rounds[0].offers[0].deal == "pact"
    assert loaded.rounds[0].narration["private"]["a"] == "своё"


def test_builtin_scenarios_include_meridian():
    assert "meridian" in J.builtin_scenarios()
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_journal.py -v`
Expected: FAIL — нет модуля `sgame.session.paths`

- [ ] **Step 3: Написать `sgame/session/paths.py`**

```python
"""Где лежат данные пользователя.

Внутрь пакета ничего не пишется: собранное приложение только читает свои
ресурсы, а сессии и настройки живут в пользовательской директории.
"""

import os
from importlib import resources
from pathlib import Path

APP_NAME = "StrategicGame"


def data_dir() -> Path:
    override = os.environ.get("SGAME_DATA_DIR")
    root = Path(override) if override else Path.home() / "Library" / "Application Support" / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def sessions_dir() -> Path:
    path = data_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def scenarios_dir() -> Path:
    path = data_dir() / "scenarios"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return data_dir() / "config.json"


def builtin_scenarios() -> dict[str, str]:
    """Сценарии, вшитые в пакет. Читаются как ресурсы, не по пути файла."""
    found: dict[str, str] = {}
    package = resources.files("sgame") / "scenarios"
    for item in package.iterdir():
        if item.name.endswith(".yaml"):
            found[item.name.removesuffix(".yaml")] = item.read_text(encoding="utf-8")
    return found


def user_scenarios() -> dict[str, str]:
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in scenarios_dir().glob("*.yaml")
    }


def all_scenarios() -> dict[str, str]:
    """Пользовательские сценарии перекрывают встроенные с тем же именем."""
    return {**builtin_scenarios(), **user_scenarios()}
```

- [ ] **Step 4: Написать `sgame/session/journal.py`**

```python
"""Журнал партии: входы игроков, из которых пересчитывается состояние."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..core.orders import DealOffer, Order
from .paths import all_scenarios, builtin_scenarios  # noqa: F401 — реэкспорт для веба

FORMAT = 1


@dataclass
class TeamSlot:
    faction: str
    team: str
    code: str


@dataclass
class RoundRecord:
    n: int
    orders: dict[str, list[Order]] = field(default_factory=dict)
    offers: list[DealOffer] = field(default_factory=list)
    responses: dict[str, bool] = field(default_factory=dict)
    narration: dict[str, Any] = field(default_factory=dict)
    resolved_at: str = ""


@dataclass
class Journal:
    format: int
    scenario_id: str
    scenario_sha256: str
    scenario_text: str
    seed: int
    created_at: str
    teams: list[TeamSlot] = field(default_factory=list)
    rounds: list[RoundRecord] = field(default_factory=list)

    def slot(self, faction: str) -> TeamSlot | None:
        return next((t for t in self.teams if t.faction == faction), None)


def new_journal(scenario_id: str, scenario_text: str, teams: list[TeamSlot], seed: int) -> Journal:
    return Journal(
        format=FORMAT,
        scenario_id=scenario_id,
        scenario_sha256=sha256(scenario_text.encode("utf-8")).hexdigest(),
        scenario_text=scenario_text,
        seed=seed,
        created_at=datetime.now().isoformat(timespec="seconds"),
        teams=list(teams),
    )


def to_dict(journal: Journal) -> dict:
    return {
        "format": journal.format,
        "scenario_id": journal.scenario_id,
        "scenario_sha256": journal.scenario_sha256,
        "scenario_text": journal.scenario_text,
        "seed": journal.seed,
        "created_at": journal.created_at,
        "teams": [asdict(t) for t in journal.teams],
        "rounds": [
            {
                "n": record.n,
                "orders": {
                    faction: [asdict(order) for order in orders]
                    for faction, orders in record.orders.items()
                },
                "offers": [asdict(offer) for offer in record.offers],
                "responses": record.responses,
                "narration": record.narration,
                "resolved_at": record.resolved_at,
            }
            for record in journal.rounds
        ],
    }


def from_dict(data: dict) -> Journal:
    if data.get("format") != FORMAT:
        raise ValueError(f"неизвестная версия файла партии: {data.get('format')!r}")
    return Journal(
        format=data["format"],
        scenario_id=data["scenario_id"],
        scenario_sha256=data["scenario_sha256"],
        scenario_text=data["scenario_text"],
        seed=data["seed"],
        created_at=data["created_at"],
        teams=[TeamSlot(**t) for t in data["teams"]],
        rounds=[
            RoundRecord(
                n=record["n"],
                orders={
                    faction: [Order(**order) for order in orders]
                    for faction, orders in record["orders"].items()
                },
                offers=[DealOffer(**offer) for offer in record["offers"]],
                responses=record["responses"],
                narration=record.get("narration", {}),
                resolved_at=record.get("resolved_at", ""),
            )
            for record in data["rounds"]
        ],
    )


def save(path: Path, journal: Journal) -> None:
    Path(path).write_text(
        json.dumps(to_dict(journal), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load(path: Path) -> Journal:
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
```

- [ ] **Step 5: Создать заглушку сценария, чтобы тест встроенных сценариев проходил**

```bash
cat > sgame/scenarios/meridian.yaml <<'YAML'
schema_version: 1
meta: { id: meridian, title: "Кризис в Меридианском заливе", rounds: 8, action_points: 3 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 200 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 30 }
factions:
  - { id: astoria, title: "Астория", start: { budget: 120 } }
  - { id: borea, title: "Борея", start: { budget: 100 } }
actions:
  - { id: invest, title: "Вложения", cost: { budget: 20 }, effects: [ { self: budget, delta: "30" } ] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
YAML
```

Заглушка намеренно валидная, а не пустая: стартовая страница разбирает каждый
найденный сценарий, и битый файл в списке ломал бы её. Полное содержимое
появится в задаче 15.

- [ ] **Step 6: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_journal.py -v`
Expected: PASS, 4 теста

- [ ] **Step 7: Коммит**

```bash
git add sgame/session tests/test_journal.py sgame/scenarios/meridian.yaml
git commit -m "feat: журнал партии и пользовательские директории"
```

---

## Task 10: Пересчёт журнала и откат раунда

**Files:**
- Create: `sgame/session/replay.py`
- Test: `tests/test_replay.py`

**Interfaces:**
- Consumes: `Journal`, `resolve`, `initial_state`, `parse_scenario`
- Produces:
  - `spec_of(journal) -> ScenarioSpec`
  - `replay(journal) -> tuple[GameState, list[tuple[Event, ...]]]`
  - `current_state(journal) -> GameState`
  - `undo_last(journal) -> None` — удаляет последний раунд на месте
  - `scenario_changed(journal, current_text) -> bool`

- [ ] **Step 1: Написать падающий тест `tests/test_replay.py`**

```python
from datetime import datetime

from sgame.core.orders import Order
from sgame.session import journal as J
from sgame.session.replay import current_state, replay, scenario_changed, undo_last

TEXT = """
schema_version: 1
meta: { id: t, title: "Т", rounds: 5, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 200 }
world: {}
factions:
  - { id: a, title: "А", start: { budget: 100 } }
  - { id: b, title: "Б", start: { budget: 100 } }
actions:
  - { id: spend, title: "Трата", cost: { budget: 10 }, effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""


def journal_with(rounds):
    journal = J.new_journal("t", TEXT, [J.TeamSlot("a", "Команда 1", "1111")], seed=5)
    for n, orders in enumerate(rounds, start=1):
        journal.rounds.append(
            J.RoundRecord(n=n, orders=orders, resolved_at=datetime.now().isoformat())
        )
    return journal


def test_replay_folds_rounds_into_state():
    journal = journal_with([{"a": [Order(action="spend")]}, {"a": [Order(action="spend")]}])
    state, per_round = current_state(journal), replay(journal)[1]
    assert state.tracks["a"]["budget"] == 80
    assert state.round == 3
    assert len(per_round) == 2


def test_replay_is_repeatable():
    journal = journal_with([{"a": [Order(action="spend")]}])
    assert replay(journal)[0].tracks == replay(journal)[0].tracks


def test_undo_returns_previous_state():
    journal = journal_with([{"a": [Order(action="spend")]}, {"a": [Order(action="spend")]}])
    undo_last(journal)
    assert len(journal.rounds) == 1
    assert current_state(journal).tracks["a"]["budget"] == 90


def test_undo_then_same_orders_reproduce_state():
    journal = journal_with([{"a": [Order(action="spend")]}, {"a": [Order(action="spend")]}])
    before = current_state(journal).tracks
    undo_last(journal)
    journal.rounds.append(J.RoundRecord(n=2, orders={"a": [Order(action="spend")]}))
    assert current_state(journal).tracks == before


def test_detects_changed_scenario():
    journal = journal_with([])
    assert scenario_changed(journal, TEXT) is False
    assert scenario_changed(journal, TEXT + "\n# правка\n") is True
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_replay.py -v`
Expected: FAIL — нет модуля `sgame.session.replay`

- [ ] **Step 3: Написать `sgame/session/replay.py`**

```python
"""Пересчёт журнала в состояние и откат раунда.

Состояние нигде не хранится: оно всегда получается прогоном всех раундов
журнала от начального состояния сценария. Отсюда воспроизводимость и
бесплатный откат.
"""

from hashlib import sha256

from ..core.events import Event
from ..core.resolve import resolve
from ..core.spec import ScenarioSpec, parse_scenario
from ..core.state import GameState, initial_state
from .journal import Journal


def spec_of(journal: Journal) -> ScenarioSpec:
    return parse_scenario(journal.scenario_text)


def replay(journal: Journal) -> tuple[GameState, list[tuple[Event, ...]]]:
    spec = spec_of(journal)
    state = initial_state(spec)
    history: list[tuple[Event, ...]] = []
    for record in journal.rounds:
        result = resolve(
            spec, state, record.orders, record.offers, record.responses, journal.seed
        )
        state = result.state
        history.append(result.events)
    return state, history


def current_state(journal: Journal) -> GameState:
    return replay(journal)[0]


def undo_last(journal: Journal) -> None:
    if journal.rounds:
        journal.rounds.pop()


def scenario_changed(journal: Journal, current_text: str) -> bool:
    return sha256(current_text.encode("utf-8")).hexdigest() != journal.scenario_sha256
```

- [ ] **Step 4: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_replay.py -v`
Expected: PASS, 5 тестов

- [ ] **Step 5: Коммит**

```bash
git add sgame/session/replay.py tests/test_replay.py
git commit -m "feat: пересчёт журнала и откат раунда"
```

---

## Task 11: Видимость и шаблонный нарратив

**Files:**
- Create: `sgame/narrate/view.py`, `sgame/narrate/templates.py`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: `Event`, `GameState`, `ScenarioSpec`, `score`
- Produces:
  - `events_for(events, viewer: str | None, role: Literal["team", "public", "host"]) -> list[Event]`
  - `tracks_for(spec, state, viewer) -> dict[str, dict[str, float]]` — чужие приватные треки скрыты
  - `narrate_public(spec, events) -> str`
  - `narrate_team(spec, events, faction) -> str`

- [ ] **Step 1: Написать падающий тест `tests/test_view.py`**

```python
from sgame.core.events import Delta, Event
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state
from sgame.narrate.templates import narrate_public, narrate_team
from sgame.narrate.view import events_for, tracks_for

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 3, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100, visibility: public }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 50, intel: 30 } }
  - { id: b, title: "Б", start: { budget: 50, intel: 70 } }
actions:
  - { id: noop, title: "Ничего", effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
""")

EVENTS = [
    Event(kind="action", title="Открытое", actor="a", audience="public"),
    Event(kind="action", title="Тайное", actor="a", target="b", audience="actor"),
    Event(kind="action", title="Раскрытое", actor="a", target="b", audience="actor_and_target"),
    Event(kind="note", title="Только ведущему", audience="host"),
]


def test_team_sees_public_own_and_addressed():
    titles = [e.title for e in events_for(EVENTS, "b", role="team")]
    assert titles == ["Открытое", "Раскрытое"]


def test_actor_sees_own_secret():
    titles = [e.title for e in events_for(EVENTS, "a", role="team")]
    assert "Тайное" in titles


def test_projector_shows_only_public():
    titles = [e.title for e in events_for(EVENTS, None, role="public")]
    assert titles == ["Открытое"]


def test_host_sees_everything():
    assert len(events_for(EVENTS, None, role="host")) == 4


def test_private_tracks_of_others_are_hidden():
    visible = tracks_for(SPEC, initial_state(SPEC), viewer="a")
    assert visible["a"]["Разведка"] == 30
    assert "Разведка" not in visible["b"]
    assert visible["b"]["Бюджет"] == 50


def test_narration_mentions_deltas():
    events = [
        Event(
            kind="action", title="Мобилизация", actor="a", audience="public",
            deltas=(Delta(scope="faction", who="a", track="Бюджет", amount=-20),),
        )
    ]
    text = narrate_public(SPEC, events)
    assert "Мобилизация" in text
    assert "Бюджет −20" in text


def test_team_narration_omits_foreign_secrets():
    text = narrate_team(SPEC, EVENTS, "b")
    assert "Тайное" not in text
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_view.py -v`
Expected: FAIL — нет модуля `sgame.narrate.view`

- [ ] **Step 3: Написать `sgame/narrate/view.py`**

```python
"""Кто что видит.

Единственное место, где решается видимость. Экраны и нарратив обязаны
ходить сюда: дублировать правило в шаблонах — верный способ его нарушить.
"""

from collections.abc import Sequence
from typing import Literal

from ..core.events import Event
from ..core.spec import ScenarioSpec
from ..core.state import GameState

Role = Literal["team", "public", "host"]


def visible_to(event: Event, viewer: str | None, role: Role) -> bool:
    if role == "host":
        return True
    if event.audience == "host":
        return False
    if event.audience == "public":
        return True
    if role == "public":
        return False
    if event.audience == "actor":
        return event.actor == viewer
    return viewer in (event.actor, event.target)


def events_for(events: Sequence[Event], viewer: str | None, role: Role) -> list[Event]:
    return [event for event in events if visible_to(event, viewer, role)]


def tracks_for(spec: ScenarioSpec, state: GameState, viewer: str | None) -> dict[str, dict[str, float]]:
    """Треки в виде «сторона → название трека → значение», с учётом приватности."""
    visible: dict[str, dict[str, float]] = {}
    for faction in spec.factions:
        own = faction.id == viewer
        visible[faction.id] = {
            track.title: state.tracks[faction.id][name]
            for name, track in spec.tracks.items()
            if own or track.visibility == "public"
        }
    return visible
```

- [ ] **Step 4: Написать `sgame/narrate/templates.py`**

```python
"""Шаблонный нарратив: работает всегда, в том числе без интернета."""

from collections.abc import Sequence

from ..core.events import Event
from ..core.spec import ScenarioSpec
from .view import events_for


def _title_of(spec: ScenarioSpec, faction_id: str | None) -> str:
    faction = spec.faction(faction_id) if faction_id else None
    return faction.title if faction else "—"


def _line(spec: ScenarioSpec, event: Event) -> str:
    parts = []
    if event.actor:
        parts.append(f"{_title_of(spec, event.actor)}:")
    parts.append(event.title)
    if event.target:
        parts.append(f"→ {_title_of(spec, event.target)}")
    if event.roll:
        parts.append(f"({event.roll})")
    line = " ".join(parts)
    if event.deltas:
        line += " — " + ", ".join(delta.describe() for delta in event.deltas)
    if event.detail:
        line += f". {event.detail}"
    return line


def _render(spec: ScenarioSpec, events: Sequence[Event]) -> str:
    if not events:
        return "За этот раунд ничего заметного не произошло."
    return "\n".join(f"• {_line(spec, event)}" for event in events)


def narrate_public(spec: ScenarioSpec, events: Sequence[Event]) -> str:
    return _render(spec, events_for(events, None, role="public"))


def narrate_team(spec: ScenarioSpec, events: Sequence[Event], faction: str) -> str:
    return _render(spec, events_for(events, faction, role="team"))


def narrate_host(spec: ScenarioSpec, events: Sequence[Event]) -> str:
    return _render(spec, events_for(events, None, role="host"))
```

- [ ] **Step 5: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_view.py -v`
Expected: PASS, 7 тестов

- [ ] **Step 6: Коммит**

```bash
git add sgame/narrate tests/test_view.py
git commit -m "feat: правила видимости и шаблонный нарратив"
```

---

## Task 12: Веб-каркас, активная сессия и пульт ведущего

Команды соответствуют сторонам сценария один к одному: сколько сторон, столько команд. Отдельного поля «число команд» нет.

**Files:**
- Create: `sgame/web/live.py`, `sgame/web/present.py`, `sgame/web/app.py`, `sgame/web/routes/host.py`, `sgame/web/templates/base.html`, `sgame/web/templates/start.html`, `sgame/web/templates/host.html`, `sgame/web/static/style.css`
- Test: `tests/test_web_host.py`

**Interfaces:**
- Consumes: `journal`, `replay`, `resolve`, `narrate_*`, `all_scenarios`
- Produces:
  - `live.start(scenario_id: str, seed: int) -> Live`, `live.current() -> Live | None`, `live.reset()`
  - `Live` с полями `path, journal, spec, drafts, offers, responses, submitted`
  - `live.state() -> GameState`, `live.history() -> list[tuple[Event, ...]]`
  - `live.close_round(force: bool = False) -> None`, `live.undo_round() -> None`
  - `present.action_options(spec, state, faction, draft) -> list[ActionOption]`
  - `create_app() -> FastAPI`, `serve(port: int, open_browser: bool) -> None`

- [ ] **Step 1: Написать падающий тест `tests/test_web_host.py`**

```python
import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app

SCENARIO = """
schema_version: 1
meta: { id: probe, title: "Проба", rounds: 2, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 20 }
factions:
  - { id: a, title: "Астория", start: { budget: 50 } }
  - { id: b, title: "Борея", start: { budget: 50 } }
actions:
  - { id: build, title: "Стройка", cost: { budget: 10 }, effects: [ { self: budget, delta: "2" } ] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "scenarios" / "probe.yaml").write_text(SCENARIO, encoding="utf-8")
    live.reset()
    yield
    live.reset()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_start_page_lists_scenarios(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Проба" in page.text


def test_creating_session_makes_a_team_per_faction(client):
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    session = live.current()
    assert [slot.faction for slot in session.journal.teams] == ["a", "b"]
    assert all(len(slot.code) == 4 for slot in session.journal.teams)


def test_host_console_shows_who_has_not_submitted(client):
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    page = client.get("/")
    assert "Астория" in page.text
    assert "не сдала" in page.text


def test_session_file_is_written(client, tmp_path):
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    assert list((tmp_path / "sessions").glob("*.json"))
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_web_host.py -v`
Expected: FAIL — нет модуля `sgame.web.live`

- [ ] **Step 3: Написать `sgame/web/live.py`**

```python
"""Активная партия в памяти процесса.

Игра идёт на одной машине, партия одна. Черновики приказов держим на
сервере: закрытая по ошибке вкладка не должна стоить команде хода.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from secrets import randbelow

from ..core.events import Event
from ..core.orders import DealOffer, Order
from ..core.resolve import resolve
from ..core.spec import ScenarioSpec, parse_scenario
from ..core.state import GameState
from ..narrate.templates import narrate_host, narrate_public, narrate_team
from ..session import journal as J
from ..session.paths import all_scenarios, sessions_dir
from ..session.replay import current_state, replay, undo_last


@dataclass
class Live:
    path: Path
    journal: J.Journal
    spec: ScenarioSpec
    drafts: dict[str, list[Order]] = field(default_factory=dict)
    offers: list[DealOffer] = field(default_factory=list)
    responses: dict[str, bool] = field(default_factory=dict)
    submitted: set[str] = field(default_factory=set)


_live: Live | None = None


def current() -> Live | None:
    return _live


def reset() -> None:
    global _live
    _live = None


def start(scenario_id: str, seed: int) -> Live:
    global _live
    text = all_scenarios()[scenario_id]
    spec = parse_scenario(text)
    teams = [
        J.TeamSlot(
            faction=faction.id,
            team=f"Команда {number}",
            code=f"{randbelow(9000) + 1000}",
        )
        for number, faction in enumerate(spec.factions, start=1)
    ]
    journal = J.new_journal(scenario_id, text, teams, seed)
    path = sessions_dir() / f"{scenario_id}-{datetime.now():%Y%m%d-%H%M%S}.json"
    J.save(path, journal)
    _live = Live(path=path, journal=journal, spec=spec, drafts={t.faction: [] for t in teams})
    return _live


def require() -> Live:
    if _live is None:
        raise LookupError("партия не начата")
    return _live


def state() -> GameState:
    return current_state(require().journal)


def history() -> list[tuple[Event, ...]]:
    return replay(require().journal)[1]


def last_events() -> tuple[Event, ...]:
    events = history()
    return events[-1] if events else ()


def submit(faction: str) -> None:
    require().submitted.add(faction)


def everyone_submitted() -> bool:
    session = require()
    return {t.faction for t in session.journal.teams} <= session.submitted


def close_round(force: bool = False) -> None:
    """Посчитать раунд. При force несдавшие команды пасуют."""
    session = require()
    if not force and not everyone_submitted():
        raise ValueError("не все команды сдали приказы")

    before = current_state(session.journal)
    orders = {
        faction: (session.drafts.get(faction, []) if faction in session.submitted else [])
        for faction in (slot.faction for slot in session.journal.teams)
    }
    result = resolve(
        session.spec, before, orders, session.offers, session.responses, session.journal.seed
    )
    narration = {
        "public": narrate_public(session.spec, result.events),
        "host": narrate_host(session.spec, result.events),
        "private": {
            slot.faction: narrate_team(session.spec, result.events, slot.faction)
            for slot in session.journal.teams
        },
    }
    session.journal.rounds.append(
        J.RoundRecord(
            n=before.round,
            orders=orders,
            offers=list(session.offers),
            responses=dict(session.responses),
            narration=narration,
            resolved_at=datetime.now().isoformat(timespec="seconds"),
        )
    )
    J.save(session.path, session.journal)
    session.drafts = {slot.faction: [] for slot in session.journal.teams}
    session.offers = []
    session.responses = {}
    session.submitted = set()


def undo_round() -> None:
    session = require()
    undo_last(session.journal)
    J.save(session.path, session.journal)
    session.drafts = {slot.faction: [] for slot in session.journal.teams}
    session.offers = []
    session.responses = {}
    session.submitted = set()
```

- [ ] **Step 4: Написать `sgame/web/present.py`**

```python
"""Подготовка данных для экранов.

Доступность действия проверяется той же фазой валидации, что и в расчёте
раунда: если правило одно, интерфейс не может разойтись с моделью.
"""

from dataclasses import dataclass

from ..core.orders import Order
from ..core.phases import phase_validate
from ..core.spec import ActionSpec, ScenarioSpec
from ..core.state import GameState, StateBuilder


@dataclass
class ActionOption:
    action: ActionSpec
    available: bool
    reason: str = ""


def action_options(
    spec: ScenarioSpec, state: GameState, faction: str, draft: list[Order]
) -> list[ActionOption]:
    others = [f.id for f in spec.factions if f.id != faction]
    options: list[ActionOption] = []

    for action in spec.actions:
        probe = Order(
            action=action.id,
            target=others[0] if action.target == "faction" and others else None,
        )
        builder = StateBuilder(spec, state)
        accepted, rejected = phase_validate(spec, builder, {faction: [*draft, probe]})
        chosen = len(draft)
        available = any(item.index == chosen for item in accepted)
        reason = ""
        if not available and rejected:
            reason = rejected[-1].detail.split(": ", 1)[-1]
        options.append(ActionOption(action=action, available=available, reason=reason))

    return options


def points_left(spec: ScenarioSpec, draft: list[Order]) -> int:
    spent = sum(spec.action(order.action).ap for order in draft if spec.action(order.action))
    return spec.meta.action_points - spent
```

- [ ] **Step 5: Написать `sgame/web/app.py`**

```python
"""Сборка и запуск локального приложения."""

import socket
import threading
import webbrowser
from importlib import resources

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_TEMPLATE_DIR = resources.files("sgame") / "web" / "templates"
_STATIC_DIR = resources.files("sgame") / "web" / "static"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def create_app() -> FastAPI:
    from .routes import host

    app = FastAPI(title="Стратегическая игра")
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    app.include_router(host.router)
    return app


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def serve(port: int = 0, open_browser: bool = True) -> None:
    import uvicorn

    chosen = port or _free_port()
    url = f"http://127.0.0.1:{chosen}/"
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Приложение открыто: {url}")
    uvicorn.run(create_app(), host="127.0.0.1", port=chosen, log_level="warning")
```

- [ ] **Step 6: Написать шаблоны и стиль**

`sgame/web/templates/base.html`:

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Стратегическая игра{% endblock %}</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <main>{% block body %}{% endblock %}</main>
</body>
</html>
```

`sgame/web/templates/start.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>Новая партия</h1>
<form method="post" action="/session/new">
  <label>Сценарий
    <select name="scenario">
      {% for id, title in scenarios.items() %}
      <option value="{{ id }}">{{ title }}</option>
      {% endfor %}
    </select>
  </label>
  <label>Ключ партии (seed)
    <input type="number" name="seed" value="{{ default_seed }}">
  </label>
  <button type="submit">Начать</button>
</form>
{% endblock %}
```

`sgame/web/templates/host.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>{{ spec.meta.title }}</h1>
<p class="round">Раунд {{ state.round }} из {{ spec.meta.rounds }}</p>

{% if state.finished %}
  <p class="big">Игра окончена.</p>
  <a class="button" href="/debrief">Перейти к разбору</a>
{% else %}
  <p class="big">{{ next_team_message }}</p>
  <table>
    <tr><th>Сторона</th><th>Команда</th><th>Код</th><th>Статус</th></tr>
    {% for slot in teams %}
    <tr>
      <td>{{ spec.faction(slot.faction).title }}</td>
      <td>{{ slot.team }}</td>
      <td class="code">{{ slot.code }}</td>
      <td>{{ "сдала" if slot.faction in submitted else "не сдала" }}</td>
    </tr>
    {% endfor %}
  </table>

  <form method="post" action="/round/close">
    <button type="submit" {% if not all_submitted %}disabled{% endif %}>Закрыть раунд</button>
  </form>
  <form method="post" action="/round/close">
    <input type="hidden" name="force" value="1">
    <button type="submit" class="secondary">Закрыть принудительно (несдавшие пасуют)</button>
  </form>
{% endif %}

<form method="post" action="/round/undo">
  <button type="submit" class="secondary" {% if not can_undo %}disabled{% endif %}>Откатить раунд</button>
</form>

<p><a href="/screen" target="_blank">Экран для проектора</a></p>
{% endblock %}
```

`sgame/web/static/style.css`:

```css
:root { color-scheme: light; font-family: -apple-system, system-ui, sans-serif; }
body { margin: 0; background: #f6f5f2; color: #1b1b1b; }
main { max-width: 60rem; margin: 0 auto; padding: 2rem 1.5rem 4rem; }
h1 { font-size: 1.6rem; }
.big { font-size: 1.5rem; font-weight: 600; background: #fff; padding: 1rem; border-radius: .5rem; }
.round { color: #666; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; background: #fff; }
th, td { text-align: left; padding: .5rem .75rem; border-bottom: 1px solid #e3e0da; }
.code { font-family: ui-monospace, monospace; letter-spacing: .1em; }
button, .button { font: inherit; padding: .6rem 1rem; border: 0; border-radius: .4rem;
  background: #2f5d50; color: #fff; cursor: pointer; text-decoration: none; display: inline-block; }
button[disabled] { background: #bdbdbd; cursor: not-allowed; }
button.secondary { background: #6b6b6b; }
form { margin: .5rem 0; }
label { display: block; margin: .75rem 0; }
.card { background: #fff; border-radius: .5rem; padding: 1rem; margin: .5rem 0; }
.card.disabled { opacity: .55; }
.news { white-space: pre-wrap; background: #fff; padding: 1rem; border-radius: .5rem; }
```

- [ ] **Step 7: Написать `sgame/web/routes/host.py`**

```python
"""Пульт ведущего."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...core.errors import ScenarioError
from ...core.spec import parse_scenario
from ...session.paths import all_scenarios
from .. import live
from ..app import templates

router = APIRouter()


@router.get("/")
def console(request: Request):
    session = live.current()
    if session is None:
        scenarios = {}
        for key, text in all_scenarios().items():
            try:
                scenarios[key] = parse_scenario(text).meta.title
            except ScenarioError:
                continue  # битый пользовательский файл не должен ломать стартовую страницу
        return templates.TemplateResponse(
            request, "start.html", {"scenarios": scenarios, "default_seed": 20260901}
        )

    state = live.state()
    waiting = [
        slot for slot in session.journal.teams if slot.faction not in session.submitted
    ]
    message = (
        f"Передайте компьютер: {session.spec.faction(waiting[0].faction).title}"
        if waiting
        else "Все команды сдали приказы — можно закрывать раунд"
    )
    return templates.TemplateResponse(
        request,
        "host.html",
        {
            "spec": session.spec,
            "state": state,
            "teams": session.journal.teams,
            "submitted": session.submitted,
            "all_submitted": not waiting,
            "can_undo": bool(session.journal.rounds),
            "next_team_message": message,
        },
    )


@router.post("/session/new")
def new_session(scenario: str = Form(...), seed: int = Form(...)):
    live.start(scenario, seed)
    return RedirectResponse("/", status_code=303)


@router.post("/round/close")
def close_round(force: str = Form(default="")):
    try:
        live.close_round(force=bool(force))
    except ValueError:
        pass  # не все сдали — просто возвращаем ведущего на пульт
    return RedirectResponse("/", status_code=303)


@router.post("/round/undo")
def undo_round():
    live.undo_round()
    return RedirectResponse("/", status_code=303)
```

- [ ] **Step 8: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_web_host.py -v`
Expected: PASS, 4 теста

- [ ] **Step 9: Коммит**

```bash
git add sgame/web tests/test_web_host.py
git commit -m "feat: веб-каркас, активная партия и пульт ведущего"
```

---

## Task 13: Экран команды и защита чужих данных

**Files:**
- Create: `sgame/web/routes/team.py`, `sgame/web/templates/team_login.html`, `sgame/web/templates/team.html`, `sgame/web/templates/team_done.html`
- Modify: `sgame/web/app.py` (подключить маршрутизатор)
- Test: `tests/test_web_team.py`, `tests/test_web_secrecy.py`

**Interfaces:**
- Consumes: `live`, `present.action_options`, `view.tracks_for`, `view.events_for`
- Produces: маршруты `/team/{faction}`, `/team/{faction}/login`, `/team/{faction}/order`, `/team/{faction}/order/remove`, `/team/{faction}/offer`, `/team/{faction}/response`, `/team/{faction}/submit`, `/team/{faction}/done`

- [ ] **Step 1: Написать падающий тест `tests/test_web_team.py`**

```python
import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app

SCENARIO = """
schema_version: 1
meta: { id: probe, title: "Проба", rounds: 2, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 20 }
factions:
  - { id: a, title: "Астория", start: { budget: 50, intel: 10 }, briefing: "ТАЙНА АСТОРИИ" }
  - { id: b, title: "Борея", start: { budget: 50, intel: 90 }, briefing: "ТАЙНА БОРЕИ" }
actions:
  - { id: build, title: "Стройка", cost: { budget: 10 }, effects: [ { self: budget, delta: "2" } ] }
  - { id: costly, title: "Неподъёмное", cost: { budget: 999 }, effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "scenarios" / "probe.yaml").write_text(SCENARIO, encoding="utf-8")
    live.reset()
    yield
    live.reset()


@pytest.fixture
def client():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    return client


def code_for(faction):
    return live.current().journal.slot(faction).code


def login(client, faction):
    client.post(f"/team/{faction}/login", data={"code": code_for(faction)}, follow_redirects=True)


def test_wrong_code_does_not_open_screen(client):
    page = client.post("/team/a/login", data={"code": "0000"}, follow_redirects=True)
    assert "ТАЙНА АСТОРИИ" not in page.text
    assert "код" in page.text.lower()


def test_correct_code_opens_own_briefing(client):
    login(client, "a")
    page = client.get("/team/a")
    assert "ТАЙНА АСТОРИИ" in page.text


def test_unavailable_action_shows_reason(client):
    login(client, "a")
    page = client.get("/team/a")
    assert "Неподъёмное" in page.text
    assert "хватает" in page.text


def test_adding_order_updates_draft_and_points(client):
    login(client, "a")
    client.post("/team/a/order", data={"action": "build", "target": ""}, follow_redirects=True)
    assert [order.action for order in live.current().drafts["a"]] == ["build"]
    assert "Очки действий: 1 из 2" in client.get("/team/a").text


def test_removing_order_restores_points(client):
    login(client, "a")
    client.post("/team/a/order", data={"action": "build", "target": ""}, follow_redirects=True)
    client.post("/team/a/order/remove", data={"index": "0"}, follow_redirects=True)
    assert live.current().drafts["a"] == []


def test_intent_text_is_kept_with_order(client):
    login(client, "a")
    client.post(
        "/team/a/order",
        data={"action": "build", "target": "", "intent": "усиливаем тыл"},
        follow_redirects=True,
    )
    assert live.current().drafts["a"][0].intent == "усиливаем тыл"


def test_submit_locks_screen_and_clears_cookie(client):
    login(client, "a")
    client.post("/team/a/submit", follow_redirects=True)
    assert "a" in live.current().submitted
    page = client.get("/team/a")
    assert "ТАЙНА АСТОРИИ" not in page.text
```

- [ ] **Step 2: Написать падающий тест `tests/test_web_secrecy.py`**

```python
import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app
from tests.test_web_team import SCENARIO  # тот же сценарий


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "scenarios" / "probe.yaml").write_text(SCENARIO, encoding="utf-8")
    live.reset()
    yield
    live.reset()


@pytest.fixture
def client():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    return client


def test_team_screen_never_shows_foreign_briefing(client):
    slot = live.current().journal.slot("a")
    client.post("/team/a/login", data={"code": slot.code}, follow_redirects=True)
    page = client.get("/team/a")
    assert "ТАЙНА БОРЕИ" not in page.text


def test_team_screen_never_shows_foreign_private_track(client):
    slot = live.current().journal.slot("a")
    client.post("/team/a/login", data={"code": slot.code}, follow_redirects=True)
    page = client.get("/team/a")
    assert "90" not in page.text


def test_team_screen_never_shows_foreign_code(client):
    slot_a = live.current().journal.slot("a")
    slot_b = live.current().journal.slot("b")
    client.post("/team/a/login", data={"code": slot_a.code}, follow_redirects=True)
    assert slot_b.code not in client.get("/team/a").text


def test_projector_shows_no_briefings_and_no_codes(client):
    page = client.get("/screen")
    assert "ТАЙНА" not in page.text
    for slot in live.current().journal.teams:
        assert slot.code not in page.text
```

- [ ] **Step 3: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_web_team.py tests/test_web_secrecy.py -v`
Expected: FAIL — маршруты команды не существуют (404)

- [ ] **Step 4: Написать `sgame/web/routes/team.py`**

```python
"""Экран команды. Единственное место, где команда что-либо вводит."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...core.orders import DealOffer, Order
from ...narrate.view import events_for, tracks_for
from .. import live, present
from ..app import templates

router = APIRouter()

COOKIE = "sgame_team"


def _authorised(request: Request, faction: str) -> bool:
    session = live.current()
    if session is None or faction in session.submitted:
        return False
    slot = session.journal.slot(faction)
    return slot is not None and request.cookies.get(COOKIE) == f"{faction}:{slot.code}"


@router.get("/team/{faction}")
def screen(request: Request, faction: str):
    session = live.require()
    if not _authorised(request, faction):
        return templates.TemplateResponse(
            request,
            "team_login.html",
            {"faction": faction, "title": session.spec.faction(faction).title, "error": ""},
        )

    state = live.state()
    draft = session.drafts.get(faction, [])
    return templates.TemplateResponse(
        request,
        "team.html",
        {
            "spec": session.spec,
            "faction": session.spec.faction(faction),
            "state": state,
            "tracks": tracks_for(session.spec, state, faction),
            "options": present.action_options(session.spec, state, faction, draft),
            "draft": draft,
            "points_left": present.points_left(session.spec, draft),
            "others": [f for f in session.spec.factions if f.id != faction],
            "news": session.journal.rounds[-1].narration["private"].get(faction, "")
            if session.journal.rounds
            else "Игра начинается.",
            "incoming": [o for o in state.pending_offers if o.receiver == faction],
            "deals": session.spec.deals,
        },
    )


@router.post("/team/{faction}/login")
def login(request: Request, faction: str, code: str = Form(...)):
    session = live.require()
    slot = session.journal.slot(faction)
    if slot is None or slot.code != code:
        return templates.TemplateResponse(
            request,
            "team_login.html",
            {
                "faction": faction,
                "title": session.spec.faction(faction).title,
                "error": "Неверный код команды",
            },
        )
    response = RedirectResponse(f"/team/{faction}", status_code=303)
    response.set_cookie(COOKIE, f"{faction}:{slot.code}", httponly=True, samesite="strict")
    return response


@router.post("/team/{faction}/order")
def add_order(
    request: Request,
    faction: str,
    action: str = Form(...),
    target: str = Form(default=""),
    intent: str = Form(default=""),
):
    if _authorised(request, faction):
        session = live.require()
        session.drafts.setdefault(faction, []).append(
            Order(action=action, target=target or None, intent=intent)
        )
    return RedirectResponse(f"/team/{faction}", status_code=303)


@router.post("/team/{faction}/order/remove")
def remove_order(request: Request, faction: str, index: int = Form(...)):
    if _authorised(request, faction):
        draft = live.require().drafts.get(faction, [])
        if 0 <= index < len(draft):
            draft.pop(index)
    return RedirectResponse(f"/team/{faction}", status_code=303)


@router.post("/team/{faction}/offer")
def make_offer(
    request: Request,
    faction: str,
    deal: str = Form(...),
    receiver: str = Form(...),
    amount: str = Form(default=""),
):
    if _authorised(request, faction):
        session = live.require()
        session.offers.append(
            DealOffer(
                id=f"{faction}:{len(session.offers)}",
                deal=deal,
                sender=faction,
                receiver=receiver,
                amount=float(amount) if amount else None,
            )
        )
    return RedirectResponse(f"/team/{faction}", status_code=303)


@router.post("/team/{faction}/response")
def respond(request: Request, faction: str, offer: str = Form(...), accept: str = Form(default="")):
    if _authorised(request, faction):
        live.require().responses[offer] = bool(accept)
    return RedirectResponse(f"/team/{faction}", status_code=303)


@router.post("/team/{faction}/submit")
def submit(request: Request, faction: str):
    if _authorised(request, faction):
        live.submit(faction)
    response = RedirectResponse(f"/team/{faction}/done", status_code=303)
    response.delete_cookie(COOKIE)
    return response


@router.get("/team/{faction}/done")
def done(request: Request, faction: str):
    session = live.require()
    waiting = [s for s in session.journal.teams if s.faction not in session.submitted]
    return templates.TemplateResponse(
        request,
        "team_done.html",
        {
            "next_team": session.spec.faction(waiting[0].faction).title if waiting else None,
        },
    )
```

- [ ] **Step 5: Написать шаблоны команды**

`sgame/web/templates/team_login.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>{{ title }}</h1>
<p>Введите код команды.</p>
{% if error %}<p class="big">{{ error }}</p>{% endif %}
<form method="post" action="/team/{{ faction }}/login">
  <label>Код <input name="code" inputmode="numeric" autocomplete="off" autofocus></label>
  <button type="submit">Войти</button>
</form>
{% endblock %}
```

`sgame/web/templates/team.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>{{ faction.title }}</h1>
<p class="round">Раунд {{ state.round }} из {{ spec.meta.rounds }} ·
   Очки действий: {{ points_left }} из {{ spec.meta.action_points }}</p>

<section class="card">
  <h2>Ваш брифинг</h2>
  <p>{{ faction.briefing }}</p>
  {% if faction.goals %}
  <ul>{% for goal in faction.goals %}<li>{{ goal.title }} — {{ goal.score }} очк.</li>{% endfor %}</ul>
  {% endif %}
</section>

<section class="card">
  <h2>Новости</h2>
  <div class="news">{{ news }}</div>
</section>

<section class="card">
  <h2>Обстановка</h2>
  <table>
    {% for id, values in tracks.items() %}
    <tr><th>{{ spec.faction(id).title }}</th>
      <td>{% for name, value in values.items() %}{{ name }}: {{ value }}{% if not loop.last %} · {% endif %}{% endfor %}</td>
    </tr>
    {% endfor %}
    <tr><th>Мир</th><td>{% for name, track in spec.world.items() %}{{ track.title }}: {{ state.world[name] }} {% endfor %}</td></tr>
  </table>
</section>

<section class="card">
  <h2>Ваши приказы</h2>
  {% if draft %}
  <ol>
    {% for order in draft %}
    <li>{{ spec.action(order.action).title }}
      {% if order.target %}→ {{ spec.faction(order.target).title }}{% endif %}
      {% if order.intent %}<em>«{{ order.intent }}»</em>{% endif %}
      <form method="post" action="/team/{{ faction.id }}/order/remove">
        <input type="hidden" name="index" value="{{ loop.index0 }}">
        <button class="secondary" type="submit">Убрать</button>
      </form>
    </li>
    {% endfor %}
  </ol>
  {% else %}<p>Приказов пока нет.</p>{% endif %}
  <form method="post" action="/team/{{ faction.id }}/submit">
    <button type="submit">Сдать приказы</button>
  </form>
</section>

<h2>Доступные действия</h2>
{% for option in options %}
<section class="card {% if not option.available %}disabled{% endif %}">
  <h3>{{ option.action.title }}</h3>
  <p>{{ option.action.description }}</p>
  <p>Стоимость: {% for name, amount in option.action.cost.items() %}{{ spec.tracks[name].title }} {{ amount }} {% endfor %}
     · Очки действий: {{ option.action.ap }}</p>
  {% if option.available %}
  <form method="post" action="/team/{{ faction.id }}/order">
    <input type="hidden" name="action" value="{{ option.action.id }}">
    {% if option.action.target == "faction" %}
    <label>Цель
      <select name="target">
        {% for other in others %}<option value="{{ other.id }}">{{ other.title }}</option>{% endfor %}
      </select>
    </label>
    {% endif %}
    <label>Замысел (для разбора после игры)
      <input name="intent" maxlength="300" placeholder="Зачем вы это делаете">
    </label>
    <button type="submit">Добавить приказ</button>
  </form>
  {% else %}
  <p><strong>Недоступно:</strong> {{ option.reason }}</p>
  {% endif %}
</section>
{% endfor %}

<h2>Дипломатия</h2>
{% for offer in incoming %}
<section class="card">
  <p>Предложение от {{ spec.faction(offer.sender).title }}: {{ spec.deal(offer.deal).title }}
     {% if offer.amount %}({{ offer.amount }}){% endif %}</p>
  <form method="post" action="/team/{{ faction.id }}/response">
    <input type="hidden" name="offer" value="{{ offer.id }}">
    <button type="submit" name="accept" value="1">Принять</button>
    <button type="submit" class="secondary">Отклонить</button>
  </form>
</section>
{% endfor %}
<section class="card">
  <form method="post" action="/team/{{ faction.id }}/offer">
    <label>Предложить
      <select name="deal">{% for deal in deals %}<option value="{{ deal.id }}">{{ deal.title }}</option>{% endfor %}</select>
    </label>
    <label>Кому
      <select name="receiver">{% for other in others %}<option value="{{ other.id }}">{{ other.title }}</option>{% endfor %}</select>
    </label>
    <label>Сколько (для передачи ресурса) <input name="amount" inputmode="numeric"></label>
    <button type="submit">Отправить предложение</button>
  </form>
  <p>Ответ придёт в следующем раунде.</p>
</section>
{% endblock %}
```

`sgame/web/templates/team_done.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>Приказы приняты</h1>
{% if next_team %}
<p class="big">Передайте компьютер команде: {{ next_team }}</p>
{% else %}
<p class="big">Все команды сдали приказы. Верните компьютер ведущему.</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 5б: Добавить заглушку экрана — кнопку «Скрыть» и таймер бездействия**

`sgame/web/static/hide.js`:

```javascript
// Экран команды гаснет по кнопке и через минуту бездействия:
// компьютер переходит из рук в руки, случайный взгляд не должен ничего показать.
(function () {
  const cover = document.getElementById("cover");
  if (!cover) return;
  let timer = null;

  function hide() { cover.hidden = false; }
  function show() { cover.hidden = true; restart(); }
  function restart() {
    clearTimeout(timer);
    timer = setTimeout(hide, 60000);
  }

  document.getElementById("hide-button").addEventListener("click", hide);
  cover.addEventListener("click", show);
  ["keydown", "pointerdown"].forEach((event) =>
    document.addEventListener(event, () => { if (cover.hidden) restart(); })
  );
  restart();
})();
```

В `sgame/web/templates/team.html` сразу после `{% block body %}` добавить:

```html
<div id="cover" hidden class="cover"><p>Экран скрыт. Нажмите, чтобы вернуться.</p></div>
<button id="hide-button" class="secondary" type="button">Скрыть экран</button>
<script src="/static/hide.js" defer></script>
```

В `sgame/web/static/style.css` добавить:

```css
.cover { position: fixed; inset: 0; background: #1b1b1b; color: #f6f5f2;
  display: flex; align-items: center; justify-content: center; font-size: 1.5rem; z-index: 10; }
```

Добавить в `tests/test_web_team.py` проверку, что заглушка на странице есть:

```python
def test_screen_has_hide_control(client):
    login(client, "a")
    page = client.get("/team/a")
    assert 'id="cover"' in page.text
    assert "/static/hide.js" in page.text
```

- [ ] **Step 6: Подключить маршрутизатор в `sgame/web/app.py`**

```python
    from .routes import host, screen, team

    app.include_router(host.router)
    app.include_router(team.router)
    app.include_router(screen.router)
```

Маршрутизатор `screen` появится в задаче 14 — до этого строку с ним не добавлять.

- [ ] **Step 7: Прогнать тесты**

Run: `.venv/bin/pytest tests/test_web_team.py -v`
Expected: PASS, 8 тестов. Тесты секретности пока падают на `/screen` — это задача 14.

- [ ] **Step 8: Коммит**

```bash
git add sgame/web tests/test_web_team.py tests/test_web_secrecy.py
git commit -m "feat: экран команды с черновиком приказов и дипломатией"
```

---

## Task 14: Проектор, закрытие раунда и экран разбора

**Files:**
- Create: `sgame/web/routes/screen.py`, `sgame/web/templates/screen.html`, `sgame/web/templates/debrief.html`
- Modify: `sgame/web/app.py` (подключить `screen.router`)
- Test: `tests/test_web_round.py`, плюс проходят ранее написанные `tests/test_web_secrecy.py`

**Interfaces:**
- Consumes: `live`, `score`, `narrate_public`
- Produces: маршруты `GET /screen`, `GET /debrief`

- [ ] **Step 1: Написать падающий тест `tests/test_web_round.py`**

```python
import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app
from tests.test_web_team import SCENARIO


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "scenarios" / "probe.yaml").write_text(SCENARIO, encoding="utf-8")
    live.reset()
    yield
    live.reset()


@pytest.fixture
def client():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    return client


def play(client, faction, action="build"):
    code = live.current().journal.slot(faction).code
    client.post(f"/team/{faction}/login", data={"code": code}, follow_redirects=True)
    client.post(f"/team/{faction}/order", data={"action": action, "target": ""}, follow_redirects=True)
    client.post(f"/team/{faction}/submit", follow_redirects=True)


def test_round_does_not_close_until_everyone_submitted(client):
    play(client, "a")
    client.post("/round/close", follow_redirects=True)
    assert live.current().journal.rounds == []
    assert live.state().round == 1


def test_closing_round_advances_state_and_writes_journal(client):
    play(client, "a")
    play(client, "b")
    client.post("/round/close", follow_redirects=True)
    session = live.current()
    assert len(session.journal.rounds) == 1
    assert live.state().round == 2
    assert session.drafts == {"a": [], "b": []}


def test_forced_close_records_pass_for_missing_team(client):
    play(client, "a")
    client.post("/round/close", data={"force": "1"}, follow_redirects=True)
    assert live.current().journal.rounds[0].orders["b"] == []


def test_undo_returns_to_previous_round(client):
    play(client, "a")
    play(client, "b")
    client.post("/round/close", follow_redirects=True)
    client.post("/round/undo", follow_redirects=True)
    assert live.state().round == 1
    assert live.current().journal.rounds == []


def test_projector_shows_public_news_after_round(client):
    play(client, "a")
    play(client, "b")
    client.post("/round/close", follow_redirects=True)
    page = client.get("/screen")
    assert "Стройка" in page.text
    assert "Напряжённость" in page.text


def test_debrief_lists_scores(client):
    play(client, "a")
    play(client, "b")
    client.post("/round/close", follow_redirects=True)
    page = client.get("/debrief")
    assert "Астория" in page.text
    assert "Итог" in page.text
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.venv/bin/pytest tests/test_web_round.py -v`
Expected: FAIL — маршрут `/screen` не найден

- [ ] **Step 3: Написать `sgame/web/routes/screen.py`**

```python
"""Проекторный экран и разбор полётов."""

from fastapi import APIRouter, Request

from ...core.scoring import score
from .. import live
from ..app import templates

router = APIRouter()


@router.get("/screen")
def projector(request: Request):
    session = live.require()
    state = live.state()
    rounds = session.journal.rounds
    return templates.TemplateResponse(
        request,
        "screen.html",
        {
            "spec": session.spec,
            "state": state,
            "news": rounds[-1].narration["public"] if rounds else "Игра начинается.",
            "shown_round": rounds[-1].n if rounds else state.round,
        },
    )


@router.get("/debrief")
def debrief(request: Request):
    session = live.require()
    state = live.state()
    results = []
    for slot in session.journal.teams:
        total, breakdown = score(session.spec, state, slot.faction)
        results.append(
            {
                "title": session.spec.faction(slot.faction).title,
                "team": slot.team,
                "total": total,
                "breakdown": breakdown,
            }
        )
    results.sort(key=lambda row: row["total"], reverse=True)

    timeline = [
        {
            "n": record.n,
            "public": record.narration.get("public", ""),
            "host": record.narration.get("host", ""),
            "intents": [
                (session.spec.faction(faction).title, order.action, order.intent)
                for faction, orders in sorted(record.orders.items())
                for order in orders
                if order.intent
            ],
        }
        for record in session.journal.rounds
    ]

    return templates.TemplateResponse(
        request,
        "debrief.html",
        {"spec": session.spec, "results": results, "timeline": timeline},
    )
```

- [ ] **Step 4: Написать шаблоны**

`sgame/web/templates/screen.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>{{ spec.meta.title }} — раунд {{ shown_round }}</h1>
<section class="card">
  <h2>Обстановка в мире</h2>
  <p>{% for name, track in spec.world.items() %}{{ track.title }}: <strong>{{ state.world[name] }}</strong>{% if not loop.last %} · {% endif %}{% endfor %}</p>
</section>
<section class="card">
  <h2>Стороны</h2>
  <table>
    {% for faction in spec.factions %}
    <tr>
      <th>{{ faction.title }}</th>
      <td>{% for name, track in spec.tracks.items() %}{% if track.visibility == "public" %}{{ track.title }}: {{ state.tracks[faction.id][name] }} {% endif %}{% endfor %}</td>
    </tr>
    {% endfor %}
  </table>
</section>
<section class="card">
  <h2>Сводка</h2>
  <div class="news">{{ news }}</div>
</section>
{% endblock %}
```

`sgame/web/templates/debrief.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>Разбор партии</h1>
<h2>Итог</h2>
<table>
  <tr><th>Место</th><th>Сторона</th><th>Команда</th><th>Очки</th><th>Из чего</th></tr>
  {% for row in results %}
  <tr>
    <td>{{ loop.index }}</td><td>{{ row.title }}</td><td>{{ row.team }}</td><td>{{ row.total }}</td>
    <td>{% for name, value in row.breakdown %}{{ name }}: {{ value }}{% if not loop.last %}; {% endif %}{% endfor %}</td>
  </tr>
  {% endfor %}
</table>

<h2>Ход игры</h2>
{% for round in timeline %}
<section class="card">
  <h3>Раунд {{ round.n }}</h3>
  <div class="news">{{ round.host }}</div>
  {% if round.intents %}
  <h4>Замыслы команд</h4>
  <ul>{% for title, action, intent in round.intents %}<li>{{ title }} ({{ action }}): «{{ intent }}»</li>{% endfor %}</ul>
  {% endif %}
</section>
{% endfor %}
{% endblock %}
```

- [ ] **Step 5: Подключить `screen.router` в `create_app`**

В `sgame/web/app.py` строка импорта и подключения должна стать такой:

```python
    from .routes import host, screen, team

    app.include_router(host.router)
    app.include_router(team.router)
    app.include_router(screen.router)
```

- [ ] **Step 6: Прогнать веб-тесты, включая тесты секретности**

Run: `.venv/bin/pytest tests/test_web_round.py tests/test_web_secrecy.py tests/test_web_team.py -v`
Expected: PASS, 17 тестов

- [ ] **Step 7: Коммит**

```bash
git add sgame/web tests/test_web_round.py
git commit -m "feat: проектор, закрытие и откат раунда, экран разбора"
```

---

## Task 15: Эталонная игра и золотой прогон

**Files:**
- Create (заменить заглушку): `sgame/scenarios/meridian.yaml`
- Create: `tests/test_meridian.py`, `tests/golden/meridian.json`
- Test: `tests/test_meridian.py`

**Interfaces:**
- Consumes: `validate_scenario`, `replay`, `builtin_scenarios`
- Produces: сценарий `meridian` и зафиксированный прогон

- [ ] **Step 1: Написать `sgame/scenarios/meridian.yaml`**

```yaml
schema_version: 1

meta:
  id: meridian
  title: "Кризис в Меридианском заливе"
  rounds: 8
  action_points: 3

tracks:
  budget:     { title: "Бюджет",        min: 0, max: 200, visibility: public }
  army:       { title: "Вооружённые силы", min: 0, max: 100, visibility: public }
  legitimacy: { title: "Легитимность",  min: 0, max: 100, visibility: public }
  intel:      { title: "Разведка",      min: 0, max: 100, visibility: private }

world:
  tension:   { title: "Напряжённость", min: 0, max: 100, start: 30 }
  attention: { title: "Внимание мира", min: 0, max: 100, start: 20 }

factions:
  - id: astoria
    title: "Астория"
    start: { budget: 120, army: 60, legitimacy: 55, intel: 40 }
    briefing: |
      Вы контролируете северный берег пролива и половину его судоходства.
      Внутри страны вас упрекают в мягкости. Открытая война обойдётся дороже,
      чем любые уступки, но отдать пролив нельзя.
    goals:
      - { id: strait, title: "Пролив под контролем при мире", when: "world.tension < 60", score: 30 }
      - { id: strong, title: "Сильная армия к финалу", when: "self.army >= 70", score: 15 }

  - id: borea
    title: "Борея"
    start: { budget: 100, army: 75, legitimacy: 45, intel: 60 }
    briefing: |
      Ваша армия сильнее соседской, но казна беднее. Внутренняя поддержка
      держится на образе защитника соотечественников за проливом.
    goals:
      - { id: pressure, title: "Астория ослаблена", when: "rel('astoria', 'borea') < -30", score: 25 }
      - { id: solvent, title: "Казна не пуста", when: "self.budget >= 80", score: 20 }

  - id: caldera
    title: "Кальдера"
    start: { budget: 140, army: 40, legitimacy: 65, intel: 50 }
    briefing: |
      Вы торговая держава: и то и другое побережье — ваши рынки. Война
      обрушит ваши доходы, но и полная тишина лишает вас роли посредника.
    goals:
      - { id: calm, title: "Регион спокоен", when: "world.tension < 40", score: 30 }
      - { id: rich, title: "Богатая казна", when: "self.budget >= 150", score: 20 }

  - id: delta
    title: "Дельта"
    start: { budget: 80, army: 50, legitimacy: 35, intel: 70 }
    briefing: |
      Вы слабее всех по экономике, но ваша разведка лучшая в регионе.
      Ваша власть держится на страхе соседей, а не на любви населения.
    goals:
      - { id: legit, title: "Легитимность выправлена", when: "self.legitimacy >= 55", score: 30 }
      - { id: chaos, title: "Соседи заняты друг другом", when: "world.tension > 55", score: 15 }

relations:
  default: 0
  pairs:
    - { a: astoria, b: borea, value: -25 }
    - { a: astoria, b: caldera, value: 15 }
    - { a: borea, b: delta, value: 10 }
    - { a: caldera, b: delta, value: -10 }

actions:
  - id: mobilize
    title: "Мобилизация"
    description: "Наращивание группировки у границы."
    cost: { budget: 20 }
    requires: "self.army < 95"
    effects:
      - { self: army, delta: "10" }
      - { self: legitimacy, delta: "-3" }
      - { world: tension, delta: "5" }

  - id: demobilize
    title: "Отвод войск"
    description: "Демонстративное сокращение группировки."
    requires: "self.army > 15"
    effects:
      - { self: army, delta: "-10" }
      - { self: budget, delta: "8" }
      - { world: tension, delta: "-6" }

  - id: invest
    title: "Вложения в экономику"
    description: "Инфраструктура и налоговая база."
    cost: { budget: 25 }
    effects:
      - { self: budget, delta: "45 - self.budget * 0.1" }
      - { self: legitimacy, delta: "2" }

  - id: propaganda
    title: "Информационная кампания"
    description: "Работа с общественным мнением внутри страны."
    cost: { budget: 15 }
    effects:
      - { self: legitimacy, delta: "8" }
      - { world: attention, delta: "3" }

  - id: intel_work
    title: "Работа разведки"
    description: "Вербовка и техническая разведка."
    cost: { budget: 12 }
    effects:
      - { self: intel, delta: "15" }

  - id: cyber_op
    title: "Кибероперация"
    description: "Удар по финансовой инфраструктуре противника."
    target: faction
    cost: { budget: 15, intel: 10 }
    requires: "self.intel >= 10"
    visibility: secret
    reveal_chance: 0.35
    countered_by: [ cyber_defense ]
    risk:
      - { p: 0.5, title: "успех", effects: [ { target: budget, delta: "-18" },
                                             { relation: [self, target], delta: "-8" } ] }
      - { p: 0.3, title: "частичный успех", effects: [ { target: budget, delta: "-6" } ] }
      - { p: 0.2, title: "провал", effects: [ { self: intel, delta: "-12" } ] }

  - id: cyber_defense
    title: "Киберзащита"
    description: "Укрепление сетей и финансовых узлов."
    cost: { budget: 10 }
    counter_multiplier: 0.25
    effects:
      - { self: intel, delta: "5" }

  - id: blockade
    title: "Морская блокада"
    description: "Досмотр судов противника в проливе."
    target: faction
    cost: { budget: 20 }
    requires: "self.army >= 40"
    risk:
      - { p: 0.6, title: "блокада держится", effects: [ { target: budget, delta: "-20" },
                                                        { world: tension, delta: "12" },
                                                        { relation: [self, target], delta: "-15" } ] }
      - { p: 0.4, title: "прорыв", effects: [ { self: legitimacy, delta: "-8" },
                                              { world: tension, delta: "8" } ] }

  - id: show_force
    title: "Демонстрация силы"
    description: "Учения у чужих берегов."
    target: faction
    cost: { budget: 12 }
    effects:
      - { self: legitimacy, delta: "4" }
      - { relation: [self, target], delta: "-10" }
      - { world: tension, delta: "7" }

  - id: diplomacy
    title: "Дипломатическая инициатива"
    description: "Переговоры и взаимные гарантии."
    target: faction
    cost: { budget: 10 }
    effects:
      - { relation: [self, target], delta: "12" }
      - { world: tension, delta: "-4" }

  - id: sanctions
    title: "Экономические санкции"
    description: "Ограничение торговли с противником."
    target: faction
    cost: { budget: 15 }
    effects:
      - { target: budget, delta: "-15" }
      - { self: budget, delta: "-5" }
      - { relation: [self, target], delta: "-12" }
      - { world: attention, delta: "5" }

  - id: aid
    title: "Помощь соседу"
    description: "Кредиты и поставки на льготных условиях."
    target: faction
    cost: { budget: 25 }
    effects:
      - { target: budget, delta: "20" }
      - { relation: [self, target], delta: "18" }
      - { self: legitimacy, delta: "-2" }

  - id: covert_support
    title: "Тайная поддержка оппозиции"
    description: "Работа с недовольными в чужой стране."
    target: faction
    cost: { budget: 18, intel: 15 }
    requires: "self.intel >= 15"
    visibility: secret
    reveal_chance: 0.45
    risk:
      - { p: 0.45, title: "успех", effects: [ { target: legitimacy, delta: "-14" } ] }
      - { p: 0.35, title: "без результата", effects: [] }
      - { p: 0.20, title: "скандал", effects: [ { self: legitimacy, delta: "-10" },
                                                { world: attention, delta: "10" } ] }

  - id: deescalate
    title: "Шаг к разрядке"
    description: "Публичный отказ от эскалации."
    cost: { budget: 8 }
    effects:
      - { world: tension, delta: "-10" }
      - { self: legitimacy, delta: "-4" }

deals:
  - { id: transfer, title: "Передача средств", kind: resource, track: budget }
  - { id: pact, title: "Пакт о ненападении", kind: status, duration: 3 }
  - { id: alliance, title: "Оборонительный союз", kind: status, duration: 4 }

world_dynamics:
  - { world: tension, delta: "-3" }
  - { world: attention, delta: "-2" }
  - { all: budget, delta: "6 + self.legitimacy * 0.05" }
  - { all: legitimacy, delta: "1" }

events:
  - id: oil_shock
    when: "round == 3"
    title: "Скачок цен на энергоносители"
    text: "Рынки лихорадит, издержки выросли у всех."
    effects: [ { all: budget, delta: "-12" } ]

  - id: un_pressure
    when: "world.tension > 70"
    once: true
    title: "Давление международного сообщества"
    text: "Совет безопасности требует деэскалации."
    effects: [ { all: legitimacy, delta: "-6" }, { world: attention, delta: "15" } ]

  - id: refugees
    when: "world.tension > 60"
    once: true
    title: "Поток беженцев"
    text: "Приграничные районы не справляются."
    effects: [ { all: budget, delta: "-8" }, { all: legitimacy, delta: "-4" } ]

  - id: summit
    when: "round == 5"
    title: "Международная конференция"
    text: "Посредники собирают стороны за одним столом."
    effects: [ { world: tension, delta: "-8" }, { all: legitimacy, delta: "3" } ]

  - id: arms_market
    when: "round == 6"
    title: "Оружейная ярмарка"
    text: "Поставщики предлагают технику со скидкой."
    effects: [ { all: army, delta: "5" }, { all: budget, delta: "-6" } ]

  - id: mediation
    when: "world.tension < 20"
    once: true
    title: "Разрядка"
    text: "Регион впервые за годы выглядит спокойным."
    effects: [ { all: budget, delta: "15" }, { all: legitimacy, delta: "5" } ]

  - id: leak
    when: "world.attention > 60"
    once: true
    title: "Утечка документов"
    text: "Пресса публикует переписку разведок."
    effects: [ { all: intel, delta: "-10" }, { all: legitimacy, delta: "-3" } ]

end:
  when: "round > meta.rounds or world.tension >= 100"
  scoring: "self.legitimacy + self.army * 0.5 + self.budget * 0.2"
```

- [ ] **Step 2: Проверить сценарий валидатором**

Run: `.venv/bin/sgame validate sgame/scenarios/meridian.yaml`
Expected: `meridian.yaml: сценарий в порядке`

- [ ] **Step 3: Написать тест `tests/test_meridian.py`**

```python
import json
import os
from pathlib import Path

from sgame.core.orders import Order
from sgame.core.scoring import score
from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.validate import validate_scenario
from sgame.session import journal as J
from sgame.session.paths import builtin_scenarios
from sgame.session.replay import replay

GOLDEN = Path(__file__).parent / "golden" / "meridian.json"

SCRIPT = [
    {"astoria": [("mobilize", None), ("intel_work", None)],
     "borea": [("show_force", "astoria"), ("propaganda", None)],
     "caldera": [("invest", None), ("diplomacy", "astoria")],
     "delta": [("intel_work", None), ("propaganda", None)]},
    {"astoria": [("cyber_defense", None), ("diplomacy", "caldera")],
     "borea": [("cyber_op", "astoria"), ("mobilize", None)],
     "caldera": [("invest", None), ("aid", "delta")],
     "delta": [("covert_support", "borea")]},
    {"astoria": [("blockade", "borea")],
     "borea": [("sanctions", "astoria"), ("intel_work", None)],
     "caldera": [("deescalate", None), ("diplomacy", "borea")],
     "delta": [("propaganda", None), ("invest", None)]},
    {"astoria": [("deescalate", None), ("invest", None)],
     "borea": [("demobilize", None)],
     "caldera": [("invest", None)],
     "delta": [("cyber_op", "caldera")]},
    {"astoria": [("propaganda", None)],
     "borea": [("diplomacy", "astoria")],
     "caldera": [("aid", "astoria")],
     "delta": [("intel_work", None), ("propaganda", None)]},
    {"astoria": [("invest", None)],
     "borea": [("invest", None)],
     "caldera": [("invest", None)],
     "delta": [("invest", None)]},
    {"astoria": [("mobilize", None)],
     "borea": [("show_force", "caldera")],
     "caldera": [("deescalate", None)],
     "delta": [("covert_support", "astoria")]},
    {"astoria": [("diplomacy", "borea")],
     "borea": [("diplomacy", "astoria")],
     "caldera": [("invest", None)],
     "delta": [("propaganda", None)]},
]


def build_journal():
    text = builtin_scenarios()["meridian"]
    teams = [
        J.TeamSlot(faction=f.id, team=f"Команда {i}", code=f"100{i}")
        for i, f in enumerate(parse_scenario(text).factions, start=1)
    ]
    journal = J.new_journal("meridian", text, teams, seed=20260901)
    for number, round_orders in enumerate(SCRIPT, start=1):
        journal.rounds.append(
            J.RoundRecord(
                n=number,
                orders={
                    faction: [Order(action=a, target=t) for a, t in items]
                    for faction, items in round_orders.items()
                },
            )
        )
    return journal


def snapshot():
    journal = build_journal()
    spec = parse_scenario(journal.scenario_text)
    state, history = replay(journal)
    return {
        "tracks": state.tracks,
        "world": state.world,
        "relations": {f"{a}|{b}": value for (a, b), value in sorted(state.relations.items())},
        "finished": state.finished,
        "scores": {f.id: score(spec, state, f.id)[0] for f in spec.factions},
        "rounds": [
            [f"{e.kind}:{e.actor}:{e.title}:{e.roll}:"
             + ",".join(d.describe() for d in e.deltas) for e in events]
            for events in history
        ],
    }


def test_scenario_passes_validator():
    text = builtin_scenarios()["meridian"]
    spec = parse_scenario(text)
    assert validate_scenario(spec, scenario_lines(text)) == []


def test_scenario_is_big_enough_for_a_class():
    spec = parse_scenario(builtin_scenarios()["meridian"])
    assert len(spec.factions) == 4
    assert len(spec.actions) >= 12
    assert len(spec.events) >= 6
    assert all(f.briefing.strip() and f.goals for f in spec.factions)


def test_full_game_matches_golden_run():
    actual = json.dumps(snapshot(), ensure_ascii=False, indent=2, sort_keys=True)
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(actual, encoding="utf-8")
    assert actual == GOLDEN.read_text(encoding="utf-8")


def test_game_finishes_and_nobody_is_wiped_out():
    journal = build_journal()
    state, _ = replay(journal)
    assert state.finished is True
    for faction in state.tracks.values():
        assert faction["legitimacy"] > 0


def test_round_resolves_faster_than_a_second():
    """Нефункциональное требование спеки: на паре не должно быть паузы."""
    import time

    from sgame.core.resolve import resolve
    from sgame.core.state import initial_state

    journal = build_journal()
    spec = parse_scenario(journal.scenario_text)
    orders = journal.rounds[0].orders
    started = time.perf_counter()
    resolve(spec, initial_state(spec), orders, [], {}, journal.seed)
    assert time.perf_counter() - started < 1.0


def test_no_single_strategy_dominates():
    """Разброс очков между сторонами не должен превращать игру в предрешённую."""
    journal = build_journal()
    spec = parse_scenario(journal.scenario_text)
    state, _ = replay(journal)
    totals = sorted(score(spec, state, f.id)[0] for f in spec.factions)
    assert totals[-1] - totals[0] < totals[-1] * 0.6
```

- [ ] **Step 4: Записать золотой файл и убедиться, что он воспроизводится**

```bash
UPDATE_GOLDEN=1 .venv/bin/pytest tests/test_meridian.py -v
.venv/bin/pytest tests/test_meridian.py -v
```
Expected: второй прогон — PASS, 6 тестов, без перезаписи файла

Если `test_no_single_strategy_dominates` падает — это сигнал не про код, а про баланс: правьте числа в сценарии, затем перезапишите золотой файл.

- [ ] **Step 5: Коммит**

```bash
git add sgame/scenarios/meridian.yaml tests/test_meridian.py tests/golden/meridian.json
git commit -m "feat: эталонная игра «Кризис в Меридианском заливе» и золотой прогон"
```

---

## Task 16: Сборка `.app`, инструкция и итоговая проверка

**Files:**
- Create: `packaging/sgame.spec`, `packaging/ИНСТРУКЦИЯ.md`, `packaging/собрать.sh`, `README.md`
- Test: ручная проверка по чек-листу ниже

**Interfaces:**
- Consumes: `sgame.cli:main`
- Produces: `dist/Стратегическая игра.app`

- [ ] **Step 1: Написать `packaging/sgame.spec`**

```python
# PyInstaller spec: onedir + .app. Ресурсы кладутся внутрь пакета sgame,
# потому что код читает их через importlib.resources.
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("sgame", includes=["web/templates/*.html", "web/static/*", "scenarios/*.yaml"])

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=["uvicorn.logging", "uvicorn.protocols.http.h11_impl",
                   "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, exclude_binaries=True, name="СтратегическаяИгра", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="СтратегическаяИгра")
app = BUNDLE(
    coll,
    name="Стратегическая игра.app",
    bundle_identifier="ru.local.strategicgame",
    info_plist={"CFBundleName": "Стратегическая игра", "LSBackgroundOnly": False},
)
```

- [ ] **Step 2: Написать `packaging/launcher.py`**

```python
"""Точка входа собранного приложения: поднять сервер и открыть браузер."""

from sgame.web.app import serve

if __name__ == "__main__":
    serve(port=0, open_browser=True)
```

- [ ] **Step 3: Написать `packaging/собрать.sh`**

```bash
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
cp packaging/launcher.py launcher.py
.venv/bin/pyinstaller --noconfirm --clean packaging/sgame.spec
rm launcher.py
cd dist && zip -qr "Стратегическая игра.zip" "Стратегическая игра.app"
echo "Готово: dist/Стратегическая игра.zip"
```

Сделать исполняемым: `chmod +x packaging/собрать.sh`

- [ ] **Step 4: Написать `packaging/ИНСТРУКЦИЯ.md`**

```markdown
# Как запустить «Стратегическую игру»

1. Распакуйте архив — появится «Стратегическая игра.app».
2. **Первый запуск:** нажмите на приложение правой кнопкой мыши, выберите
   «Открыть», затем в появившемся окне ещё раз «Открыть».
   Обычный двойной клик в первый раз не сработает: macOS блокирует программы
   без подписи разработчика. После первого раза приложение открывается как
   обычно.
3. Откроется браузер со стартовой страницей. Выберите сценарий и нажмите
   «Начать».

## Как проходит занятие

- Ведущий держит открытым **пульт** (главная страница) и, если есть проектор,
  вкладку **«Экран для проектора»**.
- Пульт показывает, какой команде передать компьютер, и код каждой команды.
- Команда открывает свою страницу, вводит код, выбирает приказы и нажимает
  «Сдать приказы». Экран сразу закрывается.
- Когда сдали все, ведущий нажимает «Закрыть раунд». Если время поджимает —
  «Закрыть принудительно»: несдавшие команды пасуют.
- Ошиблись — «Откатить раунд» возвращает всё как было.

## Где лежат данные

`~/Library/Application Support/StrategicGame/`
— `sessions/` сохранённые партии, `scenarios/` ваши сценарии.
Файл партии самодостаточен: его можно переслать коллеге.

## Свои сценарии

Положите файл `.yaml` в `scenarios/` — он появится в списке при создании
партии. Проверить файл на ошибки: `sgame validate мой-сценарий.yaml`.
```

- [ ] **Step 5: Написать `README.md`**

```markdown
# Стратегическая игра

Движок текстовых стратегических игр для учебных занятий: команды принимают
решения за стороны конфликта, детерминированная модель считает последствия,
после игры проводится разбор.

## Разработка

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/sgame run
```

## Команды

- `sgame run` — запустить приложение и открыть браузер
- `sgame validate <файл>` — проверить сценарий

## Сборка приложения для macOS

```bash
./packaging/собрать.sh
```

## Документы

- Дизайн: `docs/superpowers/specs/2026-08-29-strategic-game-engine-design.md`
- План этапа 1: `docs/superpowers/plans/2026-08-29-strategic-game-engine-stage-1.md`
```

- [ ] **Step 6: Прогнать весь набор тестов**

Run: `.venv/bin/pytest -v`
Expected: PASS, все тесты (около 70)

- [ ] **Step 7: Собрать приложение**

Run: `./packaging/собрать.sh`
Expected: появился `dist/Стратегическая игра.zip`

- [ ] **Step 8: Проверить критерии готовности этапа 1 вручную**

Пройти по чек-листу из спеки, отмечая каждый пункт:

1. Партия на 4 команды и 8 раундов проходится целиком через интерфейс без ошибок.
2. Тесты секретности проходят (`tests/test_web_secrecy.py`).
3. Откат раунда возвращает прежнее состояние (`test_undo_returns_to_previous_round`).
4. `sgame validate` находит шесть классов ошибок (`tests/test_validate.py`).
5. Золотой прогон зафиксирован и проходит (`tests/test_meridian.py`).
6. Собранное `.app` запускается на другом Mac по инструкции — проверяется переносом архива.
7. Эталонный сценарий заполнен (`test_scenario_is_big_enough_for_a_class`).

- [ ] **Step 9: Коммит**

```bash
git add packaging README.md
git commit -m "feat: сборка приложения для macOS и инструкция для получателя"
```
