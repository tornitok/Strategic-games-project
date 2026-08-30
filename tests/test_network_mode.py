"""Сетевой режим: команды заходят со своих телефонов."""

import pytest
from fastapi.testclient import TestClient

from sgame.web import config, live
from sgame.web.app import create_app, local_address, serve_host


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    live.reset()
    config.NETWORK = False
    yield
    live.reset()
    config.NETWORK = False


def test_localhost_by_default():
    assert serve_host(network=False) == "127.0.0.1"


def test_network_mode_listens_on_every_interface():
    assert serve_host(network=True) == "0.0.0.0"


def test_local_address_is_a_reachable_ip():
    address = local_address()
    assert address.count(".") == 3
    assert not address.startswith("127.")


def test_codes_are_short_and_numeric_on_one_machine():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "meridian", "seed": "1"}, follow_redirects=True)
    for slot in live.current().journal.teams:
        assert len(slot.code) == 4 and slot.code.isdigit()


def test_codes_are_stronger_in_network_mode():
    """В аудиторской сети четырёхзначный код перебирается скриптом за секунды."""
    config.NETWORK = True
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "meridian", "seed": "1"}, follow_redirects=True)
    for slot in live.current().journal.teams:
        assert len(slot.code) == 6
        assert any(ch.isalpha() for ch in slot.code)


def test_wrong_codes_are_throttled():
    config.NETWORK = True
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "meridian", "seed": "1"}, follow_redirects=True)
    faction = live.current().journal.teams[0].faction
    for _ in range(3):
        client.post(f"/team/{faction}/login", data={"code": "000000"}, follow_redirects=True)
    page = client.post(f"/team/{faction}/login", data={"code": "000000"}, follow_redirects=True)
    assert "подождите" in page.text.lower() or "wait" in page.text.lower()


def test_correct_code_still_works_after_a_single_mistake():
    config.NETWORK = True
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "meridian", "seed": "1"}, follow_redirects=True)
    slot = live.current().journal.teams[0]
    client.post(f"/team/{slot.faction}/login", data={"code": "zzzzzz"}, follow_redirects=True)
    client.post(f"/team/{slot.faction}/login", data={"code": slot.code}, follow_redirects=True)
    assert "Ваш брифинг" in client.get(f"/team/{slot.faction}").text


def test_qr_code_is_served_for_a_team():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "meridian", "seed": "1"}, follow_redirects=True)
    faction = live.current().journal.teams[0].faction
    answer = client.get(f"/qr/{faction}.svg")
    assert answer.status_code == 200
    assert answer.headers["content-type"].startswith("image/svg")
    # Для <img> нужен самостоятельный документ: фрагмент для встраивания в HTML
    # браузер не покажет, а «<svg» в ответе есть и там, и там.
    assert "xmlns" in answer.text
    assert answer.text.lstrip().startswith("<?xml") or "xmlns=" in answer.text[:200]


def test_host_console_shows_addresses_in_network_mode():
    config.NETWORK = True
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "meridian", "seed": "1"}, follow_redirects=True)
    page = client.get("/").text
    assert local_address() in page
    assert "/qr/" in page


def test_host_console_hides_addresses_on_one_machine():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "meridian", "seed": "1"}, follow_redirects=True)
    assert "/qr/" not in client.get("/").text
