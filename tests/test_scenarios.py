"""Требования ко всем встроенным сценариям сразу.

Каждый новый сценарий попадает под эти проверки автоматически — иначе
про половину из них забудут через месяц.
"""

import pytest

from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.validate import validate_scenario
from sgame.session.paths import builtin_scenarios

SCENARIOS = sorted(builtin_scenarios())


@pytest.fixture(params=SCENARIOS)
def scenario(request):
    text = builtin_scenarios()[request.param]
    return request.param, text, parse_scenario(text)


def test_passes_the_validator(scenario):
    name, text, spec = scenario
    assert validate_scenario(spec, scenario_lines(text)) == [], name


def test_has_enough_content_for_a_class(scenario):
    name, _, spec = scenario
    assert len(spec.factions) >= 3, name
    assert len(spec.actions) >= 10, name
    assert len(spec.events) >= 5, name


def test_every_side_has_a_briefing_and_goals(scenario):
    name, _, spec = scenario
    for faction in spec.factions:
        assert faction.briefing.strip(), f"{name}: {faction.id}"
        assert faction.goals, f"{name}: {faction.id}"


def test_intro_is_written(scenario):
    name, _, spec = scenario
    assert len(spec.meta.intro.strip()) > 200, name


def test_every_action_has_a_news_headline(scenario):
    name, _, spec = scenario
    missing = [action.id for action in spec.actions if not action.news]
    assert missing == [], f"{name}: без заголовка — {missing}"


def test_rumours_are_configured(scenario):
    name, _, spec = scenario
    assert spec.rumours.templates, name
    assert all("{subject}" in t for t in spec.rumours.templates), name


def test_has_random_events(scenario):
    name, _, spec = scenario
    random_events = [e for e in spec.events if "chance" in e.model_fields_set]
    assert random_events, name
