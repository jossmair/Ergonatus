"""Settings are applied explicitly; changing a model unloads the previous one."""
from dataclasses import replace
from pathlib import Path
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout)
from app import theme
from app.windows.hotkeys import parse_hotkey
from .widgets import Switch


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Réglages de Redactor")
        self.setMinimumWidth(540)
        outer = QVBoxLayout(self)
        outer.addWidget(theme.label("Préférences", "Title"))
        simple = QFormLayout()
        self.motion = Switch("Animer doucement l’orbe", config.animation != "none", animated=config.animation != "none")
        simple.addRow("Animer doucement l’orbe", self.motion)
        self.follow = Switch("Placer l’orbe au-dessus de la suite", config.follow_suite, animated=config.animation != "none")
        simple.addRow("Placer l’orbe au-dessus de la suite", self.follow)
        outer.addLayout(simple)
        advanced_button = QPushButton("Options avancées")
        advanced_button.setCheckable(True)
        outer.addWidget(advanced_button)
        from PySide6.QtWidgets import QWidget
        advanced = QWidget()
        form = QFormLayout()
        form.setSpacing(12)
        model_row = QHBoxLayout()
        self.model = QLineEdit(config.model_path or str(config.model() or ""))
        self.model.setAccessibleName("Chemin du modèle GGUF local")
        pick = QPushButton("Parcourir…")
        pick.clicked.connect(self.browse)
        model_row.addWidget(self.model, 1)
        model_row.addWidget(pick)
        form.addRow("Modèle local", model_row)
        self.threads = QSpinBox()
        self.threads.setRange(0, 64)
        self.threads.setSpecialValueText("Automatique")
        self.threads.setValue(config.threads)
        form.addRow("Threads CPU", self.threads)
        self.tokens = QSpinBox()
        self.tokens.setRange(32, 1024)
        self.tokens.setSingleStep(64)
        self.tokens.setValue(config.max_tokens)
        form.addRow("Longueur maximale (tokens)", self.tokens)
        self.context = QSpinBox()
        self.context.setRange(512, 8192)
        self.context.setSingleStep(512)
        self.context.setValue(config.context)
        form.addRow("Contexte (plus grand = plus de RAM)", self.context)
        self.text_size = QSpinBox()
        self.text_size.setRange(10, 20)
        self.text_size.setSuffix(" pt")
        self.text_size.setValue(config.text_size)
        form.addRow("Taille du texte", self.text_size)
        self.animation = QComboBox()
        for title, value in (("Douce · 25 images/s maximum", "normal"), ("Réduite · 5 images/s", "reduced"), ("Aucune animation", "none")):
            self.animation.addItem(title, value)
        self.animation.setCurrentIndex(self.animation.findData(config.animation))
        form.addRow("Animation de l’orbe", self.animation)
        self.color = QComboBox()
        self.color.addItem("Rubis · identité rouge de la suite", "red")
        self.color.addItem("Violet irisé · variante originale", "violet")
        self.color.setCurrentIndex(self.color.findData(config.orb_color))
        form.addRow("Couleur de l’orbe", self.color)
        self.hotkey = QLineEdit(config.hotkey)
        self.hotkey.setPlaceholderText("Vide pour désactiver le raccourci")
        form.addRow("Raccourci d’ouverture", self.hotkey)
        advanced.setLayout(form)
        advanced.hide()
        advanced_button.toggled.connect(advanced.setVisible)
        self.motion.toggled.connect(lambda on: self.animation.setCurrentIndex(self.animation.findData("reduced" if on else "none")))
        def sync_motion():
            self.motion.blockSignals(True)
            enabled = self.animation.currentData() != "none"
            self.motion.setChecked(enabled)
            self.motion.set_position(1. if enabled else 0.)
            self.motion.blockSignals(False)
        self.animation.currentIndexChanged.connect(sync_motion)
        outer.addWidget(advanced)
        note = theme.label("Aucun téléchargement depuis cette fenêtre. Les modèles restent séparés du programme.\nLes textes et les résultats ne sont jamais enregistrés par Redactor.", "Muted")
        note.setWordWrap(True)
        outer.addWidget(note)
        self.error = theme.label("", "Notice")
        self.error.setWordWrap(True)
        outer.addWidget(self.error)
        row = QHBoxLayout()
        row.addStretch()
        cancel, apply = QPushButton("Annuler"), QPushButton("Appliquer")
        apply.setObjectName("Primary")
        cancel.clicked.connect(self.reject)
        apply.clicked.connect(self.apply)
        row.addWidget(cancel)
        row.addWidget(apply)
        outer.addLayout(row)

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un modèle local inférieur à 2 Go", str(Path(self.model.text()).parent), "GGUF (*.gguf)")
        if path:
            self.model.setText(path)

    def apply(self):
        try:
            parse_hotkey(self.hotkey.text())
            candidate = replace(self.config, model_path=self.model.text().strip(), threads=self.threads.value(),
                max_tokens=self.tokens.value(), context=self.context.value(), text_size=self.text_size.value(),
                animation=self.animation.currentData(), orb_color=self.color.currentData(),
                hotkey=self.hotkey.text().strip(), follow_suite=self.follow.isChecked()).validate()
            if candidate.model_path and not Path(candidate.model_path).is_file():
                raise ValueError("Le fichier modèle n’existe pas.")
        except ValueError as exc:
            self.error.setText(str(exc))
            return
        self.config = candidate
        self.accept()
