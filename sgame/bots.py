"""Боты для прогона сценариев.

Нужны, чтобы проверять баланс без четырёх живых команд: сценарий гоняется
десятками партий, и сразу видно, окупается ли жёсткая линия и не выигрывает
ли кто-то сам собой. Боты играют три классические линии поведения —
оппозицию, балансирование и примыкание — плюс осторожную.
"""

from dataclasses import dataclass, field

from .core.expr import evaluate
from .core.orders import DealOffer, Order
from .core.phases import apply_effect, phase_validate
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


def _gain(spec: ScenarioSpec, state: GameState, faction: str, action: ActionSpec, target: str | None) -> float:
    """Насколько действие улучшает положение стороны относительно цели.

    Мерить только собственную выгоду нельзя: удар всегда стоит денег и в
    абсолюте выглядит убытком, хотя цели он обходится дороже. Мерить только
    урон цели — тоже: тогда бот дарит лидеру деньги, лишь бы занять очко.
    Разница между тем и другим и есть то, ради чего в такой игре вообще
    что-то делают. Риск оценивается по самому вероятному исходу: нужен
    порядок величины, а не точное ожидание.
    """
    builder = StateBuilder(spec, state)
    before = _power(spec, builder, faction)
    before_target = _power(spec, builder, target) if target else 0.0
    for name, amount in action.cost.items():
        builder.add_track(faction, name, -amount)
    effects = action.effects
    if action.risk:
        effects = max(action.risk, key=lambda outcome: outcome.p).effects
    try:
        for effect in effects:
            apply_effect(spec, builder, effect, faction, target)
    except Exception:
        return 0.0

    mine = _power(spec, builder, faction) - before
    theirs = (_power(spec, builder, target) - before_target) if target else 0.0
    return mine - theirs


def _power(spec: ScenarioSpec, builder: StateBuilder, faction: str) -> float:
    if spec.power:
        return float(evaluate(spec.power, builder.context(actor=faction)))
    return sum(
        builder.track(faction, name)
        for name, track in spec.tracks.items()
        if track.visibility == "public"
    )


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
        options = []
        for action in _shuffled(_candidates(spec, stance), rng):
            target = preferred_target if action.target == "faction" else None
            if action.target == "faction" and not target:
                continue
            options.append((action, target))

        # Порядок задаёт линия поведения, а выбор внутри линии — собственная выгода.
        scored = [
            (pair, _gain(spec, state, faction, pair[0], pair[1])) for pair in options
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        # Действия себе в убыток не берём: занять очко ценой собственного
        # ослабления хуже, чем не занимать его вовсе.
        options = [pair for pair, gain in scored if gain >= 0]

        for action, target in options:
            if len(draft) >= spec.meta.action_points:
                return draft
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


def choose_deals(
    spec: ScenarioSpec,
    state: GameState,
    faction: str,
    role: str,
    seed: int,
    round_no: int,
) -> tuple[list[DealOffer], dict[str, bool]]:
    """Дипломатия бота: кому предлагать союз и чьи предложения принимать.

    Без этого примыкание к сильному неосуществимо: весь его смысл в союзе,
    который даёт поток, а союз возникает только через сделку.
    """
    statuses = [deal for deal in spec.deals if deal.kind == "status"]
    if not statuses:
        return [], {}

    rivals = _ranked_rivals(spec, state, faction)
    if not rivals:
        return [], {}
    leader, weakest = rivals[0], rivals[-1]

    partner = {"following": leader, "balancing": weakest, "cautious": weakest}.get(role)
    offers: list[DealOffer] = []
    if partner and not state.pending_offers:
        rng = stream(seed, round_no, f"deal:{faction}:{role}")
        deal = statuses[int(rng.random() * len(statuses))]
        offers.append(
            DealOffer(id=f"{faction}:{round_no}", deal=deal.id, sender=faction, receiver=partner)
        )

    responses: dict[str, bool] = {}
    for offer in state.pending_offers:
        if offer.receiver != faction:
            continue
        if role == "opposition":
            responses[offer.id] = False
        elif role == "following":
            responses[offer.id] = offer.sender == leader
        elif role == "balancing":
            responses[offer.id] = offer.sender != leader
        else:
            responses[offer.id] = True
    return offers, responses


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
        offers: list[DealOffer] = []
        responses: dict[str, bool] = {}
        for faction, role in roles.items():
            faction_offers, faction_responses = choose_deals(
                spec, state, faction, role, seed, round_no
            )
            offers.extend(faction_offers)
            responses.update(faction_responses)
        # Отдельно от того, что бот выбрал: было ли у стороны вообще хоть одно
        # исполнимое действие. Пустой ход бота и мёртвый ход в сценарии —
        # разные диагнозы.
        stuck = []
        for faction in roles:
            others = [f.id for f in spec.factions if f.id != faction]
            has_any = False
            for action in spec.actions:
                probe = Order(
                    action=action.id,
                    target=others[0] if action.target == "faction" and others else None,
                )
                accepted, _ = phase_validate(spec, StateBuilder(spec, state), {faction: [probe]})
                if accepted:
                    has_any = True
                    break
            if not has_any:
                stuck.append(faction)

        result = resolve(spec, state, orders, offers, responses, seed)
        state = result.state
        rounds.append(
            {
                "n": round_no,
                "world": dict(state.world),
                "events": [e.title for e in result.events if e.kind == "scenario_event"],
                "rumours": [e.title for e in result.events if e.kind == "rumour"],
                "statuses": [f"{s.deal}: {s.a}+{s.b}" for s in state.statuses],
                "orders": {f: [o.action for o in os] for f, os in orders.items()},
                "tracks": {f: dict(v) for f, v in state.tracks.items()},
                "stuck": stuck,
            }
        )
        if state.finished:
            break

    return Simulation(
        state=state,
        scores={f.id: score(spec, state, f.id)[0] for f in spec.factions},
        rounds=rounds,
    )
