"""Compact family settings with large, directly clickable sliders."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QPushButton, QScrollArea, QVBoxLayout, QWidget

from services.simple_settings import CHOICES, closest_choice
from services.mouse_speed import speed_label
from .theme import Chrome, Shell, app_icon, label
from .widgets import ChoiceSlider, Switch

ZOOM_CHOICES = (("1.8", "×1,8", 1.8), ("2.5", "×2,5", 2.5), ("3.0", "×3", 3.))
MOUSE_SPEED_CHOICES = tuple((str(speed), speed_label(speed), speed) for speed in range(1, 21))
SLIDER_CHOICES = dict(CHOICES, zoom=ZOOM_CHOICES, mouse_speed=MOUSE_SPEED_CHOICES)


class SettingsWindow(QMainWindow):
    DEFAULT_WIDTH = 420
    DEFAULT_HEIGHT = 456
    MIN_HEIGHT = 340

    enabled_changed = Signal(bool)
    zoom_changed = Signal(float)
    startup_changed = Signal(bool)
    tuning_changed = Signal(object)
    mouse_speed_changed = Signal(int)

    def __init__(self, prefs, mouse_speed=None):
        super().__init__()
        self.setWindowTitle("Précisionator")
        self.setWindowIcon(app_icon())
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(self.DEFAULT_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)
        shell = Shell()
        root = QVBoxLayout(shell)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(10)
        chrome = Chrome()
        header = QHBoxLayout(chrome)
        header.setContentsMargins(0, 0, 0, 0)
        mark = label("")
        mark.setPixmap(app_icon().pixmap(26, 26))
        header.addWidget(mark)
        header.addWidget(label("PRÉCISIONATOR", "Brand"))
        header.addStretch()
        for text, name in (("—", "Réduire"), ("×", "Fermer")):
            button = QPushButton(text)
            button.setObjectName("Caption")
            button.setAccessibleName(name)
            button.setToolTip(name + " vers l’orbe")
            button.setFixedSize(28, 30)
            button.clicked.connect(self.hide)
            header.addWidget(button)
        root.addWidget(chrome)
        heading = QHBoxLayout()
        heading.addWidget(label("Loupe intelligente", "Subtitle"))
        heading.addStretch()
        self.activation = Switch()
        self.activation.setAccessibleName("Activer la loupe intelligente")
        self.activation.setMinimumWidth(128)
        self.activation.toggled.connect(self.enabled_changed)
        heading.addWidget(self.activation)
        root.addLayout(heading)

        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        card = QFrame()
        card.setObjectName("Card")
        content = QVBoxLayout(card)
        content.setContentsMargins(14, 12, 14, 10)
        content.setSpacing(5)
        self.sliders, self.value_labels = {}, {}
        self.add_slider(content, "zoom", "Grossissement", ZOOM_CHOICES)
        self.add_slider(content, "size", "Taille de la loupe", CHOICES["size"])
        self.add_slider(content, "appearance", "La loupe apparaît", CHOICES["appearance"])
        self.add_slider(content, "aim", "Temps pour viser", CHOICES["aim"])
        self.add_slider(content, "mouse_speed", "Vitesse de la souris", MOUSE_SPEED_CHOICES)
        self.sliders["mouse_speed"].markers = (0, 9, 19)
        # Commit at release so the pointer does not change speed mid-drag.
        self.sliders["mouse_speed"].setTracking(False)
        self.sliders["mouse_speed"].sliderMoved.connect(
            lambda index: self.value_labels["mouse_speed"].setText(speed_label(index + 1)))
        self.sliders["mouse_speed"].setAccessibleDescription(
            "Vitesse du pointeur dans Windows. Vers la gauche : plus lente. Vers la droite : plus rapide.")
        body_layout.addWidget(card)
        body_layout.addStretch()
        self.area.setWidget(body)
        root.addWidget(self.area, 1)

        startup_row = QHBoxLayout()
        startup_label = label("Démarrer avec Windows", "Subtitle")
        startup_label.setWordWrap(False)
        startup_row.addWidget(startup_label)
        startup_row.addStretch()
        self.startup = Switch()
        self.startup.setAccessibleName("Démarrer Précisionator avec Windows")
        self.startup.setMinimumWidth(128)
        self.startup.toggled.connect(self.startup_changed)
        startup_row.addWidget(self.startup)
        root.addLayout(startup_row)
        self.notice = label("", "Notice")
        self.notice.hide()
        root.addWidget(self.notice)
        self.setCentralWidget(shell)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self.refresh(prefs)
        self.refresh_mouse_speed(mouse_speed)

    def add_slider(self, layout, key, caption, choices):
        row = QVBoxLayout()
        row.setSpacing(0)
        heading = QHBoxLayout()
        title = label(caption)
        title.setWordWrap(False)
        heading.addWidget(title)
        heading.addStretch()
        value = label("", "SliderValue")
        value.setWordWrap(False)
        heading.addWidget(value)
        row.addLayout(heading)
        slider = ChoiceSlider(caption, choices)
        slider.valueChanged.connect(lambda index, k=key: self.slider_changed(k, index))
        title.setBuddy(slider)
        row.addWidget(slider)
        layout.addLayout(row)
        self.sliders[key], self.value_labels[key] = slider, value

    def slider_changed(self, key, index):
        choices = SLIDER_CHOICES[key]
        self.value_labels[key].setText(choices[index][1])
        if key == "zoom":
            self.zoom_changed.emit(choices[index][2])
        elif key == "mouse_speed":
            self.mouse_speed_changed.emit(choices[index][2])
        else:
            self.tuning_changed.emit(dict(choices[index][2]))

    def refresh(self, prefs):
        for switch, value in ((self.activation, prefs.enabled), (self.startup, prefs.startup)):
            switch.blockSignals(True)
            switch.setChecked(value)
            switch.setText("Activé" if value else "Désactivé")
            switch.blockSignals(False)
        for key, slider in self.sliders.items():
            if key == "mouse_speed":
                continue
            choices = SLIDER_CHOICES[key]
            if key == "zoom":
                index = next(i for i, choice in enumerate(choices) if choice[2] == prefs.magnification)
            else:
                index = next(i for i, choice in enumerate(choices) if choice[0] == closest_choice(key, prefs))
            slider.blockSignals(True)
            slider.setValue(index)
            slider.describe_value(index)
            slider.blockSignals(False)
            self.value_labels[key].setText(choices[index][1])

    def refresh_mouse_speed(self, speed):
        slider = self.sliders["mouse_speed"]
        slider.blockSignals(True)
        slider.setEnabled(speed is not None)
        if speed is None:
            self.value_labels["mouse_speed"].setText("Indisponible")
            slider.setToolTip("Vitesse Windows momentanément indisponible")
            slider.setAccessibleName("Vitesse de la souris : indisponible")
        else:
            slider.setValue(speed - 1)
            slider.describe_value(speed - 1)
            slider.setToolTip("Vitesse du pointeur dans Windows : " + speed_label(speed))
            self.value_labels["mouse_speed"].setText(speed_label(speed))
        slider.blockSignals(False)

    def error(self, message):
        self.notice.setText(message)
        self.notice.setVisible(bool(message))

    def closeEvent(self, event):
        self.hide()
        event.ignore()
