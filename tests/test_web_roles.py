"""Экраны ролей: свой вход, свои тайны, голосование и понятное состояние."""

import pytest
from fastapi.testclient import TestClient

from sgame.web import config, live
from sgame.web.app import create_app
from tests.test_live_roles import SCENARIO


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    (tmp_path / "scenarios").mkdir()
    (tmp_path / "scenarios" / "cabinet.yaml").write_text(SCENARIO, encoding="utf-8")
    config.NETWORK = False
    live.reset()
    yield
    live.reset()
    config.NETWORK = False


@pytest.fixture
def client():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "cabinet", "seed": "3"}, follow_redirects=True)
    return client


def code_of(faction, role):
    return live.current().journal.slot(faction).role_code(role)


def enter(client, faction, role):
    return client.post(f"/team/{faction}/{role}/login",
                       data={"code": code_of(faction, role)}, follow_redirects=True)


def test_team_page_offers_the_roles():
    client = TestClient(create_app())
    client.post("/session/new", data={"scenario": "cabinet", "seed": "3"}, follow_redirects=True)
    page = client.get("/team/a").text
    assert "Президент" in page and "Министр обороны" in page
    assert "Личное президента" not in page


def test_role_sees_its_own_briefing(client):
    enter(client, "a", "president")
    page = client.get("/team/a/president").text
    assert "Личное президента" in page
    assert "Общий брифинг Астории" in page


def test_role_never_sees_a_colleague_secret(client):
    enter(client, "a", "president")
    page = client.get("/team/a/president").text
    assert "Личное обороны" not in page
    assert "Личное финансов" not in page


def test_wrong_role_code_is_refused(client):
    page = client.post("/team/a/president/login", data={"code": "000000"}, follow_redirects=True)
    assert "Личное президента" not in page.text


def test_a_role_cannot_use_another_role_code(client):
    page = client.post("/team/a/president/login",
                       data={"code": code_of("a", "defence")}, follow_redirects=True)
    assert "Личное президента" not in page.text


def test_proposal_is_visible_to_the_whole_team(client):
    enter(client, "a", "defence")
    client.post("/team/a/defence/propose",
                data={"action": "arm", "target": "", "intent": "нужна армия"},
                follow_redirects=True)
    other = TestClient(create_app())
    other.post(f"/team/a/president/login", data={"code": code_of("a", "president")},
               follow_redirects=True)
    page = other.get("/team/a/president").text
    assert "Вооружение" in page
    assert "Министр обороны" in page


def test_voting_through_the_screen_changes_the_tally(client):
    enter(client, "a", "president")
    client.post("/team/a/president/propose",
                data={"action": "build", "target": "", "intent": ""}, follow_redirects=True)
    client.post("/team/a/president/vote", data={"proposal": "a:1", "support": "1"},
                follow_redirects=True)
    assert live.tally_of("a", "a:1").given == 2


def test_screen_says_what_is_expected_of_you(client):
    enter(client, "a", "defence")
    client.post("/team/a/defence/propose",
                data={"action": "arm", "target": "", "intent": ""}, follow_redirects=True)
    page = client.get("/team/a/defence").text
    assert "ваш голос" in page.lower()
    assert "нужно" in page.lower() or "не хватает" in page.lower()


def test_turn_goes_only_when_every_role_is_ready(client):
    enter(client, "a", "president")
    client.post("/team/a/president/ready", follow_redirects=True)
    assert "a" not in live.current().submitted
    for role in ("defence", "finance"):
        enter(client, "a", role)
        client.post(f"/team/a/{role}/ready", follow_redirects=True)
    assert "a" in live.current().submitted


def test_ready_screen_shows_who_is_still_deciding(client):
    enter(client, "a", "president")
    client.post("/team/a/president/ready", follow_redirects=True)
    page = client.get("/team/a/president").text
    assert "Министр обороны" in page


def test_host_console_lists_role_codes(client):
    page = client.get("/").text
    for role in ("Президент", "Министр обороны", "Министр финансов"):
        assert role in page
    for slot in live.current().journal.teams:
        for role in slot.roles:
            assert role.code in page


def test_debrief_shows_personal_scores(client):
    for faction in ("a", "b"):
        for role in [r.role for r in live.current().journal.slot(faction).roles]:
            enter(client, faction, role)
            client.post(f"/team/{faction}/{role}/ready", follow_redirects=True)
    client.post("/round/close", follow_redirects=True)
    page = client.get("/debrief").text
    assert "Президент" in page
    assert "Удержаться" in page or "Личный счёт" in page


def test_debrief_shows_the_voting_record(client):
    enter(client, "a", "defence")
    client.post("/team/a/defence/propose",
                data={"action": "arm", "target": "", "intent": "нужна армия"},
                follow_redirects=True)
    client.post("/team/a/defence/vote", data={"proposal": "a:1", "support": "1"},
                follow_redirects=True)
    for faction in ("a", "b"):
        for role in [r.role for r in live.current().journal.slot(faction).roles]:
            enter(client, faction, role)
            client.post(f"/team/{faction}/{role}/ready", follow_redirects=True)
    client.post("/round/close", follow_redirects=True)
    page = client.get("/debrief").text
    assert "Вооружение" in page
    assert "Министр обороны" in page
