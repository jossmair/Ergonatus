"""Family pill switch: a large hit area, visible thumb and native checkbox semantics."""
from PySide6.QtCore import Property, QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox
from app import theme


class Switch(QCheckBox):
    def __init__(self, caption, checked=False, parent=None, animated=True):
        super().__init__(parent)
        self.setAccessibleName(caption)
        self.setToolTip(caption)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(62, 42)
        self._position = 1. if checked else 0.
        self.setChecked(checked)
        self.slide = QPropertyAnimation(self, b"position", self)
        self.slide.setDuration(150 if animated else 0)
        self.slide.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self.transition)

    def get_position(self):
        return self._position

    def set_position(self, value):
        self._position = value
        self.update()

    position = Property(float, get_position, set_position)

    def transition(self, checked):
        self.slide.stop()
        self.slide.setStartValue(self._position)
        self.slide.setEndValue(1. if checked else 0.)
        self.slide.start()

    def hitButton(self, point):
        return self.rect().contains(point)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QRectF(7, 10, 48, 23)
        p.setPen(QPen(QColor(theme.LIGHT if self.isChecked() else theme.BORDER), 1))
        p.setBrush(QColor(theme.DEEP if self.isChecked() else theme.INPUT))
        p.drawRoundedRect(track, 11.5, 11.5)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.TEXT if self.isChecked() else theme.MUTED))
        p.drawEllipse(QPointF(18.5 + 25 * self._position, 21.5), 8.5, 8.5)
        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(theme.LIGHT), 2))
            p.drawRoundedRect(track.adjusted(-3, -3, 3, 3), 14, 14)


class CheckChip(QCheckBox):
    """Compact checked options, with real checkbox accessibility semantics."""
    def __init__(self, caption, checked=False):
        super().__init__(caption)
        self.setChecked(checked)
        self.setAccessibleName(caption)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(30)
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(caption) + 37)

    def hitButton(self, point):
        return self.rect().contains(point)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(theme.LIGHT if self.hasFocus() else theme.ACCENT if self.isChecked() else theme.BORDER), 1))
        p.setBrush(QColor(theme.HOVER if self.isChecked() else theme.INPUT))
        p.drawRoundedRect(box, 8, 8)
        mark = QRectF(10, 8, 13, 13)
        p.setPen(QPen(QColor(theme.LIGHT if self.isChecked() else theme.MUTED), 1))
        p.setBrush(QColor(theme.DEEP) if self.isChecked() else Qt.NoBrush)
        p.drawRoundedRect(mark, 3, 3)
        if self.isChecked():
            p.setPen(QPen(QColor(theme.TEXT), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(QPointF(13, 14), QPointF(16, 17))
            p.drawLine(QPointF(16, 17), QPointF(21, 11))
        p.setPen(QColor(theme.TEXT if self.isChecked() else theme.MUTED))
        p.drawText(QRectF(30, 0, self.width() - 34, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import QTimer


class GrowingEditor(QPlainTextEdit):
    """A document-sized editor; only the enclosing conversation can scroll."""
    def __init__(self):
        super().__init__()
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.max_lines = None
        self.textChanged.connect(self.fit_document)
        self.document().documentLayout().documentSizeChanged.connect(self.fit_document)
        self.fit_document()

    def fit_document(self, *args):
        # QPlainTextDocumentLayout reports its height in visual text lines.
        lines = max(1, self.document().documentLayout().documentSize().height())
        if self.max_lines:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded if lines > self.max_lines else Qt.ScrollBarAlwaysOff)
            lines = min(lines, self.max_lines)
        height = round(lines * self.fontMetrics().lineSpacing() + 2 * self.document().documentMargin() + 14)
        if height != self.height():
            self.setFixedHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.fit_document)
