"""Английский интерфейс должен отрисовываться целиком, без падений на ключах."""

import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    live.reset()
    yield
    live.reset()


def client_with(lang):
    client = TestClient(create_app())
    client.cookies.set("sgame_lang", lang)
    return client


def start(client, scenario="meridian"):
    client.post("/session/new", data={"scenario": scenario, "seed": "7"}, follow_redirects=True)


def test_start_page_switches_language():
    assert "Новая партия" in client_with("ru").get("/").text
    assert "New game" in client_with("en").get("/").text


def test_english_session_uses_the_english_scenario():
    client = client_with("en")
    start(client)
    assert "Crisis in the Meridian Gulf" in client.get("/").text


def test_no_russian_left_on_english_screens():
    """Кириллица на английской странице означает непереведённую строку.

    Ключ, которого нет в каталоге, поднимает ошибку и роняет страницу, так что
    отдельная проверка на «сырые ключи» не нужна — достаточно кода ответа.
    """
    client = client_with("en")
    start(client)
    slot = live.current().journal.teams[0]
    client.post(f"/team/{slot.faction}/login", data={"code": slot.code}, follow_redirects=True)
    for path in ("/", "/intro", "/screen", "/debrief", f"/team/{slot.faction}"):
        page = client.get(path)
        assert page.status_code == 200, path
        cyrillic = [ch for ch in page.text if "а" <= ch.lower() <= "я" or ch in "ёЁ"]
        assert not cyrillic, f"{path}: осталась кириллица — {''.join(cyrillic[:60])}"


def test_team_screen_is_english():
    client = client_with("en")
    start(client)
    slot = live.current().journal.teams[0]
    client.post(f"/team/{slot.faction}/login", data={"code": slot.code}, follow_redirects=True)
    page = client.get(f"/team/{slot.faction}").text
    assert "Your briefing" in page
    assert "Submit orders" in page


def test_language_switch_sets_the_cookie():
    client = TestClient(create_app())
    client.get("/language/en", follow_redirects=False)
    assert client.cookies.get("sgame_lang") == "en"


def test_unknown_language_falls_back_to_russian():
    client = TestClient(create_app())
    client.get("/language/de", follow_redirects=False)
    assert client.cookies.get("sgame_lang") == "ru"


def test_engine_texts_follow_the_session_language():
    client = client_with("en")
    start(client)
    for slot in live.current().journal.teams:
        client.post(f"/team/{slot.faction}/login", data={"code": slot.code}, follow_redirects=True)
        client.post(f"/team/{slot.faction}/order",
                    data={"action": "invest", "target": ""}, follow_redirects=True)
        client.post(f"/team/{slot.faction}/submit", follow_redirects=True)
    client.post("/round/close", follow_redirects=True)
    page = client.get("/screen").text
    assert "invests in ports" in page
