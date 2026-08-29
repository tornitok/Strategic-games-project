"""Боты для прогона сценариев: три линии поведения плюс осторожная."""

from sgame.bots import ROLES, choose_orders, power_of, simulate
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state

TEXT = """
schema_version: 1
meta: { id: t, title: "Т", rounds: 4, action_points: 2 }
power: "self.forces * 1.0 + self.budget * 0.1"
tracks:
  budget: { title: "Бюджет", min: 0, max: 300 }
  forces: { title: "Силы", min: 0, max: 100 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 30 }
factions:
  - { id: big,    title: "Большой",  start: { budget: 200, forces: 90 } }
  - { id: middle, title: "Средний",  start: { budget: 100, forces: 50 } }
  - { id: small,  title: "Малый",    start: { budget: 60,  forces: 20 } }
actions:
  - { id: strike, title: "Удар", news: "{actor} бьёт", target: faction, stance: hostile,
      cost: { budget: 10 }, effects: [ { target: budget, delta: "-10" } ] }
  - { id: help, title: "Помощь", news: "{actor} помогает", target: faction, stance: friendly,
      cost: { budget: 15 }, effects: [ { target: budget, delta: "12" } ] }
  - { id: build, title: "Стройка", news: "{actor} строит", stance: neutral,
      cost: { budget: 5 }, effects: [ { self: budget, delta: "8" } ] }
  - { id: unaffordable, title: "Неподъёмное", news: "{actor} мечтает", stance: neutral,
      cost: { budget: 999 }, effects: [] }
rumours:
  chance: 0.2
  templates: [ "Говорят, это {subject}" ]
events:
  - { id: e, chance: 0.2, title: "Случай", news: "Случилось", effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget * 0.1 + self.forces" }
"""

SPEC = parse_scenario(TEXT)


def actions_of(orders):
    return [(o.action, o.target) for o in orders]


def test_power_uses_the_scenario_formula():
    state = initial_state(SPEC)
    assert power_of(SPEC, state, "big") > power_of(SPEC, state, "middle")
    assert power_of(SPEC, state, "middle") > power_of(SPEC, state, "small")


def test_bot_never_orders_an_unavailable_action():
    state = initial_state(SPEC)
    for role in ROLES:
        orders = choose_orders(SPEC, state, "small", role, seed=1, round_no=1)
        assert all(action != "unaffordable" for action, _ in actions_of(orders))


def test_bot_respects_action_points():
    state = initial_state(SPEC)
    for role in ROLES:
        orders = choose_orders(SPEC, state, "big", role, seed=1, round_no=1)
        assert len(orders) <= SPEC.meta.action_points


def test_opposition_strikes_the_strongest_rival():
    state = initial_state(SPEC)
    orders = choose_orders(SPEC, state, "middle", "opposition", seed=1, round_no=1)
    assert ("strike", "big") in actions_of(orders)


def test_following_helps_the_strongest():
    state = initial_state(SPEC)
    orders = choose_orders(SPEC, state, "middle", "following", seed=1, round_no=1)
    assert ("help", "big") in actions_of(orders)


def test_balancing_hits_the_leader_and_helps_the_weakest():
    state = initial_state(SPEC)
    orders = choose_orders(SPEC, state, "middle", "balancing", seed=1, round_no=1)
    pairs = actions_of(orders)
    assert ("strike", "big") in pairs
    assert ("help", "small") in pairs


def test_cautious_bot_avoids_hostility():
    state = initial_state(SPEC)
    orders = choose_orders(SPEC, state, "middle", "cautious", seed=1, round_no=1)
    assert all(action != "strike" for action, _ in actions_of(orders))


def test_choices_are_reproducible():
    state = initial_state(SPEC)
    first = choose_orders(SPEC, state, "middle", "opposition", seed=4, round_no=2)
    second = choose_orders(SPEC, state, "middle", "opposition", seed=4, round_no=2)
    assert actions_of(first) == actions_of(second)


def test_simulation_runs_a_whole_game():
    result = simulate(SPEC, {"big": "opposition", "middle": "balancing", "small": "following"}, seed=3)
    assert result.state.finished is True
    assert len(result.rounds) == SPEC.meta.rounds
    assert set(result.scores) == {"big", "middle", "small"}


def test_simulation_is_reproducible():
    roles = {"big": "opposition", "middle": "balancing", "small": "following"}
    assert simulate(SPEC, roles, seed=8).scores == simulate(SPEC, roles, seed=8).scores


def test_different_seeds_give_different_games():
    """На настоящем сценарии: в тестовом всего четыре действия, и совпадение
    партий при разных ключах там закономерно, а не признак поломки."""
    from sgame.session.paths import builtin_scenarios

    spec = parse_scenario(builtin_scenarios()["meridian"])
    roles = dict(
        zip([f.id for f in spec.factions], ["opposition", "balancing", "following", "cautious"])
    )
    outcomes = {
        tuple(sorted(simulate(spec, roles, seed=seed).scores.items())) for seed in range(6)
    }
    assert len(outcomes) > 1
