from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.ui.main_window import MainWindow


def test_trigger_survives_restart_and_automatic_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    settings = Settings(trigger_key="f8")
    settings.configure_automatic()
    assert Settings.load().trigger_key == "f8"
    settings.trigger_key = "unsupported"
    settings.save()
    assert Settings.load().trigger_key == "shift_left"


def test_ui_rebind_is_immediate_and_does_not_queue_model_load(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    controller = Controller(Settings(), Hardware("fixture", 4, 16 * 2**30, 8 * 2**30))
    window = MainWindow(controller)
    window.set_state("Écoute…")
    changed = []
    window.trigger_changed.connect(changed.append)
    window.trigger_key.setCurrentIndex(window.trigger_key.findData("f8"))
    assert changed == ["f8"] and Settings.load().trigger_key == "f8"
    assert "F8" in window.detail.text()
    assert controller.commands.empty()
    window.show()
    app.processEvents()
    window.units.setFocus()
    QTest.keyClick(window.units, Qt.Key_Space)
    assert not window.units.isChecked()
    assert not Settings.load().abbreviate_units
    assert controller.commands.get_nowait()[0] == "text_options"
    window.hide()
    window.deleteLater()
    app.processEvents()


def test_failed_key_save_keeps_previous_binding(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    window = MainWindow(Controller(Settings(), Hardware("fixture", 4, 16 * 2**30, 8 * 2**30)))
    def fail():
        raise PermissionError("fixture")
    monkeypatch.setattr(window.preferences, "save", fail)
    changed = []
    window.trigger_changed.connect(changed.append)
    window.trigger_key.setCurrentIndex(window.trigger_key.findData("f8"))
    assert not changed
    assert window.trigger_key.currentData() == window.preferences.trigger_key == "shift_left"
    window.deleteLater()
    app.processEvents()
