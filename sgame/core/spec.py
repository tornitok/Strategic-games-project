"""Схема сценария: то, что преподаватель пишет в YAML."""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import Problem, ScenarioError
from .yamlsrc import line_for, load_with_lines

SCHEMA_VERSION = 1


class Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class MetaSpec(Base):
    id: str
    title: str
    rounds: int = Field(ge=1)
    action_points: int = Field(ge=1)


class TrackSpec(Base):
    title: str
    min: float
    max: float
    visibility: Literal["public", "private"] = "public"


class WorldTrackSpec(Base):
    title: str
    min: float
    max: float
    start: float


class GoalSpec(Base):
    id: str
    title: str
    when: str
    score: float


class FactionSpec(Base):
    id: str
    title: str
    start: dict[str, float]
    briefing: str = ""
    goals: list[GoalSpec] = []


class EffectSpec(Base):
    """Ровно одна форма адресации плюс обязательная дельта."""

    self_track: str | None = Field(default=None, alias="self")
    target: str | None = None
    world: str | None = None
    all: str | None = None
    relation: list[str] | None = None
    delta: str


class RiskOutcome(Base):
    p: float = Field(ge=0, le=1)
    title: str = ""
    effects: list[EffectSpec] = []


class ActionSpec(Base):
    id: str
    title: str
    description: str = ""
    ap: int = Field(default=1, ge=1)
    cost: dict[str, float] = {}
    requires: str | None = None
    target: Literal["none", "faction"] = "none"
    visibility: Literal["open", "secret"] = "open"
    reveal_chance: float = Field(default=0.0, ge=0, le=1)
    countered_by: list[str] = []
    counter_multiplier: float = Field(default=0.0, ge=0, le=1)
    effects: list[EffectSpec] = []
    risk: list[RiskOutcome] = []


class DealSpec(Base):
    id: str
    title: str
    kind: Literal["resource", "status"]
    track: str | None = None
    duration: int | None = None


class EventSpec(Base):
    id: str
    when: str
    title: str
    text: str = ""
    once: bool = False
    effects: list[EffectSpec] = []


class RelationPair(Base):
    a: str
    b: str
    value: float


class RelationsSpec(Base):
    default: float = 0
    pairs: list[RelationPair] = []


class EndSpec(Base):
    when: str
    scoring: str


class ScenarioSpec(Base):
    schema_version: int
    meta: MetaSpec
    tracks: dict[str, TrackSpec]
    world: dict[str, WorldTrackSpec] = {}
    factions: list[FactionSpec]
    relations: RelationsSpec = RelationsSpec()
    actions: list[ActionSpec]
    deals: list[DealSpec] = []
    world_dynamics: list[EffectSpec] = []
    events: list[EventSpec] = []
    end: EndSpec

    def action(self, action_id: str) -> ActionSpec | None:
        return next((a for a in self.actions if a.id == action_id), None)

    def faction(self, faction_id: str) -> FactionSpec | None:
        return next((f for f in self.factions if f.id == faction_id), None)

    def deal(self, deal_id: str) -> DealSpec | None:
        return next((d for d in self.deals if d.id == deal_id), None)


def parse_scenario(text: str) -> ScenarioSpec:
    data, lines = load_with_lines(text)
    if not isinstance(data, dict):
        raise ScenarioError([Problem("файл сценария должен быть отображением ключ-значение")])

    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ScenarioError([
            Problem(
                f"версия схемы {version!r} не поддерживается, нужна {SCHEMA_VERSION}",
                line_for(lines, ("schema_version",)),
            )
        ])

    try:
        return ScenarioSpec.model_validate(data)
    except ValidationError as exc:
        raise ScenarioError(
            [
                Problem(
                    f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}",
                    line_for(lines, err["loc"]),
                )
                for err in exc.errors()
            ]
        ) from exc


def load_scenario(path: Path) -> ScenarioSpec:
    return parse_scenario(Path(path).read_text(encoding="utf-8"))


def scenario_lines(text: str) -> dict[str, int]:
    """Карта «путь → строка» для того же текста: нужна валидатору."""
    _, lines = load_with_lines(text)
    return lines


def scenario_data(text: str) -> Any:
    data, _ = load_with_lines(text)
    return data
