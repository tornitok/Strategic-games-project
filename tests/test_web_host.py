import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app

SCENARIO = """
schema_version: 1
meta: { id: probe, title: "Проба", rounds: 2, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 20 }
factions:
  - { id: a, title: "Астория", start: { budget: 50 } }
  - { id: b, title: "Борея", start: { budget: 50 } }
actions:
  - { id: build, title: "Стройка", cost: { budget: 10 }, effects: [ { self: budget, delta: "2" } ] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""


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
    return TestClient(create_app())


def test_start_page_lists_scenarios(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Проба" in page.text


def test_creating_session_makes_a_team_per_faction(client):
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    session = live.current()
    assert [slot.faction for slot in session.journal.teams] == ["a", "b"]
    assert all(len(slot.code) == 4 for slot in session.journal.teams)


def test_host_console_shows_who_has_not_submitted(client):
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    page = client.get("/")
    assert "Астория" in page.text
    assert "не сдала" in page.text


def test_session_file_is_written(client, tmp_path):
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    assert list((tmp_path / "sessions").glob("*.json"))
