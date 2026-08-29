"""Свойства сценария «Ложбина»."""

from sgame.bots import simulate
from sgame.core.orders import Order
from sgame.core.resolve import resolve
from sgame.core.spec import parse_scenario
from sgame.core.state import Status, initial_state
from sgame.session.paths import builtin_scenarios

SPEC = parse_scenario(builtin_scenarios()["frontline"])


def test_offensive_belongs_to_its_own_side():
    """Каждая сторона двигает фронт к себе — иначе весь спор бессмыслен."""
    _, events = resolve(
        SPEC, initial_state(SPEC), {"osset": [Order(action="push_north", target="karria")]},
        [], {}, seed=1
    ).events, None
    rejected = [e for e in resolve(
        SPEC, initial_state(SPEC), {"osset": [Order(action="push_north", target="karria")]},
        [], {}, seed=1
    ).events if e.kind == "order_rejected"]
    assert rejected and "не для вашей стороны" in rejected[0].detail


def test_each_side_pushes_the_line_its_own_way():
    north = resolve(SPEC, initial_state(SPEC),
                    {"karria": [Order(action="push_north", target="osset")]}, [], {}, seed=2).state
    south = resolve(SPEC, initial_state(SPEC),
                    {"osset": [Order(action="push_south", target="karria")]}, [], {}, seed=2).state
    start = initial_state(SPEC).world["frontline"]
    assert north.world["frontline"] > start
    assert south.world["frontline"] < start


def test_ceasefire_stops_offensives():
    state = initial_state(SPEC)
    truce = type(state)(
        round=state.round, tracks=state.tracks, world=state.world, relations=state.relations,
        statuses=(Status(deal="ceasefire", a="karria", b="osset", until=9),),
    )
    result = resolve(SPEC, truce, {"karria": [Order(action="push_north", target="osset")]},
                     [], {}, seed=1)
    rejected = [e for e in result.events if e.kind == "order_rejected"]
    assert rejected and "условие" in rejected[0].detail


def test_the_line_actually_moves_in_play():
    """Если фронт стоит на месте, спорить в этом сценарии не о чем."""
    roles = {"karria": "opposition", "osset": "opposition",
             "tarnia": "following", "league": "cautious"}
    seen = set()
    for seed in range(1, 6):
        result = simulate(SPEC, roles, seed)
        seen.add(result.state.world["frontline"])
    assert len(seen) > 1


def test_patron_actions_are_closed_to_belligerents():
    result = resolve(SPEC, initial_state(SPEC),
                     {"karria": [Order(action="supply", target="osset")]}, [], {}, seed=1)
    rejected = [e for e in result.events if e.kind == "order_rejected"]
    assert rejected and "не для вашей стороны" in rejected[0].detail
