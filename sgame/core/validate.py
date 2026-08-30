"""Смысловые проверки сценария поверх схемы.

Схема отвечает за форму (типы, обязательные поля), этот модуль — за смысл:
ссылки, вероятности, выражения, границы.
"""

from .errors import Problem
from .expr import ExprError, used_names
from .spec import EffectSpec, ScenarioSpec
from .yamlsrc import line_for

_FUNC_NAMES = {"min", "max", "abs", "round", "floor", "ceil", "clamp", "rel",
               "track", "status", "in_status", "avg"}


def validate_scenario(spec: ScenarioSpec, lines: dict[str, int]) -> list[Problem]:
    problems: list[Problem] = []
    tracks = set(spec.tracks)
    world_tracks = set(spec.world)
    factions = {f.id for f in spec.factions}
    actions = {a.id for a in spec.actions}

    def at(*path):
        return line_for(lines, path)

    def check_expression(source: str, where: str, line: int | None) -> None:
        try:
            bare, attrs = used_names(source)
        except ExprError as exc:
            problems.append(Problem(f"{where}: {exc}", line))
            return
        for name in bare:
            if name not in {"round"} | _FUNC_NAMES:
                problems.append(Problem(f"{where}: неизвестное имя {name!r}", line))
        for namespace, field in attrs:
            if namespace in {"self", "target", "all"}:
                if field not in tracks:
                    problems.append(
                        Problem(f"{where}: неизвестный трек {namespace}.{field}", line)
                    )
            elif namespace == "world":
                if field not in world_tracks:
                    problems.append(
                        Problem(f"{where}: неизвестный мировой трек world.{field}", line)
                    )
            elif namespace == "meta":
                if field != "rounds":
                    problems.append(Problem(f"{where}: у meta есть только rounds", line))
            else:
                problems.append(
                    Problem(f"{where}: неизвестное пространство имён {namespace!r}", line)
                )

    def check_effects(effects: list[EffectSpec], path: tuple, where: str) -> None:
        for i, effect in enumerate(effects):
            line = at(*path, i)
            for name in (effect.self_track, effect.target, effect.all):
                if name is not None and name not in tracks:
                    problems.append(Problem(f"{where}: неизвестный трек {name!r}", line))
            if effect.world is not None and effect.world not in world_tracks:
                problems.append(
                    Problem(f"{where}: неизвестный мировой трек {effect.world!r}", line)
                )
            if effect.relation is not None and len(effect.relation) != 2:
                problems.append(
                    Problem(f"{where}: relation должен задавать ровно две стороны", line)
                )
            check_expression(effect.delta, f"{where}: delta", line)

    for i, faction in enumerate(spec.factions):
        line = at("factions", i)
        for name, value in faction.start.items():
            if name not in tracks:
                problems.append(
                    Problem(f"сторона {faction.id!r}: неизвестный трек {name!r}", line)
                )
                continue
            track = spec.tracks[name]
            if not track.min <= value <= track.max:
                problems.append(
                    Problem(
                        f"сторона {faction.id!r}: начальное значение {value:g} для {name!r} "
                        f"вне границ {track.min:g}–{track.max:g}",
                        line,
                    )
                )
        for missing in sorted(tracks - set(faction.start)):
            problems.append(
                Problem(f"сторона {faction.id!r}: не задано начальное значение {missing!r}", line)
            )
        for j, goal in enumerate(faction.goals):
            check_expression(goal.when, f"цель {goal.id!r}", at("factions", i, "goals", j))

    for i, action in enumerate(spec.actions):
        line = at("actions", i)
        where = f"действие {action.id!r}"
        for name in action.cost:
            if name not in tracks:
                problems.append(Problem(f"{where}: неизвестный трек в стоимости {name!r}", line))
        if action.requires:
            check_expression(action.requires, f"{where}: requires", line)
        for name in action.available_to:
            if name not in factions:
                problems.append(Problem(f"{where}: неизвестная сторона в available_to: {name!r}", line))
        for counter in action.countered_by:
            if counter == action.id:
                problems.append(Problem(f"{where}: действие гасит само себя", line))
            elif counter not in actions:
                problems.append(Problem(f"{where}: неизвестное контрдействие {counter!r}", line))
        check_effects(action.effects, ("actions", i, "effects"), where)
        if action.risk:
            total = sum(outcome.p for outcome in action.risk)
            if abs(total - 1.0) > 1e-6:
                problems.append(
                    Problem(f"{where}: сумма вероятностей исходов {total:g}, должна быть 1", line)
                )
            for j, outcome in enumerate(action.risk):
                check_effects(outcome.effects, ("actions", i, "risk", j, "effects"), where)
        for j, complication in enumerate(action.complications):
            check_effects(
                complication.effects,
                ("actions", i, "complications", j, "effects"),
                f"{where}: осложнение {complication.title!r}",
            )

    for i, deal in enumerate(spec.deals):
        line = at("deals", i)
        if deal.kind == "resource" and deal.track not in tracks:
            problems.append(Problem(f"сделка {deal.id!r}: неизвестный трек {deal.track!r}", line))
        if deal.kind == "status" and not deal.duration:
            problems.append(Problem(f"сделка {deal.id!r}: у статуса должен быть duration", line))

    for i, event in enumerate(spec.events):
        line = at("events", i)
        if event.when:  # пустое условие означает «возможно в любом раунде»
            check_expression(event.when, f"событие {event.id!r}: when", line)
        check_effects(event.effects, ("events", i, "effects"), f"событие {event.id!r}")

    check_effects(spec.world_dynamics, ("world_dynamics",), "world_dynamics")
    check_expression(spec.end.when, "end.when", at("end"))
    check_expression(spec.end.scoring, "end.scoring", at("end"))

    for i, template in enumerate(spec.rumours.templates):
        if "{subject}" not in template:
            problems.append(
                Problem(
                    f"слух {i + 1}: в шаблоне нет подстановки {{subject}}, "
                    "слух не назовёт сторону",
                    at("rumours"),
                )
            )
    if spec.rumours.templates and not any(a.plants_rumour for a in spec.actions):
        if spec.rumours.chance == 0 and spec.rumours.noise_chance == 0:
            problems.append(
                Problem("слухи описаны, но не могут появиться: обе вероятности равны нулю",
                        at("rumours"))
            )

    mentioned = {p.a for p in spec.relations.pairs} | {p.b for p in spec.relations.pairs}
    for name in sorted(mentioned - factions):
        problems.append(Problem(f"relations: неизвестная сторона {name!r}", at("relations")))

    return problems
