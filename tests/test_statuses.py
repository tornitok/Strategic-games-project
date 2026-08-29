"""Статусы из сделок должны влиять на модель, а не только храниться."""

from sgame.core.orders import DealOffer, Order
from sgame.core.resolve import resolve
from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.state import Status, initial_state
from sgame.core.validate import validate_scenario

TEXT = """
schema_version: 1
meta: { id: t, title: "Т", rounds: 5, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 300 }
world: {}
factions:
  - { id: a, title: "А", start: { budget: 100 } }
  - { id: b, title: "Б", start: { budget: 100 } }
  - { id: c, title: "В", start: { budget: 100 } }
actions:
  - { id: noop, title: "Ничего", news: "{actor} ждёт", effects: [] }
  - { id: supply, title: "Поставки по блоку", news: "{actor} получает поставки",
      requires: "in_status('bloc')", effects: [ { self: budget, delta: "20" } ] }
deals:
  - { id: bloc, title: "Блок", kind: status, duration: 3 }
world_dynamics:
  - { all: budget, delta: "in_status('bloc') * 5" }
rumours: { chance: 0.1, templates: [ "Говорят, {subject}" ] }
events:
  - { id: e, chance: 0.1, title: "Случай", news: "Случилось", effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""

SPEC = parse_scenario(TEXT)


def state_with_bloc():
    state = initial_state(SPEC)
    return type(state)(
        round=state.round,
        tracks=state.tracks,
        world=state.world,
        relations=state.relations,
        statuses=(Status(deal="bloc", a="a", b="b", until=9),),
    )


def test_members_of_the_bloc_gain_from_world_dynamics():
    result = resolve(SPEC, state_with_bloc(), {}, [], {}, seed=1)
    assert result.state.tracks["a"]["budget"] == 105
    assert result.state.tracks["b"]["budget"] == 105
    assert result.state.tracks["c"]["budget"] == 100


def test_action_can_require_a_status():
    result = resolve(SPEC, state_with_bloc(), {"c": [Order(action="supply")]}, [], {}, seed=1)
    rejected = [e for e in result.events if e.kind == "order_rejected"]
    assert rejected and "условие" in rejected[0].detail


def test_member_may_use_the_status_action():
    result = resolve(SPEC, state_with_bloc(), {"a": [Order(action="supply")]}, [], {}, seed=1)
    assert not [e for e in result.events if e.kind == "order_rejected"]
    assert result.state.tracks["a"]["budget"] == 125


def test_status_between_a_named_pair_is_readable():
    from sgame.core.state import StateBuilder

    builder = StateBuilder(SPEC, state_with_bloc())
    context = builder.context(actor="c")
    assert context["status"]("bloc", "a", "b") == 1
    assert context["status"]("bloc", "a", "c") == 0


def test_expired_status_stops_counting():
    state = initial_state(SPEC)
    expired = type(state)(
        round=5, tracks=state.tracks, world=state.world, relations=state.relations,
        statuses=(Status(deal="bloc", a="a", b="b", until=3),),
    )
    result = resolve(SPEC, expired, {}, [], {}, seed=1)
    assert result.state.tracks["a"]["budget"] == 100


def test_validator_knows_the_status_functions():
    assert validate_scenario(SPEC, scenario_lines(TEXT)) == []


def test_deal_creates_a_working_status():
    state = initial_state(SPEC)
    offer = DealOffer(id="o1", deal="bloc", sender="a", receiver="b")
    after_offer = resolve(SPEC, state, {}, [offer], {}, seed=1).state
    after_accept = resolve(SPEC, after_offer, {}, [], {"o1": True}, seed=1).state
    assert any(s.deal == "bloc" for s in after_accept.statuses)
    third = resolve(SPEC, after_accept, {}, [], {}, seed=1).state
    assert third.tracks["a"]["budget"] > third.tracks["c"]["budget"]


def test_average_across_factions_is_available():
    """Относительный счёт: отнять у соседа должно быть так же ценно, как нажить."""
    from sgame.core.state import StateBuilder

    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.add_track("a", "budget", 60)
    context = builder.context(actor="a")
    assert context["avg"]("budget") == (160 + 100 + 100) / 3
