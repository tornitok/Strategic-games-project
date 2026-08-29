"""Проекторный экран и разбор полётов."""

from fastapi import APIRouter, Request

from ...core.scoring import score
from ...core.state import initial_state
from ...narrate.changes import changes_between
from ...narrate.news import news_items
from ...narrate.reference import action_card, track_cards
from ...session.replay import states
from .. import live, present
from ..app import templates

router = APIRouter()


@router.get("/screen")
def projector(request: Request):
    session = live.require()
    state = live.state()
    rounds = session.journal.rounds

    items: list = []
    changes: list = []
    if rounds:
        snapshots = states(session.journal)
        items = news_items(session.spec, live.last_events(), viewer=None, role="public")
        changes = changes_between(
            session.spec, snapshots[-2], snapshots[-1], viewer=None
        )

    return templates.TemplateResponse(
        request,
        "screen.html",
        {
            "spec": session.spec,
            "state": state,
            "items": items,
            "changes": changes,
            "shown_round": rounds[-1].n if rounds else state.round,
            "started": bool(rounds),
        },
    )


@router.get("/debrief")
def debrief(request: Request):
    session = live.require()
    state = live.state()
    results = []
    for slot in session.journal.teams:
        total, breakdown = score(session.spec, state, slot.faction)
        results.append(
            {
                "title": session.spec.faction(slot.faction).title,
                "team": slot.team,
                "total": total,
                "breakdown": breakdown,
            }
        )
    results.sort(key=lambda row: row["total"], reverse=True)

    timeline = [
        {
            "n": record.n,
            "public": record.narration.get("public", ""),
            "host": record.narration.get("host", ""),
            "intents": [
                (session.spec.faction(faction).title, order.action, order.intent)
                for faction, orders in sorted(record.orders.items())
                for order in orders
                if order.intent
            ],
        }
        for record in session.journal.rounds
    ]

    return templates.TemplateResponse(
        request,
        "debrief.html",
        {"spec": session.spec, "results": results, "timeline": timeline},
    )


@router.get("/intro")
def intro(request: Request):
    """Общая вводная: мир плюс памятка правил, собранная из сценария."""
    session = live.require()
    spec = session.spec
    return templates.TemplateResponse(
        request,
        "intro.html",
        {
            "spec": spec,
            "intro": present.paragraphs(spec.meta.intro),
            "tracks": track_cards(spec),
            # Формулы считаем при начальных условиях: «зависит от обстановки»
            # в справочнике не помогает принять решение.
            "actions": [
                action_card(
                    spec, action,
                    state=initial_state(spec),
                    actor=spec.factions[0].id,
                    target=spec.factions[1].id if len(spec.factions) > 1 else None,
                )
                for action in spec.actions
            ],
            "deals": spec.deals,
            "has_secrets": any(a.visibility == "secret" for a in spec.actions),
            "has_counters": any(a.countered_by for a in spec.actions),
            "has_rumours": bool(spec.rumours.templates),
        },
    )
