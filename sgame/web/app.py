"""Сборка и запуск локального приложения."""

import socket
import threading
import webbrowser
from importlib import resources

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from . import present
from ..i18n import LANGUAGES, normalise, t as translate

LANG_COOKIE = "sgame_lang"

_TEMPLATE_DIR = resources.files("sgame") / "web" / "templates"
_STATIC_DIR = resources.files("sgame") / "web" / "static"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
# Числа на экранах печатаются без хвоста «.0»: «Бюджет 120», а не «Бюджет 120.0».
templates.env.filters["num"] = present.number


@pass_context
def _t(context, key: str, **kwargs) -> str:
    """Строка на языке текущей страницы. Язык берётся из контекста шаблона."""
    return translate(key, context.get("lang", "ru"), **kwargs)


templates.env.globals["t"] = _t


def language_of(request: Request) -> str:
    return normalise(request.cookies.get(LANG_COOKIE))


def page(request: Request, name: str, context: dict):
    """Ответ шаблона с языком страницы и списком языков для переключателя."""
    lang = language_of(request)
    return templates.TemplateResponse(
        request, name, {**context, "lang": lang, "languages": LANGUAGES}
    )


def create_app() -> FastAPI:
    from .routes import host, screen, team

    app = FastAPI(title="Стратегическая игра")
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    app.include_router(host.router)
    app.include_router(team.router)
    app.include_router(screen.router)
    return app


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def serve(port: int = 0, open_browser: bool = True) -> None:
    import uvicorn

    chosen = port or _free_port()
    url = f"http://127.0.0.1:{chosen}/"
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Приложение открыто: {url}")
    uvicorn.run(create_app(), host="127.0.0.1", port=chosen, log_level="warning")
