"""Состояние партии и рабочая копия для расчёта раунда.

`GameState` неизменяемо и всегда является результатом свёртки журнала.
Фазы раунда работают с `StateBuilder` — рабочей копией, которая знает
границы треков и сама зажимает значения.
"""

from copy import deepcopy
from math import isclose
from dataclasses import dataclass, field
from typing import Any

from .events import Delta
from .orders import DealOffer
from .spec import ScenarioSpec


def pair_key(a: str, b: str) -> tuple[str, str]:
    """Ключ отношения не зависит от порядка сторон."""
    return (a, b) if a <= b else (b, a)


def _clamped(applied: float, requested: float) -> bool:
    """Дельта упёрлась в границу?

    Сравнивать точно нельзя: 155.5 + 8.85 даёт разность 8.849999999999994, и
    честно применённая дельта помечалась бы как обрезанная.
    """
    return not isclose(applied, requested, rel_tol=0, abs_tol=1e-9)


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
            amount=after - before, clamped=_clamped(after - before, amount),
        )

    def add_world(self, name: str, amount: float) -> Delta:
        track = self.spec.world[name]
        before = self._world[name]
        after = min(track.max, max(track.min, before + amount))
        self._world[name] = after
        return Delta(
            scope="world", who="", track=track.title,
            amount=after - before, clamped=_clamped(after - before, amount),
        )

    def add_relation(self, a: str, b: str, amount: float) -> Delta:
        key = pair_key(a, b)
        before = self._relations.get(key, self.spec.relations.default)
        after = min(100.0, max(-100.0, before + amount))
        self._relations[key] = after
        return Delta(
            scope="relation", who=f"{key[0]}↔{key[1]}", track="Отношения",
            amount=after - before, clamped=_clamped(after - before, amount),
        )

    def track_of(self, faction: str, name: str) -> float:
        """Показатель конкретной стороны — для условий событий.

        Без него событие не может спросить «а много ли разведки у Кальдеры»:
        обычный `self` в условии события не определён, актора там нет.
        """
        try:
            return self._tracks[faction][name]
        except KeyError as exc:
            raise KeyError(f"неизвестная сторона или показатель: {faction}.{name}") from exc

    def context(self, actor: str | None = None, target: str | None = None) -> dict[str, Any]:
        """Контекст для вычисления выражений сценария."""
        return {
            "self": dict(self._tracks[actor]) if actor else {},
            "target": dict(self._tracks[target]) if target else {},
            "world": dict(self._world),
            "round": self.round,
            "meta": {"rounds": self.spec.meta.rounds},
            "rel": self.relation,
            "track": self.track_of,
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
