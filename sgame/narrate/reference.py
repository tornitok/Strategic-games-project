"""Справочник действий и показателей, собранный из самого сценария.

Писать такие описания руками нельзя: они разъедутся с моделью при первой же
правке чисел. Здесь всё выводится из спецификации, поэтому справочник всегда
говорит правду о том, что произойдёт.
"""

from ..core.expr import ExprError, evaluate
from ..core.spec import ActionSpec, EffectSpec, ScenarioSpec
from ..core.state import GameState, StateBuilder

_WORDS = ((0.8, "почти всегда"), (0.5, "чаще всего"), (0.25, "иногда"), (0.0, "редко"))


def chance_word(probability: float) -> str:
    """Словесная оценка вместо процента.

    Точные проценты превращают игру в арифметику ожидаемых значений; словами
    неопределённость остаётся неопределённостью, как в настоящей штабной работе.
    """
    for threshold, word in _WORDS:
        if probability >= threshold:
            return word
    return "редко"


def _signed(value: float) -> str:
    return f"+{value:g}" if value >= 0 else f"−{abs(value):g}"


def _amount(
    spec: ScenarioSpec, effect: EffectSpec, state: GameState | None, actor: str | None, target: str | None
) -> str | None:
    try:
        return _signed(float(effect.delta))
    except ValueError:
        pass
    if state is None:
        return None
    try:
        builder = StateBuilder(spec, state)
        return _signed(evaluate(effect.delta, builder.context(actor=actor, target=target)))
    except (ExprError, KeyError):
        return None


def describe_effect(
    spec: ScenarioSpec,
    effect: EffectSpec,
    state: GameState | None = None,
    actor: str | None = None,
    target: str | None = None,
) -> str:
    amount = _amount(spec, effect, state, actor, target)
    tail = amount if amount else "зависит от обстановки"

    if effect.self_track is not None:
        return f"{spec.tracks[effect.self_track].title} {tail}"
    if effect.target is not None:
        return f"{spec.tracks[effect.target].title} цели {tail}"
    if effect.world is not None:
        return f"{spec.world[effect.world].title} в мире {tail}"
    if effect.all is not None:
        return f"{spec.tracks[effect.all].title} у всех {tail}"
    if effect.relation is not None:
        return f"Отношения с целью {tail}"
    return tail


def track_cards(spec: ScenarioSpec) -> list[dict]:
    """Показатели с пояснением, шкалой и тем, кто их видит."""
    cards = [
        {
            "title": track.title,
            "meaning": track.meaning,
            "scale": f"{track.min:g}–{track.max:g}",
            "visibility": "виден всем" if track.visibility == "public" else "только своей команде",
            "scope": "сторона",
        }
        for track in spec.tracks.values()
    ]
    cards += [
        {
            "title": track.title,
            "meaning": track.meaning,
            "scale": f"{track.min:g}–{track.max:g}",
            "visibility": "виден всем",
            "scope": "мир",
        }
        for track in spec.world.values()
    ]
    return cards


def action_card(
    spec: ScenarioSpec,
    action: ActionSpec,
    state: GameState | None = None,
    actor: str | None = None,
    target: str | None = None,
    exact: bool = False,
) -> dict:
    cost = ", ".join(
        f"{spec.tracks[name].title} {amount:g}" for name, amount in sorted(action.cost.items())
    )
    risks = [
        {
            "title": outcome.title or "исход",
            "chance": f"{outcome.p * 100:g}%" if exact else chance_word(outcome.p),
            "effects": [
                describe_effect(spec, effect, state, actor, target) for effect in outcome.effects
            ]
            or ["ничего не происходит"],
        }
        for outcome in action.risk
    ]
    return {
        "id": action.id,
        "title": action.title,
        "description": action.description,
        "cost": cost or "без затрат",
        "points": action.ap,
        "secret": action.visibility == "secret",
        "needs_target": action.target == "faction",
        "requires": action.requires or "",
        "effects": [describe_effect(spec, effect, state, actor, target) for effect in action.effects],
        "risks": risks,
    }
