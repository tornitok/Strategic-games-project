"""Склейка фаз в один расчёт раунда."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .events import Event
from .orders import DealOffer, Order
from .phases import (
    phase_counters, phase_deals, phase_effects, phase_end,
    phase_events, phase_pay, phase_rumours, phase_validate, phase_world,
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
    events.extend(phase_events(spec, builder, seed))
    events.extend(phase_rumours(spec, builder, accepted, seed))
    finished, end_events = phase_end(spec, builder)
    events.extend(end_events)

    return RoundResult(
        state=builder.build(round_no=state.round + 1, finished=finished),
        events=tuple(events),
    )
