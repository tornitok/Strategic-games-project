import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app
from tests.test_web_team import SCENARIO


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "scenarios" / "probe.yaml").write_text(SCENARIO, encoding="utf-8")
    live.reset()
    yield
    live.reset()


@pytest.fixture
def client():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    return client


def play(client, faction, action="build"):
    code = live.current().journal.slot(faction).code
    client.post(f"/team/{faction}/login", data={"code": code}, follow_redirects=True)
    client.post(f"/team/{faction}/order", data={"action": action, "target": ""}, follow_redirects=True)
    client.post(f"/team/{faction}/submit", follow_redirects=True)


def test_round_does_not_close_until_everyone_submitted(client):
    play(client, "a")
    client.post("/round/close", follow_redirects=True)
    assert live.current().journal.rounds == []
    assert live.state().round == 1


def test_closing_round_advances_state_and_writes_journal(client):
    play(client, "a")
    play(client, "b")
    client.post("/round/close", follow_redirects=True)
    session = live.current()
    assert len(session.journal.rounds) == 1
    assert live.state().round == 2
    assert session.drafts == {"a": [], "b": []}


def test_forced_close_records_pass_for_missing_team(client):
    play(client, "a")
    client.post("/round/close", data={"force": "1"}, follow_redirects=True)
    assert live.current().journal.rounds[0].orders["b"] == []


def test_undo_returns_to_previous_round(client):
    play(client, "a")
    play(client, "b")
    client.post("/round/close", follow_redirects=True)
    client.post("/round/undo", follow_redirects=True)
    assert live.state().round == 1
    assert live.current().journal.rounds == []


def test_projector_shows_public_news_after_round(client):
    play(client, "a")
    play(client, "b")
    client.post("/round/close", follow_redirects=True)
    page = client.get("/screen")
    assert "Стройка" in page.text
    assert "Напряжённость" in page.text


def test_debrief_lists_scores(client):
    play(client, "a")
    play(client, "b")
    client.post("/round/close", follow_redirects=True)
    page = client.get("/debrief")
    assert "Астория" in page.text
    assert "Итог" in page.text
