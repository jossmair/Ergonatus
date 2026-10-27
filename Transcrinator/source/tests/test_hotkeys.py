import pytest

from app.core.hotkeys import GlobalHotkey, ShiftGesture, TRIGGER_KEYS


def tap(g, vk=0xA0):
    assert not g.event(vk, True)
    return g.event(vk, False)


def test_first_second_and_rapid_toggle():
    now = [0.0]
    g = ShiftGesture(clock=lambda: now[0])
    assert tap(g)
    now[0] = 1
    assert tap(g)
    now[0] = 1.1
    assert not tap(g)


def test_held_shift_repeats():
    g = ShiftGesture()
    for _ in range(20):
        assert not g.event(0xA0, True)
    assert g.event(0xA0, False)
    assert not g.event(0xA0, False)


def test_shift_letter_and_right_shift():
    g = ShiftGesture()
    g.event(0xA0, True)
    g.event(65, True)
    g.event(65, False)
    assert not g.event(0xA0, False)
    assert not tap(g, 0xA1)


def test_other_key_held_first():
    g = ShiftGesture()
    g.event(0x11, True)
    assert not tap(g)


def test_injected_shift_ignored():
    g = ShiftGesture()
    assert not g.event(0xA0, True, injected=True)
    assert not g.event(0xA0, False, injected=True)


def test_shift_selection_gesture_is_contaminated():
    g = ShiftGesture()
    assert not g.event(0xA0, True)
    g.contaminated = True
    assert not g.event(0xA0, False)


def test_double_shift():
    now = [0.0]
    g = ShiftGesture(double=True, clock=lambda: now[0])
    assert not tap(g)
    now[0] = 0.2
    assert tap(g)
    now[0] = 1
    assert not tap(g)
    now[0] = 2
    assert not tap(g)


@pytest.mark.parametrize("identity,name,vk", TRIGGER_KEYS)
def test_selected_key_fires_once_and_preserves_modifier_chords(identity, name, vk):
    hook = GlobalHotkey(lambda: None, trigger_key=identity)
    consumed = 0x70 <= vk <= 0x7B
    assert hook.handle_key(vk, True, held=set()) == (False, consumed)
    for _ in range(4):
        assert hook.handle_key(vk, True) == (False, consumed)
    assert hook.handle_key(vk, False) == (True, consumed)
    assert hook.handle_key(vk, False) == (False, False)
    hook = GlobalHotkey(lambda: None, trigger_key=identity)
    assert hook.handle_key(vk, True, held={0x5B}) == (False, False)
    assert hook.handle_key(vk, False) == (False, False)


def test_rebinding_cancels_partial_gesture_and_ignores_synthetic_keys():
    hook = GlobalHotkey(lambda: None, trigger_key="f8")
    assert hook.handle_key(0x77, True, held=set()) == (False, True)
    hook.set_trigger("ctrl_right")
    assert hook.handle_key(0x77, False) == (False, True)
    assert hook.handle_key(0x77, True, held=set()) == (False, False)
    hook.handle_key(0x77, False)
    assert hook.handle_key(0xA3, True, injected=True) == (False, False)
    assert hook.handle_key(0xA3, False, injected=True) == (False, False)
    assert hook.handle_key(0xA3, True, held=set()) == (False, False)
    assert hook.handle_key(0xA3, False) == (True, False)


def test_another_key_during_trigger_does_not_start_dictation():
    hook = GlobalHotkey(lambda: None, trigger_key="ctrl_right")
    hook.handle_key(0xA3, True, held=set())
    hook.handle_key(0x43, True)
    hook.handle_key(0x43, False)
    assert hook.handle_key(0xA3, False) == (False, False)
