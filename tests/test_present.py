from sgame.web.present import paragraphs


def test_lines_inside_paragraph_flow_together():
    assert paragraphs("первая строка\nвторая строка") == ["первая строка вторая строка"]


def test_blank_line_starts_new_paragraph():
    assert paragraphs("абзац один\nпродолжение\n\nабзац два") == [
        "абзац один продолжение",
        "абзац два",
    ]


def test_empty_text_gives_no_paragraphs():
    assert paragraphs("   \n\n  ") == []


def test_extra_spaces_are_collapsed():
    assert paragraphs("слово    ещё\n   слово") == ["слово ещё слово"]


def test_whole_numbers_lose_the_decimal_tail():
    from sgame.web.present import number

    assert number(120.0) == "120"
    assert number(30) == "30"


def test_fractional_numbers_keep_two_digits():
    from sgame.web.present import number

    assert number(8.75) == "8.75"
    assert number(-3.5) == "-3.5"


def test_long_tails_are_rounded():
    from sgame.web.present import number

    assert number(7.749999) == "7.75"
    assert number(6.100000000000001) == "6.1"
