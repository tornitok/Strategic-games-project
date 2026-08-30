"""Осложнения: редкое «что-то пошло не так» поверх обычного результата."""

from sgame.core.orders import Order
from sgame.core.resolve import resolve
from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.state import initial_state
from sgame.core.validate import validate_scenario
from sgame.narrate.news import news_items
from sgame.narrate.reference import action_card

TEXT = """
schema_version: 1
meta: {{ id: t, title: "Т", rounds: 20, action_points: 2 }}
tracks:
  budget: {{ title: "Бюджет", min: 0, max: 300 }}
  army:   {{ title: "Армия", min: 0, max: 100 }}
world:
  attention: {{ title: "Внимание", min: 0, max: 100, start: 20 }}
factions:
  - {{ id: a, title: "А", start: {{ budget: 100, army: 50 }} }}
  - {{ id: b, title: "Б", start: {{ budget: 100, army: 50 }} }}
actions:
  - id: mobilize
    title: "Призыв"
    news: "{{actor}} объявляет призыв"
    effects: [ {{ self: army, delta: "10" }} ]
    complications:
      - chance: {chance}
        title: "ЧП на сборном пункте"
        news: "Происшествие на сборном пункте"
        effects: [ {{ self: budget, delta: "-20" }}, {{ world: attention, delta: "10" }} ]
  - id: covert
    title: "Тайная операция"
    news: "{{actor}} действует тайно"
    visibility: secret
    complications:
      - {{ chance: 1.0, title: "След", news: "Найден след", effects: [ {{ self: budget, delta: "-5" }} ] }}
end: {{ when: "round > meta.rounds", scoring: "self.budget" }}
"""


def spec_with(chance):
    return parse_scenario(TEXT.format(chance=chance))


def play(spec, action="mobilize", seed=3):
    return resolve(spec, initial_state(spec), {"a": [Order(action=action)]}, [], {}, seed)


def test_action_works_as_usual_when_nothing_goes_wrong():
    result = play(spec_with(0.0))
    assert result.state.tracks["a"]["army"] == 60
    assert result.state.tracks["a"]["budget"] == 100
    assert not [e for e in result.events if e.kind == "complication"]


def test_complication_adds_its_effects_on_top():
    result = play(spec_with(1.0))
    assert result.state.tracks["a"]["army"] == 60, "обычный результат не отменяется"
    assert result.state.tracks["a"]["budget"] == 80


def test_complication_is_its_own_news_line():
    spec = spec_with(1.0)
    result = play(spec)
    items = news_items(spec, result.events, viewer=None, role="public")
    assert any("Происшествие на сборном пункте" in item.headline for item in items)


def test_complication_of_a_secret_action_stays_secret():
    """Иначе осложнение выдаёт автора тайной операции."""
    spec = spec_with(1.0)
    result = resolve(spec, initial_state(spec), {"a": [Order(action="covert")]}, [], {}, 3)
    complication = next(e for e in result.events if e.kind == "complication")
    assert complication.audience == "actor"
    assert not any(
        item.kind == "complication"
        for item in news_items(spec, result.events, viewer="b", role="team")
    )


def test_same_seed_gives_the_same_complication():
    spec = spec_with(0.5)
    first = [e.title for e in play(spec, seed=11).events if e.kind == "complication"]
    second = [e.title for e in play(spec, seed=11).events if e.kind == "complication"]
    assert first == second


def test_rare_complication_is_rare_but_happens():
    spec = spec_with(0.05)
    hits = sum(
        1
        for seed in range(200)
        if any(e.kind == "complication" for e in play(spec, seed=seed).events)
    )
    assert 1 <= hits <= 30, hits


def test_reference_warns_about_the_complication():
    spec = spec_with(0.05)
    card = action_card(spec, spec.action("mobilize"))
    assert card["complications"]
    assert card["complications"][0]["chance"] == "редко"
    assert "Бюджет −20" in card["complications"][0]["effects"]


def test_validator_checks_complication_effects():
    text = TEXT.format(chance=0.05).replace('{ self: budget, delta: "-20" }',
                                            '{ self: nosuchtrack, delta: "-20" }')
    spec = parse_scenario(text)
    problems = validate_scenario(spec, scenario_lines(text))
    assert any("nosuchtrack" in p.message for p in problems)
