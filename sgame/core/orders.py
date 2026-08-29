"""Ввод команд: приказы и предложения сделок."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    action: str
    target: str | None = None
    intent: str = ""


@dataclass(frozen=True)
class DealOffer:
    id: str
    deal: str
    sender: str
    receiver: str
    amount: float | None = None
