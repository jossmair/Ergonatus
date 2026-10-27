"""Non-activating hover arrows: dwell, scroll, and stop immediately on exit."""
import math

from PySide6.QtCore import QElapsedTimer, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget

from .branding import APP_NAME
from .desktop_target import protect_tool_window, reject_mouse_activation


class HoverScrollArrow(QWidget):
    scroll_requested = Signal(int)
    DWELL_MS = 350
    REPEAT_MS = 240
    WIDTH = 54
    HEIGHT = 28
    EXTENT = 18

    def __init__(self, direction):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.direction = direction
        caption = "Défiler vers le haut" if direction > 0 else "Défiler vers le bas"
        self.setWindowTitle(APP_NAME + " · " + caption)
        self.setAccessibleName(caption + " sans clic")
        self.setToolTip("Rester ici pour " + caption.lower())
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.hovered = False
        self.phase = 0.
        self.elapsed = QElapsedTimer()
        self.dwell = QTimer(self)
        self.dwell.setSingleShot(True)
        self.dwell.setInterval(self.DWELL_MS)
        self.dwell.timeout.connect(self.begin_scroll)
        self.repeat = QTimer(self)
        self.repeat.setInterval(self.REPEAT_MS)
        self.repeat.timeout.connect(self.tick)
        self.animation = QTimer(self)
        self.animation.setInterval(40)
        self.animation.timeout.connect(self.animate)

    def nativeEvent(self, event_type, message):
        handled, result = reject_mouse_activation(message)
        return (handled, result) if handled else super().nativeEvent(event_type, message)

    def showEvent(self, event):
        protect_tool_window(self)
        super().showEvent(event)

    def enterEvent(self, event):
        if self.isEnabled():
            self.hovered = True
            self.elapsed.start()
            self.dwell.start()
            self.animation.start()
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.stop_scroll()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self.stop_scroll()
        super().hideEvent(event)

    def setEnabled(self, enabled):
        if not enabled:
            self.stop_scroll()
        super().setEnabled(enabled)

    def stop_scroll(self):
        self.hovered = False
        self.dwell.stop()
        self.repeat.stop()
        self.animation.stop()
        self.phase = 0.
        self.update()

    def begin_scroll(self):
        if self.hovered and self.isVisible() and self.isEnabled():
            self.repeat.start()
            self.tick()

    def tick(self):
        if not self.hovered or not self.isVisible() or not self.isEnabled():
            self.stop_scroll()
            return
        if QApplication.mouseButtons() == Qt.NoButton:
            self.scroll_requested.emit(self.direction * 120)

    def animate(self):
        self.phase += .24
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(.38)
        if self.direction < 0:
            painter.translate(0, self.height())
            painter.scale(1, -1)
        # A stable crescent-shaped hit area leaves the orb's core accessible.
        # It is wider and taller than the visible ribbon, including at rest.
        hit = QPainterPath(QPointF(2, 27))
        hit.cubicTo(0, 12, 13, 0, 27, 0)
        hit.cubicTo(41, 0, 54, 12, 52, 27)
        hit.lineTo(44, 27)
        hit.cubicTo(42, 22, 36, 19, 27, 19)
        hit.cubicTo(18, 19, 12, 22, 10, 27)
        hit.closeSubpath()
        painter.fillPath(hit, QColor(0, 24, 28, 1))

        ribbon = QPainterPath(QPointF(4, 25))
        ribbon.cubicTo(5, 12, 14, 4, 27, 4)
        ribbon.cubicTo(40, 4, 49, 12, 50, 25)
        ribbon.cubicTo(45, 18, 37, 14, 27, 14)
        ribbon.cubicTo(17, 14, 9, 18, 4, 25)
        ribbon.closeSubpath()
        surface = QLinearGradient(0, 4, 0, 25)
        surface.setColorAt(0, QColor(105, 231, 209, 110 if self.hovered else 52))
        surface.setColorAt(.45, QColor(31, 137, 131, 105 if self.hovered else 58))
        surface.setColorAt(1, QColor(7, 54, 65, 22))
        painter.fillPath(ribbon, surface)

        arc = QPainterPath(QPointF(4, 24))
        arc.cubicTo(6, 11, 15, 4, 27, 4)
        arc.cubicTo(39, 4, 48, 11, 50, 24)
        painter.setBrush(Qt.NoBrush)
        if self.hovered:
            progress = min(1., self.elapsed.elapsed() / self.DWELL_MS) if self.elapsed.isValid() else 0.
            glow = QColor(64, 223, 202, round(15 + 20 * progress))
            painter.setPen(QPen(glow, 5, Qt.SolidLine, Qt.RoundCap))
            painter.drawPath(arc)
        edge = QLinearGradient(4, 0, 50, 0)
        edge.setColorAt(0, QColor(87, 207, 188, 0))
        edge.setColorAt(.5, QColor(147, 246, 222, 205 if self.hovered else 100))
        edge.setColorAt(1, QColor(87, 207, 188, 0))
        painter.setPen(QPen(edge, 1.25, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(arc)

        # Only the chevron moves; the hover area and ribbon stay steady.
        offset = -.85 * math.sin(self.phase) if self.hovered else 0.
        tip = QPainterPath(QPointF(22.5, 12 + offset))
        tip.lineTo(27, 7.5 + offset)
        tip.lineTo(31.5, 12 + offset)
        painter.setPen(QPen(QColor("#b0f7e8" if self.hovered else "#65b5aa"),
                            1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(tip)
