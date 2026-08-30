"""Боты в роли должностей: предлагают своё и голосуют по своим целям."""

from sgame.bots import cabinet_round, role_gain
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state

TEXT = """
schema_version: 1
meta: { id: c, title: "К", rounds: 4, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 300 }
  army:   { title: "Армия", min: 0, max: 100 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 38 }
factions:
  - id: a
    title: "А"
    start: { budget: 100, army: 40 }
    briefing: "т"
    goals: [ { id: t, title: "Командная", when: "self.budget > 0", score: 10 } ]
    roles:
      - { id: hawk, title: "Военный", weight: 1, briefing: "т",
          goals: [ { id: g, title: "Армия", when: "self.army >= 60", score: 30 } ] }
      - { id: purse, title: "Финансист", weight: 1, briefing: "т",
          goals: [ { id: g, title: "Казна", when: "self.budget >= 120", score: 30 } ] }
      - { id: head, title: "Глава", weight: 2, briefing: "т",
          goals: [ { id: g, title: "Тишина", when: "world.tension <= 30", score: 30 } ] }
          # при старте 38 разрядка (−10) доводит до 28 и цель выполняется
  - id: b
    title: "Б"
    start: { budget: 100, army: 40 }
    briefing: "т"
    goals: [ { id: t, title: "Командная", when: "self.budget > 0", score: 10 } ]
    roles:
      - { id: head, title: "Глава", weight: 1, briefing: "т",
          goals: [ { id: g, title: "Казна", when: "self.budget > 0", score: 5 } ] }
actions:
  - { id: arm, title: "Вооружение", news: "{actor} вооружается", cost: { budget: 30 },
      effects: [ { self: army, delta: "25" }, { world: tension, delta: "10" } ] }
  - { id: earn, title: "Вложения", news: "{actor} вкладывается",
      effects: [ { self: budget, delta: "25" } ] }
  - { id: calm, title: "Разрядка", news: "{actor} снижает накал",
      effects: [ { world: tension, delta: "-10" } ] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""

SPEC = parse_scenario(TEXT)


def test_a_role_values_what_serves_its_own_goal():
    state = initial_state(SPEC)
    arm = SPEC.action("arm")
    assert role_gain(SPEC, state, "a", "hawk", arm, None) > 0
    assert role_gain(SPEC, state, "a", "purse", arm, None) < 0


def test_each_role_proposes_something_of_its_own():
    state = initial_state(SPEC)
    proposals, _ = cabinet_round(SPEC, state, "a", seed=1, round_no=1)
    by_author = {p.author: p.action for p in proposals}
    assert by_author["hawk"] == "arm"
    assert by_author["purse"] == "earn"
    assert by_author["head"] == "calm"


def test_roles_vote_by_their_own_interest():
    state = initial_state(SPEC)
    proposals, _ = cabinet_round(SPEC, state, "a", seed=1, round_no=1)
    arming = next(p for p in proposals if p.action == "arm")
    assert arming.votes["hawk"] is True
    assert arming.votes["purse"] is False


def test_orders_come_only_from_what_the_cabinet_carried():
    state = initial_state(SPEC)
    proposals, orders = cabinet_round(SPEC, state, "a", seed=1, round_no=1)
    from sgame.core.voting import tally

    carried = {p.action for p in proposals if tally(SPEC.faction("a").roles, p).passed}
    assert {o.action for o in orders} == carried


def test_a_lone_role_still_needs_the_majority():
    state = initial_state(SPEC)
    _, orders = cabinet_round(SPEC, state, "b", seed=1, round_no=1)
    assert len(orders) <= SPEC.meta.action_points


def test_a_role_opposes_what_eats_its_own_figure():
    """Цели пороговые: пока порог не перейдён, личная выгода нулевая.

    Без учёта того, что действие проедает твой показатель, кабинет соглашается
    со всем подряд, и голосование перестаёт что-либо значить.
    """
    state = initial_state(SPEC)
    arm = SPEC.action("arm")  # стоит 30 бюджета — это деньги финансиста
    assert role_gain(SPEC, state, "a", "purse", arm, None) < 0


def test_a_role_supports_what_feeds_its_own_figure():
    state = initial_state(SPEC)
    earn = SPEC.action("earn")
    assert role_gain(SPEC, state, "a", "purse", earn, None) > 0
