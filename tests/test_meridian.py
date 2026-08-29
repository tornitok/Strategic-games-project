import json
import os
from pathlib import Path

from sgame.core.orders import Order
from sgame.core.scoring import score
from sgame.core.spec import parse_scenario, scenario_lines
from sgame.core.validate import validate_scenario
from sgame.session import journal as J
from sgame.session.paths import builtin_scenarios
from sgame.session.replay import replay

GOLDEN = Path(__file__).parent / "golden" / "meridian.json"

SCRIPT = [
    {"astoria": [("mobilize", None), ("intel_work", None)],
     "borea": [("show_force", "astoria"), ("propaganda", None)],
     "caldera": [("invest", None), ("diplomacy", "astoria")],
     "delta": [("intel_work", None), ("propaganda", None)]},
    {"astoria": [("cyber_defense", None), ("diplomacy", "caldera")],
     "borea": [("cyber_op", "astoria"), ("mobilize", None)],
     "caldera": [("invest", None), ("aid", "delta")],
     "delta": [("covert_support", "borea")]},
    {"astoria": [("blockade", "borea")],
     "borea": [("sanctions", "astoria"), ("intel_work", None)],
     "caldera": [("deescalate", None), ("diplomacy", "borea")],
     "delta": [("propaganda", None), ("invest", None)]},
    {"astoria": [("deescalate", None), ("invest", None)],
     "borea": [("demobilize", None)],
     "caldera": [("invest", None)],
     "delta": [("cyber_op", "caldera")]},
    {"astoria": [("propaganda", None)],
     "borea": [("diplomacy", "astoria")],
     "caldera": [("aid", "astoria")],
     "delta": [("intel_work", None), ("propaganda", None)]},
    {"astoria": [("invest", None)],
     "borea": [("invest", None)],
     "caldera": [("invest", None)],
     "delta": [("invest", None)]},
    {"astoria": [("mobilize", None)],
     "borea": [("show_force", "caldera")],
     "caldera": [("deescalate", None)],
     "delta": [("covert_support", "astoria")]},
    {"astoria": [("diplomacy", "borea")],
     "borea": [("diplomacy", "astoria")],
     "caldera": [("invest", None)],
     "delta": [("propaganda", None)]},
]


def build_journal():
    text = builtin_scenarios()["meridian"]
    teams = [
        J.TeamSlot(faction=f.id, team=f"Команда {i}", code=f"100{i}")
        for i, f in enumerate(parse_scenario(text).factions, start=1)
    ]
    journal = J.new_journal("meridian", text, teams, seed=20260901)
    for number, round_orders in enumerate(SCRIPT, start=1):
        journal.rounds.append(
            J.RoundRecord(
                n=number,
                orders={
                    faction: [Order(action=a, target=t) for a, t in items]
                    for faction, items in round_orders.items()
                },
            )
        )
    return journal


def snapshot():
    journal = build_journal()
    spec = parse_scenario(journal.scenario_text)
    state, history = replay(journal)
    return {
        "tracks": state.tracks,
        "world": state.world,
        "relations": {f"{a}|{b}": value for (a, b), value in sorted(state.relations.items())},
        "finished": state.finished,
        "scores": {f.id: score(spec, state, f.id)[0] for f in spec.factions},
        "rounds": [
            [f"{e.kind}:{e.actor}:{e.title}:{e.roll}:"
             + ",".join(d.describe() for d in e.deltas) for e in events]
            for events in history
        ],
    }


def test_scenario_passes_validator():
    text = builtin_scenarios()["meridian"]
    spec = parse_scenario(text)
    assert validate_scenario(spec, scenario_lines(text)) == []


def test_scenario_is_big_enough_for_a_class():
    spec = parse_scenario(builtin_scenarios()["meridian"])
    assert len(spec.factions) == 4
    assert len(spec.actions) >= 12
    assert len(spec.events) >= 6
    assert all(f.briefing.strip() and f.goals for f in spec.factions)


def test_full_game_matches_golden_run():
    actual = json.dumps(snapshot(), ensure_ascii=False, indent=2, sort_keys=True)
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(actual, encoding="utf-8")
    assert actual == GOLDEN.read_text(encoding="utf-8")


def test_game_finishes_and_nobody_is_wiped_out():
    journal = build_journal()
    state, _ = replay(journal)
    assert state.finished is True
    for faction in state.tracks.values():
        assert faction["legitimacy"] > 0


def test_round_resolves_faster_than_a_second():
    """Нефункциональное требование спеки: на паре не должно быть паузы."""
    import time

    from sgame.core.resolve import resolve
    from sgame.core.state import initial_state

    journal = build_journal()
    spec = parse_scenario(journal.scenario_text)
    orders = journal.rounds[0].orders
    started = time.perf_counter()
    resolve(spec, initial_state(spec), orders, [], {}, journal.seed)
    assert time.perf_counter() - started < 1.0


def test_no_single_strategy_dominates():
    """Разброс очков между сторонами не должен превращать игру в предрешённую."""
    journal = build_journal()
    spec = parse_scenario(journal.scenario_text)
    state, _ = replay(journal)
    totals = sorted(score(spec, state, f.id)[0] for f in spec.factions)
    assert totals[-1] - totals[0] < totals[-1] * 0.6
