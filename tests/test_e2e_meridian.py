"""Полная партия эталонной игры через интерфейс.

Критерий готовности этапа 1: 4 команды, 8 раундов, без ошибок — проверяется
именно через экраны, а не через пересчёт журнала.
"""

import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app

PLAN = {"astoria": "invest", "borea": "propaganda", "caldera": "invest", "delta": "intel_work"}


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    live.reset()
    yield
    live.reset()


def test_full_meridian_game_through_the_interface():
    client = TestClient(create_app())
    client.post(
        "/session/new", data={"scenario": "meridian", "seed": "20260901"}, follow_redirects=True
    )
    session = live.current()

    for round_no in range(1, 9):
        for slot in session.journal.teams:
            faction = slot.faction
            page = client.post(
                f"/team/{faction}/login", data={"code": slot.code}, follow_redirects=True
            )
            assert "Ваш брифинг" in page.text
            client.post(
                f"/team/{faction}/order",
                data={"action": PLAN[faction], "target": "", "intent": f"раунд {round_no}"},
                follow_redirects=True,
            )
            client.post(f"/team/{faction}/submit", follow_redirects=True)
        assert client.post("/round/close", follow_redirects=True).status_code == 200
        assert client.get("/screen").status_code == 200

    state = live.state()
    assert state.finished is True
    assert len(session.journal.rounds) == 8

    debrief = client.get("/debrief")
    for title in ("Астория", "Борея", "Кальдера", "Дельта"):
        assert title in debrief.text
    assert "раунд 8" in debrief.text
