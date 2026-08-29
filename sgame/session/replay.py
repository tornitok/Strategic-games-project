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


def states(journal: Journal) -> list[GameState]:
    """Срезы состояния: начальный и после каждого раунда.

    Нужны, чтобы показать «было → стало»: разница берётся между соседними.
    """
    spec = spec_of(journal)
    state = initial_state(spec)
    result = [state]
    for record in journal.rounds:
        state = resolve(
            spec, state, record.orders, record.offers, record.responses, journal.seed
        ).state
        result.append(state)
    return result


def current_state(journal: Journal) -> GameState:
    return replay(journal)[0]


def undo_last(journal: Journal) -> None:
    if journal.rounds:
        journal.rounds.pop()


def scenario_changed(journal: Journal, current_text: str) -> bool:
    return sha256(current_text.encode("utf-8")).hexdigest() != journal.scenario_sha256
