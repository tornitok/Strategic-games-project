"""Сборка и запуск локального приложения."""

import socket
import threading
import webbrowser
from importlib import resources

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_TEMPLATE_DIR = resources.files("sgame") / "web" / "templates"
_STATIC_DIR = resources.files("sgame") / "web" / "static"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def create_app() -> FastAPI:
    from .routes import host

    app = FastAPI(title="Стратегическая игра")
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    app.include_router(host.router)
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
