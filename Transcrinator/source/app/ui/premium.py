"""Transparent window chrome and a native, audio-reactive holographic interface."""
import math
import sys
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient, QLinearGradient
from PySide6.QtWidgets import QLabel, QWidget

STYLE = """
QWidget { background:transparent; color:#fff1e5; font:10pt 'Segoe UI Variable Text'; }
QMainWindow {background:transparent;}
QLabel { background:transparent; border:none; }
QLabel#Brand {font:600 18pt 'Segoe UI Variable Display';letter-spacing:4px;color:#fff5eb;}
QLabel#QuietBadge {color:#e0b18d;background:rgba(17,11,7,180);border-radius:6px;font:600 7pt 'Segoe UI Variable Text';letter-spacing:1.4px;padding:4px 9px;}
QLabel#Eyebrow {color:#ffb16e;font:600 7pt 'Segoe UI Variable Text';letter-spacing:2.2px;}
QLabel#HeroTitle {font:500 28pt 'Segoe UI Variable Display';color:#fff0e4;letter-spacing:-1px;}
QLabel#PageTitle {font:600 14pt 'Segoe UI Variable Display';}
QLabel#Subtitle {color:#b49a84;font:9pt 'Segoe UI Variable Text';}
QLabel#Instruction {color:#ecd6c4;font:600 9pt 'Segoe UI Variable Text';}
QLabel#Muted {color:#ac917c;font:8pt 'Segoe UI Variable Text';}
QLabel#Key {color:#ffd0a0;background:#2a1d12;border:1px solid #69442c;border-radius:9px;padding:10px 14px;font:600 9pt 'Segoe UI Variable Text';}
QFrame#StatusCard {background:#20160f;border:1px solid #4b3222;border-radius:14px;}
QFrame#Divider {background:#453020;max-height:1px;border:none;}
QLabel#Notice {color:#edbc83;font:9pt 'Segoe UI Variable Text';padding:4px 0;}
QPushButton {background:#332214;color:#ffd3a3;border:1px solid #765035;border-radius:9px;padding:10px 14px;font:600 9pt 'Segoe UI Variable Text';}
QPushButton:hover {background:#54331b;border-color:#d38f50;}
QPushButton#Primary {background:#4c301a;color:#ffe0b9;border:1px solid #ad703a;min-height:20px;padding:10px 18px;}
QPushButton#Caption {background:rgba(17,11,7,180);color:#ddb58f;border:none;padding:3px;}
QPushButton#Caption:hover {background:#4a2f1b;color:#ffe8c9;}
QPlainTextEdit {background:#120d09;color:#ffead6;border:1px solid #69462c;border-radius:9px;padding:9px;selection-background-color:#8f562d;}
QComboBox {background:#21160f;border:1px solid #765035;border-radius:8px;padding:8px 12px;min-width:135px;}
QComboBox QAbstractItemView {background:#21160f;selection-background-color:#57381f;}
QFrame#PreferenceTile {background:rgba(48,33,22,165);border:1px solid #463121;border-radius:11px;}
QLabel#PreferencesTitle {font:600 13pt 'Segoe UI Variable Display';color:#ffe3c4;}
QLabel#PreferenceCaption {font:600 7pt 'Segoe UI Variable Text';letter-spacing:1px;color:#c39c77;}
QLabel#PreferenceName {font:600 9pt 'Segoe UI Variable Text';color:#f4ddc6;}
QLabel#PreferenceHint {font:8pt 'Segoe UI Variable Text';color:#b79a7d;}
QLabel#DictionaryHint {font:8pt 'Segoe UI Variable Text';color:#c6a88d;background:#1c130d;border:1px solid #4a3220;border-radius:7px;padding:7px 10px;}
QPushButton#PreferenceAction {padding:6px 12px;border-radius:8px;font:600 8pt 'Segoe UI Variable Text';background:#352315;border:1px solid #89603b;}
QPushButton#CategoryFilter {padding:7px 12px;border-radius:8px;font:600 8pt 'Segoe UI Variable Text';background:#21170f;border:1px solid #513821;color:#c9ab8d;}
QPushButton#CategoryFilter:hover {background:#3b2818;border-color:#9e6839;}
QPushButton#CategoryFilter:checked {background:#51321a;border-color:#c98c4c;color:#ffe0b5;}
QComboBox {background:#17100b;border-color:#6d4c30;padding:5px 32px 5px 11px;}
QComboBox:hover,QComboBox:focus {border-color:#dc9b5a;background:#24180f;}
QComboBox::drop-down {border:none;width:30px;}
QComboBox::down-arrow {image:none;width:0;height:0;}
QComboBox QAbstractItemView::item {padding:7px 10px;min-height:22px;}
QCheckBox {spacing:8px;color:#d6b69a;font:8pt 'Segoe UI Variable Text';}
QCheckBox::indicator {width:15px;height:15px;border:1px solid #765035;border-radius:4px;background:#21160f;}
QCheckBox::indicator:checked {background:#d5914e;border:2px solid #f5c186;}
QCheckBox::indicator:hover {border-color:#f5c186;}
QTableWidget {background:#17100c;alternate-background-color:#21170f;border:1px solid #69462c;border-radius:8px;selection-background-color:#59371d;}
QHeaderView::section {background:#2d1e13;color:#e6b68c;padding:9px;border:none;}
QScrollArea {border:none;background:transparent;}
QScrollBar:vertical {background:transparent;width:5px;}
QScrollBar::handle:vertical {background:#65452f;border-radius:2px;min-height:24px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
QMenu {background:#22170f;border:1px solid #755033;padding:6px;}
QMenu::item{padding:9px 20px;border-radius:5px;}
QMenu::item:selected{background:#57381f;}
"""


def asset(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "assets" / name


@lru_cache(maxsize=32)
def artwork(name):
    return QPixmap(str(asset("hud-orange/" + name)))


@lru_cache(maxsize=64)
def scaled_artwork(name, pixels):
    source = artwork(name)
    if source.isNull():
        return source
    return source.scaled(pixels, pixels, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def draw_artwork(painter, name, destination, opacity=1., rotation=0.):
    # Reuse a few physical-pixel sizes instead of resampling megapixel art at 60 Hz.
    density = painter.device().devicePixelRatioF()
    pixels = min(2048, int(math.ceil(max(destination.width(), destination.height()) * density / 64) * 64))
    art = scaled_artwork(name, pixels)
    if art.isNull():
        return False
    painter.save()
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setOpacity(opacity)
    center = destination.center()
    painter.translate(center)
    painter.rotate(rotation)
    painter.drawPixmap(QRectF(-destination.width() / 2, -destination.height() / 2,
                             destination.width(), destination.height()), art, QRectF(art.rect()))
    painter.restore()
    return True


def draw_sprite(painter, family, destination, position, opacity=1.):
    frame = math.floor(position)
    fraction = position - frame
    current = f"frames/{family}-{frame % 4:02}.png"
    following = f"frames/{family}-{(frame + 1) % 4:02}.png"
    if artwork(current).isNull() or artwork(following).isNull():
        return False
    draw_artwork(painter, current, destination, opacity * (1 - fraction))
    draw_artwork(painter, following, destination, opacity * fraction)
    return True


def label(text, name=None):
    result = QLabel(text)
    result.setWordWrap(True)
    if name:
        result.setObjectName(name)
    return result


class Chrome(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()


class HudShell(QWidget):
    """Paint only inside the rounded shell, leaving actual alpha at all corners."""
    def paintEvent(self, event):
        _surface=QPainter(self);_surface.setRenderHint(QPainter.Antialiasing);_surface.setPen(QPen(QColor('#DCE3ED'),1));_surface.setBrush(QColor('#F6F9FD'));_surface.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),16,16);_surface.end();return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 23, 23)
        painter.setClipPath(path)
        background = QLinearGradient(0, 0, self.width(), self.height())
        background.setColorAt(0, QColor("#1a120d"))
        background.setColorAt(1, QColor("#0c0806"))
        painter.fillPath(path, background)
        draw_artwork(painter, "surface-main-v1.png", QRectF(self.rect()), opacity=.85)
        top_shade = QLinearGradient(0, 0, 0, 80)
        top_shade.setColorAt(0, QColor(16, 10, 6, 125))
        top_shade.setColorAt(1, QColor(16, 10, 6, 0))
        painter.fillRect(QRectF(0, 0, self.width(), 80), top_shade)
        painter.setPen(QPen(QColor(182, 112, 66, 12), 1))
        for x in range(30, self.width(), 36):
            for y in range(30, self.height(), 36):
                painter.drawPoint(x, y)
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#65402b"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.setPen(QPen(QColor("#fbb66d"), 1.3))
        for x, y, direction in ((19, 19, 1), (self.width() - 19, self.height() - 19, -1)):
            painter.drawLine(x, y + direction * 18, x, y)
            painter.drawLine(x, y, x + direction * 30, y)


def audio_activity(rms):
    """Perceptual display gain only; never modify audio sent to recognition."""
    if not math.isfinite(rms):
        return 0.
    return min(1., max(0., (rms - .0025) * 32)) ** .6


def wave_heights(activity, phase, count=40):
    result = []
    for i in range(count):
        position = i / (count - 1)
        envelope = .28 + .72 * math.sin(position * math.pi) ** .7
        texture = .32 + .68 * abs(math.sin(i * .61 - phase) * math.cos(i * .23 + phase * .7))
        result.append(2.5 + activity * 40 * envelope * texture)
    return result


def draw_core(painter, center, radius, phase, activity):
    from .suite_orb import draw as _suite_draw
    if _suite_draw(painter,QRectF(center.x()-radius,center.y()-radius,radius*2,radius*2),'transcrinator'):
        if activity>0:
            painter.save();painter.setPen(QPen(QColor('#D5914E'),max(1,radius*.035)));painter.setBrush(Qt.NoBrush);painter.drawEllipse(center,radius*(.90+.08*activity),radius*(.90+.08*activity));painter.restore()
        return

    """Resolution-independent concentric instruments, driven by microphone energy."""
    painter.save()
    painter.translate(center)
    glow = QRadialGradient(0, 0, radius)
    glow.setColorAt(0, QColor(255, 151, 62, int(25 + 95 * activity)))
    glow.setColorAt(.55, QColor(176, 90, 30, int(12 + 30 * activity)))
    glow.setColorAt(1, QColor(20, 12, 8, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(QPointF(0, 0), radius, radius)
    halo_side = radius * 2.05
    draw_artwork(painter, "halo-v1.png", QRectF(-halo_side / 2, -halo_side / 2, halo_side, halo_side),
                 opacity=.4 + .5 * activity, rotation=phase * 2)
    side = radius * 1.7 * (1 + .06 * activity)
    core_rect = QRectF(-side / 2, -side / 2, side, side)
    has_core = radius < 55 and draw_sprite(painter, "core", core_rect, phase * 1.4)
    if not has_core:
        has_core = draw_artwork(painter, "core-hub-v1.png" if radius < 55 else "core-main-v1.png",
                               core_rect, rotation=math.sin(phase) * 2)
    if radius < 55:
        orbit_rect = QRectF(-radius, -radius, radius * 2, radius * 2)
        draw_sprite(painter, "orbit", orbit_rect, phase, opacity=.55 + .4 * activity)
        draw_sprite(painter, "flare", orbit_rect.adjusted(-4, -4, 4, 4), phase * 1.1,
                    opacity=activity * .8)
    if radius >= 55:
        draw_artwork(painter, "orbit-overlay-v1.png", QRectF(-radius, -radius, radius * 2, radius * 2),
                     opacity=.7, rotation=-phase * 5)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor("#63412b"), max(.6, radius / 180)))
    for fraction in (.93, .69, .47):
        painter.drawEllipse(QPointF(0, 0), radius * fraction, radius * fraction)
    for index in range(60):
        angle = index * math.tau / 60
        outer = radius * .89
        inner = outer - radius * (.055 if index % 5 == 0 else .022)
        painter.setPen(QPen(QColor(228, 151, 86, 145 if index % 5 == 0 else 65), 1))
        painter.drawLine(QPointF(math.cos(angle) * inner, math.sin(angle) * inner),
                         QPointF(math.cos(angle) * outer, math.sin(angle) * outer))
    for offset, span, fraction, speed, color in (
        (0, 88, .79, 1, "#ffb961"), (148, 52, .79, 1, "#b77942"),
        (20, 103, .62, -.7, "#b8763c"), (210, 43, .62, -.7, "#ffe2b0"),
        (70, 67, .39 + .045 * activity, 1.3, "#ffbc76"),
    ):
        size = radius * fraction
        painter.setPen(QPen(QColor(color), max(1., radius * .012), Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(QRectF(-size, -size, size * 2, size * 2),
                        int((offset + phase * 16 * speed) * 16), span * 16)
    path = QPainterPath()
    for i in range(7):
        angle = math.tau * i / 6 + math.pi / 6
        point = QPointF(math.cos(angle) * radius * .26, math.sin(angle) * radius * .26)
        if i == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    painter.setPen(QPen(QColor(240, 161, 89, 90), 1))
    if not has_core:
        painter.drawPath(path)
    # Energy bars stay flat at silence. The orbital motion is decorative.
    heights = wave_heights(activity, phase, 13)
    painter.setPen(QPen(QColor("#ffe8bf"), max(1., radius * .014), Qt.SolidLine, Qt.RoundCap))
    for i, height in enumerate(heights):
        x = (i - 6) * radius * .025
        extent = height * radius / 165
        painter.drawLine(QPointF(x, -extent / 2), QPointF(x, extent / 2))
    painter.restore()


class VoiceOrb(QWidget):
    def __init__(self, size=76, ambient=False):
        super().__init__()
        self.setFixedSize(size, size)
        self.ambient = ambient
        self.level, self.display_level, self.phase = 0., 0., 0.
        self.listening = False
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.animate)

    def update_timer(self):
        if self.isVisible() and self.listening:
            self.timer.start(50)
        else:
            self.timer.stop()

    def showEvent(self, event):
        self.update_timer()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def set_state(self, state):
        self.listening = state == "Écoute…"
        self.level = 0
        if not self.listening:
            self.display_level = 0
        self.update_timer()
        self.update()

    def set_level(self, level):
        self.level = audio_activity(level)

    def animate(self):
        self.phase += .035 + .13 * self.display_level
        speed = .55 if self.level > self.display_level else .12
        self.display_level += (self.level - self.display_level) * speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        draw_core(painter, QPointF(self.width() / 2, self.height() / 2),
                  min(self.width(), self.height()) * .49, self.phase, self.display_level)


class HeroArtwork(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(270)
        self.core = VoiceOrb(300, ambient=True)
        self.core.setParent(self)
        self.core.setAttribute(Qt.WA_TransparentForMouseEvents)

    def resizeEvent(self, event):
        side = int(min(310, self.width() * .48, self.height() * .98))
        self.core.setFixedSize(side, side)
        self.core.move(self.width() - side, (self.height() - side) // 2)
        super().resizeEvent(event)
