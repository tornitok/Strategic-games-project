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
        "track": lambda faction_id, name: state.tracks[faction_id][name],
        "avg": lambda name: (
            sum(tracks[name] for tracks in state.tracks.values() if name in tracks)
            / max(1, sum(1 for tracks in state.tracks.values() if name in tracks))
        ),
        "status": lambda deal, a, b: float(
            any(s.deal == deal and {s.a, s.b} == {a, b} and s.until > state.round
                for s in state.statuses)
        ),
        "in_status": lambda deal: float(
            any(s.deal == deal and faction in (s.a, s.b) and s.until > state.round
                for s in state.statuses)
        ),
    }


def score(
    spec: ScenarioSpec, state: GameState, faction: str, lang: str = "ru"
) -> tuple[float, list[tuple[str, float]]]:
    """Итоговый счёт стороны и его расшифровка по слагаемым."""
    from ..i18n import t

    context = _context(spec, state, faction)
    base = float(evaluate(spec.end.scoring, context))
    breakdown: list[tuple[str, float]] = [(t("debrief.base_score", lang), round(base, 2))]

    spec_faction = spec.faction(faction)
    total = base
    if spec_faction:
        for goal in spec_faction.goals:
            if evaluate(goal.when, context):
                total += goal.score
                breakdown.append((goal.title, goal.score))
    return round(total, 2), breakdown
