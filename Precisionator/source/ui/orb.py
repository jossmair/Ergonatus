"""36 px family orb with a quiet texture and clearly visible activation state."""
from functools import lru_cache
import math
import numpy as np

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QGraphicsColorizeEffect, QGraphicsPixmapItem, QGraphicsScene, QWidget

from .theme import ACCENT, asset_path


@lru_cache(maxsize=32)
def amethyst_frame(frame, pixels):
    source = QPixmap(str(asset_path(f"frames/core-{frame:02}.png")))
    source = source.scaled(pixels, pixels, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(source)
    effect = QGraphicsColorizeEffect()
    effect.setColor(QColor(ACCENT))
    effect.setStrength(1.)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    scene.setSceneRect(QRectF(source.rect()))
    result = QPixmap(source.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    scene.render(painter, QRectF(result.rect()), scene.sceneRect())
    painter.end()
    image = result.toImage().convertToFormat(QImage.Format_RGBA8888)
    rgba = np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.width(), 4).copy()
    # Restore the exact 1.0.3 family artwork, only 6% darker in RGB. Preserve
    # its original transparency, highlights and texture; no opaque dark core.
    rgba[:, :, :3] = np.rint(rgba[:, :, :3] * .94).astype(np.uint8)
    recolored = QImage(rgba.data, image.width(), image.height(), rgba.strides[0], QImage.Format_RGBA8888)
    return QPixmap.fromImage(recolored)


def draw_core(painter, rect, phase):
    current = math.floor(phase)
    fraction = phase - current
    pixels = min(512, max(64, math.ceil(rect.width() * painter.device().devicePixelRatioF())))
    # Compose into a transparent layer so opacity applies to the whole sprite,
    # including at mid-crossfade, without adding light to the desktop beneath it.
    layer = QPixmap(pixels, pixels)
    layer.fill(Qt.transparent)
    blend = QPainter(layer)
    for index, (frame, alpha) in enumerate(((current % 4, 1 - fraction), ((current + 1) % 4, fraction))):
        pixmap = amethyst_frame(frame, pixels)
        if index:
            # Add premultiplied contributions: ordinary SourceOver would make
            # the middle of a crossfade 25% more transparent than its endpoints.
            blend.setCompositionMode(QPainter.CompositionMode_Plus)
        blend.setOpacity(alpha)
        blend.drawPixmap(0, 0, pixmap)
    blend.end()
    painter.drawPixmap(rect, layer, QRectF(layer.rect()))


def draw_orb(painter, rect, enabled=True, seconds=0., hovered=False, pressed=False):
    from .suite_orb import draw as _suite_draw
    if _suite_draw(painter,rect,'precisionator',enabled=enabled):return
    """A still silhouette: only a small texture blend and slow light breathing.

    The inactive orb stays visibly dimmer even on a still image. No rotation,
    size pulse or centre glyph competes with the user's pointing movement.
    """
    pulse = math.sin(math.tau * seconds / (8. if enabled else 12.))
    phase = .14 + (.10 if enabled else .012) * pulse
    opacity = (.96 + .025 * pulse) if enabled else (.42 + .004 * pulse)
    glow_alpha = (18 + 4 * pulse) if enabled else (4 + pulse)
    if hovered:
        glow_alpha += 18 if enabled else 7
        opacity = min(1., opacity + .04)
    painter.save()
    center = rect.center()
    glow = QRadialGradient(center, rect.width() / 2)
    glow.setColorAt(0, QColor(145, 100, 232, round(glow_alpha)))
    glow.setColorAt(1, QColor(0, 0, 0, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(rect)
    if pressed:
        painter.translate(center)
        painter.scale(.94, .94)
        painter.translate(-center)
    painter.setOpacity(painter.opacity() * opacity)
    draw_core(painter, rect, phase)
    painter.restore()


class Orb(QWidget):
    activated = Signal()
    moved = Signal()

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setWindowTitle("Précisionator · Orbe")
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.seconds = 0.
        self.drag_start = self.drag_position = None
        self.dragged = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.enabled = True

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        # This is the magnifier state, not QWidget.setEnabled: clicking and
        # dragging the orb must remain possible while the loupe is off.
        self._enabled = bool(value)
        self.timer.setInterval(50 if self._enabled else 120)
        self.describe_action()
        self.update()

    def describe_action(self):
        state = "Activé" if self.enabled else "Désactivé"
        action = "Désactiver" if self.enabled else "Activer"
        self.setAccessibleName(f"{action} la loupe · {state}")
        self.setAccessibleDescription("Clic simple : activer ou désactiver. Clic droit : réglages. Glisser : déplacer.")
        self.setToolTip(f"Précisionator · {state}\n{action} la loupe · Clic droit : réglages")

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def animate(self):
        # Pausing the timer for the DXGI probe also pauses decorative time.
        # Resuming it cannot cause a jump or a catch-up burst.
        self.seconds += self.timer.interval() / 1000
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start = event.globalPosition().toPoint()
            self.drag_position = self.pos()
            self.dragged = False
            self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_start is not None:
            delta = event.globalPosition().toPoint() - self.drag_start
            if delta.manhattanLength() >= QApplication.startDragDistance():
                self.dragged = True
            if self.dragged:
                self.move(self.drag_position + delta)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, "dragged", False):
            from services.ergonatus_layout import move_group
            move_group(self, "precisionator")
        if event.button() == Qt.LeftButton and self.drag_start is not None:
            self.drag_start = None
            if self.dragged:
                self.moved.emit()
            elif self.rect().contains(event.position().toPoint()):
                self.activated.emit()
            self.update()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        draw_orb(painter, QRectF(self.rect()), self.enabled, self.seconds,
                 self.underMouse(), self.drag_start is not None and not self.dragged)
