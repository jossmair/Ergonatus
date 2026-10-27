from copy import deepcopy
from unittest.mock import patch

from fortinatus.config import Mapping, Profile, Settings
from fortinatus.controller import Controller
from test_resets import Service


def configured(path, **options):
    profile = Profile(mappings=[Mapping(0xA2, "mouse_click"), Mapping(0x70, "original", enabled=False)], **options)
    settings = Settings(profiles=[profile, Profile(name="Autre", mappings=[Mapping(65, "text", text="Bonjour !")])])
    controller = Controller(settings, path, no_hooks=True)
    controller.active = True
    controller.service = Service(profile)
    return controller


def test_deleting_held_mouse_rule_releases_click_preserves_others_and_active_state(tmp_path):
    controller = configured(tmp_path / "settings.json")
    other = deepcopy(controller.settings.profiles[1])
    controller.service.engine.event(0xA2, True)
    assert controller.delete_mapping(0xA2)
    assert controller.active
    assert controller.service.events == [("mouse", "left", True), ("mouse", "left", False)]
    assert controller.settings.profile.mappings == [Mapping(0x70, "original", enabled=False)]
    assert controller.settings.profiles[1] == other
    assert Settings.load(controller.path) == controller.settings
    backup = next((tmp_path / "sauvegardes").glob("*.json"))
    assert len(Settings.load(backup).profile.mappings) == 2


def test_deleting_original_row_removes_exception_and_keeps_global_number_setting(tmp_path):
    controller = configured(tmp_path / "settings.json", invert_numbers=True)
    controller.settings.profile.mappings.append(Mapping(49, "original"))
    assert controller.delete_mapping(49)
    assert controller.settings.profile.invert_numbers
    assert not any(mapping.source == 49 for mapping in controller.settings.profile.mappings)
    controller.service.engine.event(49, True)
    assert controller.service.events == [("text", "1")]


def test_failed_deletion_backup_keeps_profile_and_held_click_intact(tmp_path):
    controller = configured(tmp_path / "settings.json")
    before = deepcopy(controller.settings)
    controller.service.engine.event(0xA2, True)
    with patch.object(controller, "backup", side_effect=OSError("disque indisponible")):
        assert not controller.delete_mapping(0xA2)
    assert controller.settings == before
    assert controller.service.events == [("mouse", "left", True)]
    controller.stop()


def test_saved_edits_and_deletion_are_restored_by_a_new_controller(tmp_path):
    path = tmp_path / "settings.json"
    controller = configured(path, invert_numbers=True, debounce_ms=250)
    assert controller.delete_mapping(0x70)
    controller.settings.profile.mappings[0].enabled = False
    controller.settings.start_minimized = True
    assert controller.commit()
    expected = deepcopy(controller.settings)
    controller.stop()
    reopened = Controller(Settings.load(path), path, no_hooks=True)
    assert reopened.settings == expected
    assert reopened.settings.profile.mappings == [Mapping(0xA2, "mouse_click", enabled=False)]
    assert reopened.settings.profiles[1].mappings[0].text == "Bonjour !"
