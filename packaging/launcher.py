"""Точка входа собранного приложения: поднять сервер и открыть браузер.

Две переменные окружения нужны для проверки собранного приложения:
SGAME_PORT задаёт порт, SGAME_NO_BROWSER не даёт открыть браузер.
"""

import os

from sgame.web.app import serve

if __name__ == "__main__":
    # Собранное приложение существует ради занятия, где команды сидят с
    # телефонами, поэтому сетевой режим включён. Выключается переменной.
    serve(
        port=int(os.environ.get("SGAME_PORT", "0")),
        open_browser=not os.environ.get("SGAME_NO_BROWSER"),
        network=not os.environ.get("SGAME_LOCAL_ONLY"),
    )
