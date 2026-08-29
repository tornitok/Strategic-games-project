"""Русская и английская копии сценария не должны разъезжаться."""

import pytest

from sgame.core.spec import parse_scenario
from sgame.session.paths import all_scenarios, builtin_scenarios

# Без отката на русскую копию: иначе сравнение шло бы файла с самим собой
PAIRS = sorted(set(builtin_scenarios("ru", fallback=False)) & set(builtin_scenarios("en", fallback=False)))


def test_english_copies_exist():
    assert PAIRS, "нет ни одной английской копии сценария"


@pytest.fixture(params=PAIRS)
def pair(request):
    ru = parse_scenario(builtin_scenarios("ru", fallback=False)[request.param])
    en = parse_scenario(builtin_scenarios("en", fallback=False)[request.param])
    return request.param, ru, en


def test_same_factions(pair):
    name, ru, en = pair
    assert [f.id for f in ru.factions] == [f.id for f in en.factions], name


def test_same_actions_with_same_numbers(pair):
    name, ru, en = pair
    assert [a.id for a in ru.actions] == [a.id for a in en.actions], name
    for left, right in zip(ru.actions, en.actions):
        assert left.cost == right.cost, f"{name}: {left.id}"
        assert left.ap == right.ap, f"{name}: {left.id}"
        assert left.stance == right.stance, f"{name}: {left.id}"
        assert left.visibility == right.visibility, f"{name}: {left.id}"
        assert left.available_to == right.available_to, f"{name}: {left.id}"
        assert [e.delta for e in left.effects] == [e.delta for e in right.effects], f"{name}: {left.id}"
        assert [o.p for o in left.risk] == [o.p for o in right.risk], f"{name}: {left.id}"


def test_same_goals_and_thresholds(pair):
    name, ru, en = pair
    for left, right in zip(ru.factions, en.factions):
        assert [g.id for g in left.goals] == [g.id for g in right.goals], f"{name}: {left.id}"
        assert [g.when for g in left.goals] == [g.when for g in right.goals], f"{name}: {left.id}"
        assert [g.score for g in left.goals] == [g.score for g in right.goals], f"{name}: {left.id}"


def test_same_world_and_rules(pair):
    name, ru, en = pair
    assert ru.meta.rounds == en.meta.rounds, name
    assert ru.meta.action_points == en.meta.action_points, name
    assert ru.end.when == en.end.when, name
    assert ru.end.scoring == en.end.scoring, name
    assert {k: v.start for k, v in ru.world.items()} == {k: v.start for k, v in en.world.items()}, name


def test_language_choice_picks_the_right_copy():
    russian = all_scenarios("ru")
    english = all_scenarios("en")
    assert "Кризис" in parse_scenario(russian["meridian"]).meta.title
    assert "Crisis" in parse_scenario(english["meridian"]).meta.title
