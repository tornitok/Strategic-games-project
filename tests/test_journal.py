from sgame.core.orders import DealOffer, Order
from sgame.session import journal as J
from sgame.session.paths import data_dir, sessions_dir

SCENARIO_TEXT = "schema_version: 1\n"


def test_data_dir_follows_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SGAME_DATA_DIR", str(tmp_path))
    assert data_dir() == tmp_path
    assert sessions_dir().exists()


def test_new_journal_records_hash_and_teams():
    journal = J.new_journal(
        scenario_id="t",
        scenario_text=SCENARIO_TEXT,
        teams=[J.TeamSlot(faction="a", team="Команда 1", code="1234")],
        seed=7,
    )
    assert journal.seed == 7
    assert len(journal.scenario_sha256) == 64
    assert journal.rounds == []


def test_roundtrip_preserves_orders_and_offers(tmp_path):
    journal = J.new_journal("t", SCENARIO_TEXT, [J.TeamSlot("a", "Команда 1", "1234")], 7)
    journal.rounds.append(
        J.RoundRecord(
            n=1,
            orders={"a": [Order(action="grow", target="b", intent="растём")]},
            offers=[DealOffer(id="o1", deal="pact", sender="a", receiver="b", amount=None)],
            responses={"o0": True},
            narration={"public": "текст", "private": {"a": "своё"}},
            resolved_at="2026-09-01T10:00:00",
        )
    )
    path = tmp_path / "s.json"
    J.save(path, journal)
    loaded = J.load(path)
    assert loaded.rounds[0].orders["a"][0].intent == "растём"
    assert loaded.rounds[0].offers[0].deal == "pact"
    assert loaded.rounds[0].narration["private"]["a"] == "своё"


def test_builtin_scenarios_include_meridian():
    assert "meridian" in J.builtin_scenarios()
