import pytest
from sgame.core.errors import ScenarioError
from sgame.core.spec import parse_scenario

MINIMAL = """
schema_version: 1
meta: { id: t, title: "Тест", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100, visibility: public }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 50 } }
  - { id: b, title: "Б", start: { budget: 50 } }
actions:
  - id: grow
    title: "Рост"
    cost: { budget: 10 }
    effects:
      - { self: budget, delta: "5" }
end:
  when: "round > meta.rounds"
  scoring: "self.budget"
"""


def test_loads_minimal_scenario():
    spec = parse_scenario(MINIMAL)
    assert spec.meta.rounds == 3
    assert spec.action("grow").ap == 1
    assert spec.faction("b").title == "Б"


def test_effect_self_alias_is_readable():
    spec = parse_scenario(MINIMAL)
    effect = spec.action("grow").effects[0]
    assert effect.self_track == "budget"
    assert effect.delta == "5"


def test_unknown_field_is_rejected_with_line():
    text = MINIMAL.replace('title: "Рост"', 'title: "Рост"\n    цена: 5')
    with pytest.raises(ScenarioError) as exc:
        parse_scenario(text)
    assert exc.value.problems[0].line is not None


def test_missing_required_field_reports_path():
    text = MINIMAL.replace("rounds: 3, ", "")
    with pytest.raises(ScenarioError) as exc:
        parse_scenario(text)
    assert "rounds" in str(exc.value)


def test_future_schema_version_rejected():
    text = MINIMAL.replace("schema_version: 1", "schema_version: 99")
    with pytest.raises(ScenarioError) as exc:
        parse_scenario(text)
    assert "99" in str(exc.value)


def test_intro_is_optional_and_defaults_to_empty():
    assert parse_scenario(MINIMAL).meta.intro == ""


def test_intro_is_read_from_meta():
    text = MINIMAL.replace(
        'meta: { id: t, title: "Тест", rounds: 3, action_points: 2 }',
        'meta:\n'
        '  id: t\n'
        '  title: "Тест"\n'
        '  rounds: 3\n'
        '  action_points: 2\n'
        '  intro: "Мир на грани."\n',
    )
    assert parse_scenario(text).meta.intro == "Мир на грани."
