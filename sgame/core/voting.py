"""Голосование внутри команды.

Приказ команды рождается из предложений её ролей. Воздержавшийся считается
голосующим против: молчание не должно проталкивать решения.
"""

from dataclasses import dataclass, field

from .spec import RoleSpec


@dataclass
class Proposal:
    id: str
    action: str
    target: str | None
    author: str
    intent: str = ""
    votes: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class Tally:
    given: int
    against: int
    needed: int
    total: int
    passed: bool
    voted: int
    waiting: int


def tally(roles: list[RoleSpec], proposal: Proposal) -> Tally:
    """Расклад по одному предложению — в весах голосов, а не в головах."""
    total = sum(role.weight for role in roles)
    given = sum(role.weight for role in roles if proposal.votes.get(role.id) is True)
    against = sum(role.weight for role in roles if proposal.votes.get(role.id) is False)
    needed = total // 2 + 1
    voted = sum(1 for role in roles if role.id in proposal.votes)
    return Tally(
        given=given,
        against=against,
        needed=needed,
        total=total,
        passed=given >= needed,
        voted=voted,
        waiting=len(roles) - voted,
    )
