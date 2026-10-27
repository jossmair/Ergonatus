import threading
import pytest
from fortinatus.config import Profile
from fortinatus.engine import Engine
from fortinatus.keys import normalize_key
from fortinatus.windows import ActionDispatcher


@pytest.mark.parametrize("raw,scan,flags,expected", [
    (0x11, 0x1D, 0, 0xA2), (0x11, 0x1D, 1, 0xA3),
    (0x12, 0x38, 0, 0xA4), (0x12, 0x38, 1, 0xA5),
    (0x10, 0x2A, 0, 0xA0), (0x10, 0x36, 0, 0xA1),
    (0xA2, 0x1D, 0, 0xA2), (65, 0x1E, 0, 65),
])
def test_generic_modifier_codes_reach_the_configured_sided_key(raw, scan, flags, expected):
    assert normalize_key(raw, scan, flags) == expected


def test_actions_keep_order_and_flush_releases_at_shutdown():
    events, thread_ids, errors = [], [], []
    class Adapter:
        def emit(self, event):
            events.append(event)
            thread_ids.append(threading.get_ident())
    worker = ActionDispatcher(Adapter(), errors.append)
    worker.submit(("mouse", "left", True))
    worker.submit(("move", 10, 0))
    worker.submit(("mouse", "left", False))
    worker.stop()
    assert events == [("mouse", "left", True), ("move", 10, 0), ("mouse", "left", False)]
    assert all(ident != threading.get_ident() for ident in thread_ids)
    assert not errors


def test_a_failed_action_does_not_prevent_queued_release_attempts():
    events, errors = [], []
    class Adapter:
        def emit(self, event):
            events.append(event)
            if event[-1] is True:
                raise RuntimeError("blocked")
    worker = ActionDispatcher(Adapter(), errors.append)
    worker.submit(("mouse", "left", True))
    worker.submit(("mouse", "left", False))
    worker.stop()
    assert events[-1] == ("mouse", "left", False)
    assert errors == ["blocked"]


def test_f12_is_ordinary_when_the_keyboard_is_restored():
    engine = Engine(lambda event: None)
    engine.configure(Profile(), False)
    assert not engine.event(0x7B, True)
    assert not engine.event(0x7B, False)


def test_emergency_consumes_its_own_release_then_restores_f12():
    engine = Engine(lambda event: None)
    engine.configure(Profile(), True)
    assert engine.event(0x7B, True)
    assert not engine.enabled
    assert engine.event(0x7B, False)
    assert not engine.event(0x7B, True)
    assert not engine.event(0x7B, False)

