"""Сборка и запуск локального приложения."""

import os
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
    """Язык страницы — тот, который выбрал читатель.

    Тексты сценария берутся из копии на этом же языке, поэтому переключение
    работает и посреди партии, не трогая ни правил, ни расчёта.
    """
    return normalise(request.cookies.get(LANG_COOKIE))


chosen_language = language_of


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


def serve_host(network: bool) -> str:
    """Какой интерфейс слушать. В сеть выходим только по явному решению."""
    return "0.0.0.0" if network else "127.0.0.1"


def local_address() -> str:
    """Адрес этой машины в локальной сети — его набирают на телефонах."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))  # адрес из документации, пакеты никуда не идут
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def public_base_url(port: int) -> str:
    """Адрес, который набирают на телефонах и который зашит в QR.

    Своё место в сети машина определяет сама, но за обратным прокси или в
    контейнере она знает только внутренний адрес: телефон по такой ссылке
    никуда не попадёт. Тогда адрес задают через SGAME_PUBLIC_URL.
    """
    override = os.environ.get("SGAME_PUBLIC_URL", "").strip()
    if override:
        return override.rstrip("/")
    return f"http://{local_address()}:{port}"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def serve(port: int = 0, open_browser: bool = True, network: bool = False) -> None:
    import uvicorn

    from . import config

    config.NETWORK = network
    chosen = port or _free_port()
    url = f"http://127.0.0.1:{chosen}/"
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Приложение открыто: {url}")
    if network:
        print(f"Команды с телефонов: {public_base_url(chosen)}/")
        print("Приложение доступно всем в этой сети.")
    uvicorn.run(create_app(), host=serve_host(network), port=chosen, log_level="warning")
