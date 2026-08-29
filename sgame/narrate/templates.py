"""Текстовое представление сводки.

Экраны показывают ленту новостей из `news.py`; здесь та же лента
разворачивается в плоский текст — он уходит в журнал партии, в отчёт
ведущему и в разбор после игры.
"""

from collections.abc import Sequence

from ..core.events import Event
from ..core.spec import ScenarioSpec


def _title_of(spec: ScenarioSpec, faction_id: str | None) -> str:
    faction = spec.faction(faction_id) if faction_id else None
    return faction.title if faction else "—"


def deltas_text(spec: ScenarioSpec, event: Event) -> str:
    """Изменения одной строкой, сгруппированные по сторонам.

    Без имён и группировки сводка мировой динамики превращается в «Бюджет
    +8.75, Бюджет +8.25, Бюджет +9.25, … , Легитимность +1, Легитимность +1» —
    список одинаковых чисел неизвестно про кого.
    """
    own: list[str] = []
    others: dict[str, list[str]] = {}
    for delta in event.deltas:
        if delta.scope == "faction" and delta.who != event.actor:
            others.setdefault(delta.who, []).append(delta.describe())
        else:
            own.append(delta.describe())

    if not others:
        return ", ".join(own)

    groups = [f"{_title_of(spec, who)}: {', '.join(items)}" for who, items in others.items()]
    return "; ".join(([", ".join(own)] if own else []) + groups)


def _render(items) -> str:
    if not items:
        return "За этот раунд ничего заметного не произошло."
    lines = []
    for item in items:
        lines.append(f"• {item.headline}" + (f" — {item.detail}" if item.detail else ""))
    return "\n".join(lines)


def narrate_public(spec: ScenarioSpec, events: Sequence[Event]) -> str:
    from .news import news_items

    return _render(news_items(spec, events, viewer=None, role="public"))


def narrate_team(spec: ScenarioSpec, events: Sequence[Event], faction: str) -> str:
    from .news import news_items

    return _render(news_items(spec, events, viewer=faction, role="team"))


def narrate_host(spec: ScenarioSpec, events: Sequence[Event]) -> str:
    from .news import news_items

    return _render(news_items(spec, events, viewer=None, role="host"))
