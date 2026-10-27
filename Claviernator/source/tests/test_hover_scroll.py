import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from dataclasses import asdict
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QEvent, QPointF, QRect, QSize
from PySide6.QtGui import QEnterEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from fortinatus.config import Settings
from fortinatus.controller import Controller
from fortinatus.desktop_target import DesktopTarget, EditingTarget, ScrollTarget
from fortinatus.hover_scroll import HoverScrollArrow
from fortinatus.keyboard_orb import VirtualKeyboardManager, orb_position, scroll_arrow_positions


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def enter(arrow, app):
    point = QPointF(18, 12)
    app.sendEvent(arrow, QEnterEvent(point, point, point))


@pytest.mark.parametrize("direction", [1, -1])
def test_dwell_scrolls_without_click_then_stops_immediately_on_leave(app, direction):
    arrow = HoverScrollArrow(direction)
    events = []
    arrow.scroll_requested.connect(events.append)
    arrow.show()
    enter(arrow, app)
    QTest.qWait(100)
    assert not events
    QTest.qWait(310)
    assert events == [direction * 120]
    assert arrow.repeat.isActive()
    app.sendEvent(arrow, QEvent(QEvent.Leave))
    QTest.qWait(300)
    assert events == [direction * 120] and not arrow.repeat.isActive()
    arrow.hide()


@pytest.mark.parametrize("action", ["hide", "disable"])
def test_hidden_or_disabled_arrow_cancels_pending_dwell(app, action):
    arrow = HoverScrollArrow(1)
    events = []
    arrow.scroll_requested.connect(events.append)
    arrow.show()
    enter(arrow, app)
    arrow.hide() if action == "hide" else arrow.setEnabled(False)
    QTest.qWait(400)
    assert not events and not arrow.dwell.isActive() and not arrow.repeat.isActive()
    arrow.hide()


@pytest.mark.parametrize("value", ["oui", 1, 0, None])
def test_hover_setting_requires_boolean(value):
    data = asdict(Settings())
    data["hover_scroll"] = value
    with pytest.raises(ValueError):
        Settings.from_dict(data)


def test_legacy_settings_keep_mappings_and_enable_hover_by_default():
    data = asdict(Settings(virtual_keyboard=False))
    del data["hover_scroll"]
    settings = Settings.from_dict(data)
    assert settings.hover_scroll and not settings.virtual_keyboard


def test_option_is_persistent_and_pause_cancels_scrolling(app, tmp_path):
    controller = Controller(Settings(), tmp_path / "settings.json", no_hooks=True)
    controller.active = True
    desktop = Mock()
    desktop.capture.return_value = EditingTarget(1, 2, 3, "Document")
    desktop.scroll.return_value = True
    manager = VirtualKeyboardManager(controller, desktop=desktop)
    try:
        chosen = ScrollTarget(1, 2, 3, 100, 100)
        manager.remember_scroll_target(chosen)
        down = manager.arrows[1]
        assert all(arrow.isVisible() for arrow in manager.arrows)
        enter(down, app)
        down.begin_scroll()
        desktop.scroll.assert_called_once_with(chosen, -120)
        controller.pause_runtime()
        assert not down.repeat.isActive() and not down.isEnabled()
        manager.scroll(-120)
        assert desktop.scroll.call_count == 1
        controller.settings.hover_scroll = False
        assert controller.commit()
        assert all(not arrow.isVisible() for arrow in manager.arrows)
        assert not Settings.load(controller.path).hover_scroll
        assert manager.orb.isVisible()
    finally:
        manager.stop()


def test_arrows_reserve_space_above_transcrinator_on_negative_monitor():
    area = QRect(-1920, 0, 1920, 1040)
    yellow = QRect(-70, 950, 36, 36)
    orb = QRect(orb_position(area, companion=yellow, scroll_arrows=True), QSize(36, 36))
    up, down = [QRect(point, QSize(HoverScrollArrow.WIDTH, HoverScrollArrow.HEIGHT))
                for point in scroll_arrow_positions(orb)]
    assert all(area.contains(rect) for rect in (up, orb, down))
    assert up.top() < orb.top() and down.bottom() > orb.bottom()
    assert not up.contains(orb.center()) and not down.contains(orb.center())
    assert down.bottom() < yellow.top() - 9


def test_wheel_routes_to_document_without_moving_pointer_or_changing_focus():
    desktop = DesktopTarget.__new__(DesktopTarget)
    desktop.user = Mock()
    desktop.adapter = Mock()
    desktop.process = Mock(return_value=3)
    desktop.user.GetForegroundWindow.return_value = 99
    desktop.user.GetAncestor.return_value = 1
    desktop.user.IsWindow.return_value = True
    target = ScrollTarget(1, 2, 3, -40, 500)
    assert desktop.scroll(target, -120)
    desktop.user.PostMessageW.assert_called_once_with(2, 0x020A, 0xFF880000, (500 << 16) | 0xFFD8)
    desktop.user.SetFocus.assert_not_called()
    desktop.user.SetCursorPos.assert_not_called()
    desktop.user.GetForegroundWindow.assert_not_called()
    desktop.adapter.send.assert_not_called()


def test_closed_document_receives_no_wheel_message():
    desktop = DesktopTarget.__new__(DesktopTarget)
    desktop.user = Mock()
    desktop.user.IsWindow.return_value = False
    assert not desktop.scroll(ScrollTarget(1, 2, 3, 20, 30), 120)
    desktop.user.PostMessageW.assert_not_called()


def test_focus_and_hover_never_replace_the_last_clicked_scroll_pane(app, tmp_path):
    controller = Controller(Settings(), tmp_path / "settings.json", no_hooks=True)
    controller.active = True
    desktop = Mock()
    desktop.capture.return_value = EditingTarget(8, 9, 10, "Champ au premier plan")
    desktop.scroll.return_value = True
    manager = VirtualKeyboardManager(controller, desktop=desktop)
    try:
        manager.scroll(-120)
        desktop.scroll.assert_not_called()  # No external click has been observed yet.
        pane = ScrollTarget(1, 2, 3, 70, 90)
        manager.remember_scroll_target(pane)
        manager.track_target()
        manager.scroll(-120)
        desktop.scroll.assert_called_once_with(pane, -120)
        next_pane = ScrollTarget(1, 4, 3, 220, 90)
        manager.remember_scroll_target(next_pane)
        manager.scroll(120)
        desktop.scroll.assert_called_with(next_pane, 120)
        assert manager.last_target == desktop.capture.return_value
    finally:
        manager.stop()


@pytest.mark.parametrize("changed", ["root", "recipient", "disabled"])
def test_reused_or_disabled_window_cannot_receive_stale_scroll(changed):
    desktop = DesktopTarget.__new__(DesktopTarget)
    desktop.user = Mock()
    desktop.user.IsWindow.return_value = True
    desktop.user.IsWindowEnabled.return_value = changed != "disabled"
    desktop.user.GetAncestor.return_value = 1
    desktop.process = lambda hwnd: 44 if hwnd == (1 if changed == "root" else 2) else 3
    assert not desktop.scroll(ScrollTarget(1, 2, 3, 20, 30), 120)
    desktop.user.PostMessageW.assert_not_called()


@pytest.fixture
def clicked_desktop():
    desktop = DesktopTarget.__new__(DesktopTarget)
    desktop.user = Mock()
    desktop.process = Mock(return_value=345)
    desktop.user.WindowFromPoint.return_value = 2
    desktop.user.GetAncestor.return_value = 1
    desktop.user.IsWindowEnabled.return_value = True
    desktop.user.GetWindowLongPtrW.return_value = 0
    def client_rect(hwnd, pointer):
        pointer._obj.right, pointer._obj.bottom = 400, 300
        return True
    def client_origin(hwnd, pointer):
        pointer._obj.x, pointer._obj.y = -100, 50
        return True
    desktop.user.GetClientRect.side_effect = client_rect
    desktop.user.ClientToScreen.side_effect = client_origin
    return desktop


def test_click_captures_exact_child_and_point_without_using_keyboard_focus(clicked_desktop):
    desktop = clicked_desktop
    assert desktop.capture_scroll(-40, 150) == ScrollTarget(1, 2, 345, -40, 150)
    desktop.user.GetForegroundWindow.assert_not_called()
    desktop.user.GetGUIThreadInfo.assert_not_called()
    desktop.user.SetFocus.assert_not_called()


@pytest.mark.parametrize("ignored", ["own", "taskbar", "menu", "orb", "titlebar", "disabled"])
def test_click_on_helpers_or_shell_does_not_replace_document_target(clicked_desktop, ignored):
    desktop = clicked_desktop
    if ignored == "own":
        desktop.process.return_value = os.getpid()
    elif ignored in ("taskbar", "menu"):
        def name(hwnd, buffer, size):
            buffer.value = "Shell_TrayWnd" if ignored == "taskbar" else "#32768"
        desktop.user.GetClassNameW.side_effect = name
    elif ignored == "orb":
        desktop.user.GetWindowLongPtrW.return_value = 0x08000000
    elif ignored == "disabled":
        desktop.user.IsWindowEnabled.return_value = False
    assert desktop.capture_scroll(-40, 40 if ignored == "titlebar" else 150) is None
