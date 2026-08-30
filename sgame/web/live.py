"""Активная партия в памяти процесса.

Игра идёт на одной машине, партия одна. Черновики приказов держим на
сервере: закрытая по ошибке вкладка не должна стоить команде хода.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from secrets import choice, randbelow

from ..core.events import Event
from ..core.orders import DealOffer, Order
from ..core.voting import Proposal, Tally, tally
from ..core.resolve import resolve
from ..core.spec import ScenarioSpec, parse_scenario
from ..core.state import GameState
from ..narrate.templates import narrate_host, narrate_public, narrate_team
from ..session import journal as J
from ..i18n import t
from ..session.paths import all_scenarios, sessions_dir
from ..session.replay import current_state, replay, undo_last


@dataclass
class Live:
    path: Path
    journal: J.Journal
    spec: ScenarioSpec
    drafts: dict[str, list[Order]] = field(default_factory=dict)
    offers: list[DealOffer] = field(default_factory=list)
    responses: dict[str, bool] = field(default_factory=dict)
    submitted: set[str] = field(default_factory=set)
    lang: str = "ru"  # язык, на котором идёт эта партия
    wrong_codes: dict[str, int] = field(default_factory=dict)
    proposals: dict[str, list[Proposal]] = field(default_factory=dict)
    proposal_counter: int = 0
    ready: dict[str, set[str]] = field(default_factory=dict)


_live: Live | None = None


def current() -> Live | None:
    return _live


def reset() -> None:
    global _live
    _live = None


# Без похожих знаков: код диктуют вслух и набирают на телефоне.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code() -> str:
    """Код команды. В сети он длиннее: четыре цифры перебираются за секунды."""
    from . import config

    if config.NETWORK:
        return "".join(choice(CODE_ALPHABET) for _ in range(6))
    return f"{randbelow(9000) + 1000}"


def start(scenario_id: str, seed: int, lang: str = "ru") -> Live:
    global _live
    text = all_scenarios(lang)[scenario_id]
    spec = parse_scenario(text)
    teams = [
        J.TeamSlot(
            faction=faction.id,
            team=t("common.team_number", lang, n=number),
            code=new_code(),
            roles=[J.RoleSlot(role=role.id, code=new_code()) for role in faction.roles],
        )
        for number, faction in enumerate(spec.factions, start=1)
    ]
    journal = J.new_journal(scenario_id, text, teams, seed)
    path = sessions_dir() / f"{scenario_id}-{datetime.now():%Y%m%d-%H%M%S}.json"
    J.save(path, journal)
    _live = Live(path=path, journal=journal, spec=spec, lang=lang,
                 drafts={t.faction: [] for t in teams},
                 proposals={t.faction: [] for t in teams})
    return _live


def display_spec(lang: str) -> ScenarioSpec:
    """Сценарий на языке читателя — только для показа текстов.

    Правила и расчёт всегда идут по копии, с которой партия начиналась.
    Копии структурно одинаковы (это проверяет тест сверки), поэтому подменять
    можно безопасно; если чужая копия всё же разошлась по идентификаторам,
    возвращаем исходную — лучше чужой язык, чем пустые названия.
    """
    session = require()
    if lang == session.lang:
        return session.spec
    text = all_scenarios(lang).get(session.journal.scenario_id)
    if not text:
        return session.spec
    try:
        other = parse_scenario(text)
    except Exception:
        return session.spec
    same_shape = [f.id for f in other.factions] == [f.id for f in session.spec.factions] and [
        a.id for a in other.actions
    ] == [a.id for a in session.spec.actions]
    return other if same_shape else session.spec


def has_roles(faction: str) -> bool:
    spec_faction = require().spec.faction(faction)
    return bool(spec_faction and spec_faction.roles)


def mark_ready(faction: str, role: str) -> None:
    """Роль отмечает готовность. Ход уходит, когда готовы все.

    Одна роль не может оборвать обсуждение за остальных.
    """
    session = require()
    session.ready.setdefault(faction, set()).add(role)
    spec_faction = session.spec.faction(faction)
    if spec_faction and session.ready[faction] >= {r.id for r in spec_faction.roles}:
        session.submitted.add(faction)


def waiting_for(faction: str) -> list[str]:
    """Кто ещё не отметил готовность — это показывается всей команде."""
    session = require()
    spec_faction = session.spec.faction(faction)
    if not spec_faction:
        return []
    done = session.ready.get(faction, set())
    return [r.id for r in spec_faction.roles if r.id not in done]


def propose(faction: str, role: str, action: str, target: str | None, intent: str) -> Proposal:
    """Роль предлагает приказ команде. Голосуют по нему все роли стороны."""
    session = require()
    session.proposal_counter += 1
    proposal = Proposal(
        id=f"{faction}:{session.proposal_counter}",
        action=action,
        target=target or None,
        author=role,
        intent=intent,
    )
    session.proposals.setdefault(faction, []).append(proposal)
    return proposal


def vote(faction: str, role: str, proposal_id: str, support: bool) -> None:
    """Голос можно изменить, пока раунд не сдан."""
    for proposal in require().proposals.get(faction, []):
        if proposal.id == proposal_id:
            proposal.votes[role] = support
            return


def proposal_of(faction: str, proposal_id: str) -> Proposal | None:
    return next(
        (p for p in require().proposals.get(faction, []) if p.id == proposal_id), None
    )


def tally_of(faction: str, proposal_id: str) -> Tally:
    session = require()
    roles = session.spec.faction(faction).roles
    proposal = proposal_of(faction, proposal_id)
    return tally(roles, proposal) if proposal else tally(roles, Proposal("", "", None, ""))


def accepted_orders(faction: str) -> list[Order]:
    """Приказы команды: принятые предложения в порядке подачи, в пределах очков."""
    session = require()
    spec_faction = session.spec.faction(faction)
    if not spec_faction or not spec_faction.roles:
        return session.drafts.get(faction, [])

    orders: list[Order] = []
    points = session.spec.meta.action_points
    for proposal in session.proposals.get(faction, []):
        if not tally(spec_faction.roles, proposal).passed:
            continue
        action = session.spec.action(proposal.action)
        if action is None or action.ap > points:
            continue
        points -= action.ap
        orders.append(Order(action=proposal.action, target=proposal.target, intent=proposal.intent))
    return orders


def require() -> Live:
    if _live is None:
        raise LookupError("партия не начата")
    return _live


def state() -> GameState:
    return current_state(require().journal)


def history() -> list[tuple[Event, ...]]:
    return replay(require().journal)[1]


def last_events() -> tuple[Event, ...]:
    events = history()
    return events[-1] if events else ()


def submit(faction: str) -> None:
    require().submitted.add(faction)


def everyone_submitted() -> bool:
    session = require()
    return {t.faction for t in session.journal.teams} <= session.submitted


def _cabinet_events(session: Live, lang: str) -> list[Event]:
    """Что происходило внутри команд — на двух уровнях.

    Своей команде расклад целиком, остальным только факт: раскол в чужом
    кабинете — повод давить именно сейчас, но кто именно возражал, снаружи не
    видно.
    """
    events: list[Event] = []
    for faction, proposals in session.proposals.items():
        spec_faction = session.spec.faction(faction)
        if not spec_faction or not spec_faction.roles or not proposals:
            continue

        def role_title(role_id: str) -> str:
            role = spec_faction.role(role_id)
            return role.title if role else role_id

        counted = [(p, tally(spec_faction.roles, p)) for p in proposals]
        for proposal, result in counted:
            action = session.spec.action(proposal.action)
            key = "news.cabinet_passed" if result.passed else "news.cabinet_failed"
            yes = [role_title(r) for r, v in proposal.votes.items() if v]
            no = [role_title(r) for r, v in proposal.votes.items() if not v]
            nobody = t("news.cabinet_nobody", lang)
            events.append(
                Event(
                    kind="cabinet",
                    title=t(
                        key, lang,
                        what=action.title if action else proposal.action,
                        author=role_title(proposal.author),
                        given=result.given, needed=result.needed,
                    ),
                    actor=faction,
                    detail=t("news.cabinet_votes", lang,
                             yes=", ".join(yes) or nobody, no=", ".join(no) or nobody),
                    audience="actor",
                )
            )

        passed = [(p, r) for p, r in counted if r.passed]
        if not passed:
            events.append(
                Event(kind="cabinet",
                      title=t("news.cabinet_deadlock", lang, side=spec_faction.title),
                      audience="public")
            )
        elif any(result.given == result.needed for _, result in passed):
            events.append(
                Event(kind="cabinet",
                      title=t("news.cabinet_narrow", lang, side=spec_faction.title),
                      audience="public")
            )
    return events


def close_round(force: bool = False) -> None:
    """Посчитать раунд. При force несдавшие команды пасуют."""
    session = require()
    if not force and not everyone_submitted():
        raise ValueError("не все команды сдали приказы")

    before = current_state(session.journal)
    orders = {
        faction: (accepted_orders(faction) if faction in session.submitted else [])
        for faction in (slot.faction for slot in session.journal.teams)
    }
    proposals = [
        J.ProposalRecord(
            id=p.id, faction=faction, action=p.action, target=p.target, author=p.author,
            intent=p.intent, votes=dict(p.votes),
            passed=tally(session.spec.faction(faction).roles, p).passed,
        )
        for faction in session.proposals
        for p in session.proposals[faction]
    ]
    result = resolve(
        session.spec, before, orders, session.offers, session.responses, session.journal.seed
    )
    # Внутренняя политика — часть сводки, но не часть модели: она не меняет
    # состояние, только рассказ о нём.
    told = list(result.events) + _cabinet_events(session, session.lang)
    narration = {
        "public": narrate_public(session.spec, told, session.lang),
        "host": narrate_host(session.spec, told, session.lang),
        "private": {
            slot.faction: narrate_team(session.spec, told, slot.faction, session.lang)
            for slot in session.journal.teams
        },
    }
    session.journal.rounds.append(
        J.RoundRecord(
            n=before.round,
            orders=orders,
            offers=list(session.offers),
            responses=dict(session.responses),
            proposals=proposals,
            narration=narration,
            resolved_at=datetime.now().isoformat(timespec="seconds"),
        )
    )
    J.save(session.path, session.journal)
    session.drafts = {slot.faction: [] for slot in session.journal.teams}
    session.proposals = {slot.faction: [] for slot in session.journal.teams}
    session.ready = {}
    session.offers = []
    session.responses = {}
    session.submitted = set()


def undo_round() -> None:
    session = require()
    undo_last(session.journal)
    J.save(session.path, session.journal)
    session.drafts = {slot.faction: [] for slot in session.journal.teams}
    session.proposals = {slot.faction: [] for slot in session.journal.teams}
    session.ready = {}
    session.offers = []
    session.responses = {}
    session.submitted = set()
