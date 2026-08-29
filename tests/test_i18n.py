"""Переключение языка: строки интерфейса, тексты движка, выбор сценария."""

import pytest

from sgame.i18n import LANGUAGES, STRINGS, t


def test_every_string_exists_in_both_languages():
    for key, values in STRINGS.items():
        assert set(values) == set(LANGUAGES), key
        assert all(value.strip() for value in values.values()), key


def test_translation_returns_the_chosen_language():
    assert t("team.briefing", "ru") != t("team.briefing", "en")


def test_unknown_key_fails_loudly():
    with pytest.raises(KeyError):
        t("no.such.key", "ru")


def test_unknown_language_falls_back_to_russian():
    assert t("team.briefing", "de") == t("team.briefing", "ru")


def test_delta_describes_itself_in_the_chosen_language():
    from sgame.core.events import Delta

    delta = Delta(scope="faction", who="a", track="Budget", amount=10, clamped=True)
    assert "предел" in delta.describe("ru")
    assert "limit" in delta.describe("en")


def test_chance_words_are_translated():
    from sgame.narrate.reference import chance_word

    assert chance_word(0.6, "ru") == "чаще всего"
    assert chance_word(0.6, "en") == "usually"


def test_covert_hint_is_translated():
    from sgame.narrate.news import covert_hint

    assert "тайн" in covert_hint("ru").lower()
    assert "quiet" in covert_hint("en").lower() or "secret" in covert_hint("en").lower()
