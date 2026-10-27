import os
from unittest.mock import Mock
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton
from fortinatus.config import Mapping, Settings
from fortinatus.controller import Controller
from fortinatus.dialog import MappingDialog
from fortinatus.theme import configure_app
from fortinatus.ui import MainWindow

_app = None


def application():
    global _app
    _app = QApplication.instance() or QApplication([])
    configure_app(_app)
    return _app


def test_notifications_stay_silent_and_trash_replaces_restore_button(tmp_path):
    app = application()
    settings = Settings()
    settings.profile.mappings = [Mapping(0x70, "original"), Mapping(0x71, keys=[66])]
    controller = Controller(settings, tmp_path / "settings.json", no_hooks=True)
    window = MainWindow(controller)
    window.show()
    controller.notice.emit("F1 : fonction d’origine rétablie.")
    app.processEvents()
    assert not window.findChildren(QLabel, "Notice")
    assert not any("origine" in item.text() for item in window.findChildren(QPushButton))
    trash = window.findChildren(QPushButton, "Delete")
    assert len(trash) == 2 and all(not item.icon().isNull() for item in trash)
    trash[0].click()
    assert [m.source for m in controller.settings.profile.mappings] == [0x71]
    assert Settings.load(controller.path) == controller.settings
    assert list((tmp_path / "sauvegardes").glob("*.json"))
    window.allow_close = True
    window.close()


def test_sequence_editor_saves_order_changes_and_timing():
    app = application()
    dialog = MappingDialog(None, source=0x70, kind="sequence")
    editor = dialog.sequence_editor
    editor.add_step([0xA2, 65])
    editor.add_step([9])
    editor.add_step([13])
    editor.move_step(-1)
    assert editor.steps == [[0xA2, 65], [13], [9]]
    editor.remove_step()
    assert editor.steps == [[0xA2, 65], [9]]
    editor.interval.setValue(120)
    dialog.save()
    assert dialog.result() == QDialog.Accepted
    assert dialog.mapping.sequence == [[0xA2, 65], [9]]
    assert dialog.mapping.interval_ms == 120
    reopened = MappingDialog(None, mapping=dialog.mapping)
    assert reopened.sequence_editor.steps == dialog.mapping.sequence
    assert reopened.sequence_editor.interval.value() == 120
    reopened.reject()
    app.processEvents()


def test_loading_backup_selects_saved_keyboard_and_preserves_existing(tmp_path, monkeypatch):
    application()
    settings = Settings()
    settings.profile.mappings = [Mapping(0x70, keys=[65])]
    controller = Controller(settings, tmp_path / "settings.json", no_hooks=True)
    window = MainWindow(controller)
    saved = Settings()
    saved.profile.mappings = [Mapping(0x71, keys=[66])]
    backup_file = tmp_path / "export.json"
    saved.save(backup_file)
    monkeypatch.setattr("fortinatus.profile_actions.QFileDialog.getOpenFileName",
                        lambda *args: (str(backup_file), ""))
    window.import_settings()
    # A name collision must still activate the loaded keyboard, preserving the old one.
    assert len(controller.settings.profiles) == 2
    assert controller.settings.profiles[0].mappings == [Mapping(0x70, keys=[65])]
    assert controller.settings.profile.mappings == saved.profile.mappings
    assert controller.settings.active_profile != saved.active_profile
    assert Settings.load(controller.path) == controller.settings
    backups = list((tmp_path / "sauvegardes").glob("*.json"))
    assert len(backups) == 1
    assert Settings.load(backups[0]).profile.mappings == [Mapping(0x70, keys=[65])]
    window.allow_close = True
    window.close()


def test_header_switch_pauses_and_resumes_without_erasing_keys(tmp_path):
    application()
    settings = Settings()
    settings.profile.mappings = [Mapping(0xA2, "mouse_hold")]
    controller = Controller(settings, tmp_path / "settings.json", no_hooks=True)
    controller.service = Mock()
    controller.active = True
    window = MainWindow(controller)
    assert window.activation.isChecked()
    window.activation.click()
    assert not controller.active
    assert not window.activation.isChecked()
    assert window.activation.text() == "En pause"
    assert Settings.load(controller.path).profile.mappings == settings.profile.mappings
    window.activation.click()
    assert controller.active and window.activation.isChecked()
    controller.service.configure.assert_called_with(settings.profile, True)
    controller.service.configure.reset_mock()
    controller.active = False
    controller.state.emit(False)
    assert not window.activation.isChecked()
    controller.service.configure.assert_not_called()
    window.allow_close = True
    window.close()
