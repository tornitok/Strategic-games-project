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
  - id: c
    title: "В"
    start: { budget: 220, army: 40 }
    briefing: "т"
    goals: [ { id: t, title: "Командная", when: "self.budget > 0", score: 10 } ]
    roles:
      - { id: head, title: "Глава", weight: 1, briefing: "т",
          goals: [ { id: g, title: "Казна", when: "self.budget > 0", score: 5 } ] }
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
  - { id: press, title: "Давление", news: "{actor} давит на {target}", target: faction,
      stance: hostile, effects: [ { target: budget, delta: "-20" }, { self: army, delta: "4" } ] }
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


# Военному оставлены полномочия только на разрядку — то, чего он сам никогда
# бы не выбрал. Если он всё равно вносит вооружение, полномочия не работают.
POWERS = TEXT.replace(
    '- { id: hawk, title: "Военный", weight: 1, briefing: "т",',
    '- { id: hawk, title: "Военный", weight: 1, briefing: "т", actions: [ calm ],',
)

# Две должности с одной и той же целью выберут один и тот же приказ.
DUPES = TEXT.replace(
    '- { id: head, title: "Глава", weight: 2, briefing: "т",',
    '- { id: purse2, title: "Казначей", weight: 1, briefing: "т",\n'
    '          goals: [ { id: g, title: "Казна", when: "self.budget >= 120", score: 30 } ] }\n'
    '      - { id: head, title: "Глава", weight: 2, briefing: "т",',
    1,
)


def test_a_role_proposes_only_what_it_is_entitled_to():
    """Иначе должности отличаются только целями, а вносить могут что угодно."""
    spec = parse_scenario(POWERS)
    proposals, _ = cabinet_round(spec, initial_state(spec), "a", seed=1, round_no=1)
    assert [p.action for p in proposals if p.author == "hawk"] in ([], ["calm"])


def test_the_cabinet_does_not_vote_on_the_same_order_twice():
    """Движок исполнит такой приказ один раз, второй голос был бы потрачен зря."""
    spec = parse_scenario(DUPES)
    proposals, orders = cabinet_round(spec, initial_state(spec), "a", seed=1, round_no=1)
    seen = [(p.action, p.target) for p in proposals]
    assert len(seen) == len(set(seen))
    made = [(o.action, o.target) for o in orders]
    assert len(made) == len(set(made))


def test_a_hostile_order_goes_to_the_strongest_rival():
    """Цель «первый в списке» означала, что все ультиматумы летят в одну сторону.

    «В» сильнее «Б» и стоит в списке позже — значит выбор именно её и есть выбор.
    """
    spec = parse_scenario(
        TEXT.replace(
            '- { id: hawk, title: "Военный", weight: 1, briefing: "т",',
            '- { id: hawk, title: "Военный", weight: 1, briefing: "т", actions: [ press ],',
        )
    )
    proposals, _ = cabinet_round(spec, initial_state(spec), "a", seed=1, round_no=1)
    press = [p for p in proposals if p.action == "press"]
    assert press and all(p.target == "c" for p in press)


# Второй способ пополнить казну, чуть менее выгодный, чем первый.
CHOICES = TEXT.replace(
    '  - { id: calm, title: "Разрядка", news: "{actor} снижает накал",',
    '  - { id: loan, title: "Заём", news: "{actor} занимает",\n'
    '      effects: [ { self: budget, delta: "20" } ] }\n'
    '  - { id: calm, title: "Разрядка", news: "{actor} снижает накал",',
    1,
)


def test_a_role_does_not_repeat_the_same_order_every_round():
    """Строгий argmax давал одну и ту же партию раз за разом.

    Живой игрок не обращается к нации шесть раундов подряд.
    """
    spec = parse_scenario(CHOICES)
    state = initial_state(spec)
    chosen = set()
    for round_no in range(1, 9):
        proposals, _ = cabinet_round(spec, state, "a", seed=7, round_no=round_no)
        chosen |= {p.action for p in proposals if p.author == "purse"}
    assert {"earn", "loan"} <= chosen


def test_a_role_still_refuses_what_hurts_it():
    """Разнообразие не должно превращаться в случайные приказы себе в убыток."""
    spec = parse_scenario(CHOICES)
    state = initial_state(spec)
    for round_no in range(1, 9):
        proposals, _ = cabinet_round(spec, state, "a", seed=7, round_no=round_no)
        assert "arm" not in {p.action for p in proposals if p.author == "purse"}
