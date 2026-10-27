from types import SimpleNamespace
import threading

import pytest
from PySide6.QtCore import QAbstractNativeEventFilter, QEvent, QObject, QPointF, Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent
from PySide6.QtTest import QTest

import application
from application import Application
from core.screen_capture import Request
from services.configuration import Configuration, Preferences
from services.orb_positioning import Rect
from services.win32 import Monitor


@pytest.fixture
def controller(app, monkeypatch, tmp_path):
    class Desktop:
        unavailable = False
        def monitors(self):
            if self.unavailable:
                raise OSError("Pilote temporairement indisponible")
            screen = app.primaryScreen()
            g = screen.geometry()
            bounds = Rect(g.x(), g.y(), g.width(), g.height())
            return [Monitor(1, screen.name(), bounds, bounds, 1)]
        def pointer(self):
            return 100, 100
        def companions(self):
            return []
        def family_layout(self):
            return [], []
    class Worker(QObject):
        frame_ready = Signal(object, object, float)
        failed = Signal(str)
        def __init__(self):
            super().__init__()
            self.needs_probe = threading.Event()
            self.needs_probe.set()
        def release(self):
            self.needs_probe.set()
        def acknowledge(self):
            pass
        def close(self):
            pass
    class Lifecycle(QAbstractNativeEventFilter):
        def __init__(self, *_):
            super().__init__()
        def nativeEventFilter(self, *_):
            return False, 0
        def close(self):
            pass
    monkeypatch.setattr(application, "Desktop", Desktop)
    monkeypatch.setattr(application, "CaptureWorker", Worker)
    monkeypatch.setattr(application, "Lifecycle", Lifecycle)
    monkeypatch.setattr(application, "InstanceServer", lambda _: SimpleNamespace(server=SimpleNamespace(close=lambda: None)))
    monkeypatch.setattr(application.windows_startup, "enabled", lambda: False)
    mouse = SimpleNamespace(speed=10, writes=[])
    monkeypatch.setattr(application.mouse_speed, "get_speed", lambda: mouse.speed)
    def set_speed(value):
        mouse.speed = value
        mouse.writes.append(value)
    monkeypatch.setattr(application.mouse_speed, "set_speed", set_speed)
    config = Configuration(tmp_path / "settings.json")
    config.save(Preferences())
    result = Application(app, config)
    result.test_mouse_speed = mouse
    result.tracker.stop()
    yield result
    result.close()


def test_capture_failure_never_disables_or_saves_a_disabled_preference(controller):
    controller.fail("Capture interrompue")
    assert controller.prefs.enabled and controller.orb.enabled
    assert controller.config.load().enabled
    assert controller.retry_timer.isActive()
    assert controller.retry_timer.interval() == 250
    controller.retry_capture()
    assert not controller.fault
    assert controller.tracker.timer.isActive()


def test_repeated_driver_failures_retry_with_bounded_backoff(controller):
    controller.fail("Pilote perdu")
    controller.desktop.unavailable = True
    delays = [controller.retry_timer.interval()]
    for _ in range(12):
        controller.retry_timer.stop()
        controller.retry_capture()
        delays.append(controller.retry_timer.interval())
    assert delays[:5] == [250, 500, 1000, 2000, 4000]
    assert all(250 <= delay <= 4000 for delay in delays)
    assert controller.prefs.enabled and controller.config.load().enabled
    controller.desktop.unavailable = False
    controller.retry_capture()
    assert not controller.fault
    assert not controller.retry_timer.isActive()


def test_user_can_disable_during_recovery_and_no_retry_reenables_it(controller):
    controller.fail("Erreur transitoire")
    controller.set_enabled(False)
    controller.retry_capture()
    controller.fail("Ancienne erreur arrivée en retard")
    assert not controller.retry_timer.isActive()
    assert not controller.tracker.timer.isActive()
    assert not controller.prefs.enabled and not controller.orb.enabled
    assert not controller.config.load().enabled


def test_lock_pauses_retries_and_resume_recovers_without_changing_preference(controller):
    controller.fail("Session momentanément inaccessible")
    controller.suspend()
    assert not controller.retry_timer.isActive()
    controller.retry_capture()
    assert not controller.tracker.timer.isActive()
    controller.resume()
    assert controller.prefs.enabled and not controller.fault
    assert controller.tracker.timer.isActive()


def test_first_good_frame_resets_backoff(controller):
    controller.retry_attempts = 5
    controller.overlay = SimpleNamespace(render=lambda *_: None, close=lambda: None, hide=lambda: None)
    image = QImage(304, 304, QImage.Format_ARGB32)
    image.fill(0xff112233)
    controller.present(Request(controller.epoch, 100, 100, 2.5, 1, diameter=300), image, .003)
    assert controller.frames_rendered == 1
    assert controller.retry_attempts == 0


def test_orb_click_toggles_loupe_and_saves_without_opening_settings_or_menu(controller):
    assert not controller.settings.isVisible()
    for enabled in (False, True, False, True):
        QTest.mouseClick(controller.orb, Qt.LeftButton)
        assert controller.prefs.enabled == enabled
        assert controller.orb.enabled == enabled
        assert controller.config.load().enabled == enabled
        assert controller.settings.activation.isChecked() == enabled
        assert controller.tracker.timer.isActive() == enabled
        assert controller.tray.activation.text() == ("Désactiver" if enabled else "Activer")
        assert not controller.stopped
        assert controller.orb.isVisible()
        assert controller.follow_timer.isActive()
        assert not controller.settings.isVisible()
        assert not controller.tray.menu.isVisible()


def test_orb_drag_and_release_outside_do_not_toggle_loupe(controller):
    orb = controller.orb
    origin = QPointF(orb.mapToGlobal(orb.rect().center()))
    for event_type, position, buttons in (
        (QEvent.MouseButtonPress, QPointF(18, 18), Qt.LeftButton),
        (QEvent.MouseMove, QPointF(78, 18), Qt.LeftButton),
        (QEvent.MouseButtonRelease, QPointF(18, 18), Qt.NoButton),
    ):
        button = Qt.NoButton if event_type == QEvent.MouseMove else Qt.LeftButton
        controller.app.sendEvent(orb, QMouseEvent(event_type, position, origin + position,
                                                button, buttons, Qt.NoModifier))
    assert orb.dragged
    assert controller.prefs.enabled and controller.config.load().enabled
    QTest.mousePress(orb, Qt.LeftButton)
    QTest.mouseRelease(orb, Qt.LeftButton, pos=orb.rect().bottomRight() * 2)
    assert controller.prefs.enabled
    assert not controller.settings.isVisible()


def test_settings_stay_open_if_already_visible_and_tray_still_opens_them(controller):
    # Invoke the actual menu command, without emitting any Windows input.
    controller.tray.menu.actions()[0].trigger()
    assert controller.settings.isVisible()
    QTest.mouseClick(controller.orb, Qt.LeftButton)
    assert not controller.prefs.enabled
    assert controller.settings.isVisible()
    assert not controller.settings.activation.isChecked()


def test_orb_click_can_cancel_recovery_and_reenable_later(controller):
    controller.fail("Erreur temporaire")
    QTest.mouseClick(controller.orb, Qt.LeftButton)
    assert not controller.prefs.enabled
    assert not controller.retry_timer.isActive()
    controller.retry_capture()
    assert not controller.tracker.timer.isActive()
    QTest.mouseClick(controller.orb, Qt.LeftButton)
    assert controller.prefs.enabled and controller.tracker.timer.isActive()
    assert "Désactiver" in controller.orb.accessibleName()
    assert "Clic droit" in controller.orb.toolTip()


def test_only_explicit_speed_slider_changes_windows_preference(controller):
    mouse = controller.test_mouse_speed
    assert mouse.writes == []
    controller.open_settings()
    controller.set_enabled(False)
    assert controller.orb.isVisible() and not controller.stopped
    assert controller.settings.sliders["mouse_speed"].isEnabled()
    controller.settings.sliders["mouse_speed"].setValue(5)
    assert mouse.speed == 6 and mouse.writes == [6]
    assert not controller.prefs.enabled
    controller.set_enabled(True)
    controller.open_settings()
    controller.close()
    assert mouse.writes == [6]
    assert not hasattr(controller.config.load(), "mouse_speed")


def test_settings_reread_external_windows_speed_without_overwriting_it(controller):
    mouse = controller.test_mouse_speed
    mouse.speed = 17
    controller.open_settings()
    assert controller.settings.sliders["mouse_speed"].value() == 16
    assert controller.settings.value_labels["mouse_speed"].text() == "Très rapide"
    assert mouse.writes == []


def test_mouse_speed_failure_does_not_disable_or_close_loupe(controller, monkeypatch):
    def unavailable(_):
        raise OSError("Réglage momentanément indisponible")
    monkeypatch.setattr(application.mouse_speed, "set_speed", unavailable)
    controller.settings.sliders["mouse_speed"].setValue(0)
    assert controller.settings.sliders["mouse_speed"].value() == 9
    assert "Vitesse de la souris" in controller.settings.notice.text()
    assert controller.prefs.enabled and controller.orb.enabled
    assert not controller.fault and not controller.retry_timer.isActive()
    assert not controller.stopped and controller.orb.isVisible()
