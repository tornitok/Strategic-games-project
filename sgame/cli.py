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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sgame", description="Движок стратегических игр")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate", help="проверить файл сценария")
    validate_cmd.add_argument("path", type=Path)

    run_cmd = sub.add_parser("run", help="запустить приложение")
    run_cmd.add_argument("--port", type=int, default=0)
    run_cmd.add_argument("--no-browser", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "validate":
        return _validate(args.path)

    from .web.app import serve

    serve(port=args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
