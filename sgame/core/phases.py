"""Восемь фаз разрешения раунда.

Порядок фаз фиксирован: он и делает результат объяснимым для студентов.
Каждая фаза — функция, принимающая рабочую копию состояния и возвращающая
список событий.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .events import Delta, Event
from .expr import evaluate
from .orders import Order
from .spec import ActionSpec, EffectSpec, ScenarioSpec
from .state import StateBuilder


@dataclass(frozen=True)
class Accepted:
    faction: str
    index: int
    order: Order
    action: ActionSpec

    @property
    def roll_id(self) -> str:
        return f"{self.faction}:{self.index}:{self.action.id}"


def _reject(faction: str, order: Order, reason: str) -> Event:
    return Event(
        kind="order_rejected",
        title="Приказ отклонён",
        actor=faction,
        detail=f"{order.action}: {reason}",
        audience="actor",
    )


def phase_validate(
    spec: ScenarioSpec,
    builder: StateBuilder,
    orders: Mapping[str, Sequence[Order]],
) -> tuple[list[Accepted], list[Event]]:
    """Фаза 1. Отсеять приказы, которые нельзя исполнить, с указанием причины."""
    accepted: list[Accepted] = []
    events: list[Event] = []
    known_factions = {f.id for f in spec.factions}

    for faction in sorted(orders):
        points_left = spec.meta.action_points
        reserved: dict[str, float] = {}

        for index, order in enumerate(orders[faction]):
            action = spec.action(order.action)
            if action is None:
                events.append(_reject(faction, order, f"неизвестное действие {order.action!r}"))
                continue
            if action.ap > points_left:
                events.append(_reject(faction, order, "не хватает очков действий"))
                continue
            if action.target == "faction":
                if not order.target:
                    events.append(_reject(faction, order, "не выбрана цель"))
                    continue
                if order.target == faction:
                    events.append(_reject(faction, order, "нельзя направить действие на себя"))
                    continue
                if order.target not in known_factions:
                    events.append(_reject(faction, order, f"неизвестная цель {order.target!r}"))
                    continue
            if action.requires:
                context = builder.context(actor=faction, target=order.target)
                if not evaluate(action.requires, context):
                    events.append(_reject(faction, order, f"не выполнено условие: {action.requires}"))
                    continue

            shortfall = next(
                (
                    name
                    for name, amount in action.cost.items()
                    if builder.track(faction, name) - reserved.get(name, 0.0) < amount
                ),
                None,
            )
            if shortfall is not None:
                events.append(
                    _reject(faction, order, f"не хватает ресурса «{spec.tracks[shortfall].title}»")
                )
                continue

            for name, amount in action.cost.items():
                reserved[name] = reserved.get(name, 0.0) + amount
            points_left -= action.ap
            accepted.append(Accepted(faction=faction, index=index, order=order, action=action))

    return accepted, events


def phase_pay(spec: ScenarioSpec, builder: StateBuilder, accepted: Sequence[Accepted]) -> list[Event]:
    """Фаза 2. Списать стоимость принятых приказов."""
    events: list[Event] = []
    for item in accepted:
        if not item.action.cost:
            continue
        deltas = tuple(
            builder.add_track(item.faction, name, -amount)
            for name, amount in sorted(item.action.cost.items())
        )
        events.append(
            Event(
                kind="cost",
                title=f"Затраты: {item.action.title}",
                actor=item.faction,
                deltas=deltas,
                audience="actor",
            )
        )
    return events


def apply_effect(
    spec: ScenarioSpec,
    builder: StateBuilder,
    effect: EffectSpec,
    actor: str | None,
    target: str | None,
    multiplier: float = 1.0,
) -> list[Delta]:
    """Применить один эффект. Форма `all` считается отдельно для каждой стороны."""
    if effect.all is not None:
        deltas = []
        for faction in spec.factions:
            amount = evaluate(effect.delta, builder.context(actor=faction.id, target=target))
            deltas.append(builder.add_track(faction.id, effect.all, amount * multiplier))
        return deltas

    amount = evaluate(effect.delta, builder.context(actor=actor, target=target)) * multiplier

    if effect.self_track is not None:
        return [builder.add_track(actor, effect.self_track, amount)]
    if effect.target is not None:
        return [builder.add_track(target, effect.target, amount)]
    if effect.world is not None:
        return [builder.add_world(effect.world, amount)]
    if effect.relation is not None:
        names = {"self": actor, "target": target}
        first, second = (names.get(n, n) for n in effect.relation)
        return [builder.add_relation(first, second, amount)]
    return []
