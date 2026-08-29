"""Случайные события и доступ к чужим показателям в условиях."""

from sgame.core.expr import evaluate
from sgame.core.resolve import resolve
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state

BASE = """
schema_version: 1
meta: {{ id: t, title: "Т", rounds: 20, action_points: 1{extra} }}
tracks:
  budget: {{ title: "Бюджет", min: 0, max: 300 }}
  intel:  {{ title: "Разведка", min: 0, max: 100, visibility: private }}
world:
  tension: {{ title: "Напряжённость", min: 0, max: 100, start: 50 }}
factions:
  - {{ id: a, title: "А", start: {{ budget: 100, intel: 20 }} }}
  - {{ id: b, title: "Б", start: {{ budget: 100, intel: 80 }} }}
actions:
  - {{ id: noop, title: "Ничего", effects: [] }}
events:
{events}
end: {{ when: "round > meta.rounds", scoring: "self.budget" }}
"""


def spec_with(events, extra=""):
    return parse_scenario(BASE.format(events=events, extra=extra))


def fired_over_rounds(spec, rounds=12, seed=7):
    state = initial_state(spec)
    fired = []
    for _ in range(rounds):
        result = resolve(spec, state, {}, [], {}, seed)
        fired.append([e.title for e in result.events if e.kind == "scenario_event"])
        state = result.state
    return fired


def test_event_without_condition_is_always_eligible():
    spec = spec_with('  - { id: e, title: "Всегда", effects: [] }')
    assert fired_over_rounds(spec, rounds=2)[0] == ["Всегда"]


def test_chance_zero_never_fires():
    spec = spec_with('  - { id: e, chance: 0, title: "Никогда", effects: [] }')
    assert all(not round_events for round_events in fired_over_rounds(spec))


def test_chance_half_fires_sometimes_but_not_always():
    spec = spec_with('  - { id: e, chance: 0.5, title: "Иногда", effects: [] }')
    rounds = fired_over_rounds(spec, rounds=20)
    hits = sum(1 for r in rounds if r)
    assert 0 < hits < 20


def test_same_seed_gives_the_same_draw():
    spec = spec_with('  - { id: e, chance: 0.5, title: "Иногда", effects: [] }')
    assert fired_over_rounds(spec, seed=3) == fired_over_rounds(spec, seed=3)


def test_different_seeds_diverge():
    spec = spec_with('  - { id: e, chance: 0.5, title: "Иногда", effects: [] }')
    assert fired_over_rounds(spec, seed=3) != fired_over_rounds(spec, seed=99)


def test_condition_and_chance_work_together():
    spec = spec_with('  - { id: e, chance: 1, when: "world.tension > 90", title: "Порог", effects: [] }')
    assert all(not round_events for round_events in fired_over_rounds(spec))


def test_cap_limits_random_events_per_round():
    events = "\n".join(
        f'  - {{ id: e{i}, chance: 1, title: "Событие {i}", effects: [] }}' for i in range(5)
    )
    spec = spec_with(events, extra=", max_random_events: 2")
    assert all(len(round_events) <= 2 for round_events in fired_over_rounds(spec))


def test_cap_does_not_touch_scheduled_events():
    events = (
        '  - { id: plan, when: "round == 1", title: "Плановое", effects: [] }\n'
        '  - { id: r1, chance: 1, title: "Случайное 1", effects: [] }\n'
        '  - { id: r2, chance: 1, title: "Случайное 2", effects: [] }'
    )
    spec = spec_with(events, extra=", max_random_events: 1")
    first = fired_over_rounds(spec, rounds=1)[0]
    assert "Плановое" in first
    assert len([t for t in first if t.startswith("Случайное")]) == 1


def test_track_function_reads_another_side():
    spec = spec_with('  - { id: e, when: "track(\'b\', \'intel\') > 50", title: "Улика", effects: [] }')
    assert fired_over_rounds(spec, rounds=1)[0] == ["Улика"]


def test_track_function_rejects_unknown_side():
    from sgame.core.expr import ExprError
    import pytest

    with pytest.raises(ExprError):
        evaluate("track('nope', 'intel')", {"track": lambda f, n: (_ for _ in ()).throw(KeyError(f))})


def test_validator_accepts_event_without_condition():
    """Пустое `when` означает «возможно всегда», а не сломанное выражение."""
    from sgame.core.spec import scenario_lines
    from sgame.core.validate import validate_scenario

    text = BASE.format(events='  - { id: e, chance: 0.3, title: "Случай", effects: [] }', extra="")
    spec = parse_scenario(text)
    assert validate_scenario(spec, scenario_lines(text)) == []
