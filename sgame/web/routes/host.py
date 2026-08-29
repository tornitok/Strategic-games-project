"""Пульт ведущего."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...core.errors import ScenarioError
from ...i18n import t
from ...core.spec import parse_scenario
from ...session.paths import all_scenarios
from .. import live
from ..app import LANG_COOKIE, language_of, page

router = APIRouter()


@router.get("/")
def console(request: Request):
    session = live.current()
    if session is None:
        scenarios = {}
        for key, text in all_scenarios(language_of(request)).items():
            try:
                scenarios[key] = parse_scenario(text).meta.title
            except ScenarioError:
                continue  # битый пользовательский файл не должен ломать стартовую страницу
        return page(
            request, "start.html", {"scenarios": scenarios, "default_seed": 20260901}
        )

    state = live.state()
    waiting = [
        slot for slot in session.journal.teams if slot.faction not in session.submitted
    ]
    lang = language_of(request)
    message = (
        t("host.pass_computer", lang, team=session.spec.faction(waiting[0].faction).title)
        if waiting
        else t("host.all_submitted", lang)
    )
    return page(
        request,
        "host.html",
        {
            "spec": session.spec,
            "state": state,
            "teams": session.journal.teams,
            "submitted": session.submitted,
            "all_submitted": not waiting,
            "can_undo": bool(session.journal.rounds),
            "next_team_message": message,
        },
    )


@router.get("/language/{lang}")
def switch_language(lang: str, request: Request):
    """Переключить язык и вернуться туда, откуда пришли."""
    from ...i18n import normalise

    back = request.headers.get("referer") or "/"
    response = RedirectResponse(back, status_code=303)
    response.set_cookie(LANG_COOKIE, normalise(lang), max_age=60 * 60 * 24 * 365)
    return response


@router.post("/session/new")
def new_session(request: Request, scenario: str = Form(...), seed: int = Form(...)):
    live.start(scenario, seed, language_of(request))
    return RedirectResponse("/", status_code=303)


@router.post("/round/close")
def close_round(force: str = Form(default="")):
    try:
        live.close_round(force=bool(force))
    except ValueError:
        pass  # не все сдали — просто возвращаем ведущего на пульт
    return RedirectResponse("/", status_code=303)


@router.post("/round/undo")
def undo_round():
    live.undo_round()
    return RedirectResponse("/", status_code=303)
