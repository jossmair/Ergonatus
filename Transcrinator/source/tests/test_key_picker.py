from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.ui.caption_button import CaptionButton
from app.ui.main_window import MainWindow
from app.ui.premium import STYLE


def window_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE)
    controller = Controller(Settings(), Hardware("fixture", 4, 16 * 2**30, 8 * 2**30))
    window = MainWindow(controller)
    window.show()
    app.processEvents()
    return app, controller, window


def test_picker_mouse_selection_is_saved_once_without_loading_model(tmp_path, monkeypatch):
    app, controller, window = window_fixture(tmp_path, monkeypatch)
    changes = []
    window.trigger_changed.connect(changes.append)
    picker = window.trigger_key
    QTest.mouseClick(picker, Qt.LeftButton)
    app.processEvents()
    popup = picker.popup
    assert popup.isVisible() and len(popup.buttons) == 16
    assert popup.width() == 322 and popup.height() < 270
    assert all(button.visibleRegion().boundingRect() == button.rect() for button in popup.buttons)
    assert popup.grab().toImage().pixelColor(0, 0).alpha() == 0
    QTest.mouseClick(popup.buttons[picker.findData("f8")], Qt.LeftButton)
    assert changes == ["f8"] and Settings.load().trigger_key == "f8"
    assert not popup.isVisible() and controller.commands.empty()
    window.hide()


def test_picker_escape_preserves_choice_and_keyboard_confirms_one_change(tmp_path, monkeypatch):
    app, controller, window = window_fixture(tmp_path, monkeypatch)
    picker = window.trigger_key
    changes = []
    window.trigger_changed.connect(changes.append)
    picker.showPopup()
    app.processEvents()
    QTest.keyClick(picker.popup.buttons[0], Qt.Key_Right)
    QTest.keyClick(picker.popup.buttons[1], Qt.Key_Escape)
    assert not changes and picker.currentData() == "shift_left"
    QTest.keyClick(picker, Qt.Key_Space)
    app.processEvents()
    QTest.keyClick(picker.popup.buttons[0], Qt.Key_Right)
    assert picker.popup.buttons[1].hasFocus()
    QTest.keyClick(picker.popup.buttons[1], Qt.Key_Return)
    assert changes == ["shift_right"]
    assert Settings.load().trigger_key == "shift_right" and controller.commands.empty()
    window.hide()


def test_caption_close_button_only_hides_the_window(tmp_path, monkeypatch):
    app, controller, window = window_fixture(tmp_path, monkeypatch)
    close = next(button for button in window.findChildren(CaptionButton) if button.close_icon)
    assert close.accessibleName() == "Masquer" and close.size().width() == 32
    QTest.mouseClick(close, Qt.LeftButton)
    assert not window.isVisible() and controller.commands.empty()
