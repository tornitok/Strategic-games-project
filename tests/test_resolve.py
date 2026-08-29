from sgame.core.orders import Order
from sgame.core.resolve import resolve
from sgame.core.scoring import score
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 2, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 200 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 50 }
factions:
  - id: a
    title: "А"
    start: { budget: 100 }
    goals: [ { id: calm, title: "Мир", when: "world.tension < 55", score: 10 } ]
  - { id: b, title: "Б", start: { budget: 100 } }
actions:
  - { id: escalate, title: "Эскалация", effects: [ { world: tension, delta: "10" } ] }
world_dynamics:
  - { all: budget, delta: "5" }
events:
  - id: shock
    when: "world.tension > 55"
    title: "Шок"
    once: true
    effects: [ { all: budget, delta: "-20" } ]
end: { when: "round > meta.rounds", scoring: "self.budget * 0.1" }
""")


def test_world_dynamics_apply_to_everyone():
    result = resolve(SPEC, initial_state(SPEC), {}, [], {}, seed=1)
    assert result.state.tracks["a"]["budget"] == 105
    assert result.state.tracks["b"]["budget"] == 105


def test_triggered_event_fires_once():
    state = initial_state(SPEC)
    first = resolve(SPEC, state, {"a": [Order(action="escalate")]}, [], {}, seed=1)
    assert "shock" in first.state.fired_events
    assert first.state.tracks["b"]["budget"] == 85
    second = resolve(SPEC, first.state, {}, [], {}, seed=1)
    assert second.state.tracks["b"]["budget"] == 90


def test_round_advances_and_game_ends():
    state = initial_state(SPEC)
    state = resolve(SPEC, state, {}, [], {}, seed=1).state
    assert state.round == 2
    assert state.finished is False
    state = resolve(SPEC, state, {}, [], {}, seed=1).state
    assert state.finished is True


def test_scoring_includes_goals():
    state = initial_state(SPEC)
    total, breakdown = score(SPEC, state, "a")
    assert total == 100 * 0.1 + 10
    assert ("Мир", 10) in breakdown


def test_order_of_factions_does_not_change_outcome():
    orders_one = {"a": [Order(action="escalate")], "b": [Order(action="escalate")]}
    orders_two = {"b": [Order(action="escalate")], "a": [Order(action="escalate")]}
    first = resolve(SPEC, initial_state(SPEC), orders_one, [], {}, seed=3)
    second = resolve(SPEC, initial_state(SPEC), orders_two, [], {}, seed=3)
    assert first.state.tracks == second.state.tracks
    assert first.state.world == second.state.world
