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


def _split_language(stem: str) -> tuple[str, str]:
    """«meridian.en» → («meridian», «en»); «meridian» → («meridian», «ru»)."""
    base, _, suffix = stem.rpartition(".")
    if base and suffix in ("ru", "en"):
        return base, suffix
    return stem, "ru"


def _pick(pool: dict[tuple[str, str], str], lang: str, fallback: bool = True) -> dict[str, str]:
    """Копия на нужном языке, а если её нет — русская.

    Непереведённый сценарий должен оставаться играбельным, а не исчезать из
    списка: смешанный язык неприятен, отсутствие партии — хуже.
    """
    chosen: dict[str, str] = {}
    for (name, file_lang), text in pool.items():
        if file_lang == lang:
            chosen[name] = text
    if fallback:
        for (name, file_lang), text in pool.items():
            if name not in chosen and file_lang == "ru":
                chosen[name] = text
    return chosen


def builtin_scenarios(lang: str = "ru", fallback: bool = True) -> dict[str, str]:
    """Сценарии, вшитые в пакет. Читаются как ресурсы, не по пути файла."""
    pool: dict[tuple[str, str], str] = {}
    package = resources.files("sgame") / "scenarios"
    for item in package.iterdir():
        if item.name.endswith(".yaml"):
            key = _split_language(item.name.removesuffix(".yaml"))
            pool[key] = item.read_text(encoding="utf-8")
    return _pick(pool, lang, fallback)


def user_scenarios(lang: str = "ru") -> dict[str, str]:
    pool = {
        _split_language(path.stem): path.read_text(encoding="utf-8")
        for path in scenarios_dir().glob("*.yaml")
    }
    return _pick(pool, lang)


def all_scenarios(lang: str = "ru") -> dict[str, str]:
    """Пользовательские сценарии перекрывают встроенные с тем же именем."""
    return {**builtin_scenarios(lang), **user_scenarios(lang)}
