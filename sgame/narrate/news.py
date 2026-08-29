"""Лента новостей раунда.

Сводка читается как выпуск новостей, а не как список изменений в таблице:
у каждого события есть заголовок, а числа уходят в подстрочник. Заголовки
пишет автор сценария — движок только подставляет стороны.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from ..core.events import Event
from ..core.spec import ScenarioSpec
from .view import Role, events_for, visible_to

COVERT_HINT = "По дипломатическим каналам началось движение тайных посольств"


@dataclass(frozen=True)
class NewsItem:
    headline: str
    detail: str = ""
    kind: str = "action"


def _title_of(spec: ScenarioSpec, faction_id: str | None) -> str:
    faction = spec.faction(faction_id) if faction_id else None
    return faction.title if faction else "—"


def _headline(spec: ScenarioSpec, event: Event) -> str:
    template = ""
    if event.kind == "action":
        action = next((a for a in spec.actions if a.title == event.title), None)
        template = action.news if action else ""
    elif event.kind == "scenario_event":
        scenario_event = next((e for e in spec.events if e.title == event.title), None)
        template = scenario_event.news if scenario_event else ""

    if template:
        return template.format(
            actor=_title_of(spec, event.actor), target=_title_of(spec, event.target)
        )

    if event.actor:
        head = f"{_title_of(spec, event.actor)}: {event.title}"
        if event.target:
            head += f" → {_title_of(spec, event.target)}"
        return head
    return event.title


def _detail(spec: ScenarioSpec, event: Event) -> str:
    from .templates import deltas_text

    parts = []
    if event.roll:
        parts.append(event.roll)
    body = deltas_text(spec, event)
    if body:
        parts.append(body)
    return " · ".join(parts)


def news_items(
    spec: ScenarioSpec,
    events: Sequence[Event],
    viewer: str | None,
    role: Role,
) -> list[NewsItem]:
    """Видимые зрителю новости раунда.

    Если в раунде были тайные действия, которых зритель не видит, лента
    заканчивается одной неопределённой строкой: ни автора, ни цели, ни числа.
    Автор единственной тайной операции намёка не получает — иначе намёк
    сообщал бы ему, что действовал кто-то ещё.
    """
    visible = events_for(events, viewer, role)
    items = [
        NewsItem(headline=_headline(spec, event), detail=_detail(spec, event), kind=event.kind)
        for event in visible
        if event.kind in {"action", "scenario_event", "deal_done", "status_expired", "world", "end"}
    ]

    hidden_secret = any(
        event.kind == "action" and not visible_to(event, viewer, role) for event in events
    )
    if hidden_secret:
        items.append(NewsItem(headline=COVERT_HINT, kind="hint"))
    return items
