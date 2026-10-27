"""Rounded native tray menu with the same family palette with amethyst selection as the window."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QMenu


def tray_icon(name):
    icon = QIcon()
    for mode, color in ((QIcon.Normal, "#B59AFF"), (QIcon.Disabled, "#786887")):
        image = QPixmap(40, 40)
        image.setDevicePixelRatio(2)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if name == "open":
            painter.drawRoundedRect(QRectF(2.5, 3.5, 15, 13), 2, 2)
            painter.drawLine(3, 7, 17, 7)
            painter.drawPoint(5, 5)
        elif name == "pause":
            painter.drawLine(6, 4, 6, 16)
            painter.drawLine(14, 4, 14, 16)
        elif name == "play":
            path = QPainterPath()
            path.moveTo(6, 3)
            path.lineTo(16, 10)
            path.lineTo(6, 17)
            path.closeSubpath()
            painter.drawPath(path)
        elif name == "quit":
            painter.drawArc(QRectF(3, 3, 14, 14), 135 * 16, 270 * 16)
            painter.drawLine(10, 1, 10, 9)
        painter.end()
        icon.addPixmap(image, mode)
    return icon


class TrayMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TrayMenu")
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(250)
        self.setStyleSheet("""
            QMenu#TrayMenu {
                background: transparent; border: none; padding: 8px;
                color: #efeaf7; font: 10pt 'Segoe UI';
            }
            QMenu#TrayMenu::item {
                padding: 11px 16px 11px 12px; margin: 2px 0;
                border: none; border-radius: 7px;
                background: transparent; color: #efeaf7;
            }
            QMenu#TrayMenu::item:selected { background: #6039AD; color: #f0e9ff; }
            QMenu#TrayMenu::item:disabled { color: #94839f; }
            QMenu#TrayMenu::separator {
                height: 1px; background: #3c334c; margin: 6px 12px;
            }
            QMenu#TrayMenu::icon { padding-left: 10px; }
        """)

    def add_command(self, text, icon_name, callback):
        action = self.addAction(tray_icon(icon_name), text)
        action.setIconVisibleInMenu(True)
        action.triggered.connect(callback)
        return action

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        background = QLinearGradient(0, 0, 0, self.height())
        background.setColorAt(0, QColor("#251e30"))
        background.setColorAt(1, QColor("#141019"))
        painter.setBrush(background)
        painter.setPen(QPen(QColor("#9164E8"), 1))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 12, 12)
        painter.end()
        super().paintEvent(event)
