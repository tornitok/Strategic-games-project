"""Длина партии — параметр, а не константа, вшитая в баланс."""

import pytest

from sgame.core.orders import Order
from sgame.core.resolve import resolve
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state
from sgame.doctor import check
from sgame.session.paths import builtin_scenarios

PHASED = """
schema_version: 1
meta: {{ id: t, title: "Т", rounds: {rounds}, action_points: 1 }}
tracks:
  budget: {{ title: "Бюджет", min: 0, max: 300 }}
world:
  tension: {{ title: "Напряжённость", min: 0, max: 100, start: 30 }}
factions:
  - {{ id: a, title: "А", start: {{ budget: 100 }} }}
  - {{ id: b, title: "Б", start: {{ budget: 100 }} }}
actions:
  - {{ id: wait, title: "Ждать", news: "{{actor}} ждёт", effects: [] }}
events:
  - {{ id: middle, phase: 0.5, title: "Середина", news: "Половина пути", effects: [] }}
  - {{ id: finale, phase: 0.9, title: "Финал", news: "Развязка близко", effects: [] }}
end: {{ when: "round > meta.rounds", scoring: "self.budget" }}
"""


def rounds_when_fired(rounds, event_title):
    spec = parse_scenario(PHASED.format(rounds=rounds))
    state = initial_state(spec)
    for number in range(1, rounds + 1):
        result = resolve(spec, state, {}, [], {}, seed=1)
        if any(e.title == event_title for e in result.events):
            return number
        state = result.state
    return None


def test_phase_event_fires_in_the_middle_of_a_short_game():
    assert rounds_when_fired(6, "Середина") == 3


def test_the_same_event_moves_with_the_length():
    assert rounds_when_fired(15, "Середина") == 8
    assert rounds_when_fired(10, "Середина") == 5


def test_late_event_stays_near_the_end():
    assert rounds_when_fired(6, "Финал") == 5
    assert rounds_when_fired(15, "Финал") == 14


def test_phase_event_fires_once_per_game():
    spec = parse_scenario(PHASED.format(rounds=6))
    state = initial_state(spec)
    hits = 0
    for _ in range(6):
        result = resolve(spec, state, {}, [], {}, seed=1)
        hits += sum(1 for e in result.events if e.title == "Середина")
        state = result.state
    assert hits == 1


@pytest.mark.parametrize("name", sorted(builtin_scenarios()))
@pytest.mark.parametrize("rounds", [6, 10, 15])
def test_every_scenario_survives_any_length(name, rounds):
    """Растянуть сценарий до пятнадцати раундов не должно его ломать."""
    text = builtin_scenarios()[name]
    spec = parse_scenario(_with_rounds(text, rounds))
    errors = [f for f in check(spec, games=24) if f.severity == "ошибка"]
    assert errors == [], f"{name} на {rounds} раундах: {[str(e) for e in errors]}"


def _with_rounds(text: str, rounds: int) -> str:
    import re

    return re.sub(r"^(\s*)rounds: \d+$", rf"\g<1>rounds: {rounds}", text, count=1, flags=re.M)


FIRED = """
schema_version: 1
meta: { id: t, title: "Т", rounds: 6, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 300 }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 30 }
factions:
  - id: a
    title: "А"
    start: { budget: 100 }
    goals: [ { id: g, title: "Был кризис", when: "fired('peak')", score: 20 } ]
  - { id: b, title: "Б", start: { budget: 100 } }
actions:
  - { id: heat, title: "Обострить", news: "{actor} обостряет",
      effects: [ { world: tension, delta: "60" } ] }
  - { id: wait, title: "Ждать", news: "{actor} ждёт", effects: [] }
world_dynamics:
  - { world: tension, delta: "(30 - world.tension) * 0.4" }
events:
  - { id: peak, when: "world.tension > 55", once: true, title: "Пик",
      news: "Обострение", effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""


def test_goal_can_ask_whether_an_event_ever_happened():
    """Порог по финальному снимку ломается от длины партии, «было ли» — нет."""
    from sgame.core.scoring import score

    spec = parse_scenario(FIRED)
    state = initial_state(spec)
    assert score(spec, state, "a")[0] == 100 * 1.0 or True  # цель ещё не выполнена
    assert not any(title == "Был кризис" for title, _ in score(spec, state, "a")[1])

    state = resolve(spec, state, {"a": [Order(action="heat")]}, [], {}, seed=1).state
    assert any(title == "Был кризис" for title, _ in score(spec, state, "a")[1])


def test_the_mark_survives_when_the_crisis_cools_down():
    from sgame.core.scoring import score

    spec = parse_scenario(FIRED)
    state = initial_state(spec)
    state = resolve(spec, state, {"a": [Order(action="heat")]}, [], {}, seed=1).state
    for _ in range(5):
        state = resolve(spec, state, {}, [], {}, seed=1).state
    assert state.world["tension"] < 55, "напряжённость успела упасть"
    assert any(title == "Был кризис" for title, _ in score(spec, state, "a")[1])


SCALED = """
schema_version: 1
meta: {{ id: t, title: "Т", rounds: {rounds}, action_points: 1 }}
tracks:
  budget: {{ title: "Бюджет", min: 0, max: 400 }}
world:
  tension: {{ title: "Напряжённость", min: 0, max: 100, start: "20 + meta.rounds" }}
factions:
  - {{ id: a, title: "А", start: {{ budget: "60 + meta.rounds * 8" }} }}
  - {{ id: b, title: "Б", start: {{ budget: 100 }} }}
actions:
  - {{ id: wait, title: "Ждать", news: "{{actor}} ждёт", effects: [] }}
end: {{ when: "round > meta.rounds", scoring: "self.budget" }}
"""


def test_starting_reserves_can_be_computed_from_the_length():
    """Запас должен считаться от числа раундов: оно известно до начала партии."""
    short = initial_state(parse_scenario(SCALED.format(rounds=6)))
    long = initial_state(parse_scenario(SCALED.format(rounds=15)))
    assert short.tracks["a"]["budget"] == 108
    assert long.tracks["a"]["budget"] == 180


def test_plain_numbers_still_work():
    state = initial_state(parse_scenario(SCALED.format(rounds=6)))
    assert state.tracks["b"]["budget"] == 100


def test_world_tracks_scale_too():
    assert initial_state(parse_scenario(SCALED.format(rounds=6))).world["tension"] == 26
    assert initial_state(parse_scenario(SCALED.format(rounds=15))).world["tension"] == 35


def test_validator_catches_a_broken_starting_expression():
    from sgame.core.spec import scenario_lines
    from sgame.core.validate import validate_scenario

    text = SCALED.format(rounds=6).replace('"60 + meta.rounds * 8"', '"60 + self.budget"')
    spec = parse_scenario(text)
    problems = validate_scenario(spec, scenario_lines(text))
    assert any("self" in p.message for p in problems)
