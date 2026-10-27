from fortinatus.config import Mapping, Profile
from fortinatus.engine import Engine


def test_mapping_does_not_release_a_physically_held_modifier():
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(mappings=[Mapping(0x70, keys=[0xA2, 67])]))
    assert not engine.event(0xA2, True)
    engine.event(0x70, True)
    engine.event(0x70, False)
    assert events == [("key", 67, True), ("key", 67, False)]
    assert not engine.event(0xA2, False)


def test_mapping_bridges_physical_release_until_its_own_release():
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(mappings=[Mapping(0x70, keys=[0xA2, 67])]))
    engine.event(0xA2, True)
    engine.event(0x70, True)
    assert engine.event(0xA2, False)
    assert ("key", 0xA2, False) not in events
    engine.event(0x70, False)
    assert events[-1] == ("key", 0xA2, False)


def test_pause_does_not_leave_passthrough_shift_stuck_after_enabling_sticky():
    events = []
    engine = Engine(events.append)
    engine.configure(Profile())
    engine.event(0xA0, True)
    engine.configure(Profile(sticky_modifiers=True))
    assert not engine.event(0xA0, False)
    assert not engine.latched


def test_remapped_modifier_is_not_used_as_sticky_modifier():
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(sticky_modifiers=True, mappings=[Mapping(0xA2, "mouse_hold")]))
    engine.event(0xA2, True)
    assert not engine.event(65, True)
    assert events == [("mouse", "left", True)]


def test_remapped_ctrl_preserves_number_shortcuts():
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(invert_numbers=True, mappings=[Mapping(0x70, keys=[0xA2])]))
    engine.event(0x70, True)
    assert not engine.event(49, True)
    assert events == [("key", 0xA2, True)]
    engine.event(49, False)
    engine.event(0x70, False)
    assert events[-1] == ("key", 0xA2, False)


def test_remapped_shift_accesses_symbols():
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(invert_numbers=True, mappings=[Mapping(0x70, keys=[0xA0])]))
    engine.event(0x70, True)
    engine.event(50, True)
    assert events == [("key", 0xA0, True), ("text", "é")]


