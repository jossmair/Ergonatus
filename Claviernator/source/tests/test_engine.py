import pytest

from fortinatus.config import Mapping, Profile
from fortinatus.engine import Engine
from fortinatus.keys import EMERGENCY, SYMBOLS


@pytest.fixture
def rig():
    events, notices, now = [], [], [10.0]
    engine = Engine(events.append, notices.append, lambda: now[0])
    engine.configure(Profile())
    return engine, events, notices, now


def tap(engine, vk):
    engine.event(vk, True)
    engine.event(vk, False)


def test_mouse_hold_retains_drag_until_source_release(rig):
    engine, events, *_ = rig
    engine.configure(Profile(mappings=[Mapping(0x70, "mouse_hold")]))
    assert engine.event(0x70, True)
    for _ in range(10):
        assert engine.event(0x70, True)
    assert events == [("mouse", "left", True)]
    assert engine.event(0x70, False)
    assert events[-1] == ("mouse", "left", False)


def test_toggle_click_requires_a_second_distinct_press(rig):
    engine, events, *_ = rig
    engine.configure(Profile(mappings=[Mapping(0x70, "mouse_toggle")]))
    tap(engine, 0x70)
    assert events == [("mouse", "left", True)]
    engine.event(0x70, True)
    engine.event(0x70, True)
    engine.event(0x70, False)
    assert events == [("mouse", "left", True), ("mouse", "left", False)]


@pytest.mark.parametrize("operation", ["pause", "configure", "emergency"])
def test_all_exit_paths_release_clicks_keys_and_consume_pending_source_up(rig, operation):
    engine, events, *_ = rig
    engine.configure(Profile(mappings=[Mapping(0x70, "mouse_toggle"), Mapping(0x71, keys=[0xA2, 67])]))
    tap(engine, 0x70)
    engine.event(0x71, True)
    if operation == "pause":
        engine.pause()
    elif operation == "configure":
        engine.configure(Profile())
    else:
        engine.event(EMERGENCY, True)
    assert ("mouse", "left", False) in events
    assert ("key", 67, False) in events
    assert ("key", 0xA2, False) in events
    assert not engine.owners
    assert engine.event(0x71, False)


def test_shared_mouse_output_has_two_owners(rig):
    engine, events, *_ = rig
    engine.configure(Profile(mappings=[Mapping(0x70, "mouse_hold"), Mapping(0x71, "mouse_hold")]))
    engine.event(0x70, True)
    engine.event(0x71, True)
    engine.event(0x70, False)
    assert events == [("mouse", "left", True)]
    engine.event(0x71, False)
    assert events[-1] == ("mouse", "left", False)


def test_hold_and_toggle_share_ownership(rig):
    engine, events, *_ = rig
    engine.configure(Profile(mappings=[Mapping(0x70, "mouse_toggle"), Mapping(0x71, "mouse_hold")]))
    tap(engine, 0x70)
    engine.event(0x71, True)
    tap(engine, 0x70)
    assert events == [("mouse", "left", True)]
    engine.event(0x71, False)
    assert events[-1] == ("mouse", "left", False)


def test_chord_press_and_reverse_release(rig):
    engine, events, *_ = rig
    engine.configure(Profile(mappings=[Mapping(0x70, keys=[0xA2, 0xA0, 83])]))
    tap(engine, 0x70)
    assert events == [("key", 0xA2, True), ("key", 0xA0, True), ("key", 83, True),
                      ("key", 83, False), ("key", 0xA0, False), ("key", 0xA2, False)]


@pytest.mark.parametrize("vk,symbol", SYMBOLS.items())
@pytest.mark.parametrize("shifted", [False, True])
def test_full_french_number_row(rig, vk, symbol, shifted):
    engine, events, *_ = rig
    engine.configure(Profile(invert_numbers=True))
    if shifted:
        assert not engine.event(0xA0, True)
    tap(engine, vk)
    assert events == [("text", symbol if shifted else chr(vk))]


@pytest.mark.parametrize("modifier", [0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C])
def test_shortcuts_and_altgr_bypass_number_inversion(rig, modifier):
    engine, events, *_ = rig
    engine.configure(Profile(invert_numbers=True))
    engine.event(modifier, True)
    assert not engine.event(49, True)
    assert not engine.event(49, False)
    assert not events


def test_explicit_mapping_overrides_number_inversion(rig):
    engine, events, *_ = rig
    engine.configure(Profile(invert_numbers=True, mappings=[Mapping(49, keys=[65])]))
    tap(engine, 49)
    assert events == [("key", 65, True), ("key", 65, False)]


def test_filter_rejects_entire_bounce_press_but_not_next_letter(rig):
    engine, events, _, now = rig
    engine.configure(Profile(debounce_ms=250, mappings=[Mapping(65, "text", text="oui")]))
    tap(engine, 65)
    now[0] += .1
    assert engine.event(65, True)
    assert engine.event(65, False)
    assert not engine.event(66, True)
    assert events == [("text", "oui")]
    now[0] += .3
    tap(engine, 65)
    assert len(events) == 2


def test_repeat_filter_preserves_first_press_and_release(rig):
    engine, events, *_ = rig
    engine.configure(Profile(suppress_repeat=True))
    assert not engine.event(65, True)
    assert engine.event(65, True)
    assert not engine.event(65, False)


def test_sticky_ctrl_then_c_releases_after_letter(rig):
    engine, events, *_ = rig
    engine.configure(Profile(sticky_modifiers=True))
    tap(engine, 0xA2)
    assert not events
    tap(engine, 67)
    assert events == [("key", 0xA2, True), ("key", 67, True), ("key", 67, False), ("key", 0xA2, False)]
    assert not engine.latched


def test_sticky_multiple_modifiers_and_cancel(rig):
    engine, events, *_ = rig
    engine.configure(Profile(sticky_modifiers=True))
    tap(engine, 0xA2)
    tap(engine, 0xA0)
    assert engine.latched == {0xA2, 0xA0}
    tap(engine, 0xA0)
    assert engine.latched == {0xA2}
    tap(engine, 0xA2)
    assert not engine.latched
    assert not events


def test_sticky_normal_held_chord_does_not_latch(rig):
    engine, events, *_ = rig
    engine.configure(Profile(sticky_modifiers=True))
    engine.event(0xA2, True)
    tap(engine, 67)
    engine.event(0xA2, False)
    assert not engine.latched
    assert events[0] == ("key", 0xA2, True)
    assert events[-1] == ("key", 0xA2, False)


def test_sticky_shift_number_inversion(rig):
    engine, events, *_ = rig
    engine.configure(Profile(sticky_modifiers=True, invert_numbers=True))
    tap(engine, 0xA0)
    tap(engine, 50)
    assert events == [("text", "é")]


def test_sticky_ctrl_number_keeps_shortcut(rig):
    engine, events, *_ = rig
    engine.configure(Profile(sticky_modifiers=True, invert_numbers=True))
    tap(engine, 0xA2)
    tap(engine, 50)
    assert events[0] == ("key", 0xA2, True)
    assert ("key", 50, True) in events


def test_pointer_moves_continuously_until_release(rig):
    engine, events, *_ = rig
    engine.configure(Profile(pointer_speed=3, mappings=[Mapping(0x70, "move", direction="left")]))
    engine.event(0x70, True)
    engine.tick()
    engine.tick()
    engine.event(0x70, False)
    engine.tick()
    assert events == [("move", -3, 0)] * 3


def test_double_click_does_not_repeat(rig):
    engine, events, *_ = rig
    engine.configure(Profile(mappings=[Mapping(0x70, "double_click")]))
    engine.event(0x70, True)
    engine.event(0x70, True)
    engine.event(0x70, False)
    assert events == [("double_click",)]


def test_disabled_rule_is_passthrough_and_disabled_action_suppresses(rig):
    engine, events, *_ = rig
    engine.configure(Profile(mappings=[Mapping(65, "disabled", enabled=False), Mapping(66, "disabled")]))
    assert not engine.event(65, True)
    assert not engine.event(65, False)
    assert engine.event(66, True)
    assert engine.event(66, False)
    assert not events


def test_release_failure_still_attempts_other_outputs(rig):
    engine, events, notices, _ = rig
    engine.configure(Profile(mappings=[Mapping(0x70, keys=[0xA2, 67])]))
    engine.event(0x70, True)
    def failing(event):
        events.append(event)
        if event == ("key", 67, False):
            raise RuntimeError("blocked")
    engine.emit = failing
    engine.pause()
    assert ("key", 0xA2, False) in events
    assert notices

