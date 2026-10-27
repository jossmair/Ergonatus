from copy import deepcopy
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPlainTextEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from .config import Mapping
from .keys import EMERGENCY, KEYS, MODIFIERS, combo_name, normalize_key
from .theme import BackdropDialog, label
from .widgets import Switch
from .sequence_editor import SequenceEditor


ACTION_CHOICES = [
    ("key", "Autre touche ou raccourci"), ("sequence", "Suite de touches"), ("text", "Écrire un texte"),
    ("mouse_click:left", "Clic gauche"), ("mouse_click:right", "Clic droit"),
    ("mouse_hold:left", "Clic gauche maintenu"), ("mouse_hold:right", "Clic droit maintenu"),
    ("double_click", "Double-clic gauche"), ("mouse_toggle", "Clic verrouillé : appui / appui"),
    ("wheel", "Défiler"), ("move", "Déplacer la souris"),
    ("mouse_click:middle", "Clic du milieu"), ("mouse_hold:middle", "Clic du milieu maintenu"),
    ("disabled", "Ne rien faire"), ("original", "Fonction normale"),
]


def key_combo(exclude_emergency=True):
    combo = QComboBox()
    combo.setMaxVisibleItems(15)
    for vk, name in sorted(KEYS.items(), key=lambda item: item[1].casefold()):
        if not exclude_emergency or vk != EMERGENCY:
            combo.addItem(name, vk)
    return combo


class CaptureButton(QPushButton):
    def __init__(self, callback, single=False):
        super().__init__("Choisir au clavier")
        self.callback, self.single, self.recording = callback, single, False
        self.keys = []
        self.clicked.connect(self.begin)
        self.setToolTip("Cliquer, puis appuyer sur la touche ou la combinaison souhaitée. F12 reste réservé.")

    def begin(self):
        self.keys = []
        self.recording = True
        self.setText("Appuyez sur votre touche…" if self.single else "Appuyez sur votre combinaison…")
        self.setFocus(Qt.OtherFocusReason)

    def event(self, event):
        if self.recording and event.type() == QEvent.ShortcutOverride:
            event.accept()
            return True
        if self.recording and event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            if event.isAutoRepeat():
                return True
            scan = event.nativeScanCode()
            vk = normalize_key(event.nativeVirtualKey(), scan, 1 if scan & 0x100 else 0)
            if vk not in KEYS or vk == EMERGENCY:
                self.setText("Touche indisponible · réessayez")
                return True
            if event.type() == QEvent.KeyPress:
                if vk not in self.keys:
                    self.keys.append(vk)
            elif self.keys and (self.single or vk not in MODIFIERS or all(k in MODIFIERS for k in self.keys)):
                keys = [self.keys[0]] if self.single else self.keys[:8]
                self.recording = False
                self.setText("Choisir au clavier")
                self.callback(keys)
            return True
        return super().event(event)

    def focusOutEvent(self, event):
        self.recording = False
        self.setText("Choisir au clavier")
        super().focusOutEvent(event)


class MappingDialog(BackdropDialog):
    def __init__(self, parent, mapping=None, source=None, kind=None):
        super().__init__(parent)
        self.setWindowTitle("Modifier une touche")
        self.reset_requested = False
        self.setMinimumWidth(520)
        self.resize(560, 540)
        self.mapping = deepcopy(mapping) if mapping else Mapping(source or 0x70, kind or "key", keys=[0x41])
        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 24, 26, 24)
        outer.setSpacing(14)
        outer.addWidget(self.header("Modifier une touche"))
        outer.addWidget(label("Touche"))
        row = QHBoxLayout()
        self.source = key_combo()
        self.source.setCurrentIndex(self.source.findData(self.mapping.source))
        row.addWidget(self.source, 1)
        row.addWidget(CaptureButton(lambda keys: self.source.setCurrentIndex(self.source.findData(keys[0])), True))
        outer.addLayout(row)
        outer.addWidget(label("Action"))
        self.kind = QComboBox()
        self.kind.setMaxVisibleItems(14)
        for value, title in ACTION_CHOICES:
            self.kind.addItem(title, value)
        outer.addWidget(self.kind)
        self.stack = QStackedWidget()
        self.pages = {}
        outer.addWidget(self.stack, 1)

        key_page = QWidget()
        key_layout = QVBoxLayout(key_page)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(label("Touche à obtenir", "Muted"))
        self.modifier_checks = []
        modifiers = QHBoxLayout()
        for name, vk, group in [("Ctrl", 0xA2, {0xA2, 0xA3}), ("Alt", 0xA4, {0xA4, 0xA5}),
                                 ("Maj", 0xA0, {0xA0, 0xA1}), ("Win", 0x5B, {0x5B, 0x5C})]:
            check = Switch(name)
            check.setChecked(bool(set(self.mapping.keys) & group) and len(self.mapping.keys) > 1)
            self.modifier_checks.append((check, vk))
            check.toggled.connect(self.manual_keys)
            modifiers.addWidget(check)
        key_layout.addLayout(modifiers)
        self.target = key_combo()
        self.target.setCurrentIndex(self.target.findData(self.mapping.keys[-1] if self.mapping.keys else 0x41))
        self.target.currentIndexChanged.connect(self.manual_keys)
        key_layout.addWidget(self.target)
        key_layout.addWidget(CaptureButton(self.set_keys))
        self.presets = QComboBox()
        self.presets.addItem("Raccourcis courants…", None)
        for title, keys in [("Copier · Ctrl + C", [0xA2, 67]), ("Coller · Ctrl + V", [0xA2, 86]),
                            ("Couper · Ctrl + X", [0xA2, 88]), ("Annuler · Ctrl + Z", [0xA2, 90]),
                            ("Rétablir · Ctrl + Y", [0xA2, 89]), ("Tout sélectionner · Ctrl + A", [0xA2, 65]),
                            ("Enregistrer · Ctrl + S", [0xA2, 83]), ("Changer de fenêtre · Alt + Tab", [0xA4, 9]),
                            ("Bureau · Win + D", [0x5B, 68]), ("Explorateur · Win + E", [0x5B, 69]),
                            ("Enregistrer sous · Ctrl + Maj + S", [0xA2, 0xA0, 83])]:
            self.presets.addItem(title, keys)
        self.presets.currentIndexChanged.connect(lambda: self.set_keys(self.presets.currentData()) if self.presets.currentData() else None)
        key_layout.addWidget(self.presets)
        self.target_keys = self.mapping.keys[:] or [0x41]
        self.key_summary = label(combo_name(self.target_keys), "Key")
        key_layout.addWidget(self.key_summary)
        key_layout.addStretch()
        self.add_page("key", key_page)
        self.sequence_editor = SequenceEditor(self.mapping, key_combo)
        self.add_page("sequence", self.sequence_editor)

        text_page = QWidget()
        text_layout = QVBoxLayout(text_page)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(label("Texte à écrire · 500 caractères maximum", "Muted"))
        self.text = QPlainTextEdit(self.mapping.text)
        self.text.setPlaceholderText("Bonjour, merci pour votre message…")
        text_layout.addWidget(self.text)
        self.add_page("text", text_page)
        self.add_page("mouse_click", label("Gardez la touche appuyée pour glisser. Relâchez pour déposer.", "Subtitle"))
        self.add_page("mouse_hold", label("Gardez la touche appuyée pour glisser. Relâchez pour déposer.", "Subtitle"))
        toggle_page = QWidget()
        toggle_layout = QVBoxLayout(toggle_page)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.addWidget(label("Un appui maintient le clic, un autre le relâche.", "Subtitle"))
        self.mouse_button = QComboBox()
        for name, value in [("Bouton gauche", "left"), ("Bouton droit", "right"), ("Bouton du milieu", "middle")]:
            self.mouse_button.addItem(name, value)
        self.mouse_button.setCurrentIndex(self.mouse_button.findData(self.mapping.button))
        toggle_layout.addWidget(self.mouse_button)
        toggle_layout.addStretch()
        self.add_page("mouse_toggle", toggle_page)
        self.add_page("double_click", label("Un appui = double-clic gauche.", "Subtitle"))
        self.wheel = QComboBox()
        for amount in (120, 240, 360, -120, -240, -360):
            self.wheel.addItem(f"{'Vers le haut' if amount > 0 else 'Vers le bas'} · {abs(amount) // 120} cran(s)", amount)
        self.wheel.setCurrentIndex(self.wheel.findData(self.mapping.amount))
        self.add_page("wheel", self.wheel)
        self.direction = QComboBox()
        for title, value in [("Vers la gauche", "left"), ("Vers la droite", "right"), ("Vers le haut", "up"), ("Vers le bas", "down")]:
            self.direction.addItem(title, value)
        self.direction.setCurrentIndex(self.direction.findData(self.mapping.direction))
        self.add_page("move", self.direction)
        self.add_page("disabled", label("Cette touche ne fait rien.", "Subtitle"))
        self.add_page("original", label("Cette touche garde son fonctionnement normal.", "Subtitle"))
        self.kind.currentIndexChanged.connect(self.show_action)
        selection = self.mapping.kind
        if selection in ("mouse_click", "mouse_hold"):
            selection += ":" + self.mapping.button
        self.kind.setCurrentIndex(self.kind.findData(selection))
        self.show_action()
        self.error = label("", "Notice")
        self.error.hide()
        outer.addWidget(self.error)
        buttons = QHBoxLayout()
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Enregistrer")
        save.setObjectName("Primary")
        save.clicked.connect(self.save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        outer.addLayout(buttons)

    def add_page(self, kind, widget):
        self.pages[kind] = widget
        self.stack.addWidget(widget)

    def show_action(self, *_):
        kind = self.kind.currentData().partition(":")[0]
        self.stack.setCurrentWidget(self.pages[kind])

    def set_keys(self, keys):
        if keys:
            self.target_keys = keys[:]
            self.key_summary.setText(combo_name(keys))

    def manual_keys(self):
        keys = [vk for checkbox, vk in self.modifier_checks if checkbox.isChecked()]
        target = self.target.currentData()
        if target not in keys:
            keys.append(target)
        self.set_keys(keys)

    def save(self):
        kind, _, button = self.kind.currentData().partition(":")
        self.mapping = Mapping(self.source.currentData(), kind, keys=self.target_keys[:],
                               text=self.text.toPlainText(),
                               button=button or self.mouse_button.currentData(),
                               amount=self.wheel.currentData(), direction=self.direction.currentData(),
                               enabled=self.mapping.enabled)
        self.mapping.sequence = [step[:] for step in self.sequence_editor.steps]
        self.mapping.interval_ms = self.sequence_editor.interval.value()
        try:
            self.mapping.validate()
        except ValueError as exc:
            self.error.setText(str(exc))
            self.error.show()
            return
        self.accept()

    def restore(self):
        self.reset_requested = True
        self.accept()

