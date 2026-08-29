"""Справочник действий и показателей, собранный из сценария."""

from sgame.core.spec import parse_scenario
from sgame.core.state import initial_state
from sgame.narrate.reference import action_card, chance_word, describe_effect, track_cards

TEXT = """
schema_version: 1
meta: { id: t, title: "Т", rounds: 5, action_points: 3 }
tracks:
  budget:
    title: "Бюджет"
    meaning: "Свободные деньги казны в условных единицах. Одна крупная операция стоит 15–25."
    min: 0
    max: 200
  army:
    title: "Армия"
    meaning: "Боеспособность в условных единицах: 100 — предел мобилизации страны."
    min: 0
    max: 100
world:
  tension:
    title: "Напряжённость"
    meaning: "Общий градус кризиса: 0 — спокойствие, 100 — война."
    min: 0
    max: 100
    start: 30
factions:
  - { id: a, title: "А", start: { budget: 100, army: 50 }, briefing: "т",
      goals: [ { id: g, title: "Ц", when: "self.budget > 0", score: 5 } ] }
  - { id: b, title: "Б", start: { budget: 100, army: 50 }, briefing: "т",
      goals: [ { id: g2, title: "Ц2", when: "self.budget > 0", score: 5 } ] }
actions:
  - id: mobilize
    title: "Мобилизация"
    description: "Призыв резервистов."
    news: "{actor} мобилизуется"
    cost: { budget: 20 }
    effects:
      - { self: army, delta: "10" }
      - { world: tension, delta: "5" }
      - { relation: [self, target], delta: "-4" }
  - id: raid
    title: "Налёт"
    news: "{actor} бьёт"
    target: faction
    cost: { budget: 15 }
    risk:
      - { p: 0.7, title: "успех", effects: [ { target: budget, delta: "-12" } ] }
      - { p: 0.3, title: "провал", effects: [ { self: army, delta: "-5" } ] }
  - id: invest
    title: "Вложения"
    news: "{actor} вкладывается"
    effects: [ { self: budget, delta: "40 - self.budget * 0.1" } ]
rumours: { chance: 0.2, templates: [ "Говорят, {subject}" ] }
events: [ { id: e, chance: 0.2, title: "Случай", news: "Случилось", effects: [] } ]
end: { when: "round > meta.rounds", scoring: "self.budget * 0.1" }
"""

SPEC = parse_scenario(TEXT)


def test_track_cards_carry_the_meaning_and_the_scale():
    cards = track_cards(SPEC)
    budget = next(card for card in cards if card["title"] == "Бюджет")
    assert "условных единицах" in budget["meaning"]
    assert budget["scale"] == "0–200"
    assert budget["visibility"] == "виден всем"


def test_world_tracks_are_included():
    assert any(card["title"] == "Напряжённость" for card in track_cards(SPEC))


def test_effect_on_self_reads_plainly():
    action = SPEC.action("mobilize")
    assert describe_effect(SPEC, action.effects[0]) == "Армия +10"


def test_effect_on_the_world_says_so():
    action = SPEC.action("mobilize")
    assert describe_effect(SPEC, action.effects[1]) == "Напряжённость в мире +5"


def test_effect_on_relations_reads_plainly():
    action = SPEC.action("mobilize")
    assert "Отношения с целью −4" == describe_effect(SPEC, action.effects[2])


def test_formula_effect_says_it_depends():
    action = SPEC.action("invest")
    assert "зависит" in describe_effect(SPEC, action.effects[0])


def test_formula_effect_becomes_a_number_when_state_is_known():
    action = SPEC.action("invest")
    text = describe_effect(SPEC, action.effects[0], state=initial_state(SPEC), actor="a")
    assert "+30" in text


def test_action_card_lists_cost_and_effects():
    card = action_card(SPEC, SPEC.action("mobilize"))
    assert card["cost"] == "Бюджет 20"
    assert "Армия +10" in card["effects"]
    assert card["points"] == 1


def test_action_without_cost_says_it_is_free():
    assert action_card(SPEC, SPEC.action("invest"))["cost"] == "без затрат"


def test_risky_action_lists_outcomes_in_words():
    card = action_card(SPEC, SPEC.action("raid"))
    assert card["risks"]
    assert card["risks"][0]["chance"] == "чаще всего"
    assert "Бюджет цели −12" in card["risks"][0]["effects"]


def test_exact_probabilities_are_available_for_the_host():
    card = action_card(SPEC, SPEC.action("raid"), exact=True)
    assert "70%" in card["risks"][0]["chance"]


def test_chance_words_cover_the_range():
    assert chance_word(0.9) == "почти всегда"
    assert chance_word(0.6) == "чаще всего"
    assert chance_word(0.35) == "иногда"
    assert chance_word(0.1) == "редко"
