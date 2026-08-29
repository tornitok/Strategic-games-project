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


def deltas_text(spec: ScenarioSpec, event: Event, lang: str = "ru") -> str:
    """Изменения одной строкой, сгруппированные по сторонам.

    Без имён и группировки сводка мировой динамики превращается в «Бюджет
    +8.75, Бюджет +8.25, Бюджет +9.25, … , Легитимность +1, Легитимность +1» —
    список одинаковых чисел неизвестно про кого.
    """
    own: list[str] = []
    others: dict[str, list[str]] = {}
    for delta in event.deltas:
        if delta.scope == "faction" and delta.who != event.actor:
            others.setdefault(delta.who, []).append(delta.describe(lang))
        else:
            own.append(delta.describe(lang))

    if not others:
        return ", ".join(own)

    groups = [f"{_title_of(spec, who)}: {', '.join(items)}" for who, items in others.items()]
    return "; ".join(([", ".join(own)] if own else []) + groups)


def _render(items, lang: str = "ru") -> str:
    from ..i18n import t

    if not items:
        return t("news.nothing", lang)
    lines = []
    for item in items:
        lines.append(f"• {item.headline}" + (f" — {item.detail}" if item.detail else ""))
    return "\n".join(lines)


def narrate_public(spec: ScenarioSpec, events: Sequence[Event], lang: str = "ru") -> str:
    from .news import news_items

    return _render(news_items(spec, events, viewer=None, role="public", lang=lang), lang)


def narrate_team(spec: ScenarioSpec, events: Sequence[Event], faction: str, lang: str = "ru") -> str:
    from .news import news_items

    return _render(news_items(spec, events, viewer=faction, role="team", lang=lang), lang)


def narrate_host(spec: ScenarioSpec, events: Sequence[Event], lang: str = "ru") -> str:
    from .news import news_items

    return _render(news_items(spec, events, viewer=None, role="host", lang=lang), lang)
