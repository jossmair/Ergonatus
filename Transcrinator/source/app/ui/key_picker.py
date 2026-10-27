"""Compact native keyboard picker, with transparent rounded popup corners."""
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout

from app.ui.preferences import ChoiceBox


class KeyCap(QPushButton):
    def __init__(self, text, selected, parent):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(selected)
        self.setAccessibleName(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)
        self.setMinimumWidth(0)
        self.setStyleSheet("QPushButton {padding:0;min-width:0;border:none;}")
        self.keyboard_focus = False

    def focusInEvent(self, event):
        self.keyboard_focus = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                           Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.parentWidget().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        chosen, hover = self.isChecked(), self.underMouse()
        fill = QLinearGradient(0, 0, 0, self.height())
        fill.setColorAt(0, QColor("#704822" if chosen else "#39291d" if hover else "#2a2018"))
        fill.setColorAt(1, QColor("#48301c" if chosen else "#251c15" if hover else "#201914"))
        painter.setBrush(fill)
        painter.setPen(QPen(QColor("#e5ad6b" if chosen else "#ae7a4e" if hover else "#59412d"), 1))
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 9, 9)
        font = self.font()
        font.setPointSizeF(9)
        font.setWeight(font.Weight.DemiBold if chosen else font.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#ffe5bd" if chosen else "#e1c9b0"))
        painter.drawText(rect, Qt.AlignCenter, self.text())
        if chosen:
            painter.setPen(QPen(QColor("#ffd79b"), 2, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(12, self.height() - 3, self.width() - 12, self.height() - 3)
        if self.hasFocus() and self.keyboard_focus:
            painter.setPen(QPen(QColor("#ffdaa0"), 1, Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 6, 6)


class KeyPopup(QFrame):
    def __init__(self, owner):
        super().__init__(owner, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.owner = owner
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setFixedWidth(322)
        self.buttons = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 14, 15, 15)
        layout.setSpacing(9)
        heading = QLabel("CHOISIR UNE TOUCHE")
        heading.setStyleSheet("color:#d7af80;font:600 7pt 'Segoe UI';letter-spacing:1.4px;")
        layout.addWidget(heading)
        modifiers = QGridLayout()
        modifiers.setSpacing(7)
        functions = QGridLayout()
        functions.setSpacing(6)
        for index in range(owner.count()):
            button = KeyCap(owner.itemText(index), index == owner.currentIndex(), self)
            button.clicked.connect(lambda checked=False, i=index: self.choose(i))
            self.buttons.append(button)
            if index < 4:
                modifiers.addWidget(button, index // 2, index % 2)
            else:
                functions.addWidget(button, (index - 4) // 6, (index - 4) % 6)
        layout.addLayout(modifiers)
        heading = QLabel("TOUCHES DE FONCTION")
        heading.setStyleSheet("color:#a98c72;font:600 7pt 'Segoe UI';letter-spacing:1px;")
        layout.addWidget(heading)
        layout.addLayout(functions)
        self.adjustSize()

    def choose(self, index):
        self.owner.setCurrentIndex(index)
        self.owner.hidePopup()
        self.owner.setFocus(Qt.PopupFocusReason)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.owner.hidePopup()
            self.owner.setFocus(Qt.PopupFocusReason)
            return
        current = next((i for i, button in enumerate(self.buttons) if button.hasFocus()), self.owner.currentIndex())
        delta = {Qt.Key_Left: -1, Qt.Key_Right: 1,
                 Qt.Key_Up: -2 if current < 4 else -6,
                 Qt.Key_Down: 2 if current < 4 else 6}.get(event.key())
        if delta is not None:
            self.buttons[max(0, min(len(self.buttons) - 1, current + delta))].setFocus(Qt.TabFocusReason)
            event.accept()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.choose(current)
        else:
            super().keyPressEvent(event)

    def hideEvent(self, event):
        # QComboBox's internal state must also be reset for outside-click dismissal.
        super().hideEvent(event)
        QComboBox.hidePopup(self.owner)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.75, .75, -.75, -.75)
        fill = QLinearGradient(0, 0, self.width(), self.height())
        fill.setColorAt(0, QColor("#30251c"))
        fill.setColorAt(1, QColor("#15110e"))
        painter.setBrush(fill)
        painter.setPen(QPen(QColor("#a77b4e"), 1))
        painter.drawRoundedRect(rect, 15, 15)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(255, 212, 153, 20), 1))
        painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 12, 12)
        painter.setPen(QPen(QColor("#edb673"), 2, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(20, 1, 62, 1)


class TriggerChoiceBox(ChoiceBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.popup = None

    def showPopup(self):
        if not self.count() or not self.isEnabled():
            return
        if self.popup is None:
            self.popup = KeyPopup(self)
        for index, button in enumerate(self.popup.buttons):
            button.setChecked(index == self.currentIndex())
        self.popup.adjustSize()
        origin = self.mapToGlobal(QPoint(0, self.height() + 6))
        area = self.screen().availableGeometry()
        x = max(area.left() + 4, min(origin.x(), area.right() - self.popup.width() - 3))
        y = origin.y()
        if y + self.popup.height() > area.bottom() - 4:
            y = self.mapToGlobal(QPoint(0, -self.popup.height() - 6)).y()
        y = max(area.top() + 4, min(y, area.bottom() - self.popup.height() - 3))
        self.popup.move(x, y)
        self.popup.show()
        self.popup.buttons[self.currentIndex()].setFocus(Qt.PopupFocusReason)

    def hidePopup(self):
        if self.popup is not None:
            self.popup.hide()
        super().hidePopup()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.popup is not None and self.popup.isVisible():
                self.hidePopup()
            else:
                self.showPopup()
            event.accept()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter, Qt.Key_F4) or (
                event.key() == Qt.Key_Down and event.modifiers() & Qt.AltModifier):
            self.showPopup()
        else:
            super().keyPressEvent(event)
