"""Формат партии второй версии: роли, предложения и голоса."""

import json

from sgame.core.orders import Order
from sgame.session import journal as J


def journal_with_roles():
    journal = J.new_journal(
        "t", "schema_version: 1\n",
        [J.TeamSlot(faction="a", team="Команда 1", code="1234",
                    roles=[J.RoleSlot(role="president", code="AB12"),
                           J.RoleSlot(role="defence", code="CD34")])],
        seed=5,
    )
    journal.rounds.append(
        J.RoundRecord(
            n=1,
            orders={"a": [Order(action="build")]},
            proposals=[J.ProposalRecord(id="p1", faction="a", action="build", target=None,
                                        author="president", intent="строим",
                                        votes={"president": True, "defence": False},
                                        passed=True)],
        )
    )
    return journal


def test_roles_have_their_own_codes():
    journal = journal_with_roles()
    slot = journal.slot("a")
    assert [r.role for r in slot.roles] == ["president", "defence"]
    assert slot.role_code("defence") == "CD34"


def test_roundtrip_keeps_proposals_and_votes(tmp_path):
    path = tmp_path / "s.json"
    J.save(path, journal_with_roles())
    loaded = J.load(path)
    proposal = loaded.rounds[0].proposals[0]
    assert proposal.author == "president"
    assert proposal.votes == {"president": True, "defence": False}
    assert proposal.passed is True
    assert loaded.slot("a").role_code("president") == "AB12"


def test_format_version_is_two():
    assert J.FORMAT == 2
    assert J.to_dict(journal_with_roles())["format"] == 2


def test_first_version_files_still_open(tmp_path):
    """Партии, сыгранные до появления ролей, должны открываться и играться."""
    old = {
        "format": 1,
        "scenario_id": "t",
        "scenario_sha256": "0" * 64,
        "scenario_text": "schema_version: 1\n",
        "seed": 5,
        "created_at": "2026-08-01T10:00:00",
        "teams": [{"faction": "a", "team": "Команда 1", "code": "1234"}],
        "rounds": [{"n": 1, "orders": {"a": [{"action": "build", "target": None, "intent": ""}]},
                    "offers": [], "responses": {}, "narration": {}, "resolved_at": ""}],
    }
    path = tmp_path / "old.json"
    path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    loaded = J.load(path)
    assert loaded.format == J.FORMAT
    assert loaded.slot("a").roles == []
    assert loaded.rounds[0].proposals == []
    assert loaded.rounds[0].orders["a"][0].action == "build"


def test_unknown_future_version_is_refused(tmp_path):
    path = tmp_path / "future.json"
    path.write_text(json.dumps({"format": 99}), encoding="utf-8")
    try:
        J.load(path)
    except ValueError as exc:
        assert "99" in str(exc)
    else:
        raise AssertionError("файл будущей версии должен отвергаться")
