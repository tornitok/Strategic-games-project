"""Пульт ведущего."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...core.errors import ScenarioError
from ...core.spec import parse_scenario
from ...session.paths import all_scenarios
from .. import live
from ..app import templates

router = APIRouter()


@router.get("/")
def console(request: Request):
    session = live.current()
    if session is None:
        scenarios = {}
        for key, text in all_scenarios().items():
            try:
                scenarios[key] = parse_scenario(text).meta.title
            except ScenarioError:
                continue  # битый пользовательский файл не должен ломать стартовую страницу
        return templates.TemplateResponse(
            request, "start.html", {"scenarios": scenarios, "default_seed": 20260901}
        )

    state = live.state()
    waiting = [
        slot for slot in session.journal.teams if slot.faction not in session.submitted
    ]
    message = (
        f"Передайте компьютер: {session.spec.faction(waiting[0].faction).title}"
        if waiting
        else "Все команды сдали приказы — можно закрывать раунд"
    )
    return templates.TemplateResponse(
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


@router.post("/session/new")
def new_session(scenario: str = Form(...), seed: int = Form(...)):
    live.start(scenario, seed)
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
