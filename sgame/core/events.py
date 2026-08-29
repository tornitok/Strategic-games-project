"""Что произошло за раунд и кому это видно."""

from dataclasses import dataclass, field
from typing import Literal

Audience = Literal["public", "actor", "actor_and_target", "host"]


@dataclass(frozen=True)
class Delta:
    """Одно изменение числа с указанием, упёрлось ли оно в границу."""

    scope: Literal["faction", "world", "relation"]
    who: str
    track: str
    amount: float
    clamped: bool = False

    def describe(self) -> str:
        sign = "+" if self.amount >= 0 else "−"
        body = f"{self.track} {sign}{abs(self.amount):g}"
        return f"{body} (предел)" if self.clamped else body


@dataclass(frozen=True)
class Event:
    kind: str
    title: str
    actor: str | None = None
    target: str | None = None
    detail: str = ""
    deltas: tuple[Delta, ...] = field(default=())
    audience: Audience = "public"
    roll: str | None = None
