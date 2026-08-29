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
