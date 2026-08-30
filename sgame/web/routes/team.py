"""Экран команды. Единственное место, где команда что-либо вводит."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...core.orders import DealOffer, Order
from ...narrate.changes import changes_between
from ...narrate.news import news_items
from ... import __name__ as _pkg  # noqa: F401
from ...i18n import t
from ...narrate.reference import action_card
from ...narrate.news import news_items
from ...narrate.view import tracks_for
from ...session.replay import states
from .. import config, live, present
from ..app import language_of, page

router = APIRouter()

COOKIE = "sgame_team"
ROLE_COOKIE = "sgame_role"


def _role_authorised(request: Request, faction: str, role: str) -> bool:
    session = live.current()
    if session is None:
        return False
    slot = session.journal.slot(faction)
    if slot is None:
        return False
    expected = slot.role_code(role)
    return bool(expected) and request.cookies.get(ROLE_COOKIE) == f"{faction}:{role}:{expected}"


def _authorised(request: Request, faction: str) -> bool:
    session = live.current()
    if session is None or faction in session.submitted:
        return False
    slot = session.journal.slot(faction)
    return slot is not None and request.cookies.get(COOKIE) == f"{faction}:{slot.code}"


@router.get("/team/{faction}")
def screen(request: Request, faction: str):
    session = live.require()
    lang = language_of(request)
    spec = live.display_spec(lang)
    if spec.faction(faction) and spec.faction(faction).roles:
        # У стороны с ролями общего экрана нет: каждый входит под своей
        # должностью, иначе тайные цели теряют смысл.
        return page(
            request,
            "role_picker.html",
            {"spec": spec, "faction": spec.faction(faction)},
        )
    if not _authorised(request, faction):
        return page(
            request,
            "team_login.html",
            {"faction": faction, "title": spec.faction(faction).title, "error": ""},
        )

    state = live.state()
    draft = session.drafts.get(faction, [])
    return page(
        request,
        "team.html",
        {
            "spec": spec,
            "faction": spec.faction(faction),
            "briefing": present.paragraphs(spec.faction(faction).briefing),
            "state": state,
            "tracks": tracks_for(spec, state, faction),
            "options": present.action_options(spec, state, faction, draft),
            "cards": {
                action.id: action_card(
                    spec, action, state=state, actor=faction,
                    target=next((f.id for f in spec.factions if f.id != faction), None),
                    lang=lang,
                )
                for action in spec.actions
            },
            "draft": draft,
            "points_left": present.points_left(spec, draft),
            "others": [f for f in spec.factions if f.id != faction],
            "items": news_items(spec, live.last_events(), viewer=faction,
                                role="team", lang=lang)
            if session.journal.rounds
            else [],
            "changes": changes_between(
                spec, *states(session.journal)[-2:], viewer=faction
            )
            if session.journal.rounds
            else [],
            "incoming": [o for o in state.pending_offers if o.receiver == faction],
            "deals": spec.deals,
            "autohide": not config.NETWORK,
        },
    )


@router.post("/team/{faction}/login")
def login(request: Request, faction: str, code: str = Form(...)):
    session = live.require()
    lang = language_of(request)
    spec = live.display_spec(lang)
    slot = session.journal.slot(faction)
    misses = session.wrong_codes.get(faction, 0)
    if misses >= 3:
        # В аудиторской сети код — единственная защита; перебор должен упираться
        # в паузу, иначе десять тысяч вариантов кончатся за минуту.
        return page(
            request,
            "team_login.html",
            {"faction": faction, "title": spec.faction(faction).title,
             "error": t("team.too_many_tries", lang)},
        )
    if slot is None or slot.code != code.strip().upper():
        session.wrong_codes[faction] = misses + 1
        return page(
            request,
            "team_login.html",
            {
                "faction": faction,
                "title": spec.faction(faction).title,
                "error": t("team.wrong_code", lang),
            },
        )
    session.wrong_codes.pop(faction, None)
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
    spec = live.display_spec(language_of(request))
    waiting = [s for s in session.journal.teams if s.faction not in session.submitted]
    return page(
        request,
        "team_done.html",
        {"next_team": spec.faction(waiting[0].faction).title if waiting else None},
    )


def _role_context(request: Request, faction: str, role_id: str) -> dict:
    """Всё, что видит роль: обстановка команды плюс своё личное и голосования."""
    session = live.require()
    lang = language_of(request)
    spec = live.display_spec(lang)
    state = live.state()
    faction_spec = spec.faction(faction)
    role = faction_spec.role(role_id)
    others = [f for f in spec.factions if f.id != faction]

    proposals = []
    for proposal in session.proposals.get(faction, []):
        counted = live.tally_of(faction, proposal.id)
        action = spec.action(proposal.action)
        proposals.append(
            {
                "id": proposal.id,
                "title": action.title if action else proposal.action,
                "target": spec.faction(proposal.target).title if proposal.target else "",
                "author": faction_spec.role(proposal.author).title
                if faction_spec.role(proposal.author)
                else proposal.author,
                "intent": proposal.intent,
                "given": counted.given,
                "needed": counted.needed,
                "passed": counted.passed,
                "waiting": counted.waiting,
                "my_vote": proposal.votes.get(role_id),
            }
        )

    waiting_roles = [
        faction_spec.role(r).title for r in live.waiting_for(faction) if faction_spec.role(r)
    ]
    return {
        "spec": spec,
        "faction": faction_spec,
        "role": role,
        "state": state,
        "briefing": present.paragraphs(faction_spec.briefing),
        "role_briefing": present.paragraphs(role.briefing if role else ""),
        "tracks": tracks_for(spec, state, faction),
        "options": present.action_options(
            spec, state, faction, live.accepted_orders(faction), role=role_id
        ),
        "cards": {
            action.id: action_card(
                spec, action, state=state, actor=faction,
                target=others[0].id if others else None, lang=lang,
            )
            for action in spec.actions
            if role is None or role.can_propose(action.id)
        },
        "others": others,
        "proposals": proposals,
        "points_left": present.points_left(spec, live.accepted_orders(faction)),
        "waiting_roles": waiting_roles,
        "i_am_ready": role_id in session.ready.get(faction, set()),
        "items": news_items(spec, live.last_events(), viewer=faction, role="team", lang=lang)
        if session.journal.rounds
        else [],
        "autohide": not config.NETWORK,
    }


@router.get("/team/{faction}/{role_id}")
def role_screen(request: Request, faction: str, role_id: str):
    session = live.require()
    spec = live.display_spec(language_of(request))
    faction_spec = spec.faction(faction)
    if faction_spec is None or faction_spec.role(role_id) is None:
        return RedirectResponse(f"/team/{faction}", status_code=303)
    if not _role_authorised(request, faction, role_id):
        return page(
            request,
            "role_login.html",
            {"faction": faction_spec, "role": faction_spec.role(role_id), "error": ""},
        )
    return page(request, "role.html", _role_context(request, faction, role_id))


@router.post("/team/{faction}/{role_id}/login")
def role_login(request: Request, faction: str, role_id: str, code: str = Form(...)):
    session = live.require()
    spec = live.display_spec(language_of(request))
    faction_spec = spec.faction(faction)
    slot = session.journal.slot(faction)
    expected = slot.role_code(role_id) if slot else None
    if not expected or expected != code.strip().upper():
        return page(
            request,
            "role_login.html",
            {
                "faction": faction_spec,
                "role": faction_spec.role(role_id),
                "error": t("team.wrong_code", language_of(request)),
            },
        )
    response = RedirectResponse(f"/team/{faction}/{role_id}", status_code=303)
    response.set_cookie(ROLE_COOKIE, f"{faction}:{role_id}:{expected}",
                        httponly=True, samesite="strict")
    return response


@router.post("/team/{faction}/{role_id}/propose")
def role_propose(
    request: Request,
    faction: str,
    role_id: str,
    action: str = Form(...),
    target: str = Form(default=""),
    intent: str = Form(default=""),
):
    if _role_authorised(request, faction, role_id):
        live.propose(faction, role_id, action=action, target=target or None, intent=intent)
    return RedirectResponse(f"/team/{faction}/{role_id}", status_code=303)


@router.post("/team/{faction}/{role_id}/vote")
def role_vote(
    request: Request,
    faction: str,
    role_id: str,
    proposal: str = Form(...),
    support: str = Form(default=""),
):
    if _role_authorised(request, faction, role_id):
        live.vote(faction, role_id, proposal, bool(support))
    return RedirectResponse(f"/team/{faction}/{role_id}", status_code=303)


@router.post("/team/{faction}/{role_id}/ready")
def role_ready(request: Request, faction: str, role_id: str):
    if _role_authorised(request, faction, role_id):
        live.mark_ready(faction, role_id)
    return RedirectResponse(f"/team/{faction}/{role_id}", status_code=303)
