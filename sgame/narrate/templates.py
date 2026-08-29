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
