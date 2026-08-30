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
    intro: str = ""
    max_random_events: int | None = Field(default=None, ge=0)


class TrackSpec(Base):
    title: str
    min: float
    max: float
    visibility: Literal["public", "private"] = "public"
    meaning: str = ""  # что означает единица показателя — для правил игроков


class WorldTrackSpec(Base):
    title: str
    min: float
    max: float
    # Число или выражение от meta.rounds: длина партии известна до её начала,
    # и стартовые величины можно считать от неё.
    start: float | str
    meaning: str = ""


class GoalSpec(Base):
    id: str
    title: str
    when: str
    score: float


class RoleSpec(Base):
    """Должность внутри команды: свой брифинг, свои цели, свой вес голоса."""

    id: str
    title: str
    briefing: str = ""
    weight: int = Field(default=1, ge=1)
    goals: list[GoalSpec] = []
    actions: list[str] = []  # что должность вправе вносить; пусто — всё

    def can_propose(self, action_id: str) -> bool:
        """Пустой список полномочий означает «любое действие»."""
        return not self.actions or action_id in self.actions


class FactionSpec(Base):
    id: str
    title: str
    start: dict[str, float | str]
    briefing: str = ""
    goals: list[GoalSpec] = []
    roles: list[RoleSpec] = []

    def role(self, role_id: str) -> "RoleSpec | None":
        return next((r for r in self.roles if r.id == role_id), None)


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


class ComplicationSpec(Base):
    """Редкое «что-то пошло не так» поверх обычного результата действия."""

    chance: float = Field(ge=0, le=1)
    title: str
    news: str = ""
    text: str = ""
    effects: list[EffectSpec] = []


class ActionSpec(Base):
    id: str
    title: str
    description: str = ""
    news: str = ""  # заголовок для сводки, подстановки {actor} и {target}
    ap: int = Field(default=1, ge=1)
    cost: dict[str, float] = {}
    requires: str | None = None
    target: Literal["none", "faction"] = "none"
    visibility: Literal["open", "secret"] = "open"
    stance: Literal["hostile", "friendly", "neutral"] = "neutral"
    repeatable: bool = False  # можно ли заказать дважды за раунд
    available_to: list[str] = []  # если задано — действие только для этих сторон
    reveal_chance: float = Field(default=0.0, ge=0, le=1)
    countered_by: list[str] = []
    plants_rumour: bool = False  # действие запускает слух о выбранной стороне
    counter_multiplier: float = Field(default=0.0, ge=0, le=1)
    effects: list[EffectSpec] = []
    risk: list[RiskOutcome] = []
    complications: list[ComplicationSpec] = []


class DealSpec(Base):
    id: str
    title: str
    kind: Literal["resource", "status"]
    track: str | None = None
    duration: int | None = None


class EventSpec(Base):
    id: str
    when: str = ""  # пусто — событие возможно в любом раунде
    # Доля партии, на которой событие происходит: 0.5 — середина, 0.9 — развязка.
    # Привязка к номеру раунда ломается при растяжении сценария: вся авторская
    # дуга остаётся в первой трети.
    phase: float | None = Field(default=None, ge=0, le=1)
    chance: float = Field(default=1.0, ge=0, le=1)
    title: str
    text: str = ""
    news: str = ""  # заголовок для сводки
    once: bool = False
    effects: list[EffectSpec] = []


class RelationPair(Base):
    a: str
    b: str
    value: float


class RelationsSpec(Base):
    default: float = 0
    pairs: list[RelationPair] = []


class RumoursSpec(Base):
    """Насколько болтлив и лжив мир вокруг команд."""

    chance: float = Field(default=0.0, ge=0, le=1)       # слух при тайной активности
    noise_chance: float = Field(default=0.0, ge=0, le=1)  # слух на пустом месте
    accuracy: float = Field(default=0.6, ge=0, le=1)      # доля правдивых
    templates: list[str] = []


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
    rumours: RumoursSpec = RumoursSpec()
    end: EndSpec
    power: str = ""  # чем измеряется сила стороны; пусто — сумма публичных треков

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
