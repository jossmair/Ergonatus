from copy import deepcopy
from unittest.mock import patch
import pytest
from fortinatus.config import Mapping, Profile, Settings
from fortinatus.controller import Controller
from fortinatus.engine import Engine


class Service:
    def __init__(self, profile):
        self.events = []
        self.engine = Engine(self.events.append)
        self.engine.configure(deepcopy(profile))

    def configure(self, profile, enabled):
        self.engine.configure(deepcopy(profile), enabled)

    def stop(self):
        self.engine.pause()


@pytest.fixture
def configured(tmp_path):
    profile = Profile(name="Personnel", mappings=[Mapping(0xA2, "mouse_hold"), Mapping(0x70, keys=[0xA2, 67])],
                      invert_numbers=True, sticky_modifiers=True, debounce_ms=150, pointer_speed=20)
    settings = Settings(active_profile="Personnel", profiles=[profile, Profile(name="Autre")], start_minimized=True)
    controller = Controller(settings, tmp_path / "settings.json", no_hooks=True)
    controller.active = True
    controller.service = Service(profile)
    controller.saved = deepcopy(settings)
    return controller


def test_normal_keyboard_releases_click_retains_rules_and_keeps_next_launch_active(configured):
    controller = configured
    before = deepcopy(controller.settings.profile)
    controller.service.engine.event(0xA2, True)
    assert controller.restore_keyboard()
    assert controller.service.events[-1] == ("mouse", "left", False)
    assert not controller.active
    assert not controller.service.engine.enabled
    assert controller.settings.profile == before
    assert Settings.load(controller.path).start_active


def test_mouse_reset_preserves_keyboard_and_comfort_and_creates_backup(configured):
    controller = configured
    assert controller.reset_mouse()
    assert [m.kind for m in controller.settings.profile.mappings] == ["key"]
    assert controller.settings.profile.pointer_speed == 8
    assert controller.settings.profile.invert_numbers
    backups = list((controller.path.parent / "sauvegardes").glob("*.json"))
    assert len(backups) == 1
    assert len(Settings.load(backups[0]).profile.mappings) == 2
    assert not controller.active


def test_profile_reset_preserves_name_other_profiles_and_general_settings(configured):
    controller = configured
    assert controller.reset_profile()
    assert controller.settings.profile == Profile(name="Personnel")
    assert controller.settings.profiles[1] == Profile(name="Autre")
    assert controller.settings.start_minimized
    assert not controller.active
    assert Settings.load(controller.path) == controller.settings


def test_full_reset_restores_defaults_and_disables_startup(configured):
    controller = configured
    with patch("fortinatus.controller.startup_enabled", return_value=True), patch("fortinatus.controller.set_startup") as startup:
        assert controller.reset_all()
    startup.assert_called_once_with(False)
    assert controller.settings == Settings()
    assert not controller.active
    assert Settings.load(controller.path) == Settings()
    backup = next((controller.path.parent / "sauvegardes").glob("*.json"))
    assert Settings.load(backup).active_profile == "Personnel"


def test_failed_backup_keeps_all_profiles_intact(configured):
    controller = configured
    before = deepcopy(controller.settings)
    with patch.object(controller, "backup", side_effect=OSError("disk error")):
        assert not controller.reset_profile()
    assert controller.settings == before
    assert not controller.active

