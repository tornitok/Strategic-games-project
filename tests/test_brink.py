"""Баланс сценария «У края».

Проверяем не числа, а свойства: жёсткая линия опасна, сдержанность работает,
и ни одна стратегия не выигрывает сама собой.
"""

from sgame.core.orders import Order
from sgame.core.resolve import resolve
from sgame.core.scoring import score
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state
from sgame.session.paths import builtin_scenarios

SPEC = parse_scenario(builtin_scenarios()["brink"])

HAWK_A = ["ultimatum:vellan", "mobilize", "alert", "sanctions:vellan"]
HAWK_V = ["ultimatum:arcadia", "mobilize", "alert", "sanctions:arcadia"]
RESTRAINT = {
    "arcadia": ["talks:vellan", "support_trade", "gesture:vellan", "address"],
    "vellan": ["talks:arcadia", "standdown", "gesture:arcadia", "address"],
    "surat": ["mediate", "support_trade", "talks:norland", "address"],
    "norland": ["intel_work", "address", "talks:surat", "support_trade"],
}
HARDLINE = {
    "arcadia": HAWK_A,
    "vellan": HAWK_V,
    "surat": ["mediate", "support_trade", "talks:arcadia", "talks:vellan"],
    "norland": ["ultimatum:surat", "alert", "mobilize", "intel_work"],
}


def play(plan, seed):
    state = initial_state(SPEC)
    for _ in range(SPEC.meta.rounds):
        orders = {
            faction: [
                Order(action=move.split(":")[0], target=(move.split(":")[1] if ":" in move else None))
                for move in moves
            ]
            for faction, moves in plan.items()
        }
        state = resolve(SPEC, state, orders, [], {}, seed).state
        if state.finished:
            break
    return state


def test_restraint_keeps_the_crisis_low():
    for seed in (11, 42, 77):
        assert play(RESTRAINT, seed).world["escalation"] < 40


def test_hardline_pushes_the_world_to_the_edge():
    peaks = [play(HARDLINE, seed).world["escalation"] for seed in (11, 42, 77)]
    assert all(value > 80 for value in peaks)


def test_hardline_does_not_pay_off():
    """Ястреб среди умеренных не должен выигрывать за чужой счёт."""
    plan = {**RESTRAINT, "arcadia": HAWK_A}
    state = play(plan, seed=42)
    scores = {f.id: score(SPEC, state, f.id)[0] for f in SPEC.factions}
    assert scores["arcadia"] < max(scores.values())


def test_nobody_is_wiped_out_under_restraint():
    state = play(RESTRAINT, seed=11)
    for faction in state.tracks.values():
        assert faction["economy"] > 0
        assert faction["legitimacy"] > 0


def test_scores_are_not_predetermined():
    state = play(RESTRAINT, seed=11)
    totals = sorted(score(SPEC, state, f.id)[0] for f in SPEC.factions)
    assert totals[-1] - totals[0] < totals[-1] * 0.6
