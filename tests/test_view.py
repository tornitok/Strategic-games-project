from sgame.core.events import Delta, Event
from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state
from sgame.narrate.templates import narrate_public, narrate_team
from sgame.narrate.view import events_for, tracks_for

SPEC = parse_scenario("""
schema_version: 1
meta: { id: t, title: "Т", rounds: 3, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 100, visibility: public }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 10 }
factions:
  - { id: a, title: "А", start: { budget: 50, intel: 30 } }
  - { id: b, title: "Б", start: { budget: 50, intel: 70 } }
actions:
  - { id: noop, title: "Ничего", effects: [] }
end: { when: "round > meta.rounds", scoring: "self.budget" }
""")

EVENTS = [
    Event(kind="action", title="Открытое", actor="a", audience="public"),
    Event(kind="action", title="Тайное", actor="a", target="b", audience="actor"),
    Event(kind="action", title="Раскрытое", actor="a", target="b", audience="actor_and_target"),
    Event(kind="note", title="Только ведущему", audience="host"),
]


def test_team_sees_public_own_and_addressed():
    titles = [e.title for e in events_for(EVENTS, "b", role="team")]
    assert titles == ["Открытое", "Раскрытое"]


def test_actor_sees_own_secret():
    titles = [e.title for e in events_for(EVENTS, "a", role="team")]
    assert "Тайное" in titles


def test_projector_shows_only_public():
    titles = [e.title for e in events_for(EVENTS, None, role="public")]
    assert titles == ["Открытое"]


def test_host_sees_everything():
    assert len(events_for(EVENTS, None, role="host")) == 4


def test_private_tracks_of_others_are_hidden():
    visible = tracks_for(SPEC, initial_state(SPEC), viewer="a")
    assert visible["a"]["Разведка"] == 30
    assert "Разведка" not in visible["b"]
    assert visible["b"]["Бюджет"] == 50


def test_narration_mentions_deltas():
    events = [
        Event(
            kind="action", title="Мобилизация", actor="a", audience="public",
            deltas=(Delta(scope="faction", who="a", track="Бюджет", amount=-20),),
        )
    ]
    text = narrate_public(SPEC, events)
    assert "Мобилизация" in text
    assert "Бюджет −20" in text


def test_team_narration_omits_foreign_secrets():
    text = narrate_team(SPEC, EVENTS, "b")
    assert "Тайное" not in text


def test_world_event_labels_each_side():
    """Четыре «Бюджет» подряд без имён сторон читаются как бессмыслица."""
    events = [
        Event(
            kind="world", title="Обстановка", audience="public",
            deltas=(
                Delta(scope="world", who="", track="Напряжённость", amount=-3),
                Delta(scope="faction", who="a", track="Бюджет", amount=8.75),
                Delta(scope="faction", who="b", track="Бюджет", amount=8.25),
            ),
        )
    ]
    text = narrate_public(SPEC, events)
    assert "А: Бюджет +8.75" in text
    assert "Б: Бюджет +8.25" in text
    assert "Напряжённость −3" in text


def test_own_deltas_are_not_labelled():
    events = [
        Event(
            kind="action", title="Мобилизация", actor="a", audience="public",
            deltas=(Delta(scope="faction", who="a", track="Бюджет", amount=-20),),
        )
    ]
    text = narrate_public(SPEC, events)
    assert "Бюджет −20" in text
    assert "А: Бюджет" not in text


def test_target_deltas_are_labelled():
    events = [
        Event(
            kind="action", title="Санкции", actor="a", target="b", audience="public",
            deltas=(Delta(scope="faction", who="b", track="Бюджет", amount=-15),),
        )
    ]
    assert "Б: Бюджет −15" in narrate_public(SPEC, events)


def test_world_deltas_are_grouped_by_side():
    """Иначе получается «Бюджет +8, Бюджет +9, … , Легитимность +1, …»."""
    events = [
        Event(
            kind="world", title="Обстановка", audience="public",
            deltas=(
                Delta(scope="world", who="", track="Напряжённость", amount=-3),
                Delta(scope="faction", who="a", track="Бюджет", amount=8),
                Delta(scope="faction", who="b", track="Бюджет", amount=9),
                Delta(scope="faction", who="a", track="Легитимность", amount=1),
                Delta(scope="faction", who="b", track="Легитимность", amount=1),
            ),
        )
    ]
    text = narrate_public(SPEC, events)
    assert "А: Бюджет +8, Легитимность +1" in text
    assert "Б: Бюджет +9, Легитимность +1" in text
