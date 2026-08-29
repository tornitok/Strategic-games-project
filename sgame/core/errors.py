from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    """Одна ошибка в сценарии, привязанная к строке файла."""

    message: str
    line: int | None = None

    def __str__(self) -> str:
        return f"строка {self.line}: {self.message}" if self.line else self.message


class ScenarioError(Exception):
    """Сценарий не удалось загрузить или он не прошёл проверки."""

    def __init__(self, problems: list[Problem]) -> None:
        self.problems = problems
        super().__init__("; ".join(str(p) for p in problems))
