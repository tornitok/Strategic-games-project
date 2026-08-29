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
