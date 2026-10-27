"""Turquoise switches retaining native checkbox keyboard/accessibility behavior."""
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QPushButton, QSizePolicy


class PauseButton(QPushButton):
    """A readable action and its shortcut in a single compact control."""
    def __init__(self, callback):
        super().__init__()
        self.setFixedSize(190, 34)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("padding:0; border:0; background:transparent; min-height:0;")
        self.clicked.connect(callback)
        self.set_active(True)

    def set_active(self, active):
        self.active = active
        self.setText("Mettre en pause" if active else "En pause")
        self.setAccessibleName(self.text() + " · F12")
        self.setToolTip("F12 : mettre les modifications en pause et relâcher les touches et les clics."
                        if active else "Modifications en pause. Réactivez l’interrupteur en haut pour reprendre.")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        painter.setBrush(QColor("#204440" if self.underMouse() else "#132f31"))
        painter.setPen(QPen(QColor("#87d6c4" if self.hasFocus() else "#3d6d66"), 1))
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#9be8d6" if self.active else "#9ab5b0"))
        for x in (12, 18):
            painter.drawRoundedRect(QRectF(x, 12, 3, 10), 1, 1)
        painter.setPen(QColor("#d6f5ec"))
        painter.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        painter.drawText(QRectF(29, 0, 119, 34), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        painter.setPen(QPen(QColor("#41665f"), 1))
        painter.setBrush(QColor("#0f2529"))
        painter.drawRoundedRect(QRectF(151, 7, 31, 20), 5, 5)
        painter.setPen(QColor("#9ac9bd"))
        painter.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        painter.drawText(QRectF(151, 7, 31, 20), Qt.AlignCenter, "F12")


class Switch(QCheckBox):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self._position = 0.
        self._keyboard_focus = False
        self.animation = QPropertyAnimation(self, b"position", self)
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self.animate)

    def sizeHint(self):
        width = 48 + (10 + self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0)
        return QSize(width + 1, 32)

    def minimumSizeHint(self):
        return self.sizeHint()

    def get_position(self):
        return self._position

    def set_position(self, value):
        self._position = value
        self.update()

    position = Property(float, get_position, set_position)

    def animate(self, checked):
        self.animation.stop()
        self.animation.setStartValue(self._position)
        self.animation.setEndValue(1. if checked else 0.)
        self.animation.start()

    def setChecked(self, checked):
        super().setChecked(checked)
        if self.signalsBlocked() or not self.isVisible():
            self.animation.stop()
            self.set_position(float(checked))

    def showEvent(self, event):
        self.animation.stop()
        self.set_position(float(self.isChecked()))
        super().showEvent(event)

    def hitButton(self, point):
        return self.rect().contains(point)

    def focusInEvent(self, event):
        self._keyboard_focus = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        self._keyboard_focus = True
        self.update()
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(.4)
        value = self._position
        track = QLinearGradient(0, 5, 48, 27)
        track.setColorAt(0, QColor(23 + int(13 * value), 43 + int(73 * value), 46 + int(57 * value)))
        track.setColorAt(1, QColor(15 + int(7 * value), 29 + int(48 * value), 32 + int(39 * value)))
        painter.setBrush(track)
        painter.setPen(QPen(QColor(57 + int(45 * value), 91 + int(117 * value), 91 + int(95 * value)), 1))
        painter.drawRoundedRect(QRectF(1.5, 5.5, 45, 21), 10.5, 10.5)
        x = 6 + 20 * value
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(124, 231, 211, int(35 * value)))
        painter.drawEllipse(QRectF(x - 3, 4, 25, 25))
        painter.setBrush(QColor(139 + int(94 * value), 164 + int(87 * value), 161 + int(81 * value)))
        painter.drawEllipse(QRectF(x, 8, 16, 16))
        if self.text():
            painter.setPen(QColor("#1E3149"))
            painter.setFont(self.font())
            painter.drawText(QRectF(58, 0, self.width() - 58, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        if self.hasFocus() and self._keyboard_focus:
            painter.setPen(QPen(QColor("#a4f4e4"), 1, Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(.5, 2.5, 47, 27), 13, 13)
