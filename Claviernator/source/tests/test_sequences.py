from copy import deepcopy
import pytest
from fortinatus.config import Mapping, Profile, Settings
from fortinatus.engine import Engine


def sequence_rig(steps=None):
    now, events = [10.0], []
    mapping = Mapping(0x70, "sequence", sequence=steps or [[0xA2, 65], [9], [13]], interval_ms=80)
    engine = Engine(events.append, clock=lambda: now[0])
    engine.configure(Profile(mappings=[mapping]))
    return engine, events, now


def finish(engine, now):
    for _ in range(100):
        now[0] += .021
        engine.tick()


def test_sequence_fires_once_continues_after_release_and_releases_each_chord():
    engine, events, now = sequence_rig()
    assert engine.event(0x70, True)
    for _ in range(10):
        assert engine.event(0x70, True)
    assert engine.event(0x70, False)
    finish(engine, now)
    assert events == [("key", 0xA2, True), ("key", 65, True), ("key", 65, False),
                      ("key", 0xA2, False), ("key", 9, True), ("key", 9, False),
                      ("key", 13, True), ("key", 13, False)]
    assert not engine.sequences and not engine.owners


@pytest.mark.parametrize("action", ["pause", "configure", "emergency"])
@pytest.mark.parametrize("phase", ["held", "between"])
def test_cancel_releases_outputs_and_discards_remaining_steps(action, phase):
    engine, events, now = sequence_rig()
    engine.event(0x70, True)
    if phase == "between":
        now[0] += .021
        engine.tick()
    if action == "configure":
        engine.configure(Profile())
    elif action == "emergency":
        assert engine.event(0x7B, True)
    else:
        engine.pause()
    finish(engine, now)
    assert events == [("key", 0xA2, True), ("key", 65, True), ("key", 65, False), ("key", 0xA2, False)]
    assert not engine.owners and not engine.sequences
    assert engine.event(0x70, False)


def test_distinct_presses_queue_serially_and_allow_repeated_steps():
    engine, events, now = sequence_rig([[65], [65], [66]])
    for _ in range(2):
        engine.event(0x70, True)
        engine.event(0x70, False)
    finish(engine, now)
    assert [event[1] for event in events if event[-1] is True] == [65, 65, 66, 65, 65, 66]
    assert not engine.owners and not engine.sequences


def test_interval_does_not_catch_up_in_a_burst_after_a_slow_tick():
    engine, events, now = sequence_rig([[65], [66]])
    engine.event(0x70, True)
    now[0] += 10
    engine.tick()
    assert events == [("key", 65, True), ("key", 65, False)]
    engine.tick()
    assert len(events) == 2
    now[0] += .081
    engine.tick()
    assert events[-1] == ("key", 66, True)


def test_sequence_does_not_release_another_mappings_owned_modifier():
    engine, events, now = sequence_rig()
    profile = deepcopy(engine.profile)
    profile.mappings.append(Mapping(0x71, keys=[0xA2]))
    engine.configure(profile)
    engine.event(0x71, True)
    engine.event(0x70, True)
    finish(engine, now)
    assert ("key", 0xA2, False) not in events
    assert engine.event(0x71, False)
    assert events[-1] == ("key", 0xA2, False)
    assert not engine.owners


def test_sequence_waits_for_a_real_modifier_to_be_released():
    engine, events, now = sequence_rig([[65]])
    assert not engine.event(0xA2, True)
    engine.event(0x70, True)
    engine.event(0x70, False)
    finish(engine, now)
    assert not events
    assert not engine.event(0xA2, False)
    finish(engine, now)
    assert events == [("key", 65, True), ("key", 65, False)]


def test_sequence_roundtrip_and_legacy_settings(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(profiles=[Profile(mappings=[Mapping(0x70, "sequence", sequence=[[0xA2, 65], [9], [9]])])])
    settings.save(path)
    assert Settings.load(path) == settings
    legacy = Settings.from_dict({"profiles": [{"mappings": [{"source": 112, "keys": [65]}]}]})
    assert legacy.profile.mappings[0].sequence == []


@pytest.mark.parametrize("change", [
    {"sequence": []}, {"sequence": [[65]] * 51}, {"sequence": [[]]},
    {"sequence": [[65, 65]]}, {"sequence": [[0x7B]]}, {"sequence": [[True]]},
    {"sequence": [[-1]]}, {"sequence": "abc"}, {"sequence": [65]},
    {"interval_ms": 0}, {"interval_ms": 2001}, {"interval_ms": True},
])
def test_invalid_sequences_are_rejected(change):
    mapping = Mapping(0x70, "sequence", sequence=[[65]])
    for key, value in change.items():
        setattr(mapping, key, value)
    with pytest.raises(ValueError):
        mapping.validate()
