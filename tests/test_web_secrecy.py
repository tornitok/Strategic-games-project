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


def test_team_screen_never_shows_foreign_briefing(client):
    slot = live.current().journal.slot("a")
    client.post("/team/a/login", data={"code": slot.code}, follow_redirects=True)
    page = client.get("/team/a")
    assert "ТАЙНА БОРЕИ" not in page.text


def test_team_screen_never_shows_foreign_private_track(client):
    slot = live.current().journal.slot("a")
    client.post("/team/a/login", data={"code": slot.code}, follow_redirects=True)
    page = client.get("/team/a")
    assert "90" not in page.text


def test_team_screen_never_shows_foreign_code(client):
    slot_a = live.current().journal.slot("a")
    slot_b = live.current().journal.slot("b")
    client.post("/team/a/login", data={"code": slot_a.code}, follow_redirects=True)
    assert slot_b.code not in client.get("/team/a").text


def test_projector_shows_no_briefings_and_no_codes(client):
    page = client.get("/screen")
    assert "ТАЙНА" not in page.text
    for slot in live.current().journal.teams:
        assert slot.code not in page.text
