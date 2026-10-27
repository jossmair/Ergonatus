import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider

from services.configuration import Preferences
from ui.settings_window import SettingsWindow


@pytest.mark.parametrize("key", ["zoom", "size", "appearance", "aim"])
def test_click_anywhere_selects_a_detent_without_dragging(app, key):
    window = SettingsWindow(Preferences())
    window.show()
    app.processEvents()
    slider = window.sliders[key]
    for fraction, expected in ((.95, 2), (.05, 0), (.50, 1)):
        QTest.mouseClick(slider, Qt.LeftButton, Qt.NoModifier,
                         QPoint(round(slider.width() * fraction), slider.height() // 2))
        assert slider.value() == expected
        assert slider.choices[expected][1] in slider.accessibleName()
        assert window.value_labels[key].text() == slider.choices[expected][1]
    window.hide()


def test_native_slider_drag_and_standard_keyboard_remain_available(app):
    window = SettingsWindow(Preferences())
    window.show()
    app.processEvents()
    slider = window.sliders["size"]
    option = QStyleOptionSlider()
    slider.initStyleOption(option)
    thumb = slider.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, slider)
    end = QPoint(slider.width() - 14, thumb.center().y())
    QTest.mousePress(slider, Qt.LeftButton, Qt.NoModifier, thumb.center())
    QTest.mouseMove(slider, end)
    QTest.mouseRelease(slider, Qt.LeftButton, Qt.NoModifier, end)
    assert slider.value() == 2
    QTest.keyClick(slider, Qt.Key_Left)
    assert slider.value() == 1
    window.hide()


def test_zoom_slider_emits_factor_and_refresh_does_not_emit(app):
    window = SettingsWindow(Preferences())
    changes = []
    window.zoom_changed.connect(changes.append)
    window.sliders["zoom"].setValue(2)
    assert changes == [3.]
    window.refresh(Preferences(magnification=1.8))
    assert changes == [3.]
    assert window.value_labels["zoom"].text() == "×1,8"


def test_compact_settings_need_no_scrolling_at_default_size(app):
    window = SettingsWindow(Preferences())
    window.show()
    app.processEvents()
    assert window.size().width() == 420 and window.size().height() == 456
    assert len(window.findChildren(QSlider)) == 5
    assert window.area.verticalScrollBar().maximum() == 0
    assert all(slider.maximum() - slider.minimum() == 2
               for key, slider in window.sliders.items() if key != "mouse_speed")
    window.hide()
