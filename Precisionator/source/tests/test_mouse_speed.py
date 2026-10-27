import ctypes as C

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QStyle, QStyleOptionSlider

from services import mouse_speed
from services.configuration import Preferences
from ui.settings_window import SettingsWindow


@pytest.mark.parametrize("speed", [1, 6, 10, 15, 20])
def test_reads_exact_windows_speed_without_writing(monkeypatch, speed):
    calls = []
    def api(action, unused, parameter, flags):
        calls.append((action, unused, flags))
        C.cast(parameter, C.POINTER(C.c_int)).contents.value = speed
        return True
    monkeypatch.setattr(mouse_speed, "_api", lambda: api)
    assert mouse_speed.get_speed() == speed
    assert calls == [(0x0070, 0, 0)]


@pytest.mark.parametrize("speed", range(1, 21))
def test_changes_only_pointer_speed_with_correct_win32_parameter(monkeypatch, speed):
    calls = []
    def api(action, unused, parameter, flags):
        assert isinstance(parameter, C.c_void_p)
        calls.append((action, unused, parameter.value, flags))
        return True
    monkeypatch.setattr(mouse_speed, "_api", lambda: api)
    mouse_speed.set_speed(speed)
    assert calls == [(0x0071, 0, speed, 3)]


@pytest.mark.parametrize("speed", [0, 21, -10, True, False, 1.5, "10", None])
def test_rejects_invalid_speed_before_loading_any_api(monkeypatch, speed):
    monkeypatch.setattr(mouse_speed, "_api", lambda: pytest.fail("No Windows access for invalid values"))
    with pytest.raises(ValueError):
        mouse_speed.set_speed(speed)


@pytest.mark.parametrize("action", [mouse_speed.get_speed, lambda: mouse_speed.set_speed(10)])
def test_windows_failure_is_reported(monkeypatch, action):
    C.set_last_error(5)
    monkeypatch.setattr(mouse_speed, "_api", lambda: lambda *_: False)
    with pytest.raises(OSError):
        action()


def test_invalid_readback_is_unavailable_instead_of_changing_windows(monkeypatch):
    monkeypatch.setattr(mouse_speed, "_api", lambda: lambda *_: True)
    with pytest.raises(OSError):
        mouse_speed.get_speed()


def test_slider_keeps_exact_existing_speed_and_refresh_emits_no_change(app):
    window = SettingsWindow(Preferences(), mouse_speed=13)
    changes = []
    window.mouse_speed_changed.connect(changes.append)
    assert window.sliders["mouse_speed"].value() == 12
    assert window.value_labels["mouse_speed"].text() == "Rapide"
    window.refresh_mouse_speed(6)
    window.refresh(Preferences(enabled=False))
    assert window.sliders["mouse_speed"].value() == 5
    assert window.value_labels["mouse_speed"].text() == "Lente"
    assert changes == []


def test_speed_bar_accepts_direct_click_and_commits_drag_on_release(app):
    window = SettingsWindow(Preferences(), mouse_speed=10)
    window.show()
    app.processEvents()
    slider = window.sliders["mouse_speed"]
    changes = []
    window.mouse_speed_changed.connect(changes.append)
    QTest.mouseClick(slider, Qt.LeftButton, pos=QPoint(slider.width() - 2, 17))
    assert changes == [20]
    assert window.value_labels["mouse_speed"].text() == "Très rapide"
    option = QStyleOptionSlider()
    slider.initStyleOption(option)
    handle = slider.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, slider)
    QTest.mousePress(slider, Qt.LeftButton, pos=handle.center())
    QTest.mouseMove(slider, QPoint(2, handle.center().y()))
    assert changes == [20]
    QTest.mouseRelease(slider, Qt.LeftButton, pos=QPoint(2, handle.center().y()))
    assert changes == [20, 1]
    assert "Très lente" in slider.accessibleName()
    window.hide()


def test_unavailable_speed_leaves_other_settings_usable(app):
    window = SettingsWindow(Preferences(), mouse_speed=10)
    window.refresh_mouse_speed(None)
    assert not window.sliders["mouse_speed"].isEnabled()
    assert window.value_labels["mouse_speed"].text() == "Indisponible"
    assert all(slider.isEnabled() for key, slider in window.sliders.items() if key != "mouse_speed")
    window.refresh_mouse_speed(10)
    assert window.sliders["mouse_speed"].isEnabled()
