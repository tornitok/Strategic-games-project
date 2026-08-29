"""Сводка раунда: лента новостей, намёк на тайное и изменения положения."""

from sgame.core.events import Delta, Event
from sgame.core.orders import Order
from sgame.core.spec import parse_scenario
from sgame.narrate.changes import changes_between
from sgame.narrate.news import news_items
from sgame.narrate.templates import narrate_public, narrate_team
from sgame.session import journal as J
from sgame.session.replay import states

TEXT = """
schema_version: 1
meta: { id: t, title: "Т", rounds: 3, action_points: 1 }
tracks:
  budget: { title: "Бюджет", min: 0, max: 200, visibility: public }
  intel:  { title: "Разведка", min: 0, max: 100, visibility: private }
world:
  tension: { title: "Напряжённость", min: 0, max: 100, start: 20 }
factions:
  - { id: a, title: "Астория", start: { budget: 100, intel: 50 } }
  - { id: b, title: "Борея", start: { budget: 100, intel: 50 } }
actions:
  - id: invest
    title: "Вложения"
    news: "{actor} вкладывается в порты и дороги"
    effects: [ { self: budget, delta: "10" } ]
  - id: pressure
    title: "Давление"
    target: faction
    news: "{actor} требует уступок от страны {target}"
    effects: [ { world: tension, delta: "5" } ]
  - id: plain
    title: "Обычное действие"
    effects: [ { self: budget, delta: "1" } ]
  - id: covert
    title: "Тайная операция"
    target: faction
    visibility: secret
    effects: [ { target: budget, delta: "-20" } ]
end: { when: "round > meta.rounds", scoring: "self.budget" }
"""

SPEC = parse_scenario(TEXT)

OPEN = Event(kind="action", title="Вложения", actor="b", audience="public",
             deltas=(Delta(scope="faction", who="b", track="Бюджет", amount=10),))
TARGETED = Event(kind="action", title="Давление", actor="a", target="b", audience="public")
PLAIN = Event(kind="action", title="Обычное действие", actor="a", audience="public")
SECRET = Event(kind="action", title="Тайная операция", actor="a", target="b", audience="actor",
               deltas=(Delta(scope="faction", who="b", track="Бюджет", amount=-20),))


def headlines(items):
    return [item.headline for item in items]


def test_headline_comes_from_the_scenario():
    items = news_items(SPEC, [OPEN], viewer=None, role="public")
    assert headlines(items) == ["Борея вкладывается в порты и дороги"]


def test_headline_substitutes_the_target():
    items = news_items(SPEC, [TARGETED], viewer=None, role="public")
    assert headlines(items) == ["Астория требует уступок от страны Борея"]


def test_action_without_its_own_headline_falls_back():
    items = news_items(SPEC, [PLAIN], viewer=None, role="public")
    assert headlines(items) == ["Астория: Обычное действие"]


def test_changes_go_into_the_item_body():
    items = news_items(SPEC, [OPEN], viewer=None, role="public")
    assert "Бюджет +10" in items[0].detail


def test_secret_action_never_appears_in_public_news():
    items = news_items(SPEC, [OPEN, SECRET], viewer=None, role="public")
    assert "Тайная операция" not in " ".join(headlines(items))


def test_hidden_action_adds_one_vague_item():
    items = news_items(SPEC, [OPEN, SECRET], viewer=None, role="public")
    hint = items[-1]
    assert "тайн" in hint.headline.lower()
    assert "Астория" not in hint.headline
    assert hint.detail == ""


def test_no_hint_when_nothing_was_hidden():
    items = news_items(SPEC, [OPEN], viewer=None, role="public")
    assert all("тайн" not in item.headline.lower() for item in items)


def test_author_of_the_only_secret_gets_no_hint():
    """Иначе намёк сообщал бы автору, что действовал кто-то ещё.

    Своё тайное действие автор при этом видит — проверяем отсутствие именно
    неопределённой строки-намёка.
    """
    items = news_items(SPEC, [OPEN, SECRET], viewer="a", role="team")
    assert [item.kind for item in items].count("hint") == 0
    assert any("Тайная операция" in item.headline for item in items)


def test_side_that_saw_nothing_gets_the_hint():
    items = news_items(SPEC, [OPEN, SECRET], viewer="b", role="team")
    assert [item.kind for item in items].count("hint") == 1
    assert all("Тайная операция" not in item.headline for item in items)


def test_plain_text_rendering_keeps_the_headlines():
    text = narrate_public(SPEC, [OPEN, TARGETED])
    assert "Борея вкладывается в порты и дороги" in text
    assert "Астория требует уступок" in text


def test_team_text_omits_foreign_secret():
    assert "Тайная операция" not in narrate_team(SPEC, [OPEN, SECRET], "b")


def journal_with_one_round():
    journal = J.new_journal("t", TEXT, [], seed=1)
    journal.rounds.append(J.RoundRecord(n=1, orders={"a": [Order(action="invest")]}))
    return journal


def test_states_include_the_position_before_the_first_round():
    all_states = states(journal_with_one_round())
    assert len(all_states) == 2
    assert all_states[0].round == 1
    assert all_states[1].round == 2


def test_changes_show_before_and_after():
    before, after = states(journal_with_one_round())
    rows = changes_between(SPEC, before, after, viewer=None)
    astoria = next(row for row in rows if row["title"] == "Астория")
    budget = next(track for track in astoria["tracks"] if track["name"] == "Бюджет")
    assert (budget["before"], budget["after"], budget["delta"]) == (100, 110, 10)


def test_private_tracks_are_hidden_from_the_projector():
    before, after = states(journal_with_one_round())
    rows = changes_between(SPEC, before, after, viewer=None)
    assert "Разведка" not in [t["name"] for row in rows for t in row["tracks"]]


def test_own_private_track_is_shown_to_its_side():
    before, after = states(journal_with_one_round())
    rows = changes_between(SPEC, before, after, viewer="a")
    astoria = next(row for row in rows if row["title"] == "Астория")
    assert "Разведка" in [t["name"] for t in astoria["tracks"]]


def test_world_row_comes_last():
    before, after = states(journal_with_one_round())
    rows = changes_between(SPEC, before, after, viewer=None)
    assert rows[-1]["title"] == "Мир"


def test_world_changes_are_not_painted_as_good_or_bad():
    """Рост напряжённости зелёным читается как «хорошо», а это неправда."""
    before, after = states(journal_with_one_round())
    rows = changes_between(SPEC, before, after, viewer=None)
    world = rows[-1]
    assert world["neutral"] is True
    assert all(row["neutral"] is False for row in rows[:-1])
