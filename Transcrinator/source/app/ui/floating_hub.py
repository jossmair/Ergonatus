import math
import time

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QCursor, QGuiApplication, QImage, QPainter, QPen,
                          QLinearGradient, QPainterPath, QRadialGradient)
from PySide6.QtWidgets import QApplication, QWidget
from app.ui.premium import audio_activity, draw_artwork, draw_core, wave_heights
from app.ui.work_area import available_area


def bottom_center(size, screen, margin=16):
    """Fixed bottom center of the usable screen, above the taskbar."""
    return QPoint(
        max(screen.left(), screen.left() + (screen.width() - size.width()) // 2),
        max(screen.top(), screen.bottom() + 1 - size.height() - margin),
    )


class FloatingHub(QWidget):
    open_requested = Signal()

    def __init__(self, settings, clock=time.monotonic):
        super().__init__(
            None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        )
        self.settings = settings
        self.setWindowTitle("Transcrinator · Orbe")
        self.clock, self.last_active, self.compacted = clock, clock(), False
        self.drag_origin = None
        self.dragged = False
        self.manual_position = None
        self.manual_area = None
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.state, self.partial = "Préparation…", ""
        self.level = 0
        self.phase = 0
        self.display_level = 0
        self.activation_started = None
        self.unfold_started = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.setInterval(16)
        self.setFixedSize(172, 44)
        QGuiApplication.primaryScreen().availableGeometryChanged.connect(self.clamp_to_screen)
        QGuiApplication.instance().primaryScreenChanged.connect(self.clamp_to_screen)
        self.apply_settings()

    def target_size(self):
        return QSize(36, 36) if self.compacted else QSize(172, 44)

    def resize_for_state(self, animated=True):
        self.setFixedSize(self.target_size())
        self.clamp_to_screen()

    def finish_transition(self):
        self.setFixedSize(self.target_size())
        self.clamp_to_screen()

    def apply_settings(self):
        self.resize_for_state(animated=False)
        self.setVisible(self.settings.hub_visible or self.state == "Écoute…")
        self.clamp_to_screen()
        self.update()

    def clamp_to_screen(self, *_):
        from app.ui.ergonatus_layout import managed_position
        managed = managed_position(self, "transcrinator")
        if managed is not None and self.drag_origin is None:
            self.move(managed)
            return
        if self.drag_origin is not None:
            return
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen:
            area = available_area(screen)
            position = (QPoint(max(area.left(), area.right() + 1 - self.width() - 16),
                               max(area.top(), area.bottom() + 1 - self.height() - 16))
                        if self.compacted else bottom_center(self.size(), area))
            if self.manual_position is not None and self.manual_area == area:
                position = self.bounded(self.manual_position, area)
            elif self.manual_area != area:
                self.manual_position = None
            if self.pos() != position:
                self.move(position)

    def bounded(self, position, area):
        return QPoint(min(max(position.x(), area.left()), max(area.left(), area.right() + 1 - self.width())),
                      min(max(position.y(), area.top()), max(area.top(), area.bottom() + 1 - self.height() - 16)))

    def reveal(self):
        self.clamp_to_screen()
        self.show()
        self.raise_()

    def moveEvent(self, event):
        # Preserve explicit native moves made by another orb in the pile.
        if event.spontaneous() and self.compacted and self.drag_origin is None:
            screen = QGuiApplication.screenAt(event.pos() + self.rect().center())
            if screen:
                self.manual_area = available_area(screen)
                self.manual_position = self.bounded(event.pos(), self.manual_area)
        super().moveEvent(event)

    def set_state(self, state):
        active = state in ("Préparation…", "Écoute…", "Traitement…")
        compact = not active and state != "Fermé"
        if self.compacted and active:
            # Every wake starts at the bottom center, even after a manual move.
            self.manual_position = self.manual_area = None
            self.unfold_started = self.clock()
        if compact and not self.compacted:
            self.manual_position = self.manual_area = None
            self.unfold_started = None
        if active and state != self.state:
            self.activation_started = self.clock()
        if state == "Écoute…" and self.state != "Écoute…":
            self.partial = ""
        self.state = state
        self.last_active = self.clock()
        self.compacted = compact
        self.level = 0
        self.resize_for_state()
        if state == "Fermé":
            self.timer.stop()
            self.hide()
        elif self.settings.hub_visible or state in ("Écoute…", "Préparation…", "Traitement…"):
            self.reveal()
            self.timer.start(16 if state == "Écoute…" else 40)
        else:
            self.timer.stop()
            self.hide()
        if state != "Écoute…":
            self.display_level = 0
        self.update()

    def animate(self):
        self.clamp_to_screen()
        self.phase += .045 + .13 * self.display_level
        target = audio_activity(self.level) if self.state == "Écoute…" else 0
        speed = .55 if target > self.display_level else .12
        self.display_level += (target - self.display_level) * speed
        self.update()

    def set_level(self, level):
        self.level = level

    def set_partial(self, text):
        self.partial = text
        self.update()

    def place(self, anchor):
        self.clamp_to_screen()

    def draw_orb(self, painter, center, radius, activity=0):
        from .suite_orb import draw as _suite_draw
        if _suite_draw(painter,QRectF(center.x()-radius,center.y()-radius,radius*2,radius*2),'transcrinator'):return
        """Fade the decorative rim into real alpha, without a dark circular plate."""
        density = self.devicePixelRatioF()
        side = math.ceil((radius * 2 + 4) * density)
        image = QImage(side, side, QImage.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(density)
        image.fill(Qt.transparent)
        local = QPainter(image)
        local.setRenderHint(QPainter.Antialiasing)
        midpoint = QPointF(side / density / 2, side / density / 2)
        draw_core(local, midpoint, radius, self.phase, activity)
        edge = QRadialGradient(midpoint, radius)
        edge.setColorAt(0, QColor(255, 255, 255, 255))
        edge.setColorAt(.71, QColor(255, 255, 255, 255))
        edge.setColorAt(.83, QColor(255, 255, 255, 170))
        edge.setColorAt(.94, QColor(255, 255, 255, 30))
        edge.setColorAt(1, QColor(255, 255, 255, 0))
        local.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        local.fillRect(QRectF(0, 0, side / density, side / density), edge)
        local.end()
        painter.drawImage(center - midpoint, image)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.compacted:
            self.draw_orb(painter, QPointF(18, 18), 17)
            return
        elapsed = self.clock() - self.unfold_started if self.unfold_started is not None else 1
        progress = min(1., max(0., elapsed / .32))
        unfold = 1 - (1 - progress) ** 3
        width = 36 + (self.width() - 6 - 36) * unfold
        body = QRectF((self.width() - width) / 2, 3, width, self.height() - 7)
        age = self.clock() - self.activation_started if self.activation_started is not None else 1
        pulse = math.sin(math.pi * max(0., min(1., age / .6))) ** .7 if age < .6 else 0
        for inset, alpha in ((0, 8), (1, 14), (2, 22)):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(body.adjusted(-3 + inset, 0, 3 - inset, 4 - inset), 18, 18)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#2c1d12"))
        gradient.setColorAt(1, QColor("#0f0a07"))
        painter.setPen(QPen(QColor(161 + int(70 * pulse), 107 + int(65 * pulse), 57 + int(40 * pulse)), 1))
        painter.setBrush(gradient)
        painter.drawRoundedRect(body, 16, 16)
        painter.save()
        clip = QPainterPath()
        clip.addRoundedRect(body, 16, 16)
        painter.setClipPath(clip)
        draw_artwork(painter, "surface-hub-v1.png", QRectF(4, 4, self.width() - 8, self.height() - 9),
                     opacity=.5)
        if pulse > .01:
            sweep = QLinearGradient(0, 0, self.width(), 0)
            center_stop = min(.92, max(.08, age / .6))
            sweep.setColorAt(max(0., center_stop - .08), QColor(255, 190, 90, 0))
            sweep.setColorAt(center_stop, QColor(255, 215, 145, int(65 * pulse)))
            sweep.setColorAt(min(1., center_stop + .08), QColor(255, 190, 90, 0))
            painter.fillRect(body, sweep)
        painter.restore()
        active = self.state == "Écoute…"
        center, radius = QPointF(25 + (self.width() / 2 - 25) * (1 - unfold), 21), 17 + 1.2 * pulse
        self.draw_orb(painter, center, radius, min(1., self.display_level + .35 * pulse))
        if pulse > .01:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 211, 133, int(180 * pulse)), 1.4))
            painter.drawEllipse(center, 17 + 3 * age / .6, 17 + 3 * age / .6)
        if active and self.display_level > .06:
            painter.setPen(Qt.NoPen)
            for i in range(15):
                angle = i * math.tau / 15 + self.phase * .35
                orbit = radius * (.85 + .12 * math.sin(self.phase + i))
                painter.setBrush(QColor(255, 191, 110, int(210 * self.display_level)))
                point = center + QPointF(math.cos(angle) * orbit, math.sin(angle) * orbit)
                painter.drawEllipse(point, 1 + self.display_level, 1 + self.display_level)
        start = center.x() + 26
        painter.save()
        painter.setClipPath(clip)
        painter.setOpacity(unfold)
        if active or self.state == "Prêt":
            wave = QLinearGradient(start, 0, self.width() - 22, 0)
            wave.setColorAt(0, QColor("#8a512e"))
            wave.setColorAt(.5, QColor("#fff0ce"))
            wave.setColorAt(1, QColor("#cf8c47"))
            painter.setPen(QPen(wave, 2, Qt.SolidLine, Qt.RoundCap))
            heights = wave_heights(self.display_level, self.phase, 32 if active else 24)
            for i, height in enumerate(heights):
                x = start + i * ((self.width() - start - 23) / (len(heights) - 1))
                height = min(19, height * .48)
                painter.drawLine(QPointF(x, 21 - height / 2), QPointF(x, 21 + height / 2))
        elif self.state in ("Préparation…", "Traitement…"):
            # One uninterrupted beam, with a smooth shuttle of warm light.
            # This is indeterminate activity; microphone bars remain for speech.
            end = self.width() - 23
            left, right = QPointF(start, 21), QPointF(end, 21)
            painter.setPen(QPen(QColor(183, 119, 58, 65), 1, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(left, right)
            head = .18 + .64 * (.5 + .5 * math.sin(self.phase * 1.7))
            for width, alpha in ((9, 18), (4, 60), (1.8, 255)):
                beam = QLinearGradient(start, 0, end, 0)
                beam.setColorAt(0, QColor(255, 169, 72, 0))
                beam.setColorAt(max(0., head - .26), QColor(255, 169, 72, 0))
                beam.setColorAt(head, QColor(255, 231, 186, alpha))
                beam.setColorAt(min(1., head + .26), QColor(255, 169, 72, 0))
                beam.setColorAt(1, QColor(255, 169, 72, 0))
                painter.setPen(QPen(beam, width, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(left, right)
        painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_origin = event.globalPosition().toPoint()
            self.drag_start = self.pos()
            self.dragged = False
            self.last_active = self.clock()
            event.accept()
    def mouseMoveEvent(self, event):
        if self.drag_origin is None:
            return
        point = event.globalPosition().toPoint()
        delta = point - self.drag_origin
        if self.dragged or delta.manhattanLength() >= QApplication.startDragDistance():
            self.dragged = True
            screen = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
            area = available_area(screen)
            self.manual_position = self.bounded(self.drag_start + delta, area)
            self.manual_area = QRect(area)
            self.move(self.manual_position)
            self.last_active = self.clock()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, "dragged", False):
            from app.ui.ergonatus_layout import move_group
            move_group(self, "transcrinator")
        if event.button() == Qt.LeftButton:
            clicked = self.drag_origin is not None and not self.dragged
            self.drag_origin = None
            self.last_active = self.clock()
            if clicked:
                self.open_requested.emit()
            event.accept()
