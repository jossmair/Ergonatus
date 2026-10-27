"""Companion orb placement and lifetime for the non-activating keyboard."""
import ctypes
from ctypes import wintypes
import math
from functools import lru_cache

from PySide6.QtCore import QElapsedTimer, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QGraphicsColorizeEffect, QGraphicsPixmapItem, QGraphicsScene, QWidget

from .desktop_target import DesktopTarget, PasteDelivery, protect_tool_window, reject_mouse_activation
from .click_tracker import ClickTracker
from .hover_scroll import HoverScrollArrow
from .theme import asset_path
from .virtual_keyboard import VirtualKeyboard
from .work_area import available_area


def orb_position(area, size=QSize(36, 36), companion=None, scroll_arrows=False):
    # The yellow Transcrinator orb is 36 px, 16 px above the taskbar.
    anchor = companion or QRect(area.right() + 1 - 16 - 36, area.bottom() + 1 - 16 - 36, 36, 36)
    x = anchor.left() + (anchor.width() - size.width()) // 2
    reserve = HoverScrollArrow.EXTENT if scroll_arrows else 0
    horizontal = (HoverScrollArrow.WIDTH - size.width()) // 2 if scroll_arrows else 0
    y = anchor.top() - size.height() - 10 - reserve
    return QPoint(min(max(x, area.left() + horizontal), area.right() + 1 - size.width() - horizontal),
                  min(max(y, area.top() + reserve), area.bottom() + 1 - size.height() - reserve))


def scroll_arrow_positions(orb):
    x = orb.center().x() + 1 - HoverScrollArrow.WIDTH // 2
    return (QPoint(x, orb.top() - HoverScrollArrow.EXTENT),
            QPoint(x, orb.bottom() + 1 + HoverScrollArrow.EXTENT - HoverScrollArrow.HEIGHT))


def panel_position(area, size, orb):
    return QPoint(max(area.left() + 8, min(orb.right() + 1 - size.width(), area.right() - size.width() - 12)),
                  max(area.top() + 8, orb.top() - size.height() - 10))


def bounded_panel_position(area, size, position):
    return QPoint(max(area.left() + 8, min(position.x(), area.right() + 1 - size.width() - 8)),
                  max(area.top() + 8, min(position.y(), area.bottom() + 1 - size.height() - 8)))


def keyboard_size(area):
    """Use logical pixels and cap the panel instead of filling a large monitor."""
    return QSize(min(900, max(820, area.width() - 24)), 320)


def monitor_screen(screens, device, native_origin):
    # Qt may expose a monitor's friendly name ("VC279") instead of DISPLAY2.
    # On Windows, Qt retains native monitor origins even with mixed DPI.
    return (next((screen for screen in screens if screen.name().casefold() == device.casefold()), None)
            or next((screen for screen in screens if screen.geometry().topLeft() == native_origin), None))


@lru_cache(maxsize=24)
def turquoise_frame(family, frame, pixels):
    """Style Transcrinator's existing animation frames with a native Qt effect."""
    source = QPixmap(str(asset_path(f"keyboard/frames/{family}-{frame:02}.png")))
    if source.isNull():
        return source
    source = source.scaled(pixels, pixels, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(source)
    effect = QGraphicsColorizeEffect()
    effect.setColor(QColor("#42dbca"))
    effect.setStrength(1.)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    scene.setSceneRect(QRectF(source.rect()))
    result = QPixmap(source.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    scene.render(painter, QRectF(result.rect()), scene.sceneRect())
    painter.end()
    return result


def draw_orb_sprite(painter, family, rect, phase, opacity=1.):
    from .suite_orb import draw as _suite_draw
    if _suite_draw(painter,rect,'claviernator'):return
    current = math.floor(phase)
    fraction = phase - current
    pixels = min(144, max(64, math.ceil(rect.width() * painter.device().devicePixelRatioF())))
    for frame, alpha in ((current % 4, 1 - fraction), ((current + 1) % 4, fraction)):
        pixmap = turquoise_frame(family, frame, pixels)
        painter.setOpacity(opacity * alpha)
        painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))
    painter.setOpacity(1.)


def transcrinator_anchor(preferred_screen=None):
    """Find the small visible orb owned by Transcrinator's (possibly hidden) main window."""
    if QApplication.platformName() == "offscreen":
        return None
    user = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    windows = []

    def collect(hwnd, unused):
        title = ctypes.create_unicode_buffer(256)
        user.GetWindowTextW(hwnd, title, 256)
        pid, rect = wintypes.DWORD(), wintypes.RECT()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if user.GetWindowRect(hwnd, ctypes.byref(rect)):
            windows.append((int(hwnd), pid.value, title.value.casefold(), rect, bool(user.IsWindowVisible(hwnd))))
        return True

    user.EnumWindows(callback_type(collect), 0)
    processes = {pid for _, pid, title, _, _ in windows
                 if title.startswith(("transcrinator", "transcri ·", "transcrihub")) or title == "transcri"}
    candidates = [(hwnd, rect) for hwnd, pid, _, rect, visible in windows
                  if visible and pid in processes and 24 <= rect.right - rect.left <= 100
                  and 24 <= rect.bottom - rect.top <= 100
                  and .7 <= (rect.right - rect.left) / (rect.bottom - rect.top) <= 1.4]
    if not candidates:
        return None
    class MonitorInfo(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT), ("work", wintypes.RECT),
                    ("flags", wintypes.DWORD), ("device", wintypes.WCHAR * 32)]

    user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user.MonitorFromWindow.restype = wintypes.HANDLE
    user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    screens = QGuiApplication.screens()
    anchors = []
    for hwnd, rect in candidates:
        info = MonitorInfo()
        info.size = ctypes.sizeof(info)
        if not user.GetMonitorInfoW(user.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
            continue
        screen = monitor_screen(screens, info.device, QPoint(info.monitor.left, info.monitor.top))
        if screen is None or (preferred_screen is not None and screen != preferred_screen):
            continue
        ratio = screen.devicePixelRatio()
        origin = screen.geometry().topLeft()
        logical = QRect(origin.x() + round((rect.left - info.monitor.left) / ratio),
                        origin.y() + round((rect.top - info.monitor.top) / ratio),
                        round((rect.right - rect.left) / ratio), round((rect.bottom - rect.top) / ratio))
        anchors.append((screen, logical))
    return max(anchors, key=lambda item: item[1].bottom()) if anchors else None


class KeyboardOrb(QWidget):
    pressed = Signal()
    activated = Signal()

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setWindowTitle("Claviernator · Orbe du clavier")
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAccessibleName("Ouvrir le clavier virtuel Claviernator")
        self.setToolTip("Clavier virtuel · Clic droit : menu")
        self.phase = 0.
        self.opened = False
        self.down = False
        self.animation = QTimer(self)
        self.animation.setInterval(40)
        self.animation.timeout.connect(self.animate)

    def nativeEvent(self, event_type, message):
        handled, result = reject_mouse_activation(message)
        return (handled, result) if handled else super().nativeEvent(event_type, message)

    def showEvent(self, event):
        protect_tool_window(self)
        self.animation.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.animation.stop()
        super().hideEvent(event)

    def animate(self):
        self.phase += .045
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pressed.emit()
            self.down = True
            self.update()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            clicked = self.down and self.rect().contains(event.position().toPoint())
            self.down = False
            self.update()
            if clicked:
                self.activated.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        center = QPointF(18, 18)
        glow = QRadialGradient(center, 18)
        glow.setColorAt(0, QColor(66, 238, 210, 42 if self.opened or self.underMouse() else 16))
        glow.setColorAt(1, QColor(5, 55, 62, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(0, 0, 36, 36))
        if self.down:
            painter.translate(center)
            painter.scale(.94, .94)
            painter.translate(-center)
        draw_orb_sprite(painter, "core", QRectF(0, 0, 36, 36), self.phase * 1.4)


class VirtualKeyboardManager:
    def __init__(self, controller, enabled=True, desktop=None):
        self.controller = controller
        self.desktop = desktop if desktop is not None else (None if QApplication.platformName() == "offscreen" else DesktopTarget())
        self.delivery = PasteDelivery(self.desktop) if self.desktop else None
        self.target = self.last_target = None
        self.scroll_target = None
        self.click_tracker = None
        self.tracking_error = ""
        self.choosing_target = False
        self.pick_candidate = None
        self.pick_elapsed = QElapsedTimer()
        self.orb = KeyboardOrb()
        self.pick_timer = QTimer(self.orb)
        self.pick_timer.setSingleShot(True)
        self.pick_timer.setInterval(120)
        self.pick_timer.timeout.connect(self.finish_target_pick)
        self.arrows = (HoverScrollArrow(1), HoverScrollArrow(-1))
        for arrow in self.arrows:
            arrow.scroll_requested.connect(self.scroll)
        self.panel = VirtualKeyboard()
        self.allowed = enabled
        self.stopped = False
        if enabled and isinstance(self.desktop, DesktopTarget) and QApplication.platformName() != "offscreen":
            self.click_tracker = ClickTracker(self.desktop, self.orb)
            self.click_tracker.clicked.connect(self.remember_scroll_target, Qt.QueuedConnection)
            try:
                self.click_tracker.start()
            except Exception as exc:
                self.tracking_error = str(exc)
                controller.notice.emit(self.tracking_error)
        self.panel_positions = {}
        self.orb.pressed.connect(self.capture_target)
        self.orb.activated.connect(self.toggle)
        self.panel.hidden.connect(self.panel_hidden)
        self.panel.insert_requested.connect(self.insert)
        self.panel.target_pick_requested.connect(self.begin_target_pick)
        self.panel.key_requested.connect(self.send_keys)
        self.panel.emergency_requested.connect(controller.pause_runtime)
        self.panel.moved.connect(self.remember_panel_position)
        self.fit_timer = QTimer(self.panel)
        self.fit_timer.setSingleShot(True)
        self.fit_timer.setInterval(20)
        self.fit_timer.timeout.connect(self.fit_panel)
        self.panel.winId()
        self.panel.windowHandle().screenChanged.connect(lambda screen: self.fit_timer.start())
        self.panel.fit_requested.connect(self.fit_timer.start)
        self.poll = QTimer(self.orb)
        self.poll.setInterval(180)
        self.poll.timeout.connect(self.track_target)
        self.placement = QTimer(self.orb)
        self.placement.setInterval(120)
        self.placement.timeout.connect(self.place)
        controller.changed.connect(self.refresh)
        controller.state.connect(self.scroll_state)
        QGuiApplication.instance().screenAdded.connect(self.screens_changed)
        QGuiApplication.instance().screenRemoved.connect(self.screens_changed)
        for screen in QGuiApplication.screens():
            screen.availableGeometryChanged.connect(self.place)
        self.refresh()

    def refresh(self):
        if self.stopped:
            return
        visible = self.allowed and self.controller.settings.virtual_keyboard
        arrows_visible = visible and self.controller.settings.hover_scroll
        for arrow in self.arrows:
            arrow.setEnabled(self.controller.active and not self.tracking_error)
            if self.tracking_error:
                arrow.setToolTip(self.tracking_error)
            if not arrows_visible:
                arrow.hide()
        if visible:
            self.place()
            protect_tool_window(self.orb)
            self.orb.show()
            if arrows_visible:
                for arrow in self.arrows:
                    arrow.show()
            self.poll.start()
            self.placement.start()
        else:
            self.cancel_target_pick()
            self.panel.hide_keyboard()
            self.orb.hide()
            self.poll.stop()
            self.placement.stop()

    def scroll_state(self, active):
        for arrow in self.arrows:
            arrow.setEnabled(active and not self.tracking_error)

    def remember_scroll_target(self, target):
        if not self.stopped:
            self.scroll_target = target
            if self.choosing_target:
                self.pick_candidate = target
                self.pick_elapsed.start()
                self.pick_timer.start()

    def begin_target_pick(self):
        if self.stopped or not self.allowed or not self.controller.settings.virtual_keyboard:
            return
        if not self.desktop or self.tracking_error:
            self.panel.show_error(self.tracking_error or "Le choix du champ est désactivé dans cet aperçu.")
            return
        self.cancel_target_pick()
        self.panel.hide_keyboard()
        self.choosing_target = True
        self.orb.setToolTip("Cliquez dans le champ où écrire · Orbe : retour au clavier")
        self.orb.setAccessibleName("Retour au clavier sans perdre le texte")

    def cancel_target_pick(self):
        self.choosing_target = False
        self.pick_candidate = None
        self.pick_timer.stop()
        self.orb.setToolTip("Clavier virtuel · Clic droit : menu")
        self.orb.setAccessibleName("Ouvrir le clavier virtuel Claviernator")

    def finish_target_pick(self):
        if not self.choosing_target or self.stopped or not self.pick_candidate:
            return
        # Never interrupt a held click or a drag used to select text.
        if self.desktop.mouse_buttons_held():
            self.pick_timer.start()
            return
        target = self.desktop.capture()
        candidate = self.pick_candidate
        if (target and target.window == candidate.window and target.process == candidate.process
                and self.desktop.target_exists(target)):
            self.cancel_target_pick()
            self.target = self.last_target = target
            self.reveal_panel()
        elif self.pick_elapsed.elapsed() < 2000:
            # Let the clicked app finish activating and assigning focus.
            self.pick_timer.start()
        else:
            self.pick_candidate = None  # Wait for another explicit click.

    def scroll(self, amount):
        if (not self.stopped and self.desktop and self.controller.active
                and self.controller.settings.hover_scroll and self.controller.settings.virtual_keyboard
                and not self.controller.suspended):
            if self.scroll_target and self.desktop.scroll(self.scroll_target, amount):
                return
        for arrow in self.arrows:
            arrow.stop_scroll()

    def track_target(self):
        if self.desktop:
            target = self.desktop.capture()
            if target:
                # Closing a document can expose an unrelated app underneath.
                # Keep the draft until the user actually chooses another field.
                if (self.panel.isVisible() and self.target is not None
                        and not self.desktop.target_exists(self.target)
                        and not self.desktop.pointer_over(target)):
                    return
                self.last_target = target
                if self.panel.isVisible() and target != self.target:
                    self.target = target
                    self.panel.set_target(target)

    def capture_target(self):
        if self.desktop:
            self.target = self.desktop.capture() or self.last_target
            if self.target:
                self.last_target = self.target

    def toggle(self):
        self.cancel_target_pick()
        if self.panel.isVisible():
            self.panel.hide_keyboard()
            return
        if self.target is None:
            self.capture_target()
        self.reveal_panel()

    def reveal_panel(self):
        self.panel.set_target(self.target)
        self.place_panel()
        self.panel.reveal()
        self.orb.opened = True
        self.orb.update()

    def panel_hidden(self):
        self.orb.opened = False
        self.orb.update()

    def insert(self, text):
        if not self.delivery:
            self.panel.show_error("L’insertion est désactivée dans cet aperçu.")
            return
        try:
            self.track_target()
            if self.delivery.paste(self.target, text):
                self.panel.clear_text()
                self.panel.clear_modifiers()
        except Exception as exc:
            self.panel.show_error(str(exc))

    def send_keys(self, keys):
        if not self.desktop:
            self.panel.show_error("Les raccourcis sont désactivés dans cet aperçu.")
            return
        try:
            self.track_target()
            self.desktop.send_keys(self.target, keys)
            self.panel.error.setText("")
        except Exception as exc:
            self.panel.show_error(str(exc))

    def place(self):
        # Follow the mouse's screen just like Transcrinator, even when it is
        # closed or is still catching up on the previous monitor.
        if self.stopped or self.orb.down:
            return
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if not screen:
            return
        area = available_area(screen)
        # Do not slide away from a pointer that is about to click the orb while
        # Transcrinator's own placement timer finishes catching up.
        arrows = getattr(self, "arrows", ())
        if ((self.orb.isVisible() and self.orb.underMouse() or any(arrow.hovered for arrow in arrows))
                and area.contains(self.orb.geometry().center())):
            return
        anchor = transcrinator_anchor(screen)
        companion = anchor[1] if anchor and anchor[0] == screen else None
        show_arrows = bool(arrows) and self.controller.settings.hover_scroll
        from .ergonatus_layout import managed_position
        managed = managed_position(self.orb, "claviernator")
        self.orb.move(managed if managed is not None else orb_position(area, self.orb.size(), companion, show_arrows))
        for arrow, point in zip(arrows, scroll_arrow_positions(self.orb.geometry())):
            arrow.move(point)

    def screens_changed(self, screen):
        if self.stopped:
            return
        if screen in QGuiApplication.screens():
            screen.availableGeometryChanged.connect(self.place)
        self.place()
        if self.panel.isVisible():
            self.place_panel()

    def remember_panel_position(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or self.panel.screen()
        if screen:
            self.panel.setFixedSize(keyboard_size(screen.availableGeometry()))
            position = bounded_panel_position(screen.availableGeometry(), self.panel.size(), self.panel.pos())
            self.panel.move(position)
            self.panel_positions[screen.name()] = position

    def fit_panel(self):
        if self.stopped:
            return
        screen = self.panel.screen()
        if screen:
            area = screen.availableGeometry()
            size = keyboard_size(area)
            # After WM_DPICHANGED, Windows can retain the old physical frame
            # even though Qt already reports the new logical size. An actual
            # resize makes Qt rebuild both the native frame and input region.
            self.panel.setFixedSize(size + QSize(1, 1))
            self.panel.setFixedSize(size)
            if self.panel.isVisible() and not self.panel.handle.dragged:
                self.panel.move(bounded_panel_position(area, self.panel.size(), self.panel.pos()))

    def place_panel(self):
        screen = QGuiApplication.screenAt(self.orb.geometry().center()) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.panel.setFixedSize(keyboard_size(area))
        saved = self.panel_positions.get(screen.name())
        anchor = self.arrows[0].geometry() if self.controller.settings.hover_scroll else self.orb.geometry()
        self.panel.move(bounded_panel_position(area, self.panel.size(), saved) if saved is not None
                        else panel_position(area, self.panel.size(), anchor))

    def stop(self):
        if self.stopped:
            return
        self.stopped = True
        self.cancel_target_pick()
        if self.click_tracker:
            self.click_tracker.stop()
        self.controller.changed.disconnect(self.refresh)
        self.controller.state.disconnect(self.scroll_state)
        self.poll.stop()
        self.fit_timer.stop()
        self.placement.stop()
        self.panel.hide_keyboard()
        self.orb.hide()
        for arrow in self.arrows:
            arrow.hide()
        if self.delivery:
            self.delivery.restore()
        application = QGuiApplication.instance()
        application.screenAdded.disconnect(self.screens_changed)
        application.screenRemoved.disconnect(self.screens_changed)
        for screen in QGuiApplication.screens():
            screen.availableGeometryChanged.disconnect(self.place)
