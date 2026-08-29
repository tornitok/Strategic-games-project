"""Поиск мест, где сценарий может сломаться.

Такие вещи не видны глазами в YAML: цель, которую нельзя выполнить; действие,
которое никогда не по карману; трек, залипший в потолке; партия, кончающаяся
на втором раунде. Поэтому сценарий прогоняется ботами десятки раз, и выводы
делаются по тому, что произошло, а не по тому, что задумывалось.
"""

from collections import Counter
from dataclasses import dataclass
from itertools import permutations

from .bots import ROLES, choose_orders, simulate
from .core.expr import evaluate
from .core.phases import phase_validate
from .core.scoring import score
from .core.orders import Order
from .core.spec import ScenarioSpec
from .core.state import StateBuilder, initial_state

DOMINANCE = 0.6      # доля побед, после которой перекос считается поломкой
STUCK_SHARE = 0.5    # доля раундов у границы, после которой трек считается залипшим
EARLY_SHARE = 0.6    # партия короче этой доли раундов считается оборванной
ENOUGH_GAMES = 20    # ниже этого «ни разу» — повод присмотреться, а не приговор


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.message}"


def _role_plans(spec: ScenarioSpec) -> list[dict[str, str]]:
    ids = [f.id for f in spec.factions]
    plans = []
    for roles in permutations(ROLES, min(len(ids), len(ROLES))):
        assignment = list(roles) + [ROLES[0]] * (len(ids) - len(roles))
        plans.append(dict(zip(ids, assignment)))
    return plans


def observed_ranges(spec: ScenarioSpec, games: int = 12) -> dict[str, tuple[float, float, float]]:
    """Какие значения показатели принимали на самом деле.

    Нужна, чтобы калибровать пороги целей по тому, что происходит, а не по
    тому, что задумывалось: цель «армия не ниже 70» бесполезна, если армия
    никогда не поднимается выше 50.
    """
    plans = _role_plans(spec)
    values: dict[str, list[float]] = {}
    for index in range(games):
        result = simulate(spec, plans[index % len(plans)], index + 1)
        for record in result.rounds:
            for tracks in record["tracks"].values():
                for name, value in tracks.items():
                    values.setdefault(name, []).append(value)
            for name, value in record["world"].items():
                values.setdefault(f"world.{name}", []).append(value)
    summary = {}
    for name, series in values.items():
        ordered = sorted(series)
        summary[name] = (ordered[0], ordered[len(ordered) // 2], ordered[-1])
    return summary


def check(spec: ScenarioSpec, games: int = 12) -> list[Finding]:
    findings: list[Finding] = []
    plans = _role_plans(spec)

    wins_by_faction: Counter = Counter()
    wins_by_role: Counter = Counter()
    goal_hits: Counter = Counter()
    chosen_actions: Counter = Counter()
    available_actions: set[str] = set()
    stuck: Counter = Counter()
    dead_turns = 0
    track_values: dict[str, list[float]] = {}
    observations = 0
    short_games = 0
    played = 0

    for index in range(games):
        plan = plans[index % len(plans)]
        seed = index + 1
        result = simulate(spec, plan, seed)
        played += 1

        if len(result.rounds) < spec.meta.rounds * EARLY_SHARE:
            short_games += 1

        winner = max(result.scores, key=result.scores.get)
        wins_by_faction[winner] += 1
        wins_by_role[plan[winner]] += 1

        for faction in spec.factions:
            _, breakdown = score(spec, result.state, faction.id)
            for title, _ in breakdown[1:]:
                goal_hits[(faction.id, title)] += 1

        for record in result.rounds:
            observations += 1
            for name, track in spec.world.items():
                value = record["world"][name]
                if value <= track.min or value >= track.max:
                    stuck[track.title] += 1

        # Что боты действительно заказывали — по самой партии, а не по повторной прикидке
        for record in result.rounds:
            dead_turns += len(record.get("stuck", []))
            for faction, ordered in record["orders"].items():
                for action_id in ordered:
                    chosen_actions[action_id] += 1
                    available_actions.add(action_id)
            for faction, values in record["tracks"].items():
                for name, value in values.items():
                    track_values.setdefault(name, []).append(value)

        # Доступность проверяем отдельно: действие могло быть по карману, но
        # ни разу не понадобиться — это другой диагноз.
        state = initial_state(spec)
        for faction in plan:
            others = [f.id for f in spec.factions if f.id != faction]
            for action in spec.actions:
                probe = Order(
                    action=action.id,
                    target=others[0] if action.target == "faction" and others else None,
                )
                accepted, _ = phase_validate(spec, StateBuilder(spec, state), {faction: [probe]})
                if accepted:
                    available_actions.add(action.id)

    # --- выводы ---
    for action in spec.actions:
        if action.id not in available_actions and action.id not in chosen_actions:
            findings.append(
                Finding(
                    "unusable_action",
                    "ошибка",
                    f"действие «{action.title}» ни разу не было доступно — "
                    "проверьте стоимость и условие",
                )
            )
        elif action.id not in chosen_actions:
            findings.append(
                Finding(
                    "ignored_action",
                    "предупреждение",
                    f"действие «{action.title}» доступно, но боты его не выбирают — "
                    "возможно, оно бессмысленно",
                )
            )

    for faction in spec.factions:
        for goal in faction.goals:
            hits = goal_hits[(faction.id, goal.title)]
            if hits == 0:
                enough = played >= ENOUGH_GAMES
                note = "" if enough else " — но прогонов мало, проверьте на большем числе"
                findings.append(
                    Finding(
                        "unreachable_goal",
                        "ошибка" if enough else "предупреждение",
                        f"цель «{goal.title}» ({faction.title}) не выполнена ни разу "
                        f"за {played} партий{note}",
                    )
                )
            elif hits == played:
                findings.append(
                    Finding(
                        "free_goal",
                        "предупреждение",
                        f"цель «{goal.title}» ({faction.title}) выполняется всегда — "
                        "это бесплатные очки",
                    )
                )

    for title, count in stuck.items():
        if observations and count / observations > STUCK_SHARE:
            findings.append(
                Finding(
                    "stuck_track",
                    "предупреждение",
                    f"трек «{title}» упирается в границу в {count * 100 // observations}% "
                    "раундов — шкала подобрана неверно",
                )
            )

    free_actions = [a for a in spec.actions if not a.cost and not a.requires]
    if not free_actions:
        findings.append(
            Finding(
                "no_free_action",
                "предупреждение",
                "нет ни одного действия без стоимости и условий: команда, оставшаяся "
                "без ресурсов, не сможет сделать ход",
            )
        )

    if short_games:
        findings.append(
            Finding(
                "early_end",
                "ошибка" if short_games > played / 2 else "предупреждение",
                f"партия обрывается досрочно в {short_games} из {played} прогонов",
            )
        )

    if dead_turns:
        findings.append(
            Finding(
                "dead_turn",
                "ошибка",
                f"{dead_turns} раз у команды не было ни одного исполнимого действия — "
                "мёртвый ход",
            )
        )

    for faction_id, count in wins_by_faction.items():
        if count / played > DOMINANCE:
            findings.append(
                Finding(
                    "dominant_faction",
                    "предупреждение",
                    f"сторона «{spec.faction(faction_id).title}» побеждает в "
                    f"{count * 100 // played}% партий",
                )
            )
    for role, count in wins_by_role.items():
        if count / played > DOMINANCE:
            findings.append(
                Finding(
                    "dominant_role",
                    "предупреждение",
                    f"линия «{role}» побеждает в {count * 100 // played}% партий",
                )
            )

    return findings
