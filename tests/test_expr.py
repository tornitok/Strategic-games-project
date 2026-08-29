import pytest
from sgame.core.expr import ExprError, evaluate


def test_arithmetic():
    assert evaluate("2 + 2 * 3", {}) == 8


def test_namespace_attribute():
    assert evaluate("self.army * 0.5", {"self": {"army": 60}}) == 30.0


def test_functions():
    assert evaluate("clamp(120, 0, 100)", {}) == 100
    assert evaluate("min(3, 5) + max(1, 2)", {}) == 5


def test_comparison_and_logic():
    assert evaluate("self.intel >= 10 and round < 5", {"self": {"intel": 40}, "round": 2}) is True


def test_ternary():
    assert evaluate("10 if world.tension > 50 else 1", {"world": {"tension": 70}}) == 10


def test_context_callable():
    ctx = {"rel": lambda a, b: -20}
    assert evaluate('rel("astoria", "borea")', ctx) == -20


def test_rejects_import():
    with pytest.raises(ExprError):
        evaluate("__import__('os').listdir('.')", {})


def test_rejects_lambda():
    with pytest.raises(ExprError):
        evaluate("(lambda: 1)()", {})


def test_rejects_subscript():
    with pytest.raises(ExprError):
        evaluate("self['army']", {"self": {"army": 1}})


def test_unknown_name_message_names_it():
    with pytest.raises(ExprError) as exc:
        evaluate("self.cyberdef + 1", {"self": {"army": 1}})
    assert "cyberdef" in str(exc.value)


def test_syntax_error_is_expr_error():
    with pytest.raises(ExprError):
        evaluate("2 +", {})
