from sgame.core.orders import DealOffer, Order
from sgame.core.phases import (
    phase_counters, phase_deals, phase_effects, phase_validate,
)
from sgame.core.spec import parse_scenario
from sgame.core.state import Status, StateBuilder, initial_state

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 5, action_points: 3 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 200 }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 100, intel: 50 } }
  - { id: b, title: "Б", start: { budget: 100, intel: 50 } }
actions:
  - id: open_hit
    title: "Открытый удар"
    target: faction
    countered_by: [ shield ]
    effects:
      - { target: budget, delta: "-20" }
      - { world: tension, delta: "5" }
  - id: shield
    title: "Щит"
    counter_multiplier: 0.25
    effects: []
  - id: covert
    title: "Тайная операция"
    target: faction
    visibility: secret
    reveal_chance: 1.0
    effects: [ { target: budget, delta: "-10" } ]
  - id: gamble
    title: "Риск"
    risk:
      - { p: 1.0, title: "успех", effects: [ { self: budget, delta: "10" } ] }
deals:
  - { id: transfer, title: "Передача", kind: resource, track: budget }
  - { id: pact, title: "Пакт", kind: status, duration: 2 }
end: { when: "round > meta.rounds", scoring: "self.budget" }
""")


def prepared(orders):
    builder = StateBuilder(SPEC, initial_state(SPEC))
    accepted, _ = phase_validate(SPEC, builder, orders)
    return builder, accepted


def test_counter_reduces_effect():
    builder, accepted = prepared({
        "a": [Order(action="open_hit", target="b")],
        "b": [Order(action="shield")],
    })
    multipliers = phase_counters(SPEC, accepted)
    phase_effects(SPEC, builder, accepted, multipliers, seed=1)
    assert builder.track("b", "budget") == 95


def test_without_counter_full_effect():
    builder, accepted = prepared({"a": [Order(action="open_hit", target="b")]})
    phase_effects(SPEC, builder, accepted, phase_counters(SPEC, accepted), seed=1)
    assert builder.track("b", "budget") == 80


def test_secret_action_is_private_until_revealed():
    builder, accepted = prepared({"a": [Order(action="covert", target="b")]})
    events = phase_effects(SPEC, builder, accepted, {}, seed=1)
    assert events[0].audience == "actor_and_target"


def test_risk_outcome_is_recorded():
    builder, accepted = prepared({"a": [Order(action="gamble")]})
    events = phase_effects(SPEC, builder, accepted, {}, seed=7)
    assert events[0].roll == "успех"
    assert builder.track("a", "budget") == 110


def test_resource_deal_moves_value_when_accepted():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.pending_offers = [DealOffer(id="o1", deal="transfer", sender="a", receiver="b", amount=30)]
    phase_deals(SPEC, builder, offers=[], responses={"o1": True})
    assert builder.track("a", "budget") == 70
    assert builder.track("b", "budget") == 130


def test_rejected_deal_changes_nothing():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.pending_offers = [DealOffer(id="o1", deal="transfer", sender="a", receiver="b", amount=30)]
    phase_deals(SPEC, builder, offers=[], responses={"o1": False})
    assert builder.track("a", "budget") == 100


def test_status_deal_sets_expiry():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.pending_offers = [DealOffer(id="o2", deal="pact", sender="a", receiver="b")]
    phase_deals(SPEC, builder, offers=[], responses={"o2": True})
    assert builder.statuses == [Status(deal="pact", a="a", b="b", until=3)]


def test_expired_status_is_removed():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    builder.round = 4
    builder.statuses = [Status(deal="pact", a="a", b="b", until=3)]
    events = phase_deals(SPEC, builder, offers=[], responses={})
    assert builder.statuses == []
    assert any(e.kind == "status_expired" for e in events)


def test_new_offers_become_pending():
    builder = StateBuilder(SPEC, initial_state(SPEC))
    offer = DealOffer(id="o3", deal="pact", sender="a", receiver="b")
    phase_deals(SPEC, builder, offers=[offer], responses={})
    assert builder.pending_offers == [offer]
