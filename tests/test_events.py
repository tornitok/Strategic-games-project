from sgame.core.events import Delta, Event


def test_delta_describes_itself_in_russian():
    delta = Delta(scope="faction", who="astoria", track="Бюджет", amount=-15)
    assert delta.describe() == "Бюджет −15"


def test_clamped_delta_is_marked():
    delta = Delta(scope="faction", who="a", track="ВС", amount=10, clamped=True)
    assert "предел" in delta.describe()


def test_event_defaults_to_public():
    event = Event(kind="action", title="Мобилизация")
    assert event.audience == "public"


def test_event_is_hashable_and_frozen():
    event = Event(kind="action", title="Мобилизация", deltas=())
    assert hash(event)
