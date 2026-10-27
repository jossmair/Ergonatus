"""One screen with compact amber preferences and no transcript panel."""
from dataclasses import replace
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QMainWindow,
    QScrollArea, QVBoxLayout, QWidget,
)

from app.core import autostart
from app.core.hotkeys import TRIGGER_KEYS, trigger_spec
from app.ui.premium import Chrome, HeroArtwork, HudShell, VoiceOrb, label
from app.ui.preferences import DictionaryButton, PreferencesCard, Toggle
from app.ui.key_picker import TriggerChoiceBox
from app.ui.caption_button import CaptionButton
from app.ui.vocabulary_dialog import VocabularyDialog


class MainWindow(QMainWindow):
    trigger_changed = Signal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.preferences = replace(controller.settings)
        self.state_name = "Préparation…"
        self.setWindowTitle("Transcrinator")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setMinimumSize(600, 480)
        area = self.screen().availableGeometry()
        self.resize(min(680, area.width() - 32), min(550, area.height() - 32))

        shell = HudShell()
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)
        chrome = Chrome()
        bar = QHBoxLayout(chrome)
        bar.setContentsMargins(24, 16, 18, 10)
        bar.addWidget(label("TRANSCRINATOR", "Brand"))
        bar.addStretch()
        self.caption_buttons = []
        for close, action in ((False, self.showMinimized), (True, self.hide)):
            button = CaptionButton(close)
            button.clicked.connect(action)
            bar.addWidget(button)
            self.caption_buttons.append(button)
        outer.addWidget(chrome)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.viewport().setAutoFillBackground(False)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 0, 24, 18)
        layout.setSpacing(10)
        hero = self.hero = HeroArtwork()
        hero.setFixedHeight(120)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(0, 6, 0, 6)
        hero_layout.addStretch()
        headline = label('Dictée<br><span style="color:#AD6826">vocale</span>', "HeroTitle")
        headline.setMaximumWidth(350)
        hero_layout.addWidget(headline)
        hero_layout.addStretch()
        layout.addWidget(hero)

        status_card = QFrame()
        status_card.setObjectName("StatusCard")
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(16, 8, 22, 8)
        self.orb = VoiceOrb(60)
        status_layout.addWidget(self.orb)
        words = QVBoxLayout()
        words.setSpacing(5)
        self.status = label("Chargement…", "PageTitle")
        self.detail = label("Initialisation du moteur.", "Subtitle")
        words.addWidget(self.status)
        words.addWidget(self.detail)
        status_layout.addLayout(words, 1)
        layout.addWidget(status_card)
        self.notice = label("", "Notice")
        self.notice.hide()
        layout.addWidget(self.notice)

        self.preferences_panel = PreferencesCard()
        card = QVBoxLayout(self.preferences_panel)
        card.setContentsMargins(18, 14, 18, 18)
        card.setSpacing(12)
        header = QHBoxLayout()
        header.addWidget(label("Préférences", "PreferencesTitle"))
        header.addStretch()
        self.dictionary_button = DictionaryButton()
        self.dictionary_button.clicked.connect(self.edit_vocabulary)
        header.addWidget(self.dictionary_button)
        card.addLayout(header)
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        def selector(title):
            tile = QFrame()
            tile.setObjectName("PreferenceTile")
            box = QVBoxLayout(tile)
            box.setContentsMargins(13, 10, 13, 12)
            box.setSpacing(7)
            box.addWidget(label(title, "PreferenceCaption"))
            return tile, box

        tile, box = selector("TOUCHE DE DÉCLENCHEMENT")
        self.trigger_key = TriggerChoiceBox()
        self.trigger_key.setAccessibleName("Touche de déclenchement")
        for identity, name, vk in TRIGGER_KEYS:
            self.trigger_key.addItem(name, identity)
        self.trigger_key.setCurrentIndex(max(0, self.trigger_key.findData(self.preferences.trigger_key)))
        self.trigger_key.currentIndexChanged.connect(self.save_trigger)
        box.addWidget(self.trigger_key)
        grid.addWidget(tile, 0, 0)
        def toggle_tile(title, example, toggle):
            tile = QFrame()
            tile.setObjectName("PreferenceTile")
            row = QHBoxLayout(tile)
            row.setContentsMargins(13, 12, 13, 12)
            text = QVBoxLayout()
            text.setSpacing(4)
            text.addWidget(label(title, "PreferenceName"))
            text.addWidget(example if isinstance(example, QWidget) else label(example, "PreferenceHint"))
            row.addLayout(text, 1)
            row.addWidget(toggle)
            return tile

        self.number_style = Toggle("Écrire les nombres en chiffres")
        self.number_style.setChecked(self.preferences.number_style == "digits")
        self.number_hint = label(self.number_example(), "PreferenceHint")
        self.number_style.toggled.connect(self.save_text_options)
        grid.addWidget(toggle_tile("Nombres en chiffres", self.number_hint, self.number_style), 0, 1)
        self.units = Toggle("Abréger les unités")
        self.units.setChecked(self.preferences.abbreviate_units)
        self.units.toggled.connect(self.save_text_options)
        grid.addWidget(toggle_tile("Unités abrégées", "250 grammes → 250 g", self.units), 1, 0)
        self.startup = Toggle("Lancer avec Windows")
        self.startup.setChecked(self.preferences.autostart)
        self.startup.toggled.connect(self.save_startup)
        grid.addWidget(toggle_tile("Démarrage Windows", "À l’ouverture de session", self.startup), 1, 1)
        card.addLayout(grid)
        layout.addWidget(self.preferences_panel)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self.setCentralWidget(shell)
        controller.status.connect(self.set_state)
        controller.status.connect(self.orb.set_state)
        controller.status.connect(self.hero.core.set_state)
        controller.level.connect(self.orb.set_level)
        controller.level.connect(self.hero.core.set_level)

    def set_state(self, state):
        self.state_name = state
        key = trigger_spec(self.preferences.trigger_key)[1]
        title, description = {
            "Prêt": ("Prêt", f"{key} pour parler."),
            "Préparation…": ("Chargement…", "Initialisation du moteur."),
            "Écoute…": ("Écoute…", f"{key} pour arrêter."),
            "Traitement…": ("Transcription…", ""),
            "Erreur": ("Erreur", f"Réessayez avec {key}."),
            "Fermé": ("Fermé", "Microphone fermé."),
        }.get(state, (state, ""))
        self.status.setText(title)
        self.detail.setText(description)
        if state == "Écoute…":
            self.notice.hide()

    def show_error(self, message):
        self.notice.setText(message)
        self.notice.show()

    def edit_vocabulary(self):
        dialog = VocabularyDialog(self.preferences.vocabulary, self,
            save_callback=lambda entries: self.save_text_options(vocabulary=entries))
        dialog.exec()

    def save_text_options(self, *_, vocabulary=None):
        candidate = replace(self.preferences,
            number_style="digits" if self.number_style.isChecked() else "words",
            abbreviate_units=self.units.isChecked(),
            vocabulary=self.preferences.vocabulary if vocabulary is None else vocabulary)
        try:
            candidate.save()
        except OSError:
            for toggle, checked in ((self.number_style, self.preferences.number_style == "digits"),
                                    (self.units, self.preferences.abbreviate_units)):
                toggle.blockSignals(True)
                toggle.setChecked(checked)
                toggle.blockSignals(False)
            self.number_hint.setText(self.number_example())
            self.show_error("Les modifications n’ont pas pu être enregistrées. Réessayez.")
            return False
        self.preferences = candidate
        self.number_hint.setText(self.number_example())
        self.controller.request("text_options", {"vocabulary": self.preferences.vocabulary,
            "number_style": self.preferences.number_style, "abbreviate_units": self.preferences.abbreviate_units})
        return True

    def number_example(self):
        return "vingt-cinq → 25" if self.number_style.isChecked() else "25 → vingt-cinq"

    def save_trigger(self, *_):
        previous = self.preferences.trigger_key
        identity = self.trigger_key.currentData()
        self.preferences.trigger_key = identity
        try:
            self.preferences.save()
        except OSError:
            self.preferences.trigger_key = previous
            self.trigger_key.blockSignals(True)
            self.trigger_key.setCurrentIndex(self.trigger_key.findData(previous))
            self.trigger_key.blockSignals(False)
            self.show_error("La touche n’a pas pu être enregistrée.")
            return
        self.set_state(self.state_name)
        self.trigger_changed.emit(identity)

    def save_startup(self, enabled):
        previous = self.preferences.autostart
        try:
            autostart.set_enabled(enabled)
            self.preferences.autostart = enabled
            self.preferences.save()
        except OSError:
            try:
                autostart.set_enabled(previous)
            except OSError:
                pass
            self.preferences.autostart = previous
            self.startup.blockSignals(True)
            self.startup.setChecked(previous)
            self.startup.blockSignals(False)
            self.show_error("Le réglage du démarrage Windows n’a pas pu être enregistré.")

    def closeEvent(self, event):
        self.hide()
        event.ignore()
