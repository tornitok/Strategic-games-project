"""Проекторный экран и разбор полётов."""

from fastapi import APIRouter, Request

from ...core.scoring import role_score, score
from ...core.state import initial_state
from ...narrate.changes import changes_between
from ...narrate.news import news_items
from ...narrate.reference import action_card, track_cards
from ...session.replay import states
from .. import live, present
from ..app import language_of, page

router = APIRouter()


@router.get("/screen")
def projector(request: Request):
    session = live.require()
    lang = language_of(request)
    spec = live.display_spec(lang)
    state = live.state()
    rounds = session.journal.rounds

    items: list = []
    changes: list = []
    if rounds:
        snapshots = states(session.journal)
        items = news_items(spec, live.last_events(), viewer=None,
                           role="public", lang=lang)
        changes = changes_between(
            spec, snapshots[-2], snapshots[-1], viewer=None
        )

    return page(
        request,
        "screen.html",
        {
            "spec": spec,
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
    lang = language_of(request)
    spec = live.display_spec(lang)
    state = live.state()
    results = []
    for slot in session.journal.teams:
        total, breakdown = score(spec, state, slot.faction, lang)
        faction_spec = spec.faction(slot.faction)
        results.append(
            {
                "title": faction_spec.title,
                "team": slot.team,
                "total": total,
                "breakdown": breakdown,
                "roles": [
                    {
                        "title": role.title,
                        "total": role_score(spec, state, slot.faction, role.id, lang)[0],
                        "goals": [
                            g for g, _ in role_score(spec, state, slot.faction, role.id, lang)[1]
                        ],
                    }
                    for role in faction_spec.roles
                ],
            }
        )
    results.sort(key=lambda row: row["total"], reverse=True)

    timeline = [
        {
            "n": record.n,
            "public": record.narration.get("public", ""),
            "host": record.narration.get("host", ""),
            "votes": [
                {
                    "side": spec.faction(p.faction).title,
                    "what": (spec.action(p.action).title if spec.action(p.action) else p.action),
                    "author": (
                        spec.faction(p.faction).role(p.author).title
                        if spec.faction(p.faction) and spec.faction(p.faction).role(p.author)
                        else p.author
                    ),
                    "passed": p.passed,
                    "for": [
                        spec.faction(p.faction).role(r).title
                        for r, v in p.votes.items()
                        if v and spec.faction(p.faction).role(r)
                    ],
                    "against": [
                        spec.faction(p.faction).role(r).title
                        for r, v in p.votes.items()
                        if not v and spec.faction(p.faction).role(r)
                    ],
                }
                for p in record.proposals
            ],
            "intents": [
                (spec.faction(faction).title, order.action, order.intent)
                for faction, orders in sorted(record.orders.items())
                for order in orders
                if order.intent
            ],
        }
        for record in session.journal.rounds
    ]

    return page(
        request,
        "debrief.html",
        {"spec": spec, "results": results, "timeline": timeline},
    )


@router.get("/intro")
def intro(request: Request):
    """Общая вводная: мир плюс памятка правил, собранная из сценария."""
    lang = language_of(request)
    spec = live.display_spec(lang)
    return page(
        request,
        "intro.html",
        {
            "spec": spec,
            "intro": present.paragraphs(spec.meta.intro),
            "tracks": track_cards(spec, lang),
            # Формулы считаем при начальных условиях: «зависит от обстановки»
            # в справочнике не помогает принять решение.
            "actions": [
                action_card(
                    spec, action,
                    state=initial_state(spec),
                    actor=spec.factions[0].id,
                    target=spec.factions[1].id if len(spec.factions) > 1 else None,
                    lang=lang,
                )
                for action in spec.actions
            ],
            "deals": spec.deals,
            "has_secrets": any(a.visibility == "secret" for a in spec.actions),
            "has_counters": any(a.countered_by for a in spec.actions),
            "has_rumours": bool(spec.rumours.templates),
        },
    )
