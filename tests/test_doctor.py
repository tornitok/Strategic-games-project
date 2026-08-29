"""Поиск мест, где сценарий может сломаться."""

from sgame.core.spec import parse_scenario
from sgame.doctor import check

BASE = """
schema_version: 1
meta: {{ id: t, title: "Т", rounds: 6, action_points: 2 }}
tracks:
  budget: {{ title: "Бюджет", min: 0, max: 200 }}
  intel:  {{ title: "Разведка", min: 0, max: 100, visibility: private }}
world:
  tension: {{ title: "Напряжённость", min: 0, max: 100, start: 30 }}
factions:
  - id: a
    title: "А"
    start: {{ budget: 100, intel: 40 }}
    briefing: "текст"
    goals: [ {{ id: g1, title: "Цель А", when: "{goal_a}", score: 10 }} ]
  - id: b
    title: "Б"
    start: {{ budget: 100, intel: 40 }}
    briefing: "текст"
    goals: [ {{ id: g2, title: "Цель Б", when: "self.budget > 0", score: 10 }} ]
  - id: c
    title: "В"
    start: {{ budget: 100, intel: 40 }}
    briefing: "текст"
    goals: [ {{ id: g3, title: "Цель В", when: "self.budget > 0", score: 10 }} ]
actions:
  - {{ id: build, title: "Стройка", news: "{{actor}} строит", stance: neutral,
      cost: {{ budget: 10 }}, effects: [ {{ self: budget, delta: "18" }} ] }}
  - {{ id: hit, title: "Удар", news: "{{actor}} бьёт", target: faction, stance: hostile,
      cost: {{ budget: 12 }}, effects: [ {{ target: budget, delta: "-15" }} ] }}
{extra_actions}
rumours: {{ chance: 0.2, templates: [ "Говорят, {{subject}}" ] }}
events:
  - {{ id: e, chance: 0.2, title: "Случай", news: "Случилось", effects: [] }}
end: {{ when: "{end_when}", scoring: "self.budget * 0.1" }}
"""


def scenario(goal_a="self.budget > 0", extra_actions="", end_when="round > meta.rounds"):
    return parse_scenario(BASE.format(goal_a=goal_a, extra_actions=extra_actions, end_when=end_when))


def codes(findings):
    return {finding.code for finding in findings}


def test_healthy_scenario_has_no_findings_about_goals_or_actions():
    found = codes(check(scenario(), games=4))
    assert "unreachable_goal" not in found
    assert "unusable_action" not in found


def test_detects_a_goal_nobody_can_ever_meet():
    found = check(scenario(goal_a="self.budget > 5000"), games=4)
    assert any(f.code == "unreachable_goal" and "Цель А" in f.message for f in found)


def test_detects_a_goal_that_is_always_met():
    found = check(scenario(goal_a="round > 0"), games=4)
    assert any(f.code == "free_goal" and "Цель А" in f.message for f in found)


def test_detects_an_action_that_is_never_available():
    extra = ('  - { id: dream, title: "Мечта", news: "{actor} мечтает", stance: neutral,\n'
             '      cost: { budget: 9999 }, effects: [] }')
    found = check(scenario(extra_actions=extra), games=4)
    assert any(f.code == "unusable_action" and "Мечта" in f.message for f in found)


def test_detects_a_game_that_ends_far_too_early():
    found = check(scenario(end_when="round > 1"), games=4)
    assert any(f.code == "early_end" for f in found)


def test_detects_a_track_stuck_against_its_limit():
    extra = ('  - { id: pump, title: "Накачка", news: "{actor} качает", stance: neutral,\n'
             '      effects: [ { world: tension, delta: "60" } ] }')
    found = check(scenario(extra_actions=extra), games=4)
    assert any(f.code == "stuck_track" and "Напряжённость" in f.message for f in found)


def test_reports_a_dominant_line_of_behaviour():
    found = check(scenario(), games=6)
    dominant = [f for f in found if f.code == "dominant_role"]
    assert all("%" in f.message for f in dominant)


def test_findings_carry_severity():
    for finding in check(scenario(goal_a="self.budget > 5000"), games=4):
        assert finding.severity in {"ошибка", "предупреждение"}


def test_warns_when_there_is_no_free_action():
    """Разорившейся команде должно остаться хоть что-то — иначе мёртвый ход."""
    found = check(scenario(), games=2)
    assert any(f.code == "no_free_action" for f in found)


def test_no_warning_when_a_free_action_exists():
    extra = ('  - { id: wait, title: "Пауза", news: "{actor} выжидает", stance: neutral,\n'
             '      effects: [ { self: intel, delta: "2" } ] }')
    found = check(scenario(extra_actions=extra), games=2)
    assert not any(f.code == "no_free_action" for f in found)
