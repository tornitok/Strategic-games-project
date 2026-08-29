"""Восемь фаз разрешения раунда.

Порядок фаз фиксирован: он и делает результат объяснимым для студентов.
Каждая фаза — функция, принимающая рабочую копию состояния и возвращающая
список событий.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .events import Delta, Event
from .expr import evaluate
from .orders import DealOffer, Order
from .rng import choose, happens, stream
from .spec import ActionSpec, EffectSpec, ScenarioSpec
from .state import StateBuilder, Status


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
        used: set[str] = set()

        for index, order in enumerate(orders[faction]):
            action = spec.action(order.action)
            if action is None:
                events.append(_reject(faction, order, f"неизвестное действие {order.action!r}"))
                continue
            if action.id in used and not action.repeatable:
                events.append(_reject(faction, order, "это действие уже заказано в этом раунде"))
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
            used.add(action.id)
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


def phase_deals(
    spec: ScenarioSpec,
    builder: StateBuilder,
    offers: Sequence[DealOffer],
    responses: Mapping[str, bool],
) -> list[Event]:
    """Фаза 3. Ответы на прошлые предложения, истечение статусов, новые предложения."""
    events: list[Event] = []

    for offer in builder.pending_offers:
        deal = spec.deal(offer.deal)
        if deal is None:
            continue
        if not responses.get(offer.id, False):
            events.append(
                Event(
                    kind="deal_rejected",
                    title=f"Отклонено: {deal.title}",
                    actor=offer.sender,
                    target=offer.receiver,
                    audience="actor_and_target",
                )
            )
            continue

        if deal.kind == "resource":
            amount = offer.amount or 0.0
            deltas = (
                builder.add_track(offer.sender, deal.track, -amount),
                builder.add_track(offer.receiver, deal.track, amount),
            )
            events.append(
                Event(
                    kind="deal_done",
                    title=f"Исполнено: {deal.title}",
                    actor=offer.sender,
                    target=offer.receiver,
                    deltas=deltas,
                    audience="public",
                )
            )
        else:
            builder.statuses.append(
                Status(
                    deal=deal.id,
                    a=offer.sender,
                    b=offer.receiver,
                    until=builder.round + (deal.duration or 1),
                )
            )
            events.append(
                Event(
                    kind="deal_done",
                    title=f"Заключено: {deal.title}",
                    actor=offer.sender,
                    target=offer.receiver,
                    audience="public",
                )
            )

    still_active = []
    for status in builder.statuses:
        if status.until <= builder.round:
            deal = spec.deal(status.deal)
            events.append(
                Event(
                    kind="status_expired",
                    title=f"Истекло: {deal.title if deal else status.deal}",
                    actor=status.a,
                    target=status.b,
                    audience="public",
                )
            )
        else:
            still_active.append(status)
    builder.statuses = still_active

    builder.pending_offers = list(offers)
    for offer in offers:
        deal = spec.deal(offer.deal)
        events.append(
            Event(
                kind="deal_offered",
                title=f"Предложено: {deal.title if deal else offer.deal}",
                actor=offer.sender,
                target=offer.receiver,
                detail="ответ ожидается в следующем раунде",
                audience="actor_and_target",
            )
        )
    return events


def phase_counters(spec: ScenarioSpec, accepted: Sequence[Accepted]) -> dict[tuple[str, int], float]:
    """Фаза 4. Множитель эффекта для каждого приказа, который встретил контрдействие."""
    by_faction: dict[str, set[str]] = {}
    for item in accepted:
        by_faction.setdefault(item.faction, set()).add(item.action.id)

    multipliers: dict[tuple[str, int], float] = {}
    for item in accepted:
        if not item.action.countered_by or not item.order.target:
            continue
        defences = by_faction.get(item.order.target, set()) & set(item.action.countered_by)
        if not defences:
            continue
        multipliers[(item.faction, item.index)] = min(
            spec.action(name).counter_multiplier for name in defences
        )
    return multipliers


def phase_effects(
    spec: ScenarioSpec,
    builder: StateBuilder,
    accepted: Sequence[Accepted],
    multipliers: Mapping[tuple[str, int], float],
    seed: int,
) -> list[Event]:
    """Фаза 5. Броски и применение эффектов.

    Бросок делается всегда, даже если действие погашено контрдействием:
    иначе очередь обращений к генератору зависела бы от чужих приказов.
    """
    events: list[Event] = []

    for item in accepted:
        effects = item.action.effects
        roll_title = None
        if item.action.risk:
            rng = stream(seed, builder.round, item.roll_id)
            index = choose(rng, [outcome.p for outcome in item.action.risk])
            outcome = item.action.risk[index]
            effects = outcome.effects
            roll_title = outcome.title or f"исход {index + 1}"

        multiplier = multipliers.get((item.faction, item.index), 1.0)
        deltas: list[Delta] = []
        for effect in effects:
            deltas.extend(
                apply_effect(spec, builder, effect, item.faction, item.order.target, multiplier)
            )

        audience = "public"
        if item.action.visibility == "secret":
            audience = "actor"
            if item.order.target and item.action.reveal_chance:
                revealed = happens(
                    stream(seed, builder.round, item.roll_id + ":reveal"),
                    item.action.reveal_chance,
                )
                if revealed:
                    audience = "actor_and_target"

        detail = item.action.description
        if multiplier < 1.0:
            detail = (detail + " " if detail else "") + "Действие встретило противодействие."

        events.append(
            Event(
                kind="action",
                title=item.action.title,
                actor=item.faction,
                target=item.order.target,
                detail=detail.strip(),
                deltas=tuple(deltas),
                audience=audience,
                roll=roll_title,
            )
        )

        if multiplier < 1.0:
            events.append(
                Event(
                    kind="counter",
                    title=f"Противодействие: {item.action.title}",
                    actor=item.order.target,
                    target=item.faction,
                    audience="actor_and_target",
                )
            )

    return events


def phase_world(spec: ScenarioSpec, builder: StateBuilder) -> list[Event]:
    """Фаза 6. Динамика мира: то, что происходит независимо от команд."""
    deltas: list[Delta] = []
    for effect in spec.world_dynamics:
        deltas.extend(apply_effect(spec, builder, effect, actor=None, target=None))
    if not deltas:
        return []
    return [
        Event(kind="world", title="Обстановка", deltas=tuple(deltas), audience="public")
    ]


def phase_events(spec: ScenarioSpec, builder: StateBuilder, seed: int) -> list[Event]:
    """Фаза 7. Плановые, триггерные и случайные события сценария.

    Событие срабатывает, когда выполнено его условие (пустое условие годится
    всегда) и прошёл бросок `chance`. Потолок `max_random_events` ограничивает
    только случайные события: плановые он не трогает, иначе расписание
    сценария зависело бы от везения.
    """
    events: list[Event] = []
    random_fired = 0
    cap = spec.meta.max_random_events

    for scenario_event in spec.events:
        if scenario_event.once and scenario_event.id in builder.fired_events:
            continue
        if scenario_event.when and not evaluate(scenario_event.when, builder.context()):
            continue

        # Случайное — то, где автор сценария явно написал chance, даже если
        # написал единицу. Иначе потолок нельзя ни задать осмысленно, ни
        # проверить: «chance: 1» тоже часть случайного пула.
        is_random = "chance" in scenario_event.model_fields_set
        if is_random:
            if cap is not None and random_fired >= cap:
                continue
            rng = stream(seed, builder.round, f"event:{scenario_event.id}")
            if not happens(rng, scenario_event.chance):
                continue
            random_fired += 1

        deltas: list[Delta] = []
        for effect in scenario_event.effects:
            deltas.extend(apply_effect(spec, builder, effect, actor=None, target=None))
        builder.fired_events.add(scenario_event.id)
        events.append(
            Event(
                kind="scenario_event",
                title=scenario_event.title,
                detail=scenario_event.text,
                deltas=tuple(deltas),
                audience="public",
            )
        )
    return events


def phase_end(spec: ScenarioSpec, builder: StateBuilder) -> tuple[bool, list[Event]]:
    """Фаза 8. Проверка условия окончания. Раунд уже прожит, поэтому проверяем следующий."""
    context = builder.context()
    context["round"] = builder.round + 1
    finished = bool(evaluate(spec.end.when, context))
    if not finished:
        return False, []
    return True, [Event(kind="end", title="Игра окончена", audience="public")]


def _rumour_event(spec: ScenarioSpec, rng, subject: str, truth: bool, source: str | None) -> Event:
    templates = spec.rumours.templates
    template = templates[choose(rng, [1.0] * len(templates))]
    faction = spec.faction(subject)
    return Event(
        kind="rumour",
        title=template.format(subject=faction.title if faction else subject),
        audience="public",
        subject=subject,
        truth=truth,
        source=source,
    )


def phase_rumours(
    spec: ScenarioSpec,
    builder: StateBuilder,
    accepted: Sequence[Accepted],
    seed: int,
) -> list[Event]:
    """Фаза 7б. Слухи — модельные и запущенные командами.

    Слух публичен и подан как слух. Кто его запустил и правда ли это,
    хранится в событии, но показывается только ведущему: игроки должны
    решать, верить ли, а не читать ответ.
    """
    config = spec.rumours
    if not config.templates:
        return []

    events: list[Event] = []

    for item in accepted:
        if item.action.plants_rumour and item.order.target:
            rng = stream(seed, builder.round, item.roll_id + ":rumour")
            events.append(
                _rumour_event(spec, rng, item.order.target, truth=False, source=item.faction)
            )

    secret_actors = sorted({i.faction for i in accepted if i.action.visibility == "secret"})
    rng = stream(seed, builder.round, "rumour")
    everyone = [f.id for f in spec.factions]

    if secret_actors:
        if happens(rng, config.chance):
            truthful = happens(rng, config.accuracy)
            if truthful:
                subject = secret_actors[choose(rng, [1.0] * len(secret_actors))]
            else:
                others = [f for f in everyone if f not in secret_actors] or everyone
                subject = others[choose(rng, [1.0] * len(others))]
            events.append(_rumour_event(spec, rng, subject, truth=truthful, source=None))
    elif happens(rng, config.noise_chance):
        subject = everyone[choose(rng, [1.0] * len(everyone))]
        events.append(_rumour_event(spec, rng, subject, truth=False, source=None))

    return events
