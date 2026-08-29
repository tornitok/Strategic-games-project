import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app

SCENARIO = """
schema_version: 1
meta:
  id: probe
  title: "Проба"
  rounds: 4
  action_points: 2
  intro: |
    ВВОДНАЯ О МИРЕ: залив, два берега, один пролив.
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 20 }
factions:
  - { id: a, title: "Астория", start: { budget: 50, intel: 10 }, briefing: "ТАЙНА АСТОРИИ" }
  - { id: b, title: "Борея", start: { budget: 50, intel: 90 }, briefing: "ТАЙНА БОРЕИ" }
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
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "probe", "seed": "11"}, follow_redirects=True)
    return client


def test_intro_shows_world_text(client):
    assert "ВВОДНАЯ О МИРЕ" in client.get("/intro").text


def test_intro_shows_rules_from_scenario(client):
    page = client.get("/intro").text
    assert "4" in page and "Раунд" in page
    assert "Очки действий" in page
    assert "Бюджет" in page


def test_intro_explains_what_tracks_mean(client):
    page = client.get("/intro").text
    assert "Разведка" in page
    assert "Напряжённость" in page


def test_intro_keeps_secrets(client):
    page = client.get("/intro").text
    assert "ТАЙНА" not in page
    for slot in live.current().journal.teams:
        assert slot.code not in page


def test_host_console_links_to_intro(client):
    assert "/intro" in client.get("/").text
