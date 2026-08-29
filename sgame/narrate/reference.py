"""Справочник действий и показателей, собранный из самого сценария.

Писать такие описания руками нельзя: они разъедутся с моделью при первой же
правке чисел. Здесь всё выводится из спецификации, поэтому справочник всегда
говорит правду о том, что произойдёт.
"""

from ..core.expr import ExprError, evaluate
from ..core.spec import ActionSpec, EffectSpec, ScenarioSpec
from ..core.state import GameState, StateBuilder

from ..i18n import t

_WORDS = (
    (0.8, "chance.almost_always"),
    (0.5, "chance.usually"),
    (0.25, "chance.sometimes"),
    (0.0, "chance.rarely"),
)


def chance_word(probability: float, lang: str = "ru") -> str:
    """Словесная оценка вместо процента.

    Точные проценты превращают игру в арифметику ожидаемых значений; словами
    неопределённость остаётся неопределённостью, как в настоящей штабной работе.
    """
    for threshold, key in _WORDS:
        if probability >= threshold:
            return t(key, lang)
    return t("chance.rarely", lang)


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
    lang: str = "ru",
) -> str:
    amount = _amount(spec, effect, state, actor, target)
    tail = amount if amount else t("ref.depends", lang)

    if effect.self_track is not None:
        return f"{spec.tracks[effect.self_track].title} {tail}"
    if effect.target is not None:
        return f"{spec.tracks[effect.target].title} {t('ref.of_target', lang)} {tail}"
    if effect.world is not None:
        return f"{spec.world[effect.world].title} {t('ref.in_world', lang)} {tail}"
    if effect.all is not None:
        return f"{spec.tracks[effect.all].title} {t('ref.for_all', lang)} {tail}"
    if effect.relation is not None:
        return f"{t('ref.relations', lang)} {tail}"
    return tail


def track_cards(spec: ScenarioSpec, lang: str = "ru") -> list[dict]:
    """Показатели с пояснением, шкалой и тем, кто их видит."""
    cards = [
        {
            "title": track.title,
            "meaning": track.meaning,
            "scale": f"{track.min:g}–{track.max:g}",
            "visibility": t("intro.visible_all", lang) if track.visibility == "public"
            else t("intro.visible_own", lang),
            "scope": "faction",
        }
        for track in spec.tracks.values()
    ]
    cards += [
        {
            "title": track.title,
            "meaning": track.meaning,
            "scale": f"{track.min:g}–{track.max:g}",
            "visibility": t("intro.visible_all", lang),
            "scope": "world",
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
    lang: str = "ru",
) -> dict:
    cost = ", ".join(
        f"{spec.tracks[name].title} {amount:g}" for name, amount in sorted(action.cost.items())
    )
    risks = [
        {
            "title": outcome.title or t("ref.outcome", lang),
            "chance": f"{outcome.p * 100:g}%" if exact else chance_word(outcome.p, lang),
            "effects": [
                describe_effect(spec, effect, state, actor, target, lang)
                for effect in outcome.effects
            ]
            or [t("ref.nothing_happens", lang)],
        }
        for outcome in action.risk
    ]
    return {
        "id": action.id,
        "title": action.title,
        "description": action.description,
        "cost": cost or t("ref.free", lang),
        "points": action.ap,
        "secret": action.visibility == "secret",
        "needs_target": action.target == "faction",
        "requires": action.requires or "",
        "effects": [
            describe_effect(spec, effect, state, actor, target, lang) for effect in action.effects
        ],
        "risks": risks,
    }
