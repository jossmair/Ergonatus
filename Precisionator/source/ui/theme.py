"""Fortinatus shell, spacing and typography, with amethyst controls."""
from functools import lru_cache
from pathlib import Path
import os
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

ACCENT = "#9164E8"
LIGHT = "#B59AFF"
DEEP = "#6039AD"

STYLE = """
QWidget {color:#efeaf7; font:10pt 'Segoe UI'; background:transparent;}
QLabel {border:none; background:transparent;}
QLabel#Brand {font:700 16pt 'Segoe UI'; letter-spacing:1.4px;}
QLabel#Subtitle {color:#b8aec8; font:10pt 'Segoe UI';}
QLabel#Muted {color:#a197b1; font:9pt 'Segoe UI';}
QLabel#CardTitle {font:600 12pt 'Segoe UI';}
QLabel#Notice {color:#edcf9d; font:9pt 'Segoe UI';}
QFrame#Card {background:#191622; border:1px solid #3c334c; border-radius:14px;}
QPushButton {background:#191622; color:#efeaf7; border:1px solid #3c334c; border-radius:11px;
 padding:10px 16px; min-height:20px; font:600 10pt 'Segoe UI';}
QPushButton:hover {background:#2c2439; border-color:#B59AFF;}
QPushButton:pressed {background:#21182e;}
QPushButton:checked {background:#6039AD; border-color:#9164E8; color:#ffffff;}
QPushButton:checked:hover {background:#7048ba; border-color:#B59AFF;}
QPushButton:focus {border:2px solid #B59AFF;}
QPushButton#Caption {background:transparent; border:none; padding:2px; min-height:22px; color:#b8aec8;}
QPushButton#Caption:hover {background:#2c2439; color:#ffffff;}
QPushButton#Choice {padding:7px 8px; min-height:34px;}
QLabel#SliderValue {color:#B59AFF; font:600 10pt 'Segoe UI';}
QSlider::groove:horizontal {height:6px; background:#3c334c; border-radius:3px;}
QSlider::sub-page:horizontal {background:#9164E8; border-radius:3px;}
QSlider::add-page:horizontal {background:#3c334c; border-radius:3px;}
QSlider::handle:horizontal {width:24px; margin:-9px 0; background:#9164E8;
 border:1px solid #B59AFF; border-radius:12px;}
QSlider::handle:horizontal:hover {background:#a980f0;}
QSlider::handle:horizontal:focus {border:2px solid #f0e9ff;}
QScrollArea,QScrollArea > QWidget > QWidget {border:none; background:transparent;}
QScrollBar:vertical {background:transparent; width:8px; margin:2px;}
QScrollBar::handle:vertical {background:#554467; border-radius:3px; min-height:28px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QMenu {background:#191622; border:1px solid #3c334c; padding:6px;}
QMenu::item {padding:11px 22px; border-radius:7px;}
QMenu::item:selected {background:#6039AD; color:#ffffff;}
QToolTip {background:#191622; color:#efeaf7; border:1px solid #9164E8; padding:8px;}
"""


def asset_path(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "assets" / name


def configure_app(app):
    if "Segoe UI" not in QFontDatabase.families():
        fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
            QFontDatabase.addApplicationFont(str(fonts / name))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(app_icon())


def label(text, name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.PlainText)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


@lru_cache(maxsize=1)
def app_icon():
    return QIcon(str(asset_path("precisionator.ico")))


@lru_cache(maxsize=1)
def background():
    return QPixmap(str(asset_path("backgrounds/main-amethyst-v1.png")))


class Chrome(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()


class Shell(QWidget):
    """Family shell with the requested amethyst texture and 18 px outline."""
    def paintEvent(self, event):
        _surface=QPainter(self);_surface.setRenderHint(QPainter.Antialiasing);_surface.setPen(QPen(QColor('#DCE3ED'),1));_surface.setBrush(QColor('#F6F9FD'));_surface.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),16,16);_surface.end();return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path.addRoundedRect(rect, 18, 18)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#191520"))
        gradient.setColorAt(1, QColor("#100e16"))
        painter.fillPath(path, gradient)
        painter.setClipPath(path)
        image = background()
        if not image.isNull():
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
            painter.drawPixmap(rect, image, source)
        painter.fillPath(path, QColor(10, 6, 18, 38))
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#493a60"), 1))
        painter.drawPath(path)
