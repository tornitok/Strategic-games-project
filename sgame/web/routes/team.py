"""Экран команды. Единственное место, где команда что-либо вводит."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...core.orders import DealOffer, Order
from ...narrate.changes import changes_between
from ...narrate.news import news_items
from ...narrate.reference import action_card
from ...narrate.view import tracks_for
from ...session.replay import states
from .. import live, present
from ..app import templates

router = APIRouter()

COOKIE = "sgame_team"


def _authorised(request: Request, faction: str) -> bool:
    session = live.current()
    if session is None or faction in session.submitted:
        return False
    slot = session.journal.slot(faction)
    return slot is not None and request.cookies.get(COOKIE) == f"{faction}:{slot.code}"


@router.get("/team/{faction}")
def screen(request: Request, faction: str):
    session = live.require()
    if not _authorised(request, faction):
        return templates.TemplateResponse(
            request,
            "team_login.html",
            {"faction": faction, "title": session.spec.faction(faction).title, "error": ""},
        )

    state = live.state()
    draft = session.drafts.get(faction, [])
    return templates.TemplateResponse(
        request,
        "team.html",
        {
            "spec": session.spec,
            "faction": session.spec.faction(faction),
            "briefing": present.paragraphs(session.spec.faction(faction).briefing),
            "state": state,
            "tracks": tracks_for(session.spec, state, faction),
            "options": present.action_options(session.spec, state, faction, draft),
            "cards": {
                action.id: action_card(
                    session.spec, action, state=state, actor=faction,
                    target=next((f.id for f in session.spec.factions if f.id != faction), None),
                )
                for action in session.spec.actions
            },
            "draft": draft,
            "points_left": present.points_left(session.spec, draft),
            "others": [f for f in session.spec.factions if f.id != faction],
            "items": news_items(session.spec, live.last_events(), viewer=faction, role="team")
            if session.journal.rounds
            else [],
            "changes": changes_between(
                session.spec, *states(session.journal)[-2:], viewer=faction
            )
            if session.journal.rounds
            else [],
            "incoming": [o for o in state.pending_offers if o.receiver == faction],
            "deals": session.spec.deals,
        },
    )


@router.post("/team/{faction}/login")
def login(request: Request, faction: str, code: str = Form(...)):
    session = live.require()
    slot = session.journal.slot(faction)
    if slot is None or slot.code != code:
        return templates.TemplateResponse(
            request,
            "team_login.html",
            {
                "faction": faction,
                "title": session.spec.faction(faction).title,
                "error": "Неверный код команды",
            },
        )
    response = RedirectResponse(f"/team/{faction}", status_code=303)
    response.set_cookie(COOKIE, f"{faction}:{slot.code}", httponly=True, samesite="strict")
    return response


@router.post("/team/{faction}/order")
def add_order(
    request: Request,
    faction: str,
    action: str = Form(...),
    target: str = Form(default=""),
    intent: str = Form(default=""),
):
    if _authorised(request, faction):
        session = live.require()
        session.drafts.setdefault(faction, []).append(
            Order(action=action, target=target or None, intent=intent)
        )
    return RedirectResponse(f"/team/{faction}", status_code=303)


@router.post("/team/{faction}/order/remove")
def remove_order(request: Request, faction: str, index: int = Form(...)):
    if _authorised(request, faction):
        draft = live.require().drafts.get(faction, [])
        if 0 <= index < len(draft):
            draft.pop(index)
    return RedirectResponse(f"/team/{faction}", status_code=303)


@router.post("/team/{faction}/offer")
def make_offer(
    request: Request,
    faction: str,
    deal: str = Form(...),
    receiver: str = Form(...),
    amount: str = Form(default=""),
):
    if _authorised(request, faction):
        session = live.require()
        session.offers.append(
            DealOffer(
                id=f"{faction}:{len(session.offers)}",
                deal=deal,
                sender=faction,
                receiver=receiver,
                amount=float(amount) if amount else None,
            )
        )
    return RedirectResponse(f"/team/{faction}", status_code=303)


@router.post("/team/{faction}/response")
def respond(request: Request, faction: str, offer: str = Form(...), accept: str = Form(default="")):
    if _authorised(request, faction):
        live.require().responses[offer] = bool(accept)
    return RedirectResponse(f"/team/{faction}", status_code=303)


@router.post("/team/{faction}/submit")
def submit(request: Request, faction: str):
    if _authorised(request, faction):
        live.submit(faction)
    response = RedirectResponse(f"/team/{faction}/done", status_code=303)
    response.delete_cookie(COOKIE)
    return response


@router.get("/team/{faction}/done")
def done(request: Request, faction: str):
    session = live.require()
    waiting = [s for s in session.journal.teams if s.faction not in session.submitted]
    return templates.TemplateResponse(
        request,
        "team_done.html",
        {"next_team": session.spec.faction(waiting[0].faction).title if waiting else None},
    )
