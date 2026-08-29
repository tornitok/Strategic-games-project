"""Боты для прогона сценариев.

Нужны, чтобы проверять баланс без четырёх живых команд: сценарий гоняется
десятками партий, и сразу видно, окупается ли жёсткая линия и не выигрывает
ли кто-то сам собой. Боты играют три классические линии поведения —
оппозицию, балансирование и примыкание — плюс осторожную.
"""

from dataclasses import dataclass, field

from .core.expr import evaluate
from .core.orders import Order
from .core.phases import phase_validate
from .core.resolve import resolve
from .core.rng import stream
from .core.scoring import score
from .core.spec import ActionSpec, ScenarioSpec
from .core.state import GameState, StateBuilder, initial_state

ROLES = ("opposition", "balancing", "following", "cautious")


def power_of(spec: ScenarioSpec, state: GameState, faction: str) -> float:
    """Насколько сторона сильна — по формуле сценария или по сумме публичных треков."""
    if spec.power:
        builder = StateBuilder(spec, state)
        return float(evaluate(spec.power, builder.context(actor=faction)))
    return sum(
        state.tracks[faction][name]
        for name, track in spec.tracks.items()
        if track.visibility == "public"
    )


def _ranked_rivals(spec: ScenarioSpec, state: GameState, faction: str) -> list[str]:
    rivals = [f.id for f in spec.factions if f.id != faction]
    return sorted(rivals, key=lambda other: power_of(spec, state, other), reverse=True)


def _wishlist(role: str, leader: str | None, weakest: str | None) -> list[tuple[str, str | None]]:
    """Чего хочет эта линия поведения, в порядке предпочтения."""
    if role == "opposition":
        return [("hostile", leader), ("neutral", None), ("friendly", weakest)]
    if role == "balancing":
        return [("hostile", leader), ("friendly", weakest), ("neutral", None)]
    if role == "following":
        return [("friendly", leader), ("neutral", None)]
    return [("neutral", None), ("friendly", weakest)]


def _is_available(
    spec: ScenarioSpec, state: GameState, faction: str, draft: list[Order], candidate: Order
) -> bool:
    builder = StateBuilder(spec, state)
    accepted, _ = phase_validate(spec, builder, {faction: [*draft, candidate]})
    return any(item.index == len(draft) for item in accepted)


def _candidates(spec: ScenarioSpec, stance: str) -> list[ActionSpec]:
    return [action for action in spec.actions if action.stance == stance]


def choose_orders(
    spec: ScenarioSpec,
    state: GameState,
    faction: str,
    role: str,
    seed: int,
    round_no: int,
) -> list[Order]:
    """Приказы бота на раунд. Выбор случаен, но воспроизводим по ключу партии."""
    rivals = _ranked_rivals(spec, state, faction)
    leader = rivals[0] if rivals else None
    weakest = rivals[-1] if rivals else None
    rng = stream(seed, round_no, f"bot:{faction}:{role}")

    draft: list[Order] = []
    for stance, preferred_target in _wishlist(role, leader, weakest):
        for action in _shuffled(_candidates(spec, stance), rng):
            if len(draft) >= spec.meta.action_points:
                return draft
            target = preferred_target if action.target == "faction" else None
            if action.target == "faction" and not target:
                continue
            candidate = Order(action=action.id, target=target, intent=f"линия: {role}")
            if _is_available(spec, state, faction, draft, candidate):
                draft.append(candidate)
    return draft


def _shuffled(items: list, rng) -> list:
    """Перемешивание своим потоком: глобальный random в проекте не используется."""
    pool = list(items)
    result = []
    while pool:
        result.append(pool.pop(int(rng.random() * len(pool))))
    return result


@dataclass
class Simulation:
    state: GameState
    scores: dict[str, float]
    rounds: list[dict] = field(default_factory=list)


def simulate(spec: ScenarioSpec, roles: dict[str, str], seed: int) -> Simulation:
    """Прогнать сценарий ботами до конца и вернуть, что получилось."""
    state = initial_state(spec)
    rounds: list[dict] = []

    for round_no in range(1, spec.meta.rounds + 1):
        orders = {
            faction: choose_orders(spec, state, faction, role, seed, round_no)
            for faction, role in roles.items()
        }
        result = resolve(spec, state, orders, [], {}, seed)
        state = result.state
        rounds.append(
            {
                "n": round_no,
                "world": dict(state.world),
                "events": [e.title for e in result.events if e.kind == "scenario_event"],
                "rumours": [e.title for e in result.events if e.kind == "rumour"],
            }
        )
        if state.finished:
            break

    return Simulation(
        state=state,
        scores={f.id: score(spec, state, f.id)[0] for f in spec.factions},
        rounds=rounds,
    )
