from datetime import datetime

from sgame.core.orders import Order
from sgame.session import journal as J
from sgame.session.replay import current_state, replay, scenario_changed, undo_last

TEXT = """
schema_version: 1
meta: { id: t, title: "Т", rounds: 5, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 200 }
world: {}
factions:
  - { id: a, title: "А", start: { budget: 100 } }
  - { id: b, title: "Б", start: { budget: 100 } }
actions:
  - { id: spend, title: "Трата", cost: { budget: 10 }, effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""


def journal_with(rounds):
    journal = J.new_journal("t", TEXT, [J.TeamSlot("a", "Команда 1", "1111")], seed=5)
    for n, orders in enumerate(rounds, start=1):
        journal.rounds.append(
            J.RoundRecord(n=n, orders=orders, resolved_at=datetime.now().isoformat())
        )
    return journal


def test_replay_folds_rounds_into_state():
    journal = journal_with([{"a": [Order(action="spend")]}, {"a": [Order(action="spend")]}])
    state, per_round = current_state(journal), replay(journal)[1]
    assert state.tracks["a"]["budget"] == 80
    assert state.round == 3
    assert len(per_round) == 2


def test_replay_is_repeatable():
    journal = journal_with([{"a": [Order(action="spend")]}])
    assert replay(journal)[0].tracks == replay(journal)[0].tracks


def test_undo_returns_previous_state():
    journal = journal_with([{"a": [Order(action="spend")]}, {"a": [Order(action="spend")]}])
    undo_last(journal)
    assert len(journal.rounds) == 1
    assert current_state(journal).tracks["a"]["budget"] == 90


def test_undo_then_same_orders_reproduce_state():
    journal = journal_with([{"a": [Order(action="spend")]}, {"a": [Order(action="spend")]}])
    before = current_state(journal).tracks
    undo_last(journal)
    journal.rounds.append(J.RoundRecord(n=2, orders={"a": [Order(action="spend")]}))
    assert current_state(journal).tracks == before


def test_detects_changed_scenario():
    journal = journal_with([])
    assert scenario_changed(journal, TEXT) is False
    assert scenario_changed(journal, TEXT + "\n# правка\n") is True
