"""Живая партия с ролями: предложения, голоса, сдача хода."""

import pytest

from sgame.web import config, live

SCENARIO = """
schema_version: 1
meta: { id: cabinet, title: "Кабинет", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 300 }
  army:   { title: "Армия", min: 0, max: 100 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 30 }
factions:
  - id: a
    title: "Астория"
    start: { budget: 100, army: 50 }
    briefing: "Общий брифинг Астории."
    goals: [ { id: t, title: "Командная", when: "self.budget > 0", score: 10 } ]
    roles:
      - { id: president, title: "Президент", weight: 2, briefing: "Личное президента.",
          goals: [ { id: stay, title: "Удержаться", when: "self.budget >= 90", score: 25 } ] }
      - { id: defence, title: "Министр обороны", weight: 1, briefing: "Личное обороны.",
          goals: [ { id: army, title: "Армия", when: "self.army >= 60", score: 20 } ] }
      - { id: finance, title: "Министр финансов", weight: 1, briefing: "Личное финансов.",
          goals: [ { id: rich, title: "Казна", when: "self.budget >= 130", score: 15 } ] }
  - id: b
    title: "Борея"
    start: { budget: 100, army: 50 }
    briefing: "Общий брифинг Бореи."
    goals: [ { id: t2, title: "Командная", when: "self.budget > 0", score: 10 } ]
    roles:
      - { id: president, title: "Президент", weight: 2, briefing: "Личное.",
          goals: [ { id: s, title: "Ц", when: "self.budget > 0", score: 5 } ] }
      - { id: defence, title: "Министр обороны", weight: 1, briefing: "Личное.",
          goals: [ { id: a2, title: "Ц", when: "self.army > 0", score: 5 } ] }
actions:
  - { id: build, title: "Стройка", news: "{actor} строит", effects: [ { self: budget, delta: "12" } ] }
  - { id: arm, title: "Вооружение", news: "{actor} вооружается", effects: [ { self: army, delta: "15" } ] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""


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


def started():
    live.start("cabinet", seed=3, lang="ru")
    return live.require()


def test_every_role_gets_its_own_code():
    session = started()
    slot = session.journal.slot("a")
    assert {r.role for r in slot.roles} == {"president", "defence", "finance"}
    codes = [r.code for r in slot.roles]
    assert len(set(codes)) == 3


def test_proposal_appears_for_the_whole_team():
    session = started()
    live.propose("a", "president", action="build", target=None, intent="строим")
    assert len(session.proposals["a"]) == 1
    assert session.proposals["a"][0].author == "president"


def test_vote_is_counted_by_weight():
    started()
    live.propose("a", "defence", action="arm", target=None, intent="")
    live.vote("a", "defence", "a:1", True)
    assert live.tally_of("a", "a:1").passed is False
    live.vote("a", "president", "a:1", True)
    assert live.tally_of("a", "a:1").passed is True


def test_a_role_can_change_its_vote_before_the_round_closes():
    started()
    live.propose("a", "president", action="build", target=None, intent="")
    live.vote("a", "president", "a:1", True)
    live.vote("a", "president", "a:1", False)
    assert live.tally_of("a", "a:1").given == 0


def test_only_passed_proposals_become_orders():
    session = started()
    live.propose("a", "president", action="build", target=None, intent="")
    live.propose("a", "defence", action="arm", target=None, intent="")
    live.vote("a", "president", "a:1", True)
    live.vote("a", "defence", "a:1", True)
    live.vote("a", "defence", "a:2", True)
    live.submit("a")
    for slot in session.journal.teams:
        if slot.faction != "a":
            live.submit(slot.faction)
    live.close_round(force=True)
    record = session.journal.rounds[0]
    assert [o.action for o in record.orders["a"]] == ["build"]
    assert [(p.id, p.passed) for p in record.proposals] == [("a:1", True), ("a:2", False)]


def test_a_split_cabinet_passes_nothing():
    """Паралич — законный исход, а не сбой."""
    session = started()
    live.propose("a", "defence", action="arm", target=None, intent="")
    live.vote("a", "defence", "a:1", True)
    live.vote("a", "president", "a:1", False)
    live.submit("a")
    live.submit("b")
    live.close_round(force=True)
    assert session.journal.rounds[0].orders["a"] == []


def test_action_points_limit_what_gets_through():
    session = started()
    for _ in range(3):
        live.propose("a", "president", action="build", target=None, intent="")
    for number in (1, 2, 3):
        live.vote("a", "president", f"a:{number}", True)
        live.vote("a", "defence", f"a:{number}", True)
    live.submit("a")
    live.submit("b")
    live.close_round(force=True)
    assert len(session.journal.rounds[0].orders["a"]) == 2


def test_votes_reset_between_rounds():
    session = started()
    live.propose("a", "president", action="build", target=None, intent="")
    live.vote("a", "president", "a:1", True)
    live.vote("a", "defence", "a:1", True)
    live.submit("a")
    live.submit("b")
    live.close_round(force=True)
    assert session.proposals["a"] == []
