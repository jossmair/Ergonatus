"""Generated family orb composited by Qt, at most 25 FPS, with local PNGs."""
import math
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QApplication, QWidget
from app import theme
from app.config import assets_root
from functools import lru_cache
from PySide6.QtGui import QPixmap


@lru_cache(maxsize=24)
def orb_image(color, pixels):
    source = assets_root() / "orbs" / ("violet-family.png" if color == "violet" else "ruby-v2.png")
    return QPixmap(str(source)).scaled(pixels, pixels, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def draw_orb(p, rect, state="idle", seconds=0., color="red", hovered=False):
    from .suite_orb import draw as _suite_draw
    if _suite_draw(p,rect,'redactor',error=state=='error'):return
    """Generated family glass ribbons, composited by Qt with a very quiet halo."""
    p.save()
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    center = rect.center()
    wave = math.sin(math.tau * seconds / (4 if state == "generating" else 10))
    halo = QRadialGradient(center, rect.width() * .5)
    tint = QColor(theme.LIGHT)
    tint.setAlpha(32 if state == "ready" else 16 + round(4 * wave))
    halo.setColorAt(0, tint)
    halo.setColorAt(.6, tint)
    halo.setColorAt(1, QColor(theme.TRANSPARENT))
    p.setPen(Qt.NoPen)
    p.setBrush(halo)
    p.drawEllipse(rect)
    pixels = min(512, max(48, round(rect.width() * p.device().devicePixelRatioF())))
    image = orb_image(color, pixels)
    if not image.isNull():
        p.translate(center)
        p.rotate(1.2 * math.sin(seconds * .3) if state in ("analyzing", "generating") else .35 * wave)
        p.setOpacity(.78 if state == "error" else .96 + .015 * wave)
        target = QRectF(-rect.width() * .5, -rect.height() * .5, rect.width(), rect.height())
        p.drawPixmap(target, image, QRectF(image.rect()))
    p.restore()


class OrbWidget(QWidget):
    def __init__(self, parent=None, size=48):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.state, self.color, self.animation = "idle", "red", "reduced"
        self.seconds = 0.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.setAccessibleName("État de l’assistant Redactor")

    def tick(self):
        self.seconds += self.timer.interval() / 1000
        self.update()

    def configure(self, animation="reduced", color="red"):
        self.animation, self.color = animation, color
        self.timer.stop()
        if animation != "none" and self.isVisible():
            self.timer.start(40 if animation == "normal" else 200)
        self.update()

    def set_state(self, state):
        self.state = state
        self.setAccessibleDescription({"idle": "Au repos", "analyzing": "Chargement du moteur",
            "generating": "Génération en cours", "ready": "Résultat prêt", "error": "Erreur"}[state])
        self.update()
        if state == "error":
            QTimer.singleShot(3000, lambda: self.set_state("idle") if self.state == "error" else None)

    def showEvent(self, event):
        self.configure(self.animation, self.color)
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        draw_orb(p, QRectF(self.rect()), self.state, self.seconds, self.color, self.underMouse())


class DesktopOrb(OrbWidget):
    activated = Signal()
    moved = Signal()
    context_requested = Signal(object)

    def __init__(self):
        super().__init__(size=theme.ORB_SIZE)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Redactor · Orbe")
        self.setAccessibleName("Ouvrir Redactor")
        self.setToolTip("Redactor · Assistant de rédaction\nOuvrir · Clic droit : menu · Glisser : déplacer")
        self.setCursor(Qt.PointingHandCursor)
        self.start = self.origin = None
        self.dragged = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start = event.globalPosition().toPoint()
            self.origin = self.pos()
            self.dragged = False

    def mouseMoveEvent(self, event):
        if self.start is not None:
            delta = event.globalPosition().toPoint() - self.start
            if delta.manhattanLength() >= QApplication.startDragDistance():
                self.dragged = True
            if self.dragged:
                wanted = self.origin + delta
                screen = QApplication.screenAt(event.globalPosition().toPoint()) or QApplication.primaryScreen()
                area = screen.availableGeometry()
                self.move(max(area.left(), min(wanted.x(), area.right() - self.width() + 1)),
                          max(area.top(), min(wanted.y(), area.bottom() - self.height() + 1)))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, "dragged", False):
            from app.windows.ergonatus_layout import move_group
            move_group(self, "redactor")
        if event.button() == Qt.LeftButton and self.start is not None:
            self.start = None
            if self.dragged:
                self.moved.emit()
            elif self.rect().contains(event.position().toPoint()):
                self.activated.emit()

    def contextMenuEvent(self, event):
        self.context_requested.emit(event.globalPos())
