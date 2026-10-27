"""Coordinates motion, bounded capture, UI and local Windows services."""
import logging
import time

import numpy as np
from PySide6.QtCore import QObject, QPoint, QTimer, Qt
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtWidgets import QSystemTrayIcon

from core.motion_analyzer import MotionAnalyzer
from core.mouse_tracker import MouseTracker
from core.screen_capture import CaptureWorker, ExclusionProbe, Request
from core.zoom_controller import ZoomController
from services.configuration import Configuration, TUNING_LIMITS
from services.lifecycle import InstanceServer, Lifecycle
from services.orb_positioning import Rect, choose_position, companions_on_screen, obstacles_on_screen
from services.work_area import available_area
from services.win32 import Desktop, physical_to_logical
from services import mouse_speed, windows_startup
from services.screen_following import FOLLOW_INTERVAL_MS, ScreenFollower
from ui.magnifier_overlay import MagnifierOverlay
from ui.orb import Orb
from ui.settings_window import SettingsWindow
from ui.tray_icon import TrayIcon


class Application(QObject):
    def __init__(self, app, config=None):
        super().__init__()
        # Load COM/DXGI while starting, before showing our UI. No duplication
        # or screen capture is created here; the first approach stays responsive.
        try:
            import dxcam
        except Exception:
            logging.exception("Initialisation DXGI différée")
        self.app = app
        self.config = config or Configuration()
        self.prefs = self.config.load()
        self.desktop = Desktop()
        self.monitors = self.desktop.monitors()
        self.prefs.startup = windows_startup.enabled()
        self.settings = SettingsWindow(self.prefs)
        self.sync_mouse_speed()
        self.orb = Orb()
        self.orb.enabled = self.prefs.enabled
        self.overlay = None
        self.analyzer = MotionAnalyzer(self.prefs.thresholds())
        self.zoom = ZoomController(self.prefs.magnification)
        self.tracker = MouseTracker(self.desktop)
        self.worker = CaptureWorker()
        self.suspended = False
        self.fault = ""
        self.retry_attempts = 0
        self.retry_timer = QTimer(self)
        self.retry_timer.setSingleShot(True)
        self.retry_timer.timeout.connect(self.retry_capture)
        self.serial = 0
        self.last_submitted = 0.
        self.frame_interval = 1 / 60
        self.capture_average = .005
        self.epoch = 0
        self.last_pointer = None
        self.last_probe_at = 0
        self.last_frame_at = 0
        self.stopped = False
        self.frames_rendered = 0
        self.capture_costs = []
        self.started_at = time.monotonic()
        self.orb_screen_name = ""
        self.next_stack_check = 0.
        self.screen_follower = ScreenFollower()
        self.tracker.sampled.connect(self.sample)
        self.tracker.failed.connect(self.fail)
        self.worker.frame_ready.connect(self.present)
        self.worker.failed.connect(self.fail)
        self.settings.enabled_changed.connect(self.set_enabled)
        self.settings.zoom_changed.connect(self.set_zoom)
        self.settings.startup_changed.connect(self.set_startup)
        self.settings.tuning_changed.connect(self.set_tuning)
        self.settings.mouse_speed_changed.connect(self.set_mouse_speed)
        self.orb.activated.connect(self.toggle_enabled)
        self.orb.moved.connect(self.remember_orb)
        self.tray = TrayIcon(self.open_settings, self.toggle_enabled, self.quit)
        self.tray.setToolTip(self.orb.toolTip())
        self.orb.setContextMenuPolicy(Qt.CustomContextMenu)
        self.orb.customContextMenuRequested.connect(lambda p: self.tray.menu.exec(self.orb.mapToGlobal(p)))
        self.tray.refresh(self.prefs.enabled)
        self.server = InstanceServer(self.open_settings)
        self.lifecycle = Lifecycle(int(self.orb.winId()), self.suspend, self.resume, self.schedule_screens)
        app.installNativeEventFilter(self.lifecycle)
        self.screen_timer = QTimer(self)
        self.screen_timer.setSingleShot(True)
        self.screen_timer.setInterval(350)
        self.screen_timer.timeout.connect(self.screens_changed)
        app.screenAdded.connect(self.attach_screen)
        app.screenRemoved.connect(self.schedule_screens)
        for screen in app.screens():
            self.attach_screen(screen)
        self.position_orb()
        self.screen_timer.stop()
        self.orb.show()
        self.follow_timer = QTimer(self)
        self.follow_timer.setTimerType(Qt.PreciseTimer)
        self.follow_timer.setInterval(FOLLOW_INTERVAL_MS)
        self.follow_timer.timeout.connect(self.follow_pointer_screen)
        self.follow_timer.start()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.hide()
        self.watchdog = QTimer(self)
        self.watchdog.setInterval(250)
        self.watchdog.timeout.connect(self.check_stale)
        self.watchdog.start()
        if self.prefs.enabled:
            self.tracker.start()
        app.aboutToQuit.connect(self.close)

    def attach_screen(self, screen):
        screen.availableGeometryChanged.connect(self.schedule_screens)
        screen.geometryChanged.connect(self.schedule_screens)
        screen.logicalDotsPerInchChanged.connect(self.schedule_screens)
        self.schedule_screens()

    def schedule_screens(self, *_):
        if not self.stopped:
            self.screen_timer.start()

    def screens_changed(self):
        try:
            self.stop_effect()
            self.monitors = self.desktop.monitors()
            self.position_orb()
            if self.fault and self.prefs.enabled and not self.suspended:
                self.retry_capture()
        except Exception as error:
            self.fail(str(error))

    def screen_pairs(self):
        result = []
        for screen in self.app.screens():
            origin = screen.geometry().topLeft()
            monitor = next((m for m in self.monitors if m.device.casefold() == screen.name().casefold()), None)
            monitor = monitor or next((m for m in self.monitors if (m.bounds.x, m.bounds.y) == (origin.x(), origin.y())), None)
            if monitor:
                result.append((screen, monitor))
        return result

    def position_orb(self, manual=None, screen_name=None):
        from services.ergonatus_layout import managed_position
        managed = managed_position(self.orb, "precisionator")
        if managed is not None and manual is None:
            managed_screen=self.app.screenAt(managed) or self.app.primaryScreen()
            screen_name=managed_screen.name()
        pairs = self.screen_pairs()
        if not pairs:
            return
        selected = next((pair for pair in pairs if pair[0].name() == screen_name), None)
        if selected is None and manual is not None:
            selected = next((pair for pair in pairs if pair[0].geometry().contains(QPoint(*manual))), None)
        if selected is None:
            pointer = self.desktop.pointer()
            selected = next((pair for pair in pairs if pair[1].bounds.contains(Rect(*pointer, 1, 1))), None)
        screen, monitor = selected or next((pair for pair in pairs if pair[0] == self.app.primaryScreen()), pairs[0])
        geometry = available_area(screen)
        area = Rect(geometry.x(), geometry.y(), geometry.width(), geometry.height())
        companions = []
        native_companions, native_obstacles = self.desktop.family_layout()
        for family, bounds in native_companions:
            origin = next((pair for pair in pairs if pair[1].bounds.contains(Rect(bounds.x, bounds.y, 1, 1))), None)
            if origin:
                source_screen, source_monitor = origin
                x, y = physical_to_logical((bounds.x, bounds.y), source_monitor, source_screen)
                ratio = source_screen.devicePixelRatio()
                companions.append((family, Rect(x, y, round(bounds.w / ratio), round(bounds.h / ratio)), source_screen.name()))
        obstacles = []
        for bounds in native_obstacles:
            origin = next((pair for pair in pairs if pair[1].bounds.contains(Rect(bounds.x, bounds.y, 1, 1))), None)
            if origin:
                source_screen, source_monitor = origin
                x, y = physical_to_logical((bounds.x, bounds.y), source_monitor, source_screen)
                ratio = source_screen.devicePixelRatio()
                obstacles.append((Rect(x, y, round(bounds.w / ratio), round(bounds.h / ratio)), source_screen.name()))
        projected = companions_on_screen(area, companions, screen.name())
        obstacles = obstacles_on_screen(companions, obstacles, screen.name(), projected)
        companions = projected
        saved = manual if manual is not None else self.prefs.orb_positions.get(screen.name())
        if saved is None and self.prefs.orb_position is not None:
            if self.prefs.orb_screen == screen.name() or (not self.prefs.orb_screen and area.contains(Rect(*self.prefs.orb_position, 36, 36))):
                saved = self.prefs.orb_position
        position = (managed.x(),managed.y()) if managed is not None and manual is None else choose_position([area], companions, saved, obstacles=obstacles)
        if self.orb.pos() != QPoint(*position):
            if self.orb_screen_name != screen.name() or (self.orb.isVisible() and not self.orb.timer.isActive()):
                self.stop_effect()
            self.orb.move(QPoint(*position))
        self.orb_screen_name = screen.name()
        if saved is not None and not companions:
            self.prefs.orb_positions[screen.name()] = position

    def follow_pointer_screen(self):
        if self.stopped:
            return
        try:
            pointer = self.desktop.pointer()
            pair = next((pair for pair in self.screen_pairs() if pair[1].bounds.contains(Rect(*pointer, 1, 1))), None)
            target = pair[0].name() if pair else None
            now = time.monotonic()
            blocked = self.suspended or self.orb.drag_start is not None or self.tray.menu.isVisible()
            requested = self.screen_follower.update(now, target, self.orb_screen_name, blocked=blocked)
            if requested or (target and not blocked and now >= self.next_stack_check):
                self.position_orb(screen_name=requested or target)
                self.next_stack_check = now + .12
        except OSError:
            # Locked/secure desktops can temporarily refuse pointer queries.
            pass

    def remember_orb(self):
        self.position_orb((self.orb.x(), self.orb.y()))
        self.prefs.orb_position = (self.orb.x(), self.orb.y())
        self.prefs.orb_screen = self.orb_screen_name
        self.prefs.orb_positions[self.orb_screen_name] = self.prefs.orb_position
        self.save()

    def make_probe(self):
        # Keep the displayed orb frame steady while DXGI verifies its exclusion.
        # The orb remains visible and interactive; only decorative motion pauses.
        self.orb.timer.stop()
        image = self.orb.grab().toImage().convertToFormat(QImage.Format_ARGB32)
        bounds = self.desktop.window_rect(int(self.orb.winId()))
        if image.width() != bounds.w or image.height() != bounds.h:
            image = image.scaled(bounds.w, bounds.h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        reference = np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine())[:, :image.width() * 4].reshape(image.height(), image.width(), 4).copy()
        return ExclusionProbe(int(self.orb.winId()), bounds.x + bounds.w // 2, bounds.y + bounds.h // 2, reference)

    def sample(self, now, x, y):
        if self.stopped or self.suspended or self.fault or not self.prefs.enabled:
            return
        try:
            monitor = next((m for m in self.monitors if m.bounds.contains(Rect(x, y, 1, 1))), None)
            if not monitor:
                self.stop_effect()
                return
            # Avoid magnifying our own controls (and use the real cursor only).
            for widget in (self.orb, self.settings, self.tray.menu):
                if widget.isVisible() and self.desktop.window_rect(int(widget.winId())).contains(Rect(x, y, 1, 1)):
                    self.stop_effect()
                    return
            motion = self.analyzer.update(now, x, y, monitor.scale)
            state = self.zoom.update(now, motion.active, motion.reason)
            self.last_pointer = (x, y)
            if state.opacity <= .002:
                if self.overlay:
                    self.overlay.hide()
                self.epoch += 1
                return
            if now - self.last_submitted < self.frame_interval - .002:
                return
            if self.overlay is None:
                self.overlay = MagnifierOverlay(self.desktop, self.prefs.lens_diameter)
            probe = self.make_probe() if self.worker.needs_probe.is_set() else None
            self.last_submitted = now
            self.serial += 1
            self.worker.submit(Request(self.epoch, x, y, state.factor, state.opacity, probe, self.prefs.lens_diameter))
        except Exception as error:
            self.fail(str(error))

    def present(self, request, image, elapsed):
        self.worker.acknowledge()
        if not self.stopped and not self.worker.needs_probe.is_set() and self.orb.isVisible() and not self.orb.timer.isActive():
            self.orb.timer.start()
        if self.stopped or self.suspended or self.fault or not self.prefs.enabled or request.serial != self.epoch:
            return
        try:
            # Stale capture must never float over a new real pointer position.
            current = self.desktop.pointer()
            offset = (current[0] - request.x, current[1] - request.y)
            margin = (image.width() - request.diameter / request.zoom) / 2 - 1
            if max(abs(offset[0]), abs(offset[1])) > margin:
                if self.overlay:
                    self.overlay.hide()
                return
            aligned = Request(request.serial, *current, request.zoom, request.opacity, diameter=request.diameter)
            self.overlay.render(aligned, image, offset)
            self.frames_rendered += 1
            self.retry_attempts = 0
            self.last_frame_at = time.monotonic()
            self.capture_average += .08 * (min(elapsed, .2) - self.capture_average)
            self.frame_interval = 1 / (60 if self.capture_average < .012 else 40 if self.capture_average < .022 else 30)
        except Exception as error:
            self.fail(str(error))

    def check_stale(self):
        if self.overlay and self.overlay.visible and time.monotonic() - self.last_frame_at > .20:
            self.overlay.hide()

    def stop_effect(self):
        self.epoch += 1
        self.analyzer.reset()
        self.zoom.reset()
        if self.overlay:
            self.overlay.hide()
        self.worker.release()
        if not self.stopped and self.orb.isVisible() and not self.orb.timer.isActive():
            self.orb.timer.start()

    def fail(self, message):
        if self.stopped or not self.prefs.enabled:
            return
        logging.warning("Reprise automatique : %s", message)
        self.fault = message
        self.stop_effect()
        self.tracker.stop()
        self.settings.error("Reprise automatique de la loupe…")
        self.orb.setToolTip("Précisionator · Activé · Reprise automatique")
        self.tray.setToolTip(self.orb.toolTip())
        if not self.suspended and not self.retry_timer.isActive():
            self.retry_attempts += 1
            self.retry_timer.start(min(4000, 250 * 2 ** min(self.retry_attempts - 1, 4)))

    def retry_capture(self):
        if self.stopped or self.suspended or not self.prefs.enabled:
            return
        self.retry_timer.stop()
        try:
            self.stop_effect()
            if self.overlay:
                self.overlay.close()
                self.overlay = None
            self.monitors = self.desktop.monitors()
            if not self.monitors:
                raise OSError("Écrans momentanément indisponibles.")
            self.position_orb()
            self.fault = ""
            self.last_submitted = 0.
            self.settings.error("")
            self.orb.describe_action()
            self.tray.setToolTip(self.orb.toolTip())
            self.tracker.start()
        except Exception as error:
            self.fail(str(error))

    def save(self):
        try:
            self.config.save(self.prefs)
        except OSError as error:
            logging.error("Préférences : %s", error)
            self.settings.error("Enregistrement impossible : " + str(error))

    def set_enabled(self, enabled):
        self.retry_timer.stop()
        self.retry_attempts = 0
        self.prefs.enabled = enabled
        self.fault = ""
        self.settings.error("")
        self.stop_effect()
        self.orb.enabled = enabled
        self.tray.setToolTip(self.orb.toolTip())
        self.settings.refresh(self.prefs)
        self.tray.refresh(enabled)
        self.orb.update()
        if enabled and not self.suspended:
            self.tracker.start()
        else:
            self.tracker.stop()
        self.save()

    def set_zoom(self, factor):
        self.prefs.magnification = factor
        self.zoom.factor = factor
        self.stop_effect()
        self.save()

    def set_tuning(self, values):
        old_diameter = self.prefs.lens_diameter
        for key in TUNING_LIMITS:
            if key in values:
                setattr(self.prefs, key, values[key])
        self.prefs.normalize_tuning()
        self.stop_effect()
        self.analyzer.configure(self.prefs.thresholds())
        if old_diameter != self.prefs.lens_diameter and self.overlay:
            self.overlay.close()
            self.overlay = None
        self.settings.refresh(self.prefs)
        self.save()

    def set_startup(self, enabled):
        try:
            windows_startup.set_enabled(enabled)
            self.prefs.startup = windows_startup.enabled()
            self.save()
        except OSError as error:
            self.settings.error("Démarrage Windows : " + str(error))
        self.settings.refresh(self.prefs)

    def sync_mouse_speed(self):
        try:
            self.settings.refresh_mouse_speed(mouse_speed.get_speed())
        except OSError as error:
            logging.warning("Lecture vitesse souris : %s", error)
            self.settings.refresh_mouse_speed(None)

    def set_mouse_speed(self, speed):
        try:
            mouse_speed.set_speed(speed)
            self.sync_mouse_speed()
            if self.settings.notice.text().startswith("Vitesse de la souris :"):
                self.settings.error("")
        except (OSError, ValueError) as error:
            self.sync_mouse_speed()
            self.settings.error("Vitesse de la souris : " + str(error))

    def open_settings(self):
        self.sync_mouse_speed()
        screen = self.orb.screen() or self.app.primaryScreen()
        area = screen.availableGeometry()
        self.settings.resize(self.settings.DEFAULT_WIDTH,
            max(self.settings.MIN_HEIGHT, min(self.settings.DEFAULT_HEIGHT, area.height() - 24)))
        x = max(area.left(), min(self.orb.x() + 36 - self.settings.width(), area.right() + 1 - self.settings.width()))
        y = max(area.top(), min(self.orb.y() - self.settings.height() - 10, area.bottom() + 1 - self.settings.height()))
        self.settings.move(x, y)
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def toggle_enabled(self):
        self.set_enabled(not self.prefs.enabled)

    def suspend(self):
        self.suspended = True
        self.retry_timer.stop()
        self.tracker.stop()
        self.stop_effect()

    def resume(self):
        if self.stopped:
            return
        self.suspended = False
        self.screens_changed()
        if self.prefs.enabled:
            self.retry_capture()

    def close(self):
        if self.stopped:
            return
        self.stopped = True
        self.tracker.stop()
        self.watchdog.stop()
        self.screen_timer.stop()
        self.follow_timer.stop()
        self.retry_timer.stop()
        self.stop_effect()
        self.worker.close()
        if self.overlay:
            self.overlay.close()
        self.app.removeNativeEventFilter(self.lifecycle)
        self.lifecycle.close()
        self.server.server.close()
        self.tray.hide()
        self.orb.hide()
        self.settings.hide()
        logging.info("Fermeture après %.1f s : %d images affichées, coût capture lissé %.2f ms.",
                     time.monotonic() - self.started_at, self.frames_rendered, self.capture_average * 1000)

    def quit(self):
        # Settings' titlebar close intentionally hides to the orb. Clean up and
        # exit the event loop explicitly so that convention cannot veto Quit.
        self.close()
        self.app.exit(0)
