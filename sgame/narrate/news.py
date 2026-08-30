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

def covert_hint(lang: str = "ru") -> str:
    from ..i18n import t

    return t("news.covert_hint", lang)


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
    elif event.kind == "complication":
        action = next(
            (
                complication
                for candidate in spec.actions
                for complication in candidate.complications
                if complication.title == event.title
            ),
            None,
        )
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


def _detail(spec: ScenarioSpec, event: Event, role: Role, lang: str = "ru") -> str:
    from .templates import deltas_text

    if event.kind == "rumour":
        # Игроки должны решать, верить ли слуху. Правду и автора видит только
        # ведущий — иначе на разборе нечего будет обсуждать.
        if role != "host":
            return ""
        from ..i18n import t

        parts = [t("news.rumour_true" if event.truth else "news.rumour_false", lang)]
        if event.source:
            parts.append(t("news.rumour_planted", lang, side=_title_of(spec, event.source)))
        return ", ".join(parts)

    parts = []
    if event.roll:
        parts.append(event.roll)
    body = deltas_text(spec, event, lang)
    if body:
        parts.append(body)
    # Текстовое пояснение события — расклад голосов, описание последствий —
    # тоже часть новости, а не только числа.
    if event.detail:
        parts.append(event.detail)
    return " · ".join(parts)


def news_items(
    spec: ScenarioSpec,
    events: Sequence[Event],
    viewer: str | None,
    role: Role,
    lang: str = "ru",
) -> list[NewsItem]:
    """Видимые зрителю новости раунда.

    Если в раунде были тайные действия, которых зритель не видит, лента
    заканчивается одной неопределённой строкой: ни автора, ни цели, ни числа.
    Автор единственной тайной операции намёка не получает — иначе намёк
    сообщал бы ему, что действовал кто-то ещё.
    """
    visible = events_for(events, viewer, role)
    items = [
        NewsItem(
            headline=_headline(spec, event),
            detail=_detail(spec, event, role, lang),
            kind=event.kind,
        )
        for event in visible
        if event.kind in {"action", "scenario_event", "deal_done", "status_expired",
                          "world", "end", "rumour", "complication", "cabinet"}
    ]

    # Слух уже говорит о тайной активности — общий намёк рядом с ним лишний.
    spoke_of_secrets = any(item.kind == "rumour" for item in items)
    hidden_secret = any(
        event.kind == "action" and not visible_to(event, viewer, role) for event in events
    )
    if hidden_secret and not spoke_of_secrets:
        items.append(NewsItem(headline=covert_hint(lang), kind="hint"))
    return items
