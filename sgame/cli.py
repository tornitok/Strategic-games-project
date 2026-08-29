"""Точка входа: sgame run | validate."""

import argparse
import sys
from pathlib import Path

from .core.errors import ScenarioError
from .core.spec import load_scenario, scenario_lines
from .core.validate import validate_scenario


def _validate(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    try:
        spec = load_scenario(path)
    except ScenarioError as exc:
        for problem in exc.problems:
            print(f"{path.name}:{problem.line or 0}: {problem.message}")
        return 1

    problems = validate_scenario(spec, scenario_lines(text))
    for problem in problems:
        print(f"{path.name}:{problem.line or 0}: {problem.message}")
    if problems:
        print(f"Найдено проблем: {len(problems)}")
        return 1
    print(f"{path.name}: сценарий в порядке")
    return 0


def _simulate(scenario: str, seeds: int, roles: list[str] | None) -> int:
    from .bots import ROLES, simulate
    from .core.spec import parse_scenario
    from .session.paths import all_scenarios

    available = all_scenarios()
    if scenario not in available:
        print(f"нет такого сценария: {scenario}. Есть: {', '.join(sorted(available))}")
        return 1

    spec = parse_scenario(available[scenario])
    ids = [f.id for f in spec.factions]
    chosen = roles or [ROLES[i % len(ROLES)] for i in range(len(ids))]
    if len(chosen) != len(ids):
        print(f"ролей нужно {len(ids)} по числу сторон, задано {len(chosen)}")
        return 1
    plan = dict(zip(ids, chosen))

    print(f"{spec.meta.title} — {seeds} партий")
    print("роли: " + ", ".join(f"{spec.faction(f).title}: {r}" for f, r in plan.items()))
    print()

    wins: dict[str, int] = {}
    for seed in range(1, seeds + 1):
        result = simulate(spec, plan, seed)
        winner = max(result.scores, key=result.scores.get)
        wins[winner] = wins.get(winner, 0) + 1
        world = ", ".join(f"{spec.world[k].title} {v:g}" for k, v in result.state.world.items())
        scores = " ".join(f"{spec.faction(f).title} {v:g}" for f, v in result.scores.items())
        print(f"  ключ {seed:>3}: раундов {len(result.rounds)} · {world}")
        print(f"            {scores}")

    print()
    print("побед: " + ", ".join(
        f"{spec.faction(f).title} {n}" for f, n in sorted(wins.items(), key=lambda x: -x[1])
    ))
    return 0


def _doctor(scenario: str, games: int) -> int:
    from .core.spec import parse_scenario
    from .doctor import check
    from .session.paths import all_scenarios

    available = all_scenarios()
    if scenario not in available:
        print(f"нет такого сценария: {scenario}. Есть: {', '.join(sorted(available))}")
        return 1

    spec = parse_scenario(available[scenario])
    findings = check(spec, games=games)
    print(f"{spec.meta.title} — {games} прогонов\n")
    if not findings:
        print("проблемных мест не найдено")
        return 0

    errors = [f for f in findings if f.severity == "ошибка"]
    for finding in findings:
        print(f"  {finding}")
    print(f"\nвсего: {len(findings)}, из них ошибок: {len(errors)}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sgame", description="Движок стратегических игр")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate", help="проверить файл сценария")
    validate_cmd.add_argument("path", type=Path)

    run_cmd = sub.add_parser("run", help="запустить приложение")
    run_cmd.add_argument("--port", type=int, default=0)
    run_cmd.add_argument("--no-browser", action="store_true")

    sim_cmd = sub.add_parser("simulate", help="прогнать сценарий ботами")
    sim_cmd.add_argument("scenario")
    sim_cmd.add_argument("--seeds", type=int, default=5)
    sim_cmd.add_argument("--roles", help="через запятую: opposition, balancing, following, cautious")

    doc_cmd = sub.add_parser("doctor", help="найти места, где сценарий может сломаться")
    doc_cmd.add_argument("scenario")
    doc_cmd.add_argument("--games", type=int, default=24)

    args = parser.parse_args(argv)
    if args.command == "validate":
        return _validate(args.path)

    if args.command == "doctor":
        return _doctor(args.scenario, args.games)

    if args.command == "simulate":
        roles = args.roles.split(",") if args.roles else None
        return _simulate(args.scenario, args.seeds, roles)

    from .web.app import serve

    serve(port=args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
