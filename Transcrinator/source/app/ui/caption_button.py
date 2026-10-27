from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton


class CaptionButton(QPushButton):
    def __init__(self, close=False):
        super().__init__()
        self.close_icon = close
        self.setAccessibleName("Masquer" if close else "Réduire")
        self.setToolTip(self.accessibleName())
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(32, 30)
        self.keyboard_focus = False

    def focusInEvent(self, event):
        self.keyboard_focus = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)
        super().focusInEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hover = self.underMouse()
        painter.setBrush(QColor("#51301d" if hover else "#201812"))
        painter.setPen(QPen(QColor("#bc8651" if hover else "#58402b"), 1))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.75, .75, -.75, -.75), 9, 9)
        painter.setPen(QPen(QColor("#ffe2bb" if hover else "#d8b995"), 1.6, Qt.SolidLine, Qt.RoundCap))
        x, y = self.width() / 2, self.height() / 2
        if self.close_icon:
            painter.drawLine(int(x - 4), int(y - 4), int(x + 4), int(y + 4))
            painter.drawLine(int(x - 4), int(y + 4), int(x + 4), int(y - 4))
        else:
            painter.drawLine(int(x - 5), int(y + 1), int(x + 5), int(y + 1))
        if self.hasFocus() and self.keyboard_focus:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ffdaa4"), 1, Qt.DotLine))
            painter.drawRoundedRect(QRectF(3, 3, self.width() - 6, self.height() - 6), 6, 6)
