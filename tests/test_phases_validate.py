from sgame.core.orders import Order
from sgame.core.phases import phase_pay, phase_validate
from sgame.core.spec import parse_scenario
from sgame.core.state import StateBuilder, initial_state

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 3, action_points: 2 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100 }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 30, intel: 5 } }
  - { id: b, title: "Б", start: { budget: 30, intel: 5 } }
actions:
  - { id: cheap, title: "Дёшево", cost: { budget: 10 }, effects: [] }
  - { id: pricey, title: "Дорого", cost: { budget: 25 }, effects: [] }
  - { id: gated, title: "Условное", requires: "self.intel >= 10", effects: [] }
  - { id: strike, title: "Удар", target: faction, effects: [] }
  - { id: heavy, title: "Тяжёлое", ap: 2, effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
""")


def builder():
    return StateBuilder(SPEC, initial_state(SPEC))


def test_accepts_valid_order():
    accepted, events = phase_validate(SPEC, builder(), {"a": [Order(action="cheap")]})
    assert len(accepted) == 1
    assert events == []


def test_rejects_unknown_action():
    accepted, events = phase_validate(SPEC, builder(), {"a": [Order(action="nope")]})
    assert accepted == []
    assert events[0].kind == "order_rejected"
    assert events[0].audience == "actor"
    assert "nope" in events[0].detail


def test_rejects_when_requires_is_false():
    _, events = phase_validate(SPEC, builder(), {"a": [Order(action="gated")]})
    assert "условие" in events[0].detail


def test_rejects_when_action_points_exhausted():
    orders = {"a": [Order(action="heavy"), Order(action="cheap")]}
    accepted, events = phase_validate(SPEC, builder(), orders)
    assert [x.order.action for x in accepted] == ["heavy"]
    assert "очк" in events[0].detail


def test_rejects_unaffordable_second_order():
    orders = {"a": [Order(action="pricey"), Order(action="cheap")]}
    accepted, events = phase_validate(SPEC, builder(), orders)
    assert [x.order.action for x in accepted] == ["pricey"]
    assert "хватает" in events[0].detail


def test_rejects_targeted_action_without_target():
    _, events = phase_validate(SPEC, builder(), {"a": [Order(action="strike")]})
    assert "цель" in events[0].detail


def test_rejects_targeting_self():
    _, events = phase_validate(SPEC, builder(), {"a": [Order(action="strike", target="a")]})
    assert "себя" in events[0].detail


def test_payment_subtracts_cost():
    work = builder()
    accepted, _ = phase_validate(SPEC, work, {"a": [Order(action="cheap")]})
    events = phase_pay(SPEC, work, accepted)
    assert work.track("a", "budget") == 20
    assert events[0].audience == "actor"
