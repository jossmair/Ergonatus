"""Native conversation bubbles; content stays in memory only."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget, QPushButton, QSizePolicy
from app import theme


class ChatPanel(QWidget):
    def __init__(self, result):
        super().__init__()
        self.setAccessibleName("Conversation avec Redactor")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.flow = QVBoxLayout(self)
        self.flow.setContentsMargins(0, 0, 3, 0)
        self.flow.setSpacing(9)
        self.flow.setAlignment(Qt.AlignTop)
        self.scroller = None
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.scroll_to_bottom)
        self.composer_editor = None
        self.result = result
        self.current = None
        self.thinking = theme.label("", "Muted")
        self.thinking.hide()
        self.phase = 0
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.animate_thinking)
        self.result.hide()

    def bubble(self, role, text=None):
        row = QWidget()
        row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        align = QHBoxLayout(row)
        align.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        frame.setObjectName("UserBubble" if role == "Vous" else "AssistantBubble")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(13, 9, 13, 9)
        layout.setSpacing(5)

        if text is not None:
            label = theme.label(text)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            layout.addWidget(label)
        frame.setMaximumWidth(340)
        frame.setAccessibleName("Votre message" if role == "Vous" else "Réponse de Redactor")
        if role == "Vous":
            align.addStretch(1)
            align.addWidget(frame, 8)
        else:
            align.addWidget(frame, 8)
            align.addStretch(1)
        self.flow.addWidget(row)
        return layout

    def begin(self, user_text, regenerate=False):
        if not regenerate:
            if self.current is not None:
                text = self.result.toPlainText()
                self.current.removeWidget(self.result)
                self.result.setParent(None)
                label = theme.label(text)
                label.setWordWrap(True)
                label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
                self.current.addWidget(label)
            self.bubble("Vous", user_text)
            self.current = self.bubble("Redactor")
            self.current.addWidget(self.result)
        self.flow.removeWidget(self.thinking)
        self.flow.addWidget(self.thinking)
        self.result.clear()
        self.result.show()
        self.resize_result()
        self.scroll_latest()

    def resize_result(self):
        self.result.fit_document()
        self.scroll_latest()

    def animate_thinking(self):
        self.phase = (self.phase + 1) % 4
        self.thinking.setText("Redactor réfléchit" + "·" * (self.phase + 1))

    def set_thinking(self, active):
        self.thinking.setVisible(active)
        if active:
            self.animate_thinking()
            self.timer.start()
        else:
            self.timer.stop()

    def scroll_latest(self):
        if self.scroller:
            self.scroll_timer.start(0)

    def scroll_to_bottom(self):
        if self.scroller:
            bar = self.scroller.verticalScrollBar()
            bar.setValue(bar.maximum())

    def reset(self):
        if self.current:
            self.current.removeWidget(self.result)
            self.result.setParent(None)
            self.result.hide()
        while self.flow.count():
            item = self.flow.takeAt(0)
            if item.widget() is self.thinking:
                continue
            if item.widget(): item.widget().deleteLater()
        self.set_thinking(False)
        self.current = None
