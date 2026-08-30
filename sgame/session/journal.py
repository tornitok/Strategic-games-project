"""Журнал партии: входы игроков, из которых пересчитывается состояние."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..core.orders import DealOffer, Order
from .paths import all_scenarios, builtin_scenarios  # noqa: F401 — реэкспорт для веба

FORMAT = 2


@dataclass
class RoleSlot:
    """Должность внутри команды со своим кодом входа."""

    role: str
    code: str


@dataclass
class TeamSlot:
    faction: str
    team: str
    code: str
    roles: list[RoleSlot] = field(default_factory=list)

    def role_code(self, role: str) -> str | None:
        return next((r.code for r in self.roles if r.role == role), None)


@dataclass
class ProposalRecord:
    """Предложение роли и то, как за него проголосовали."""

    id: str
    faction: str
    action: str
    target: str | None = None
    author: str = ""
    intent: str = ""
    votes: dict[str, bool] = field(default_factory=dict)
    passed: bool = False


@dataclass
class RoundRecord:
    n: int
    orders: dict[str, list[Order]] = field(default_factory=dict)
    offers: list[DealOffer] = field(default_factory=list)
    responses: dict[str, bool] = field(default_factory=dict)
    proposals: list[ProposalRecord] = field(default_factory=list)
    narration: dict[str, Any] = field(default_factory=dict)
    resolved_at: str = ""


@dataclass
class Journal:
    format: int
    scenario_id: str
    scenario_sha256: str
    scenario_text: str
    seed: int
    created_at: str
    teams: list[TeamSlot] = field(default_factory=list)
    rounds: list[RoundRecord] = field(default_factory=list)

    def slot(self, faction: str) -> TeamSlot | None:
        return next((t for t in self.teams if t.faction == faction), None)


def new_journal(scenario_id: str, scenario_text: str, teams: list[TeamSlot], seed: int) -> Journal:
    return Journal(
        format=FORMAT,
        scenario_id=scenario_id,
        scenario_sha256=sha256(scenario_text.encode("utf-8")).hexdigest(),
        scenario_text=scenario_text,
        seed=seed,
        created_at=datetime.now().isoformat(timespec="seconds"),
        teams=list(teams),
    )


def to_dict(journal: Journal) -> dict:
    return {
        "format": journal.format,
        "scenario_id": journal.scenario_id,
        "scenario_sha256": journal.scenario_sha256,
        "scenario_text": journal.scenario_text,
        "seed": journal.seed,
        "created_at": journal.created_at,
        "teams": [asdict(t) for t in journal.teams],
        "rounds": [
            {
                "n": record.n,
                "orders": {
                    faction: [asdict(order) for order in orders]
                    for faction, orders in record.orders.items()
                },
                "offers": [asdict(offer) for offer in record.offers],
                "responses": record.responses,
                "proposals": [asdict(p) for p in record.proposals],
                "narration": record.narration,
                "resolved_at": record.resolved_at,
            }
            for record in journal.rounds
        ],
    }


def _migrate(data: dict) -> dict:
    """Партии, сыгранные до появления ролей, должны открываться и играться."""
    version = data.get("format")
    if version == FORMAT:
        return data
    if version == 1:
        data = dict(data)
        data["format"] = FORMAT
        data["teams"] = [{**team, "roles": []} for team in data["teams"]]
        data["rounds"] = [{**record, "proposals": []} for record in data["rounds"]]
        return data
    raise ValueError(f"неизвестная версия файла партии: {version!r}")


def from_dict(data: dict) -> Journal:
    data = _migrate(data)
    return Journal(
        format=data["format"],
        scenario_id=data["scenario_id"],
        scenario_sha256=data["scenario_sha256"],
        scenario_text=data["scenario_text"],
        seed=data["seed"],
        created_at=data["created_at"],
        teams=[
            TeamSlot(
                faction=t["faction"], team=t["team"], code=t["code"],
                roles=[RoleSlot(**r) for r in t.get("roles", [])],
            )
            for t in data["teams"]
        ],
        rounds=[
            RoundRecord(
                n=record["n"],
                orders={
                    faction: [Order(**order) for order in orders]
                    for faction, orders in record["orders"].items()
                },
                offers=[DealOffer(**offer) for offer in record["offers"]],
                responses=record["responses"],
                proposals=[ProposalRecord(**p) for p in record.get("proposals", [])],
                narration=record.get("narration", {}),
                resolved_at=record.get("resolved_at", ""),
            )
            for record in data["rounds"]
        ],
    )


def save(path: Path, journal: Journal) -> None:
    Path(path).write_text(
        json.dumps(to_dict(journal), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load(path: Path) -> Journal:
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
