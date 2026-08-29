from sgame.core.rng import choose, happens, stream


def test_same_key_gives_same_numbers():
    a = stream(42, 3, "astoria:1:cyber_op").random()
    b = stream(42, 3, "astoria:1:cyber_op").random()
    assert a == b


def test_different_roll_ids_are_independent():
    a = stream(42, 3, "astoria:1:cyber_op").random()
    b = stream(42, 3, "borea:1:cyber_op").random()
    assert a != b


def test_choose_respects_weights_at_boundaries():
    class Fixed:
        def __init__(self, value):
            self.value = value

        def random(self):
            return self.value

    assert choose(Fixed(0.0), [0.5, 0.3, 0.2]) == 0
    assert choose(Fixed(0.6), [0.5, 0.3, 0.2]) == 1
    assert choose(Fixed(0.99), [0.5, 0.3, 0.2]) == 2


def test_happens_never_and_always():
    rng = stream(1, 1, "x")
    assert happens(rng, 0.0) is False
    assert happens(rng, 1.0) is True
