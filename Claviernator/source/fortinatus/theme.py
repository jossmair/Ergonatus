"""Native Qt interface, with Transcri's dark rounded surfaces in turquoise."""
import math
from functools import lru_cache
from pathlib import Path
import os
import sys
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

STYLE = """
QWidget {color:#e4f4f1; font:10pt 'Segoe UI'; background:transparent;}
QMainWindow, QDialog {background:#0b1315;}
QFrame#Sidebar {background:#101c1e; border-right:1px solid #243c3f;}
QFrame#Card {background:#112024; border:1px solid #294246; border-radius:14px;}
QFrame#QuickOption {background:rgba(16,33,36,235); border:1px solid #2d4b4d; border-radius:12px;}
QFrame#MappingRow {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #183632,stop:1 #112523); border:1px solid #31534c; border-radius:16px;}
QLabel {border:none; background:transparent;}
QLabel#Brand {font:700 16pt 'Segoe UI'; letter-spacing:1.4px;}
QLabel#Eyebrow {color:#6bd9ce; font:600 8pt 'Segoe UI'; letter-spacing:1.8px;}
QLabel#Title {font:600 23pt 'Segoe UI'; letter-spacing:-0.6px;}
QLabel#HeroTitle {font:600 32pt 'Segoe UI'; letter-spacing:-1px;}
QLabel#Subtitle {color:#a0bbba; font:10pt 'Segoe UI';}
QLabel#Muted {color:#89aaa9; font:9pt 'Segoe UI';}
QLabel#CardTitle {font:600 12pt 'Segoe UI';}
QLabel#ActionText {color:#d4eee5; font:600 11pt 'Segoe UI';}
QLabel#ShortcutHint {color:#b1d1cb; font:600 9pt 'Segoe UI';}
QLabel#MappingArrow {color:#78a99b; font:16pt 'Segoe UI'; padding:0 5px;}
QLabel#StateLabel {color:#b8d9d3; font:600 10pt 'Segoe UI';}
QLabel#StateDot {background:#79e2c6; border-radius:4px;}
QLabel#StateDot[paused="true"] {background:#d9b77b;}
QLabel#DialogTitle {font:600 18pt 'Segoe UI'; letter-spacing:-0.4px;}
QLabel#Notice {color:#f1d7a4; background:#2c281e; border:1px solid #63563b; border-radius:8px; padding:9px 12px;}
QLabel#Key {color:#c4f8e6; background:#244b40; border:1px solid #3a6c59; border-bottom:3px solid #102e25; border-radius:10px; padding:9px 15px; font:600 10pt 'Segoe UI';}
QPushButton {background:#20453e; color:#d8eee6; border:1px solid #355e52; border-radius:11px; padding:10px 16px; min-height:20px; font:600 10pt 'Segoe UI';}
QPushButton:hover {background:#2c5b4e; border-color:#72bfa4;}
QPushButton:pressed {background:#0f272a;}
QPushButton:focus, QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus {border:2px solid #7ce7d8;}
QPushButton:disabled {color:#69817f; border-color:#263b3d; background:#152426;}
QPushButton#Primary {background:#81e2c6; border:1px solid #a2edd7; color:#0c3026; border-radius:12px;}
QPushButton#Primary:hover {background:#a0f0d9;}
QPushButton#AddMapping {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1d5555,stop:1 #123b40);
    color:#d6fff0; border:1px solid #518f84; border-radius:13px; padding:7px 12px; min-height:23px; font:600 9pt 'Segoe UI';}
QPushButton#AddMapping:hover {background:#28665e; border-color:#a3ead4;}
QPushButton#AddMapping:focus {border:2px solid #a2efdc;}
QPushButton#Quiet {background:transparent; border:1px solid transparent; color:#adcac0;}
QPushButton#Quiet:hover {background:#203c33; border-color:#385e4e; color:#dcf9ed;}
QPushButton#Footer {background:transparent; border:1px solid transparent; color:#a6c6c1; border-radius:9px; padding:6px 10px; font:9pt 'Segoe UI';}
QPushButton#Footer:hover {background:#183b39; border-color:#335f58; color:#dcfff3;}
QPushButton#Footer:focus {border:2px solid #7ce7d8;}
QPushButton#Pause {background:#295e4e; border:1px solid #45836b; color:#ddfaec; border-radius:21px; padding:10px 22px;}
QPushButton#Pause:hover {background:#34765e; border-color:#86d6b5;}
QPushButton#Edit {background:#1c4545; border:1px solid #3c706b; border-radius:10px; padding:6px 13px; font:600 9pt 'Segoe UI';}
QPushButton#Edit:hover {background:#2b6159; border-color:#91d4be;}
QPushButton#Danger {color:#f3c0b3; border-color:#835c53; background:#302322;}
QPushButton#Delete {background:transparent; border:1px solid transparent; padding:0; min-height:0;}
QPushButton#Delete:hover {background:#402929; border-color:#865752;}
QPushButton#Delete:focus {border:2px solid #e7ac9f;}
QPushButton#Nav {text-align:left; background:transparent; color:#9eb9b8; border:1px solid transparent; padding:12px 14px;}
QPushButton#Nav:checked {color:#a0f1e3; background:#1a3738; border:1px solid #2d5756;}
QPushButton#Nav:hover {background:#1a2e31;}
QPushButton#Caption {background:transparent; border:none; padding:2px; min-height:22px; color:#a1bdbb;}
QPushButton#DialogClose {background:#193437; border:1px solid #335355; padding:0; min-height:0; color:#c7e5df; font:20pt 'Segoe UI'; border-radius:10px;}
QPushButton#DialogClose:hover {background:#34514f; border-color:#7ccdbb; color:#ffffff;}
QPushButton#DialogClose:focus {border:2px solid #a4f4e4;}
QPushButton#Keycap {padding:4px; min-width:27px; min-height:32px; font:600 9pt 'Segoe UI'; border-radius:6px;}
QPushButton#Keycap[mapped="true"] {background:#28574f; color:#b8ffec; border-color:#5cc7ae;}
QPushButton#Keycap:disabled {color:#7c9492; background:#172326;}
QComboBox, QSpinBox, QLineEdit {background:#0c191c; border:1px solid #365558; border-radius:8px; padding:9px 10px; min-height:22px; selection-background-color:#285a54;}
QComboBox::drop-down {border:none; width:24px;}
QComboBox QAbstractItemView {background:#14292c; color:#e4f4f1; selection-background-color:#285b54; border:1px solid #47716f; padding:4px;}
QSpinBox::up-button, QSpinBox::down-button {width:20px;}
QPlainTextEdit {background:#0c191c; border:1px solid #365558; border-radius:9px; padding:10px; selection-background-color:#285a54;}
QListWidget {background:#0c191c; border:1px solid #365558; border-radius:8px; padding:5px;}
QListWidget::item {padding:6px 8px; border-radius:5px;}
QListWidget::item:selected {background:#285b54; color:#e4fff5;}
QCheckBox {spacing:12px; padding:7px 0; color:#c5ddda;}
QCheckBox::indicator {width:21px; height:21px; border:1px solid #416a68; border-radius:6px; background:#102225;}
QCheckBox::indicator:checked {background:#72dfcc; border:3px solid #b0f9e8;}
QCheckBox::indicator:focus {border:2px solid #dbfff7;}
QScrollArea, QScrollArea > QWidget > QWidget {border:none; background:transparent;}
QScrollBar:vertical {background:transparent; width:8px; margin:2px;}
QScrollBar::handle:vertical {background:#365d5b; border-radius:3px; min-height:28px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height:0;}
QMenu {background:#13292c; border:1px solid #3a6864; padding:6px;}
QMenu::item {padding:10px 22px; border-radius:5px;}
QMenu::item:selected {background:#28574f;}
QToolTip {background:#1b393b; color:#e9fff9; border:1px solid #5c9c94; padding:8px;}
QSizeGrip {background:transparent;}
"""


def configure_app(application):
    # The offscreen Qt platform (used for QA) cannot enumerate Windows fonts.
    if "Segoe UI" not in QFontDatabase.families():
        fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
        for filename in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "seguisym.ttf"):
            QFontDatabase.addApplicationFont(str(fonts / filename))
    application.setStyle("Fusion")
    palette = QPalette()
    for role, color in [(QPalette.Window, "#0b1315"), (QPalette.WindowText, "#e4f4f1"),
                        (QPalette.Base, "#0c191c"), (QPalette.AlternateBase, "#14292c"),
                        (QPalette.Text, "#e4f4f1"), (QPalette.Button, "#1b3336"),
                        (QPalette.ButtonText, "#d4eeea"), (QPalette.Highlight, "#285b54"),
                        (QPalette.HighlightedText, "#e4f4f1"), (QPalette.PlaceholderText, "#89aaa9")]:
        palette.setColor(role, QColor(color))
    application.setPalette(palette)
    application.setStyleSheet(STYLE)


def label(text, name=None):
    item = QLabel(text)
    item.setWordWrap(True)
    item.setTextFormat(Qt.PlainText)
    if name:
        item.setObjectName(name)
    return item


def card():
    result = QFrame()
    result.setObjectName("Card")
    return result


def asset_path(name):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root / "assets" / name


def icon_pixmap(size=256):
    return QPixmap(str(asset_path("logo-clavier-v1.png"))).scaled(
        size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def app_icon():
    return QIcon(str(asset_path("logo-clavier-v1.png")))


def add_key_icon():
    return QIcon(str(asset_path("ajouter-touche-v1.png")))


@lru_cache(maxsize=2)
def utility_icon(name):
    pixmap = QPixmap(40, 40)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor("#95bfb5"), 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if name == "options":
        for y, knob in [(5, 7), (10, 13), (15, 8)]:
            painter.drawLine(3, y, knob - 2, y)
            painter.drawLine(knob + 2, y, 17, y)
            painter.drawEllipse(QPointF(knob, y), 2, 2)
    else:
        painter.drawArc(QRectF(4, 4, 12, 12), 25 * 16, 285 * 16)
        painter.drawLine(16, 3, 16, 7)
        painter.drawLine(12, 7, 16, 7)
    painter.end()
    return QIcon(pixmap)


@lru_cache(maxsize=1)
def trash_icon():
    icon = QIcon()
    for mode, color in ((QIcon.Normal, "#a6c7c1"), (QIcon.Active, "#ffd0c2"), (QIcon.Disabled, "#58716e")):
        pixmap = QPixmap(40, 40)
        pixmap.setDevicePixelRatio(2)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(3, 5, 17, 5)
        painter.drawRoundedRect(QRectF(7, 2, 6, 3), 1, 1)
        painter.drawLine(5, 5, 6, 17)
        painter.drawLine(6, 17, 14, 17)
        painter.drawLine(14, 17, 15, 5)
        painter.drawLine(8, 8, 8, 14)
        painter.drawLine(12, 8, 12, 14)
        painter.end()
        icon.addPixmap(pixmap, mode)
    return icon


@lru_cache(maxsize=2)
def background(name):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return QPixmap(str(root / "assets" / "backgrounds" / name))


def draw_background(painter, rect, name):
    image = background(name)
    if image.isNull() or rect.isEmpty():
        return
    # Cover the surface without stretching the generated artwork.
    source = QRectF(image.rect())
    ratio = rect.width() / rect.height()
    if source.width() / source.height() > ratio:
        width = source.height() * ratio
        source.setLeft((image.width() - width) / 2)
        source.setWidth(width)
    else:
        height = source.width() / ratio
        source.setTop((image.height() - height) / 2)
        source.setHeight(height)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawPixmap(rect, image, source)


class BackdropDialog(QDialog):
    Accepted = QDialog.DialogCode.Accepted
    Rejected = QDialog.DialogCode.Rejected

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(app_icon())

    def header(self, title):
        self.setWindowTitle(title)
        chrome = Chrome()
        row = QHBoxLayout(chrome)
        row.setContentsMargins(0, 0, 0, 8)
        row.addWidget(label(title, "DialogTitle"))
        row.addStretch()
        close = QPushButton("×")
        close.setObjectName("DialogClose")
        close.setFixedSize(38, 38)
        close.setAccessibleName("Fermer")
        close.setToolTip("Fermer · Échap")
        close.setAutoDefault(False)
        close.clicked.connect(self.reject)
        row.addWidget(close)
        return chrome

    def paintEvent(self, event):
        _surface=QPainter(self);_surface.setRenderHint(QPainter.Antialiasing);_surface.setPen(QPen(QColor('#DCE3ED'),1));_surface.setBrush(QColor('#F6F9FD'));_surface.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),16,16);_surface.end();return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        border = QPainterPath()
        border.addRoundedRect(rect, 18, 18)
        painter.setClipPath(border)
        painter.fillRect(rect, QColor("#0b171b"))
        draw_background(painter, rect, "dialog-v1.png")
        painter.fillRect(rect, QColor(5, 15, 18, 100))
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#3c6260"), 1))
        painter.drawPath(border)


class Chrome(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, event):
        window = self.window()
        window.showNormal() if window.isMaximized() else window.showMaximized()


class Shell(QWidget):
    def paintEvent(self, event):
        _surface=QPainter(self);_surface.setRenderHint(QPainter.Antialiasing);_surface.setPen(QPen(QColor('#DCE3ED'),1));_surface.setBrush(QColor('#F6F9FD'));_surface.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),16,16);_surface.end();return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 18, 18)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#101d20"))
        gradient.setColorAt(1, QColor("#0a1215"))
        painter.fillPath(path, gradient)
        painter.setClipPath(path)
        draw_background(painter, QRectF(self.rect()), "main-v1.png")
        painter.fillPath(path, QColor(4, 15, 18, 38))
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#335252"), 1))
        painter.drawPath(path)


class Hero(QWidget):
    """Static, vector-painted keyboard: no decorative motion or image dependency."""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(270)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        p.setClipPath(path)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#112d30"))
        gradient.setColorAt(1, QColor("#08191e"))
        p.fillPath(path, gradient)
        cx, cy = self.width() * .79, self.height() * .47
        radius = 190
        glow = QRadialGradient(cx, cy, radius)
        glow.setColorAt(0, QColor(73, 228, 195, 44))
        glow.setColorAt(1, QColor(12, 30, 33, 0))
        p.fillRect(rect, glow)
        p.setBrush(Qt.NoBrush)
        for index in range(3):
            r = 80 + index * 35
            p.setPen(QPen(QColor(90, 211, 188, 40 - index * 8), 1))
            p.drawEllipse(QPointF(cx, cy), r, r)
        for index in range(36):
            angle = index * math.tau / 36
            p.setPen(QPen(QColor(108, 226, 205, 65), 1))
            p.drawLine(QPointF(cx + math.cos(angle) * 149, cy + math.sin(angle) * 149),
                       QPointF(cx + math.cos(angle) * 153, cy + math.sin(angle) * 153))
        p.save()
        p.translate(cx - 77, cy - 55)
        p.rotate(-10)
        for x, y, text, selected in [(0, 0, "Ctrl", False), (73, 0, "C", True),
                                      (0, 69, "1", False), (73, 69, "↵", False)]:
            p.setPen(QPen(QColor("#76dcc8" if selected else "#3a7773"), 1.3))
            p.setBrush(QColor("#24594f" if selected else "#16383b"))
            p.drawRoundedRect(QRectF(x, y, 62, 59), 11, 11)
            p.setPen(QColor("#bdffed" if selected else "#9dc7c2"))
            p.setFont(QFont("Segoe UI", 19 if len(text) == 1 else 12, QFont.DemiBold))
            p.drawText(QRectF(x, y, 62, 57), Qt.AlignCenter, text)
        p.restore()
        # Fade keeps text legible when the window is narrow.
        fade = QLinearGradient(0, 0, self.width() * .7, 0)
        fade.setColorAt(0, QColor("#112d30"))
        fade.setColorAt(.63, QColor("#112d30"))
        fade.setColorAt(1, QColor(17, 45, 48, 0))
        p.fillRect(rect, fade)
        p.setClipping(False)
        p.setPen(QPen(QColor("#2e5556"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

