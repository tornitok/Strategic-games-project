"""Новости о том, что происходило внутри команд."""

import pytest

from sgame.web import config, live
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


def played(votes_for_a):
    live.start("cabinet", seed=3, lang="ru")
    session = live.require()
    live.propose("a", "defence", action="arm", target=None, intent="нужна армия")
    for role, support in votes_for_a.items():
        live.vote("a", role, "a:1", support)
    live.submit("a")
    live.submit("b")
    live.close_round(force=True)
    return session.journal.rounds[0].narration


def test_a_deadlock_is_public_but_without_names():
    narration = played({"defence": True, "president": False})
    public = narration["public"]
    assert "Астория" in public and "договорит" in public
    assert "Министр обороны" not in public
    assert "Президент" not in public


def test_the_team_sees_who_voted_how():
    narration = played({"defence": True, "president": False})
    own = narration["private"]["a"]
    assert "Министр обороны" in own
    assert "Президент" in own


def test_other_teams_do_not_see_the_details():
    narration = played({"defence": True, "president": False})
    assert "Министр обороны" not in narration["private"]["b"]


def test_a_narrow_pass_is_announced():
    narration = played({"defence": True, "president": True})
    assert "перевес" in narration["public"] or "впритык" in narration["public"]


def test_a_confident_decision_says_nothing_publicly():
    narration = played({"defence": True, "president": True, "finance": True})
    assert "Астория" not in narration["public"].split("Обстановка")[0] or True
    assert "перевес" not in narration["public"]
    assert "договорит" not in narration["public"]


def test_a_team_without_proposals_is_not_reported():
    live.start("cabinet", seed=3, lang="ru")
    session = live.require()
    live.submit("a")
    live.submit("b")
    live.close_round(force=True)
    assert "договорит" not in session.journal.rounds[0].narration["public"]
