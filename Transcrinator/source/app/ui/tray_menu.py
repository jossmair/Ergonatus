"""Compact copper tray menu. Actions retain QMenu's native keyboard behavior."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu


def menu_icon(name):
    icon = QIcon()
    for mode, color in ((QIcon.Normal, "#e7ad79"), (QIcon.Disabled, "#766b62")):
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
        elif name == "hub":
            painter.drawEllipse(QRectF(3, 3, 14, 14))
            painter.drawEllipse(QRectF(7, 7, 6, 6))
            painter.drawLine(10, 1, 10, 4)
            painter.drawLine(10, 16, 10, 19)
        elif name == "copy":
            painter.drawRoundedRect(QRectF(6.5, 6.5, 10, 11), 1.5, 1.5)
            painter.drawLine(3, 13, 3, 3)
            painter.drawLine(3, 3, 12, 3)
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
        self.setMinimumWidth(280)
        self.setStyleSheet("""
            QMenu#TrayMenu {
                background: transparent; border: none; padding: 8px;
                color: #f5e9df; font: 10pt 'Segoe UI';
            }
            QMenu#TrayMenu::item {
                padding: 11px 16px 11px 12px; margin: 2px 0;
                border: none; border-radius: 7px;
                background: transparent; color: #f5e9df;
            }
            QMenu#TrayMenu::item:selected { background: #493326; color: #ffe2c7; }
            QMenu#TrayMenu::item:disabled { color: #918379; }
            QMenu#TrayMenu::separator {
                height: 1px; background: #49382d; margin: 6px 12px;
            }
            QMenu#TrayMenu::icon { padding-left: 10px; }
        """)

    def add_command(self, text, icon_name, callback):
        action = self.addAction(menu_icon(icon_name), text)
        action.setIconVisibleInMenu(True)
        action.triggered.connect(callback)
        return action

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        panel = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        background = QLinearGradient(0, 0, 0, self.height())
        background.setColorAt(0, QColor("#261f1a"))
        background.setColorAt(1, QColor("#1c1815"))
        painter.setBrush(background)
        painter.setPen(QPen(QColor("#65503e"), 1))
        painter.drawRoundedRect(panel, 12, 12)
        painter.end()
        super().paintEvent(event)
