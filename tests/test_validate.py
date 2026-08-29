from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.validate import validate_scenario

BASE = """
schema_version: 1
meta: { id: t, title: "Тест", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
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


def problems_for(text):
    spec = parse_scenario(text)
    return validate_scenario(spec, scenario_lines(text))


def test_clean_scenario_has_no_problems():
    assert problems_for(BASE) == []


def test_unknown_track_in_effect():
    text = BASE.replace("{ self: budget, delta: \"5\" }", "{ self: cyberdef, delta: \"5\" }")
    problems = problems_for(text)
    assert any("cyberdef" in p.message for p in problems)
    assert all(p.line is not None for p in problems)


def test_risk_probabilities_must_sum_to_one():
    text = BASE.replace(
        '    effects:\n      - { self: budget, delta: "5" }',
        '    risk:\n      - { p: 0.5, effects: [ { self: budget, delta: "5" } ] }\n'
        '      - { p: 0.2, effects: [ { self: budget, delta: "1" } ] }',
    )
    assert any("вероятност" in p.message for p in problems_for(text))


def test_broken_expression_syntax():
    text = BASE.replace('delta: "5"', 'delta: "5 +"')
    assert any("не разбирается" in p.message for p in problems_for(text))


def test_unknown_name_in_expression():
    text = BASE.replace('scoring: "self.budget"', 'scoring: "self.reputation"')
    assert any("reputation" in p.message for p in problems_for(text))


def test_start_value_out_of_bounds():
    text = BASE.replace("start: { budget: 50 } }\n  - { id: b", "start: { budget: 500 } }\n  - { id: b")
    assert any("500" in p.message or "границ" in p.message for p in problems_for(text))


def test_action_counters_itself():
    text = BASE.replace('    cost: { budget: 10 }', '    cost: { budget: 10 }\n    countered_by: [ grow ]')
    assert any("само" in p.message for p in problems_for(text))
