"""Где лежат данные пользователя.

Внутрь пакета ничего не пишется: собранное приложение только читает свои
ресурсы, а сессии и настройки живут в пользовательской директории.
"""

import os
from importlib import resources
from pathlib import Path

APP_NAME = "StrategicGame"


def data_dir() -> Path:
    override = os.environ.get("SGAME_DATA_DIR")
    root = Path(override) if override else Path.home() / "Library" / "Application Support" / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def sessions_dir() -> Path:
    path = data_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def scenarios_dir() -> Path:
    path = data_dir() / "scenarios"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return data_dir() / "config.json"


def builtin_scenarios() -> dict[str, str]:
    """Сценарии, вшитые в пакет. Читаются как ресурсы, не по пути файла."""
    found: dict[str, str] = {}
    package = resources.files("sgame") / "scenarios"
    for item in package.iterdir():
        if item.name.endswith(".yaml"):
            found[item.name.removesuffix(".yaml")] = item.read_text(encoding="utf-8")
    return found


def user_scenarios() -> dict[str, str]:
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in scenarios_dir().glob("*.yaml")
    }


def all_scenarios() -> dict[str, str]:
    """Пользовательские сценарии перекрывают встроенные с тем же именем."""
    return {**builtin_scenarios(), **user_scenarios()}
