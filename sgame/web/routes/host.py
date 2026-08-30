"""Пульт ведущего."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from ...core.errors import ScenarioError
from ...i18n import t
from ...core.spec import parse_scenario
from ...session.paths import all_scenarios
from .. import live
from .. import config
from ..app import LANG_COOKIE, chosen_language, language_of, local_address, page

router = APIRouter()


@router.get("/")
def console(request: Request):
    session = live.current()
    if session is None:
        scenarios = {}
        for key, text in all_scenarios(chosen_language(request)).items():
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
    spec = live.display_spec(lang)
    message = (
        t("host.pass_computer", lang, team=spec.faction(waiting[0].faction).title)
        if waiting
        else t("host.all_submitted", lang)
    )
    return page(
        request,
        "host.html",
        {
            "spec": spec,
            "state": state,
            "teams": session.journal.teams,
            "submitted": session.submitted,
            "all_submitted": not waiting,
            "can_undo": bool(session.journal.rounds),
            "next_team_message": message,
            "network": config.NETWORK,
            "base_url": f"http://{local_address()}:{request.url.port or 80}",
        },
    )


@router.get("/qr/{faction}.svg")
def team_qr(request: Request, faction: str):
    """QR со ссылкой на экран команды: набирать адрес на телефоне — это опечатки."""
    import io

    import segno
    from fastapi.responses import Response

    from ..app import local_address

    port = request.url.port or 80
    url = f"http://{local_address()}:{port}/team/{faction}"
    buffer = io.BytesIO()
    segno.make(url, error="m").save(
        buffer, kind="svg", scale=4, dark="#111111", light="#ffffff", xmldecl=True
    )
    return Response(buffer.getvalue(), media_type="image/svg+xml")


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
    live.start(scenario, seed, chosen_language(request))
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
