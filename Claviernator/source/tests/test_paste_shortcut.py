import pytest

from fortinatus.config import Mapping, Profile
from fortinatus.engine import Engine


def rig(control=0xA2, kind="mouse_hold", button="left", extra=None, **options):
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(mappings=[Mapping(control, kind, button=button), *(extra or [])], **options))
    return engine, events


@pytest.mark.parametrize("control", [0xA2, 0xA3])
@pytest.mark.parametrize("kind", ["mouse_click", "mouse_hold"])
@pytest.mark.parametrize("button", ["left", "right"])
def test_paste_releases_mouse_and_holds_real_ctrl_until_source_release(control, kind, button):
    engine, events = rig(control, kind, button)
    assert engine.event(control, True)
    assert events == [("mouse", button, True)]
    assert engine.event(0x56, True)
    assert events == [("mouse", button, True), ("mouse", button, False),
                      ("key", control, True), ("key", 0x56, True)]
    engine.event(control, True)  # Modifier repeats must not press the mouse again.
    assert engine.event(0x56, False)
    assert events[-1] == ("key", 0x56, False)
    assert engine.owners[("key", control)] == 1
    assert engine.event(control, False)
    assert events[-1] == ("key", control, False)
    assert not engine.owners and not engine.paste_controls


@pytest.mark.parametrize("rule", [Mapping(0x56,"disabled"), Mapping(0x56,"text",text="autre"),
                                   Mapping(0x56,keys=[65]), Mapping(0x56,"original")])
def test_ctrl_paste_takes_priority_over_v_remapping_and_filters(rule):
    engine, events = rig(extra=[rule], debounce_ms=1000, suppress_repeat=True)
    engine.event(0xA2, True)
    for _ in range(2):
        assert engine.event(0x56, True)
        assert engine.event(0x56, False)
    engine.event(0xA2, False)
    assert [event for event in events if event == ("key", 0x56, True)] == [("key", 0x56, True)] * 2
    assert not any(event[0] == "text" or event[:2] == ("key", 65) for event in events)
    assert not engine.owners


def test_repeat_v_and_release_ctrl_before_v_leave_no_held_output():
    engine, events = rig()
    engine.event(0xA2, True)
    engine.event(0x56, True)
    engine.event(0x56, True)
    assert events[-1] == ("key", 0x56, True)
    engine.event(0xA2, False)
    engine.event(0x56, False)
    assert events[-2:] == [("key", 0xA2, False), ("key", 0x56, False)]
    assert not engine.owners and not engine.paste_controls


@pytest.mark.parametrize("exit_action", ["pause", "configure", "emergency"])
def test_exit_paths_release_paste_keys_and_consume_source_releases(exit_action):
    engine, events = rig()
    engine.event(0xA2, True)
    engine.event(0x56, True)
    if exit_action == "pause":
        engine.pause()
    elif exit_action == "configure":
        engine.configure(Profile())
    else:
        engine.event(0x7B, True)
    assert events[-2:] == [("key", 0x56, False), ("key", 0xA2, False)]
    assert engine.event(0xA2, False) and engine.event(0x56, False)
    assert not engine.owners and not engine.paste_controls


def test_both_control_keys_release_shared_mouse_before_paste_and_release_independently():
    engine, events = rig(extra=[Mapping(0xA3,"mouse_hold")])
    engine.event(0xA2, True)
    engine.event(0xA3, True)
    engine.event(0x56, True)
    assert events[:2] == [("mouse","left",True), ("mouse","left",False)]
    assert engine.owners[("key",0xA2)] and engine.owners[("key",0xA3)]
    engine.event(0x56, False)
    engine.event(0xA2, False)
    assert engine.owners[("key",0xA3)]
    engine.event(0xA3, False)
    assert not engine.owners


def test_mouse_toggle_is_released_for_paste_without_relocking_on_ctrl_up():
    engine, events = rig(kind="mouse_toggle")
    engine.event(0xA2, True)
    engine.event(0x56, True)
    engine.event(0x56, False)
    engine.event(0xA2, False)
    assert not engine.toggled and not engine.owners
    assert events.count(("mouse","left",False)) == 1


def test_other_mouse_owner_is_not_released_by_paste():
    engine, events = rig(extra=[Mapping(0x70,"mouse_hold")])
    engine.event(0x70, True)
    engine.event(0xA2, True)
    engine.event(0x56, True)
    assert ("mouse","left",False) not in events
    engine.event(0x56, False)
    engine.event(0xA2, False)
    engine.event(0x70, False)
    assert events[-1] == ("mouse","left",False)


def test_unmapped_ctrl_and_ctrl_with_alt_keep_existing_rules():
    engine, events = rig(control=0xA3)
    assert not engine.event(0xA2, True)
    assert not engine.event(0x56, True)
    assert not events
    engine.event(0x56, False)
    engine.event(0xA2, False)
    engine.event(0xA3, True)
    engine.event(0xA4, True)
    assert not engine.event(0x56, True)
    assert not engine.paste_controls
