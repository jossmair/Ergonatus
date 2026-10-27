"""All family visual constants: ruby shell, restrained orb and accessible controls."""
from functools import lru_cache
import os
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt
import math
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QWidget
from .config import assets_root

WIDTH, HEIGHT = 460, 520
MIN_WIDTH, MIN_HEIGHT = 420, 460
RADIUS, BUTTON_HEIGHT, ORB_SIZE, ORB_GAP = 18, 36, 36, 10
BG, SURFACE, INPUT = "#F6F9FD", "#FFFFFF", "#FFFFFF"
TEXT, MUTED, BORDER = "#1E3149", "#64758B", "#DCE3ED"
ACCENT, LIGHT, DEEP, HOVER = "#c84448", "#f2a199", "#703037", "#382027"
SUCCESS, WARNING, ERROR, WHITE = "#abdfbd", "#f2d6a0", "#f5a3a8", "#ffffff"
SHADOW, TRANSPARENT = "#090406", "#00000000"
ORB_PALETTES = {
    "red": ("#ffe0e6", "#f18ba3", "#d03b61", "#76203c", "#2b1024"),
    "violet": ("#f5eaff", "#c4a2f7", "#9164e8", "#50308e", "#211338"),
    "error": ("#f0c5c5", "#bd7b82", "#954b5a", "#63313e", "#27141c"),
}
FONT_FALLBACK = "Segoe UI"


def stylesheet():
    return f"""
QWidget {{color:{TEXT}; background:transparent; font-family:'Segoe UI'; font-size:10pt;}}
QDialog, QMessageBox {{background:{BG};}}
QLabel {{background:transparent; border:none;}}
QLabel#Brand {{font-size:12pt; font-weight:600; letter-spacing:0px;}}
QLabel#Title {{font-size:18pt; font-weight:600;}}
QLabel#Hero {{font-size:24pt; font-weight:400;}}
QFrame#UserBubble {{background:{DEEP}; border:none; border-radius:16px;}}
QFrame#AssistantBubble {{background:{SURFACE}; border:none; border-radius:16px;}}
QLabel#Greeting {{font-size:21pt; font-weight:500;}}
QPushButton#Suggestion {{background:{SURFACE}; border:1px solid {BORDER}; text-align:left; font-weight:400; min-height:20px; padding:5px 12px;}}
QFrame#Composer {{background:{INPUT}; border:1px solid {BORDER}; border-radius:20px;}}
QPlainTextEdit#ComposerInput {{background:transparent; border:none; padding:3px;}}
QPlainTextEdit#ChatResult {{background:transparent; border:none; padding:2px;}}
QLabel#ChatRole {{color:{LIGHT}; font-size:8pt; font-weight:700; letter-spacing:1px;}}
QPushButton#Small {{padding:3px 10px; min-height:25px; border-radius:8px;}}
QPushButton#Quiet {{background:transparent; border-color:transparent; color:{MUTED};}}
QPushButton#Quiet:hover {{background:{HOVER}; border-color:{BORDER}; color:{TEXT};}}
QPushButton#Tab {{background:transparent; border-color:transparent;}}
QPushButton#Tab:checked {{background:{DEEP}; border-color:{BORDER};}}
QLabel#Muted {{color:{MUTED}; font-size:9pt;}}
QLabel#Status {{color:{LIGHT}; font-size:9pt;}}
QLabel#Notice {{color:{WARNING};}}
QFrame#Card {{background:{SURFACE}; border:1px solid {BORDER}; border-radius:14px;}}
QPushButton {{background:{SURFACE}; border:1px solid {BORDER}; border-radius:10px;
 padding:5px 12px; min-height:30px; font-weight:600;}}
QPushButton:hover {{background:{HOVER}; border-color:{LIGHT};}}
QPushButton:pressed {{background:{DEEP};}}
QPushButton:checked {{background:{DEEP}; border-color:{LIGHT};}}
QPushButton:disabled {{color:{MUTED}; border-color:{BORDER}; background:{BG};}}
QPushButton:focus, QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{border:2px solid {LIGHT};}}
QPushButton#Primary {{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {DEEP},stop:1 {HOVER}); color:{TEXT}; border-color:{ACCENT};}}
QPushButton#Primary:hover {{background:{DEEP}; border-color:{LIGHT};}}
QPushButton#Caption {{background:{SURFACE}; border:1px solid {BORDER}; border-radius:8px; padding:0; min-height:26px;}}
QPushButton#Caption:hover {{background:{HOVER};}}
QPlainTextEdit, QLineEdit, QComboBox, QSpinBox {{background:{INPUT}; border:1px solid {BORDER};
 border-radius:10px; padding:8px; selection-background-color:{DEEP}; color:{TEXT};}}
QComboBox {{min-height:26px; padding:5px 10px;}}
QComboBox::drop-down {{border:none; width:24px;}}
QComboBox QAbstractItemView {{background:{SURFACE}; color:{TEXT}; selection-background-color:{DEEP};}}
QCheckBox {{spacing:10px; padding:8px 0;}}
QCheckBox::indicator {{width:24px; height:24px; border:1px solid {BORDER}; border-radius:6px; background:{INPUT};}}
QCheckBox::indicator:checked {{background:{ACCENT}; border:3px solid {LIGHT};}}
QScrollArea {{border:none; background:transparent;}}
QScrollBar:vertical {{background:transparent; width:12px;}}
QScrollBar::handle:vertical {{background:{BORDER}; border-radius:5px; min-height:28px;}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{height:0;}}
QMenu {{background:{SURFACE}; border:1px solid {BORDER}; padding:6px;}}
QMenu::item {{padding:12px 24px; border-radius:7px;}}
QMenu::item:selected {{background:{DEEP};}}
QToolTip {{background:{SURFACE}; color:{TEXT}; border:1px solid {ACCENT}; padding:8px;}}
QSplitter::handle {{background:{BORDER}; height:5px; margin:2px 0;}}
"""


def configure_app(app):
    app.setStyle("Fusion")
    if FONT_FALLBACK not in QFontDatabase.families():
        fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "seguisym.ttf"):
            QFontDatabase.addApplicationFont(str(fonts / name))
    families = QFontDatabase.families()
    font = "Segoe UI Variable" if "Segoe UI Variable" in families else FONT_FALLBACK
    app.setFont(QFont(font, 10))
    palette = QPalette()
    for role, color in ((QPalette.Window, BG), (QPalette.WindowText, TEXT), (QPalette.Text, TEXT),
                        (QPalette.Base, INPUT), (QPalette.Button, SURFACE), (QPalette.ButtonText, TEXT),
                        (QPalette.Highlight, DEEP), (QPalette.HighlightedText, TEXT), (QPalette.PlaceholderText, MUTED)):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet().replace("'Segoe UI'", f"'{font}'"))


def label(text, name=None):
    item = QLabel(text)
    item.setTextFormat(Qt.PlainText)
    if name:
        item.setObjectName(name)
    return item


@lru_cache(maxsize=1)
def background():
    return QPixmap(str(assets_root() / "backgrounds" / "main-ruby-v2.png"))


@lru_cache(maxsize=1)
def app_icon():
    return QIcon(str(assets_root() / "redactor.ico"))


@lru_cache(maxsize=16)
def utility_icon(name):
    canvas = QPixmap(40, 40)
    canvas.setDevicePixelRatio(2)
    canvas.fill(Qt.transparent)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(LIGHT), 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if name == "settings":
        p.drawEllipse(QPointF(10, 10), 5, 5)
        p.drawEllipse(QPointF(10, 10), 1.7, 1.7)
        for i in range(8):
            a = i * math.tau / 8
            p.drawLine(QPointF(10 + 5 * math.cos(a), 10 + 5 * math.sin(a)), QPointF(10 + 7.2 * math.cos(a), 10 + 7.2 * math.sin(a)))
    elif name == "refresh":
        p.drawArc(QRectF(4, 4, 12, 12), 30 * 16, 290 * 16)
        p.drawLine(16, 3, 16, 7)
        p.drawLine(12, 7, 16, 7)
    elif name == "copy":
        p.drawRoundedRect(QRectF(7, 6, 9, 11), 2, 2)
        p.drawLine(4, 13, 4, 3)
        p.drawLine(4, 3, 12, 3)
    elif name == "insert":
        p.drawLine(11, 4, 16, 4)
        p.drawLine(16, 4, 16, 16)
        p.drawLine(16, 16, 11, 16)
        p.drawLine(3, 10, 12, 10)
        p.drawLine(8, 6, 12, 10)
        p.drawLine(8, 14, 12, 10)
    elif name == "target":
        p.drawEllipse(QPointF(10, 10), 5, 5)
        p.drawLine(10, 2, 10, 7)
        p.drawLine(10, 13, 10, 18)
        p.drawLine(2, 10, 7, 10)
        p.drawLine(13, 10, 18, 10)
    elif name == "selection":
        for x, direction in ((3, 1), (17, -1)):
            p.drawLine(x, 4, x + direction * 3, 4)
            p.drawLine(x, 4, x, 16)
            p.drawLine(x, 16, x + direction * 3, 16)
        p.drawLine(7, 8, 13, 8)
        p.drawLine(7, 12, 13, 12)
    elif name == "send":
        path = QPainterPath(QPointF(3, 4))
        for point in (QPointF(17, 10), QPointF(3, 16), QPointF(6, 10), QPointF(3, 4)): path.lineTo(point)
        p.drawPath(path)
        p.drawLine(6, 10, 13, 10)
    else:
        p.drawLine(10, 4, 10, 16)
        p.drawLine(4, 10, 16, 10)
    p.end()
    return QIcon(canvas)


class Shell(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)
        p.setClipPath(path)
        p.fillPath(path, QColor(BG))
        p.setClipping(False)
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawPath(path)


class Chrome(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, event):
        w = self.window()
        w.showNormal() if w.isMaximized() else w.showMaximized()
