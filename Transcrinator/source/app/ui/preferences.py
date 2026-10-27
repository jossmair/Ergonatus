"""Native amber controls with keyboard accessibility and compact layouts."""
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QPushButton


class Toggle(QCheckBox):
    def __init__(self, accessible_name, parent=None):
        super().__init__(parent)
        self.setAccessibleName(accessible_name)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(48, 28)
        self._position = 0.
        self.animation = QPropertyAnimation(self, b"position", self)
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self.animate)

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

    def showEvent(self, event):
        self.animation.stop()
        self.set_position(1. if self.isChecked() else 0.)
        super().showEvent(event)

    def hitButton(self, point):
        return self.rect().contains(point)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(.4)
        value = self._position
        track = QLinearGradient(0, 0, self.width(), self.height())
        track.setColorAt(0, QColor(34 + int(107 * value), 25 + int(58 * value), 19 + int(17 * value)))
        track.setColorAt(1, QColor(24 + int(65 * value), 19 + int(26 * value), 15 + int(9 * value)))
        painter.setPen(QPen(QColor(98 + int(122 * value), 70 + int(91 * value), 46 + int(43 * value)), 1))
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(1.5, 3.5, 45, 21), 10.5, 10.5)
        x = 6 + 20 * value
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 183, 94, int(38 * value)))
        painter.drawEllipse(QRectF(x - 3, 2, 25, 25))
        painter.setBrush(QColor(173 + int(82 * value), 150 + int(85 * value), 126 + int(74 * value)))
        painter.drawEllipse(QRectF(x, 6, 16, 16))
        if self.hasFocus():
            painter.setPen(QPen(QColor("#ffd6a0"), 1, Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(0.5, 0.5, 47, 27), 13, 13)


class ChoiceBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(38)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#e7b27c"), 1.5, Qt.SolidLine, Qt.RoundCap))
        x, y = self.width() - 19, self.height() // 2
        painter.drawLine(x - 3, y - 1, x, y + 2)
        painter.drawLine(x, y + 2, x + 3, y - 1)


class PreferencesCard(QFrame):
    def sizeHint(self):
        return QSize(620, 220)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        fill = QLinearGradient(0, 0, self.width(), self.height())
        fill.setColorAt(0, QColor(255, 255, 255, 255))
        fill.setColorAt(1, QColor(255, 255, 255, 255))
        painter.setBrush(fill)
        painter.setPen(QPen(QColor("#DCE3ED"), 1))
        painter.drawRoundedRect(rect, 17, 17)
        painter.setPen(QPen(QColor("#e9a763"), 2, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(20, 1, 62, 1)


class DictionaryButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("Dictionnaire", parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)
        self.setMinimumWidth(170)
        self._light = 0.
        self.animation = QPropertyAnimation(self, b"light", self)
        self.animation.setDuration(160)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)

    def sizeHint(self):
        return QSize(170, 38)

    def get_light(self):
        return self._light

    def set_light(self, value):
        self._light = value
        self.update()

    light = Property(float, get_light, set_light)

    def fade(self, target):
        self.animation.stop()
        self.animation.setStartValue(self._light)
        self.animation.setEndValue(target)
        self.animation.start()

    def enterEvent(self, event):
        self.fade(1.)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.fade(0.)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(.4)
        light = self._light
        fill = QLinearGradient(0, 0, self.width(), self.height())
        fill.setColorAt(0, QColor(67 + int(light * 26), 41 + int(light * 18), 23 + int(light * 6)))
        fill.setColorAt(1, QColor(36 + int(light * 19), 24 + int(light * 12), 15 + int(light * 4)))
        edge = QLinearGradient(0, 0, self.width(), self.height())
        edge.setColorAt(0, QColor("#efbb77"))
        edge.setColorAt(1, QColor("#775032"))
        painter.setPen(QPen(edge, 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(QRectF(.75, .75, self.width() - 1.5, self.height() - 1.5), 11, 11)
        painter.setPen(QPen(QColor(255, 215, 151, 40 + int(55 * light)), 1))
        painter.drawLine(15, 2, self.width() - 15, 2)
        if self.isDown():
            painter.translate(0, 1)
        painter.save()
        painter.translate(14, self.height() / 2 - 7)
        book = QPainterPath()
        book.moveTo(0, 0)
        book.quadTo(5, -2, 10, 1)
        book.quadTo(15, -2, 20, 0)
        book.lineTo(20, 13)
        book.quadTo(15, 11, 10, 14)
        book.quadTo(5, 11, 0, 13)
        book.closeSubpath()
        painter.setBrush(QColor(255, 181, 85, 15 + int(light * 20)))
        painter.setPen(QPen(QColor("#f5bb74"), 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(book)
        painter.drawLine(10, 1, 10, 14)
        painter.restore()
        font = self.font()
        font.setPointSizeF(9)
        font.setWeight(font.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#ffe2bb"))
        painter.drawText(QRectF(45, 0, self.width() - 69, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        painter.setPen(QPen(QColor("#e9b77e"), 1.4, Qt.SolidLine, Qt.RoundCap))
        x, y = self.width() - 16, self.height() // 2
        painter.drawLine(x - 2, y - 3, x + 1, y)
        painter.drawLine(x + 1, y, x - 2, y + 3)
        if self.hasFocus():
            painter.setPen(QPen(QColor("#ffdaa4"), 1, Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(3, 3, self.width() - 6, self.height() - 6), 8, 8)
