"""Native local chat, compact checked options and editable assistant proposals."""
from PySide6.QtCore import Qt, Signal, Slot, QEvent
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLineEdit,
    QMainWindow, QPlainTextEdit, QPushButton, QSizeGrip, QVBoxLayout, QMenu, QScrollArea, QWidget)
from app import theme
from app.ai.prompts import Request, STYLES
from .orb import OrbWidget
from .chat import ChatPanel
from .widgets import CheckChip, GrowingEditor

ACTIONS = (("compose", "Rédiger"), ("reply", "Répondre"), ("correct", "Corriger"),
           ("rewrite", "Reformuler"), ("summarize", "Résumer"), ("expand", "Développer"))


def button(text, name=None, callback=None):
    item = QPushButton(text)
    item.setMinimumHeight(34)
    item.setAccessibleName(text)
    if name: item.setObjectName(name)
    if callback: item.clicked.connect(callback)
    return item


class MainWindow(QMainWindow):
    generate_requested = Signal()
    regenerate_requested = Signal()
    new_requested = Signal()
    cancel_requested = Signal()
    capture_requested = Signal()
    destination_requested = Signal()
    insert_requested = Signal()
    copy_requested = Signal()
    settings_requested = Signal()

    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("REDACTOR")
        self.setWindowIcon(theme.app_icon())
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(theme.MIN_WIDTH, theme.MIN_HEIGHT)
        self.resize(theme.WIDTH, theme.HEIGHT)
        self.action, self.engine_ready, self.busy = "compose", False, False
        self.action_buttons = {}
        self.chat_history = []
        self.current_history_index = None
        self.orb, self.mini_orb = OrbWidget(size=34), OrbWidget(size=12)
        self.editor, self.result = GrowingEditor(), GrowingEditor()
        self.editor.setObjectName("ComposerInput")
        self.result.setObjectName("ChatResult")
        self.editor.setAccessibleName("Votre message à Redactor")
        self.result.setAccessibleName("Dernière réponse modifiable avant copie")
        self.editor.setPlaceholderText("Message…")
        self.editor.installEventFilter(self)
        self.editor.setToolTip("Entrée pour envoyer · Maj+Entrée pour une nouvelle ligne")
        self.result.setPlaceholderText("Je prépare votre texte…")
        self.instruction = QLineEdit(self)
        self.instruction.setMaxLength(3000)
        self.instruction.hide()
        self.style = QComboBox(self)
        self.style.addItems(STYLES)
        self.style.setCurrentText("Naturel")
        self.style.hide()
        self.metrics = theme.label("", "Muted")
        self.metrics.hide()
        self.target_label = theme.label("Aucun champ choisi", "Muted")
        self.target_label.hide()
        self.notice = theme.label("Échangez, ajustez, puis copiez votre réponse. Tout reste sur ce PC.", "Muted")
        self.notice.setWordWrap(True)
        self.notice.setAccessibleName("Information de Redactor")
        self.status = theme.label("Préparation du moteur…", "Muted")
        self.capture = button("Sélection", "Quiet", self.capture_requested.emit)
        self.target = button("Destination", "Quiet", self.destination_requested.emit)
        self.target.setParent(self)
        self.target.hide()
        self.generate = button("", "Primary", self.generate_requested.emit)
        self.regenerate = button("↻", "Small", self.regenerate_requested.emit)
        self.regenerate.setAccessibleName("Régénérer la dernière proposition")
        self.regenerate.setToolTip("Régénérer la dernière proposition")
        self.regenerate.setFixedWidth(36)
        self.cancel = button("■", "Small", self.cancel_requested.emit)
        self.copy = button("Copier la réponse", "Primary", self.copy_requested.emit)
        self.copy.setToolTip("Copier uniquement la dernière réponse, avec vos modifications")
        self.insert = button("Insérer…", "Primary", self.insert_requested.emit)
        self.insert.setParent(self)
        self.insert.hide()
        self.settings = button("⚙", "Caption", self.settings_requested.emit)
        self.settings.setAccessibleName("Préférences")
        self.settings.setToolTip("Préférences")
        self.settings.setFixedSize(32, 32)
        shell = theme.Shell()
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(18, 14, 18, 12)
        outer.setSpacing(8)
        chrome = theme.Chrome()
        header = QHBoxLayout(chrome)
        header.setContentsMargins(0, 0, 0, 0)
        names = QVBoxLayout()
        names.setSpacing(2)
        names.addWidget(theme.label("Redactor", "Brand"))
        status_row = QHBoxLayout()
        status_row.setSpacing(5)
        status_row.addWidget(self.mini_orb)
        status_row.addWidget(self.status)
        status_row.addStretch()
        names.addLayout(status_row)
        header.addWidget(self.orb)
        header.addLayout(names, 1)
        self.settings.hide()
        for text, caption in (("−", "Réduire vers l’orbe"), ("×", "Fermer vers l’orbe")):
            item = button(text, "Caption", self.hide)
            item.setFixedSize(32, 32)
            item.setAccessibleName(caption)
            item.setToolTip(caption)
            header.addWidget(item)
        outer.addWidget(chrome)
        options = QHBoxLayout()
        options.setSpacing(6)
        self.mode = QComboBox()
        for key, caption in ACTIONS: self.mode.addItem(caption, key)
        self.mode.setAccessibleName("Action de rédaction")
        self.mode.setFixedWidth(114)
        self.mode.currentIndexChanged.connect(lambda _: self.select_action(self.mode.currentData()))
        self.mode.setParent(self)
        self.mode.hide()
        self.natural = CheckChip("Naturel", True)
        self.mail = CheckChip("Mail")
        self.professional = CheckChip("Professionnel")
        self.short = CheckChip("Court")
        self.tones = QButtonGroup(self)
        self.tones.setExclusive(True)
        self.tones.addButton(self.natural)
        self.tones.addButton(self.professional)
        for chip in (self.natural, self.mail, self.short): options.addWidget(chip)
        self.professional.setParent(self)
        self.professional.hide()
        self.natural.toggled.connect(lambda on: self.style.setCurrentText("Naturel") if on else None)
        self.professional.toggled.connect(lambda on: self.style.setCurrentText("Professionnel") if on else None)
        self.tone_menu = QMenu(self)
        modes = self.tone_menu.addMenu("Que souhaitez-vous faire ?")
        for key, caption in ACTIONS:
            modes.addAction(caption, lambda checked=False, value=key: self.select_action(value))
        self.tone_menu.addSeparator()
        self.tone_actions = {}
        for style in STYLES:
            action = self.tone_menu.addAction(style)
            action.setCheckable(True)
            action.setChecked(style == "Naturel")
            action.triggered.connect(lambda checked=False, value=style: self.style.setCurrentText(value))
            self.tone_actions[style] = action
        self.more = button("⋯", "Caption")
        self.more.setFixedSize(32, 32)
        self.more.setAccessibleName("Options, actions et préférences")
        self.more.clicked.connect(lambda: self.tone_menu.popup(self.more.mapToGlobal(self.more.rect().bottomLeft())))
        self.tone_menu.addSeparator()
        self.tone_menu.addAction("Préférences", self.settings_requested.emit)
        options.addWidget(self.more)
        self.style.currentTextChanged.connect(self.sync_tones)
        options.addStretch()
        outer.addLayout(options)
        self.chat = ChatPanel(self.result)
        composer = QFrame()
        composer.setObjectName("Composer")
        write = QVBoxLayout(composer)
        write.setContentsMargins(10, 5, 10, 7)
        write.setSpacing(2)
        write.addWidget(self.editor)
        self.conversation = QScrollArea()
        self.conversation.setWidgetResizable(True)
        self.conversation.setFrameShape(QFrame.NoFrame)
        self.conversation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        conversation_layout = QVBoxLayout(content)
        conversation_layout.setContentsMargins(0, 0, 0, 0)
        conversation_layout.setSpacing(6)
        conversation_layout.addWidget(self.chat)
        conversation_layout.addStretch()
        self.conversation.setWidget(content)
        self.chat.scroller = self.conversation
        self.conversation.verticalScrollBar().rangeChanged.connect(lambda *_: self.chat.scroll_latest())
        outer.addWidget(self.conversation, 1)
        self.composer = composer
        self.editor.max_lines = 8
        self.editor.fit_document()
        write.setContentsMargins(12, 8, 8, 8)
        entry_row = QHBoxLayout()
        entry_row.addWidget(self.editor, 1)
        self.generate.setFixedSize(36, 36)
        self.generate.setToolTip("Envoyer")
        self.generate.setAccessibleName("Envoyer le message")
        self.cancel.setFixedSize(36, 36)
        self.cancel.setToolTip("Arrêter la réponse")
        write.removeWidget(self.editor)
        entry_row.addWidget(self.generate, 0, Qt.AlignBottom)
        entry_row.addWidget(self.cancel, 0, Qt.AlignBottom)
        write.addLayout(entry_row)
        outer.addWidget(composer)
        for control in (self.capture, self.regenerate):
            control.setParent(self)
            control.hide()
        self.tone_menu.addSeparator()
        self.send_menu = self.tone_menu.addAction("Envoyer · Entrée", self.generate_requested.emit)
        self.stop_menu = self.tone_menu.addAction("Arrêter", self.cancel_requested.emit)
        self.tone_menu.addAction("Nouvelle conversation", self.new_requested.emit)
        footer = QHBoxLayout()
        self.new = button("+  Nouveau", "Quiet", self.new_requested.emit)
        self.new.setToolTip("Nouvelle conversation · historique en mémoire uniquement")
        self.new.setText("")
        self.new.setFixedWidth(34)
        self.new.setAccessibleName("Nouvelle conversation")
        self.new.setIcon(theme.utility_icon("plus"))
        for control, icon in ((self.capture, "selection"), (self.target, "target"),
                (self.generate, "send"), (self.regenerate, "refresh"), (self.copy, "copy"),
                (self.insert, "insert"), (self.settings, "settings")):
            control.setIcon(theme.utility_icon(icon))
        self.settings.setText("")
        self.regenerate.setText("")
        self.new.setParent(self)
        self.new.hide()
        footer.addStretch()
        footer.addWidget(self.copy)
        footer.addWidget(QSizeGrip(self))
        outer.addLayout(footer)
        self.notice.hide()
        outer.addWidget(self.notice)
        self.setCentralWidget(shell)
        self.result.textChanged.connect(self.refresh_actions)
        self.result.textChanged.connect(self.chat.resize_result)
        self.apply_config(config)
        focus = [self.mode, self.natural, self.mail, self.professional, self.short, self.result,
                 self.editor, self.capture, self.generate, self.cancel,
                 self.new, self.regenerate, self.copy, self.settings]
        for a, b in zip(focus, focus[1:]): self.setTabOrder(a, b)
        self.refresh_actions()

    def eventFilter(self, watched, event):
        if watched is self.editor and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers():
                if self.engine_ready and not self.busy and self.editor.toPlainText().strip():
                    self.generate_requested.emit()
                    return True
        return super().eventFilter(watched, event)

    def apply_config(self, config):
        for editor in (self.editor, self.result):
            font = editor.font()
            font.setPointSize(config.text_size)
            editor.setFont(font)
        for editor in (self.editor, self.result): editor.fit_document()
        for orb in (self.orb, self.mini_orb): orb.configure(config.animation, config.orb_color)

    def select_action(self, key):
        self.action = key
        index = self.mode.findData(key)
        if index != self.mode.currentIndex(): self.mode.setCurrentIndex(index)
        self.style.setEnabled(key != "correct")
        if key == "reply": self.message("Ajoutez le message reçu, puis demandez une réponse. Vous pourrez la copier après relecture.")

    def sync_tones(self, value):
        self.tones.setExclusive(False)
        for chip, name in ((self.natural, "Naturel"), (self.professional, "Professionnel")):
            chip.blockSignals(True)
            chip.setChecked(value == name)
            chip.blockSignals(False)
        self.tones.setExclusive(True)
        for name, action in self.tone_actions.items(): action.setChecked(name == value)
        self.more.setToolTip("Ton : " + value + " · Autres tons")

    def request(self):
        # Include the user's manual edits in the conversational context.
        if self.current_history_index is not None and self.current_history_index < len(self.chat_history):
            self.chat_history[self.current_history_index] = ("assistant", self.result.toPlainText())
        extra = [self.instruction.text().strip()]
        if self.mail.isChecked() and self.action != "correct": extra.append("Présente le texte sous forme de mail, sans inventer le nom du signataire.")
        if self.short.isChecked() and self.action != "correct": extra.append("Réponse courte, sans perdre les informations essentielles.")
        return Request(self.action, self.editor.toPlainText(), self.style.currentText(),
                       " ".join(s for s in extra if s), tuple(self.chat_history[-6:]))

    def begin_turn(self, request, regenerate=False):
        self.current_history_index = None
        if regenerate:
            if self.chat_history and self.chat_history[-1][0] == "assistant": self.chat_history.pop()
        else:
            self.chat_history.append(("user", request.messages()[-1]["content"]))
        self.chat.begin(request.text, regenerate)
        self.editor.clear()
        self.editor.setReadOnly(True)
        self.set_busy(True)

    def complete_turn(self, cancelled=False):
        text = self.result.toPlainText()
        if text.strip():
            self.current_history_index = len(self.chat_history)
            self.chat_history.append(("assistant", text))
        elif self.chat_history and self.chat_history[-1][0] == "user":
            self.chat_history.pop()
        self.editor.setReadOnly(False)
        self.editor.setFocus(Qt.OtherFocusReason)
        self.chat.scroll_latest()

    def reset_chat(self):
        self.chat_history.clear()
        self.current_history_index = None
        self.chat.reset()
        self.result.clear()
        self.editor.clear()
        self.instruction.clear()
        self.metrics.clear()
        self.refresh_actions()

    @Slot()
    def refresh_actions(self):
        if not hasattr(self, "generate"): return
        has_result = bool(self.result.toPlainText().strip())
        self.generate.setVisible(not self.busy)
        self.generate.setEnabled(self.engine_ready and not self.busy)
        self.cancel.setVisible(self.busy)
        self.cancel.setEnabled(self.busy)
        for item in (self.copy,):
            item.setVisible(has_result and not self.busy)
            item.setEnabled(not self.busy and has_result)
        self.regenerate.hide()
        self.regenerate.setEnabled(self.engine_ready and not self.busy and has_result)
        self.send_menu.setEnabled(self.engine_ready and not self.busy)
        self.stop_menu.setEnabled(self.busy)
        self.capture.setEnabled(not self.busy)
        self.target.setEnabled(not self.busy)
        self.mode.setEnabled(not self.busy)
        self.new.setEnabled(not self.busy)
        for chip in (self.natural, self.mail, self.professional, self.short): chip.setEnabled(not self.busy)
        self.result.setReadOnly(self.busy)

    def set_engine(self, ready, text):
        self.engine_ready = ready
        self.status.setText(text)
        self.refresh_actions()

    def set_busy(self, busy):
        self.busy = busy
        self.editor.setReadOnly(busy)
        self.chat.set_thinking(busy)
        self.refresh_actions()

    @Slot(str)
    def append_result(self, text):
        cursor = self.result.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.result.setTextCursor(cursor)
        self.chat.scroll_latest()

    def set_state(self, state):
        self.orb.set_state(state)
        self.mini_orb.set_state(state)

    def message(self, text):
        self.notice.setVisible(any(word in text.casefold() for word in ("échou", "erreur", "impossible", "copiée", "absent", "limite")))
        self.notice.setText(text)
        self.notice.setToolTip(text)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

