from copy import deepcopy
import pytest
from fortinatus.config import Mapping, Profile, Settings
from fortinatus.controller import Controller
from fortinatus.engine import Engine
from test_resets import Service


def test_restore_one_ctrl_preserves_other_mappings_profiles_and_running_state(tmp_path):
    profile = Profile(mappings=[Mapping(0xA2, "mouse_hold"), Mapping(0xA3, "mouse_hold")])
    settings = Settings(profiles=[profile, Profile(name="Autre")])
    controller = Controller(settings, tmp_path / "settings.json", no_hooks=True)
    controller.active = True
    controller.service = Service(profile)
    controller.service.engine.event(0xA2, True)
    other = deepcopy(settings.profiles[1])
    assert controller.restore_key(0xA2)
    assert controller.settings.profile.mappings == [Mapping(0xA3, "mouse_hold")]
    assert controller.settings.profiles[1] == other
    assert controller.active
    assert ("mouse", "left", False) in controller.service.events
    backup = next((tmp_path / "sauvegardes").glob("*.json"))
    assert len(Settings.load(backup).profile.mappings) == 2


def test_restore_one_number_bypasses_inversion_only_for_that_key(tmp_path):
    settings = Settings(profiles=[Profile(invert_numbers=True)])
    controller = Controller(settings, tmp_path / "settings.json", no_hooks=True)
    assert controller.restore_key(49)
    assert settings.profile.invert_numbers
    events = []
    engine = Engine(events.append)
    engine.configure(Settings.load(controller.path).profile)
    assert not engine.event(49, True)
    assert not engine.event(49, False)
    assert engine.event(50, True)
    assert events == [("text", "2")]


def test_restored_key_bypasses_repeat_and_bounce_filters_but_others_do_not():
    engine = Engine(lambda event: None)
    engine.configure(Profile(suppress_repeat=True, debounce_ms=500, mappings=[Mapping(65, "original")]))
    for _ in range(2):
        assert not engine.event(65, True)
        assert not engine.event(65, True)
        assert not engine.event(65, False)
    assert not engine.event(66, True)
    assert engine.event(66, True)


def test_original_ctrl_preserves_normal_shortcuts_while_numbers_are_inverted():
    events = []
    engine = Engine(events.append)
    engine.configure(Profile(invert_numbers=True, mappings=[Mapping(0xA2, "original")]))
    assert not engine.event(0xA2, True)
    assert not engine.event(49, True)
    assert not engine.event(49, False)
    assert not engine.event(0xA2, False)
    assert not events


def test_original_ctrl_never_latches_with_sequential_modifiers():
    engine = Engine(lambda event: None)
    engine.configure(Profile(sticky_modifiers=True, mappings=[Mapping(0xA2, "original")]))
    assert not engine.event(0xA2, True)
    assert not engine.event(0xA2, False)
    assert not engine.latched


@pytest.mark.parametrize("source", [0x7B, -1, 999, "A"])
def test_reserved_and_invalid_keys_cannot_be_restored(source, tmp_path):
    settings = Settings()
    controller = Controller(settings, tmp_path / "settings.json", no_hooks=True)
    assert not controller.restore_key(source)
    assert settings == Settings()

