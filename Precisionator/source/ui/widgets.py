"""Family switches with amethyst accents retaining native checkbox keyboard/accessibility behavior."""
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QProxyStyle, QSlider, QStyle, QStyleFactory, QStyleOptionSlider, QSizePolicy


class DirectSliderStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_Slider_AbsoluteSetButtons:
            return Qt.LeftButton.value
        return super().styleHint(hint, option, widget, returnData)


class ChoiceSlider(QSlider):
    """Native accessible slider: a click anywhere chooses a large detent.

    Qt retains standard dragging, focus, keyboard and accessibility behavior;
    precise dragging of the thumb is optional rather than required.
    """
    def __init__(self, caption, choices, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.caption, self.choices = caption, choices
        self.markers = tuple(range(len(choices)))
        self.click_style = DirectSliderStyle(QStyleFactory.create("Fusion"))
        self.click_style.setParent(self)
        self.setStyle(self.click_style)
        self.setRange(0, len(choices) - 1)
        self.setSingleStep(1)
        self.setPageStep(1)
        self.setTickPosition(QSlider.TicksBelow)
        self.setTickInterval(1)
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleDescription(" · ".join(choice[1] for choice in choices))
        self.valueChanged.connect(self.describe_value)
        self.describe_value(0)

    def describe_value(self, index):
        text = self.caption + " : " + self.choices[index][1]
        self.setAccessibleName(text)
        self.setToolTip(text)

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        for index in self.markers:
            option.sliderPosition = index
            handle = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)
            painter.setBrush(QColor("#9164E8" if index == self.value() else "#685678"))
            painter.drawEllipse(QPointF(handle.center().x(), self.height() - 3), 1.5, 1.5)


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
        track.setColorAt(0, QColor(33 + int(63 * value), 29 + int(28 * value), 43 + int(130 * value)))
        track.setColorAt(1, QColor(23 + int(56 * value), 20 + int(22 * value), 31 + int(111 * value)))
        painter.setBrush(track)
        painter.setPen(QPen(QColor(78 + int(103 * value), 66 + int(88 * value), 96 + int(159 * value)), 1))
        painter.drawRoundedRect(QRectF(1.5, 5.5, 45, 21), 10.5, 10.5)
        x = 6 + 20 * value
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(181, 154, 255, int(35 * value)))
        painter.drawEllipse(QRectF(x - 3, 4, 25, 25))
        painter.setBrush(QColor(158 + int(75 * value), 147 + int(104 * value), 176 + int(66 * value)))
        painter.drawEllipse(QRectF(x, 8, 16, 16))
        if self.text():
            painter.setPen(QColor("#1E3149"))
            painter.setFont(self.font())
            painter.drawText(QRectF(58, 0, self.width() - 58, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        if self.hasFocus() and self._keyboard_focus:
            painter.setPen(QPen(QColor("#B59AFF"), 1, Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(.5, 2.5, 47, 27), 13, 13)
