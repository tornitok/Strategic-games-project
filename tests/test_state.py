from sgame.core.spec import parse_scenario
from sgame.core.state import StateBuilder, initial_state, pair_key

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
  army:   { title: "ВС", min: 0, max: 50 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 50, army: 10 } }
  - { id: b, title: "Б", start: { budget: 50, army: 10 } }
relations:
  default: 0
  pairs: [ { a: a, b: b, value: -20 } ]
actions:
  - { id: noop, title: "Ничего", effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
""")


def test_initial_state_reads_scenario():
    state = initial_state(SPEC)
    assert state.round == 1
    assert state.tracks["a"]["budget"] == 50
    assert state.world["tension"] == 10
    assert state.relations[pair_key("a", "b")] == -20


def test_builder_clamps_at_upper_bound():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    delta = builder.add_track("a", "army", 100)
    assert builder.track("a", "army") == 50
    assert delta.amount == 40
    assert delta.clamped is True


def test_builder_clamps_at_lower_bound():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    delta = builder.add_track("a", "budget", -80)
    assert builder.track("a", "budget") == 0
    assert delta.clamped is True


def test_builder_does_not_mutate_source_state():
    state = initial_state(SPEC)
    builder = StateBuilder(SPEC, state)
    builder.add_track("a", "budget", -10)
    assert state.tracks["a"]["budget"] == 50


def test_relations_are_symmetric():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.add_relation("b", "a", 5)
    assert builder.relation("a", "b") == -15


def test_context_exposes_namespaces():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    ctx = builder.context(actor="a", target="b")
    assert ctx["self"]["budget"] == 50
    assert ctx["target"]["army"] == 10
    assert ctx["world"]["tension"] == 10
    assert ctx["meta"]["rounds"] == 3
    assert ctx["rel"]("a", "b") == -20


def test_no_false_clamp_from_floating_point():
    """155.5 + 8.85 в двоичной арифметике даёт 8.849999999999994.

    Из-за точного сравнения дельта помечалась как упёршаяся в границу, и в
    сводке появлялось «(предел)» там, где до потолка было далеко.
    """
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.add_track("a", "budget", 5.5)
    delta = builder.add_track("a", "budget", 8.85)
    assert builder.track("a", "budget") < SPEC.tracks["budget"].max
    assert delta.clamped is False


def test_real_clamp_is_still_reported():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    delta = builder.add_track("a", "budget", 500)
    assert delta.clamped is True
