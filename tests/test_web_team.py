import pytest
from fastapi.testclient import TestClient

from sgame.web import live
from sgame.web.app import create_app

SCENARIO = """
schema_version: 1
meta: { id: probe, title: "Проба", rounds: 2, action_points: 2 }
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
  - { id: costly, title: "Неподъёмное", cost: { budget: 999 }, effects: [] }
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


def code_for(faction):
    return live.current().journal.slot(faction).code


def login(client, faction):
    client.post(f"/team/{faction}/login", data={"code": code_for(faction)}, follow_redirects=True)


def test_wrong_code_does_not_open_screen(client):
    page = client.post("/team/a/login", data={"code": "0000"}, follow_redirects=True)
    assert "ТАЙНА АСТОРИИ" not in page.text
    assert "код" in page.text.lower()


def test_correct_code_opens_own_briefing(client):
    login(client, "a")
    page = client.get("/team/a")
    assert "ТАЙНА АСТОРИИ" in page.text


def test_unavailable_action_shows_reason(client):
    login(client, "a")
    page = client.get("/team/a")
    assert "Неподъёмное" in page.text
    assert "хватает" in page.text


def test_adding_order_updates_draft_and_points(client):
    login(client, "a")
    client.post("/team/a/order", data={"action": "build", "target": ""}, follow_redirects=True)
    assert [order.action for order in live.current().drafts["a"]] == ["build"]
    assert "Очки действий: 1 из 2" in client.get("/team/a").text


def test_removing_order_restores_points(client):
    login(client, "a")
    client.post("/team/a/order", data={"action": "build", "target": ""}, follow_redirects=True)
    client.post("/team/a/order/remove", data={"index": "0"}, follow_redirects=True)
    assert live.current().drafts["a"] == []


def test_intent_text_is_kept_with_order(client):
    login(client, "a")
    client.post(
        "/team/a/order",
        data={"action": "build", "target": "", "intent": "усиливаем тыл"},
        follow_redirects=True,
    )
    assert live.current().drafts["a"][0].intent == "усиливаем тыл"


def test_submit_locks_screen_and_clears_cookie(client):
    login(client, "a")
    client.post("/team/a/submit", follow_redirects=True)
    assert "a" in live.current().submitted
    page = client.get("/team/a")
    assert "ТАЙНА АСТОРИИ" not in page.text


def test_screen_has_hide_control(client):
    login(client, "a")
    page = client.get("/team/a")
    assert 'id="cover"' in page.text
    assert "/static/hide.js" in page.text
