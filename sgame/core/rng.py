"""Детерминированные потоки случайности.

Глобальный генератор не используется: каждый бросок получает собственный
поток, выведенный из ключа партии, номера раунда и идентификатора броска.
Поэтому порядок вычислений не влияет на результат, а пересчёт журнала
воспроизводит те же исходы.
"""

import random
from collections.abc import Sequence
from hashlib import blake2b


def stream(seed: int, round_no: int, roll_id: str) -> random.Random:
    key = f"{seed}|{round_no}|{roll_id}".encode("utf-8")
    return random.Random(blake2b(key, digest_size=16).digest())


def choose(rng, weights: Sequence[float]) -> int:
    """Индекс исхода по накопленным вероятностям."""
    point = rng.random() * sum(weights)
    total = 0.0
    for index, weight in enumerate(weights):
        total += weight
        if point < total:
            return index
    return len(weights) - 1


def happens(rng, chance: float) -> bool:
    if chance <= 0:
        return False
    if chance >= 1:
        return True
    return rng.random() < chance
