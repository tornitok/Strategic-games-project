"""Слухи: модельные и запущенные командами, правдивые и ложные."""

from sgame.core.orders import Order
from sgame.core.resolve import resolve
from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.state import initial_state
from sgame.core.validate import validate_scenario
from sgame.narrate.news import news_items

BASE = """
schema_version: 1
meta: {{ id: t, title: "Т", rounds: 20, action_points: 2 }}
tracks:
  budget: {{ title: "Бюджет", min: 0, max: 300 }}
  intel:  {{ title: "Разведка", min: 0, max: 100, visibility: private }}
world:
  tension: {{ title: "Напряжённость", min: 0, max: 100, start: 50 }}
factions:
  - {{ id: a, title: "Астория", start: {{ budget: 100, intel: 50 }} }}
  - {{ id: b, title: "Борея", start: {{ budget: 100, intel: 50 }} }}
  - {{ id: c, title: "Кальдера", start: {{ budget: 100, intel: 50 }} }}
actions:
  - {{ id: noop, title: "Ничего", effects: [] }}
  - id: covert
    title: "Тайная операция"
    target: faction
    visibility: secret
    effects: [ {{ self: intel, delta: "-5" }} ]
  - id: disinform
    title: "Дезинформация"
    target: faction
    plants_rumour: true
    effects: [ {{ self: intel, delta: "-10" }} ]
rumours:
  chance: {chance}
  noise_chance: {noise}
  accuracy: {accuracy}
  templates:
    - "По неподтверждённым данным, за этим стоит {{subject}}"
end: {{ when: "round > meta.rounds", scoring: "self.budget" }}
"""


def spec_with(chance=0.0, noise=0.0, accuracy=0.6):
    return parse_scenario(BASE.format(chance=chance, noise=noise, accuracy=accuracy))


def rumours_of(spec, orders, seed=5):
    result = resolve(spec, initial_state(spec), orders, [], {}, seed)
    return [e for e in result.events if e.kind == "rumour"]


def test_no_rumours_when_both_chances_are_zero():
    assert rumours_of(spec_with(), {"a": [Order(action="covert", target="b")]}) == []


def test_true_rumour_names_the_real_author():
    spec = spec_with(chance=1.0, accuracy=1.0)
    rumour = rumours_of(spec, {"a": [Order(action="covert", target="b")]})[0]
    assert rumour.subject == "a"
    assert rumour.truth is True
    assert "Астория" in rumour.title


def test_false_rumour_names_somebody_else():
    spec = spec_with(chance=1.0, accuracy=0.0)
    rumour = rumours_of(spec, {"a": [Order(action="covert", target="b")]})[0]
    assert rumour.subject != "a"
    assert rumour.truth is False


def test_noise_rumour_appears_when_nothing_was_hidden():
    spec = spec_with(noise=1.0)
    rumour = rumours_of(spec, {"a": [Order(action="noop")]})[0]
    assert rumour.truth is False


def test_planted_rumour_points_at_the_chosen_side():
    spec = spec_with()
    rumour = rumours_of(spec, {"a": [Order(action="disinform", target="c")]})[0]
    assert rumour.subject == "c"
    assert rumour.source == "a"
    assert rumour.truth is False


def test_rumour_is_public():
    spec = spec_with()
    assert rumours_of(spec, {"a": [Order(action="disinform", target="c")]})[0].audience == "public"


def test_players_see_neither_source_nor_truth():
    spec = spec_with()
    events = resolve(
        spec, initial_state(spec), {"a": [Order(action="disinform", target="c")]}, [], {}, 5
    ).events
    items = news_items(spec, events, viewer="b", role="team")
    rumour = next(item for item in items if item.kind == "rumour")
    assert "Астория" not in rumour.headline
    assert rumour.detail == ""


def test_host_sees_who_planted_it_and_whether_it_is_true():
    spec = spec_with()
    events = resolve(
        spec, initial_state(spec), {"a": [Order(action="disinform", target="c")]}, [], {}, 5
    ).events
    items = news_items(spec, events, viewer=None, role="host")
    rumour = next(item for item in items if item.kind == "rumour")
    assert "ложь" in rumour.detail.lower()
    assert "Астория" in rumour.detail


def test_same_seed_gives_the_same_rumour():
    spec = spec_with(chance=0.5, accuracy=0.5)
    orders = {"a": [Order(action="covert", target="b")]}
    first = [(r.subject, r.truth) for r in rumours_of(spec, orders, seed=11)]
    second = [(r.subject, r.truth) for r in rumours_of(spec, orders, seed=11)]
    assert first == second


def test_vague_hint_is_dropped_when_a_rumour_already_speaks():
    spec = spec_with(chance=1.0, accuracy=1.0)
    events = resolve(
        spec, initial_state(spec), {"a": [Order(action="covert", target="b")]}, [], {}, 5
    ).events
    items = news_items(spec, events, viewer="c", role="team")
    assert [item.kind for item in items].count("hint") == 0
    assert any(item.kind == "rumour" for item in items)


def test_validator_requires_subject_in_template():
    text = BASE.format(chance=0.5, noise=0, accuracy=0.6).replace("{subject}", "кто-то")
    spec = parse_scenario(text)
    problems = validate_scenario(spec, scenario_lines(text))
    assert any("subject" in p.message for p in problems)
