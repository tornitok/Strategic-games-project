"""Как изменилось положение за раунд.

Строки собираются из двух состояний — до и после, — потому что состояние
партии получается пересчётом журнала и оба среза уже доступны.
"""

from ..core.spec import ScenarioSpec
from ..core.state import GameState


def changes_between(
    spec: ScenarioSpec, before: GameState, after: GameState, viewer: str | None
) -> list[dict]:
    rows: list[dict] = []

    for faction in spec.factions:
        own = faction.id == viewer
        tracks = []
        for name, track in spec.tracks.items():
            if not own and track.visibility != "public":
                continue
            was = before.tracks[faction.id][name]
            now = after.tracks[faction.id][name]
            tracks.append(
                {"name": track.title, "before": was, "after": now, "delta": round(now - was, 2)}
            )
        rows.append({"title": faction.title, "own": own, "neutral": False, "tracks": tracks})

    world_tracks = [
        {
            "name": track.title,
            "before": before.world[name],
            "after": after.world[name],
            "delta": round(after.world[name] - before.world[name], 2),
        }
        for name, track in spec.world.items()
    ]
    if world_tracks:
        # Мировые треки не красим в «хорошо/плохо»: рост напряжённости зелёным
        # читался бы как успех, хотя для всех сторон это тревожный сигнал.
        rows.append({"title": "Мир", "own": False, "neutral": True, "tracks": world_tracks})
    return rows
