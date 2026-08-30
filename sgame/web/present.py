"""Подготовка данных для экранов.

Доступность действия проверяется той же фазой валидации, что и в расчёте
раунда: если правило одно, интерфейс не может разойтись с моделью.
"""

from dataclasses import dataclass

from ..core.orders import Order
from ..core.phases import phase_validate
from ..core.spec import ActionSpec, ScenarioSpec
from ..core.state import GameState, StateBuilder


@dataclass
class ActionOption:
    action: ActionSpec
    available: bool
    reason: str = ""


def action_options(
    spec: ScenarioSpec, state: GameState, faction: str, draft: list[Order],
    role: str | None = None,
) -> list[ActionOption]:
    """Список приказов для экрана. Должность видит только то, что вправе вносить."""
    others = [f.id for f in spec.factions if f.id != faction]
    spec_faction = spec.faction(faction)
    role_spec = spec_faction.role(role) if spec_faction and role else None
    options: list[ActionOption] = []

    for action in spec.actions:
        if role_spec is not None and not role_spec.can_propose(action.id):
            continue
        probe = Order(
            action=action.id,
            target=others[0] if action.target == "faction" and others else None,
        )
        builder = StateBuilder(spec, state)
        accepted, rejected = phase_validate(spec, builder, {faction: [*draft, probe]})
        chosen = len(draft)
        available = any(item.index == chosen for item in accepted)
        reason = ""
        if not available and rejected:
            reason = rejected[-1].detail.split(": ", 1)[-1]
        options.append(ActionOption(action=action, available=available, reason=reason))

    return options


def points_left(spec: ScenarioSpec, draft: list[Order]) -> int:
    spent = sum(spec.action(order.action).ap for order in draft if spec.action(order.action))
    return spec.meta.action_points - spent


def paragraphs(text: str) -> list[str]:
    """Разбить текст сценария на абзацы.

    В YAML длинные тексты пишут блоком с переносами по 80 колонок. Показывать
    их как есть — значит рвать строки посреди экрана, поэтому внутри абзаца
    переносы схлопываются, а пустая строка начинает новый абзац.
    """
    return [" ".join(block.split()) for block in (text or "").split("\n\n") if block.strip()]


def number(value: float) -> str:
    """Число для экрана: без хвоста «.0» у целых значений."""
    rounded = round(float(value), 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:g}"
