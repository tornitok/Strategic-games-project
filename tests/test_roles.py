"""Роли внутри команды: личные цели и голосование."""

import pytest

from sgame.core.scoring import role_score, score
from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.state import initial_state
from sgame.core.validate import validate_scenario
from sgame.core.voting import Proposal, tally

TEXT = """
schema_version: 1
meta: { id: t, title: "Т", rounds: 4, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 300 }
  army:   { title: "Армия", min: 0, max: 100 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 30 }
factions:
  - id: a
    title: "А"
    start: { budget: 100, army: 50 }
    briefing: "Общий брифинг стороны."
    goals: [ { id: team, title: "Командная цель", when: "self.budget > 50", score: 30 } ]
    roles:
      - id: president
        title: "Президент"
        weight: 2
        briefing: "Личное: удержаться."
        goals: [ { id: stay, title: "Остаться у власти", when: "self.budget >= 90", score: 25 } ]
      - id: defence
        title: "Министр обороны"
        weight: 1
        briefing: "Личное: армия."
        goals: [ { id: strong, title: "Армия не ниже 60", when: "self.army >= 60", score: 20 } ]
      - id: finance
        title: "Министр финансов"
        weight: 1
        briefing: "Личное: казна."
        goals: [ { id: rich, title: "Казна не ниже 120", when: "self.budget >= 120", score: 15 } ]
  - { id: b, title: "Б", start: { budget: 100, army: 50 }, briefing: "т",
      goals: [ { id: g, title: "Ц", when: "self.budget > 0", score: 5 } ] }
actions:
  - { id: build, title: "Стройка", news: "{actor} строит", effects: [ { self: budget, delta: "10" } ] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""


def spec_with_start(a_budget=100, a_army=50):
    return parse_scenario(
        TEXT.replace("start: { budget: 100, army: 50 }",
                     f"start: {{ budget: {a_budget}, army: {a_army} }}")
    )


SPEC = spec_with_start()


def test_roles_are_read_from_the_scenario():
    faction = SPEC.faction("a")
    assert [r.id for r in faction.roles] == ["president", "defence", "finance"]
    assert faction.role("president").weight == 2


def test_faction_without_roles_still_works():
    assert SPEC.faction("b").roles == []


def test_personal_score_counts_only_own_goals():
    state = initial_state(SPEC)
    total, breakdown = role_score(SPEC, state, "a", "president")
    assert total == 25
    assert [title for title, _ in breakdown] == ["Остаться у власти"]


def test_personal_goals_are_separate_from_the_team_score():
    state = initial_state(SPEC)
    team_total, team_breakdown = score(SPEC, state, "a")
    assert "Остаться у власти" not in [t for t, _ in team_breakdown]
    assert team_total > 0


def test_unmet_personal_goal_scores_nothing():
    state = initial_state(spec_with_start(a_budget=100, a_army=10))
    total, _ = role_score(SPEC, state, "a", "defence")
    assert total == 0


def test_proposal_passes_with_more_than_half_the_weight():
    roles = SPEC.faction("a").roles
    proposal = Proposal(id="p1", action="build", target=None, author="president",
                        votes={"president": True, "defence": True})
    assert tally(roles, proposal).passed is True


def test_two_junior_ministers_cannot_outvote_the_president():
    """Следствие весов 2/1/1: без президента ничего не проходит.

    Оно же обратное: одного президента тоже мало — ему нужен союзник.
    Сценарий, где нужен коллегиальный орган, задаёт равные веса.
    """
    roles = SPEC.faction("a").roles
    juniors = Proposal(id="p", action="build", target=None, author="defence",
                       votes={"defence": True, "finance": True})
    alone = Proposal(id="p", action="build", target=None, author="president",
                     votes={"president": True})
    assert tally(roles, juniors).passed is False
    assert tally(roles, alone).passed is False


def test_abstaining_counts_against():
    """Молчание не должно проталкивать решения."""
    roles = SPEC.faction("a").roles
    proposal = Proposal(id="p1", action="build", target=None, author="defence",
                        votes={"defence": True})
    result = tally(roles, proposal)
    assert result.passed is False
    assert result.needed == 3 and result.given == 1


def test_weight_makes_the_president_heavier():
    roles = SPEC.faction("a").roles
    with_president = Proposal(id="p", action="build", target=None, author="president",
                              votes={"president": True, "defence": True})
    without = Proposal(id="p", action="build", target=None, author="defence",
                       votes={"defence": True, "finance": True})
    assert tally(roles, with_president).given == 3
    assert tally(roles, without).given == 2


def test_validator_requires_unique_role_ids():
    text = TEXT.replace('      - id: finance', '      - id: defence')
    spec = parse_scenario(text)
    problems = validate_scenario(spec, scenario_lines(text))
    assert any("defence" in p.message and "дважды" in p.message for p in problems)


def test_validator_wants_roles_everywhere_or_nowhere():
    problems = validate_scenario(SPEC, scenario_lines(TEXT))
    assert any("роли" in p.message.lower() for p in problems)
