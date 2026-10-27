from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QMainWindow,
                              QPushButton, QScrollArea, QSizeGrip, QSizePolicy, QVBoxLayout, QWidget)
from . import __version__
from .keys import combo_name, key_name
from .profile_actions import ProfileActions
from .theme import BackdropDialog, Chrome, Shell, add_key_icon, app_icon, card, label, trash_icon, utility_icon
from .windows import set_startup, startup_enabled
from .widgets import PauseButton, Switch


def button(text, callback, primary=False):
    item = QPushButton(text)
    if primary:
        item.setObjectName("Primary")
    item.clicked.connect(callback)
    return item


def action_text(mapping):
    if mapping.kind == "key":
        return combo_name(mapping.keys)
    if mapping.kind == "sequence":
        text = " → ".join(combo_name(step) for step in mapping.sequence)
        return text if len(text) <= 50 else text[:47] + "…"
    if mapping.kind == "text":
        return "Écrire : " + mapping.text.replace("\n", " ↵ ")[:40]
    if mapping.kind in ("mouse_click", "mouse_hold", "mouse_toggle"):
        name = {"left": "Clic gauche", "right": "Clic droit", "middle": "Clic du milieu"}[mapping.button]
        if mapping.kind == "mouse_click":
            return name
        return name + (" · maintenir" if mapping.kind == "mouse_hold" else " · appui / appui")
    if mapping.kind == "wheel":
        return "Défiler vers " + ("le haut" if mapping.amount > 0 else "le bas")
    if mapping.kind == "move":
        return "Souris vers " + {"left": "la gauche", "right": "la droite", "up": "le haut", "down": "le bas"}[mapping.direction]
    return {"double_click": "Double-clic", "disabled": "Ne rien faire", "original": "Fonction normale"}[mapping.kind]


class MainWindow(QMainWindow, ProfileActions):
    quit_requested = Signal()

    def __init__(self, controller, config_dir=None):
        super().__init__()
        self.controller, self.config_dir = controller, config_dir
        self.allow_close = self.tray_available = False
        self.setWindowTitle("Claviernator")
        self.setWindowIcon(app_icon())
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(600, 480)
        screen = self.screen().availableGeometry()
        self.resize(min(680, screen.width() - 32), min(550, screen.height() - 32))
        shell = Shell()
        root = QVBoxLayout(shell)
        root.setContentsMargins(18, 14, 18, 12)
        root.setSpacing(10)
        chrome = Chrome()
        title = QHBoxLayout(chrome)
        title.setContentsMargins(0, 0, 0, 0)
        mark = label("")
        mark.setPixmap(app_icon().pixmap(30, 30))
        title.addWidget(mark)
        title.addWidget(label("CLAVIERNATOR", "Brand"))
        title.addStretch()
        self.activation = Switch("Actif")
        self.activation.setFixedWidth(125)
        self.activation.setAccessibleName("Activer les modifications du clavier")
        self.activation.setToolTip("Désactiver pour retrouver le clavier d’origine. F12 : pause.")
        self.activation.toggled.connect(self.toggle_adaptations)
        title.addWidget(self.activation)
        for text, tip, callback in [("—", "Réduire", self.showMinimized), ("×", "Fermer", self.close)]:
            item = button(text, callback)
            item.setObjectName("Caption")
            item.setAccessibleName(tip)
            item.setFixedSize(32, 30)
            title.addWidget(item)
        root.addWidget(chrome)
        heading = QHBoxLayout()
        self.heading = label("Mes touches", "CardTitle")
        heading.addWidget(self.heading)
        heading.addStretch()
        add = button("Ajouter une touche", self.edit_mapping, True)
        add.setObjectName("AddMapping")
        add.setIcon(add_key_icon())
        add.setIconSize(QSize(20, 20))
        heading.addWidget(add)
        root.addLayout(heading)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.viewport().setAutoFillBackground(False)
        self.rows_widget = QWidget()
        self.rows = QVBoxLayout(self.rows_widget)
        self.rows.setContentsMargins(0, 0, 7, 0)
        self.rows.setSpacing(9)
        self.rows.addStretch()
        area.setWidget(self.rows_widget)
        root.addWidget(area, 1)
        common_layout = QHBoxLayout()
        common_layout.setSpacing(12)
        self.numbers = Switch("Inverser chiffres et caractères")
        self.numbers.setToolTip("Sans Maj : 1234567890. Avec Maj : &é\"'(-è_çà.")
        self.numbers.toggled.connect(lambda value: self.change_option("invert_numbers", value))
        self.keyboard = Switch("Clavier virtuel")
        self.keyboard.setToolTip("Afficher l’orbe turquoise pour ouvrir le clavier.")
        self.keyboard.toggled.connect(self.change_keyboard)
        for control, stretch in ((self.numbers, 3), (self.keyboard, 2)):
            tile = card()
            tile.setObjectName("QuickOption")
            tile_layout = QHBoxLayout(tile)
            tile_layout.setContentsMargins(12, 8, 12, 8)
            tile_layout.addWidget(control)
            common_layout.addWidget(tile, stretch)
        root.addLayout(common_layout)
        self.scroll = Switch("Flèches de défilement")
        self.scroll.setToolTip("Rester sur la flèche du haut ou du bas pour faire défiler, sans clic.")
        self.scroll.toggled.connect(self.change_hover_scroll)
        scroll_tile = card()
        scroll_tile.setObjectName("QuickOption")
        scroll_layout = QHBoxLayout(scroll_tile)
        scroll_layout.setContentsMargins(12, 4, 12, 4)
        scroll_layout.addWidget(self.scroll)
        root.addWidget(scroll_tile)
        footer = QHBoxLayout()
        for caption, icon_name, callback in [("Options", "options", self.open_options),
                                             ("Tout réinitialiser", "reset", self.reset_all)]:
            control = button(caption, callback)
            control.setObjectName("Footer")
            control.setIcon(utility_icon(icon_name))
            control.setIconSize(QSize(18, 18))
            footer.addWidget(control)
        footer.addStretch()
        self.pause_button = PauseButton(controller.pause_runtime)
        footer.addWidget(self.pause_button)
        footer.addWidget(label("v" + __version__, "Muted"))
        footer.addWidget(QSizeGrip(self))
        root.addLayout(footer)
        self.setCentralWidget(shell)
        controller.state.connect(self.set_state)
        controller.notice.connect(self.show_notice)
        controller.changed.connect(self.rebuild)
        self.rebuild()
        self.set_state(controller.active)

    @property
    def profile(self):
        return self.controller.settings.profile

    def set_state(self, active):
        self.pause_button.set_active(active)
        self.activation.blockSignals(True)
        self.activation.setChecked(active)
        self.activation.setText("Actif" if active else "En pause")
        self.activation.blockSignals(False)

    def toggle_adaptations(self, enabled):
        if enabled != self.controller.active:
            if enabled:
                self.controller.toggle()
            else:
                self.controller.restore_keyboard()
        self.set_state(self.controller.active)

    def show_notice(self, text):
        # Keep diagnostics available internally, without banners or pop-ups.
        self.last_notice = text

    def rebuild(self):
        while self.rows.count() > 1:
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.heading.setText("Mes touches" if len(self.controller.settings.profiles) == 1 else "Mes touches · " + self.profile.name)
        self.numbers.blockSignals(True)
        self.numbers.setChecked(self.profile.invert_numbers)
        self.numbers.blockSignals(False)
        self.keyboard.blockSignals(True)
        self.keyboard.setChecked(self.controller.settings.virtual_keyboard)
        self.keyboard.blockSignals(False)
        self.scroll.blockSignals(True)
        self.scroll.setChecked(self.controller.settings.hover_scroll)
        self.scroll.blockSignals(False)
        if not self.profile.mappings:
            self.rows.insertWidget(0, label("Aucune touche modifiée.", "Subtitle"))
        for mapping in self.profile.mappings:
            row_card = card()
            row_card.setObjectName("MappingRow")
            row = QHBoxLayout(row_card)
            row.setContentsMargins(13, 11, 13, 11)
            row.setSpacing(10)
            enabled = Switch()
            enabled.setChecked(mapping.enabled)
            enabled.setAccessibleName("Activer le réglage de " + key_name(mapping.source))
            enabled.toggled.connect(lambda checked, m=mapping: self.toggle_mapping(m, checked))
            row.addWidget(enabled)
            source = label(key_name(mapping.source), "Key")
            source.setWordWrap(False)
            source.setMaximumWidth(140)
            row.addWidget(source)
            row.addWidget(label("→", "MappingArrow"))
            row.addWidget(label(action_text(mapping), "ActionText"), 1)
            edit = button("Modifier", lambda checked=False, m=mapping: self.edit_mapping(mapping=m))
            edit.setObjectName("Edit")
            row.addWidget(edit)
            delete = button("", lambda checked=False, vk=mapping.source: self.controller.delete_mapping(vk))
            delete.setObjectName("Delete")
            delete.setIcon(trash_icon())
            delete.setIconSize(QSize(20, 20))
            delete.setFixedSize(40, 40)
            delete.setToolTip("Supprimer cette ligne")
            delete.setAccessibleName("Supprimer la ligne " + key_name(mapping.source))
            row.addWidget(delete)
            self.rows.insertWidget(self.rows.count() - 1, row_card)

    def change_option(self, name, value):
        setattr(self.profile, name, value)
        self.controller.commit()

    def toggle_mapping(self, mapping, enabled):
        mapping.enabled = enabled
        self.controller.commit()

    def change_keyboard(self, enabled):
        self.controller.settings.virtual_keyboard = enabled
        self.controller.commit()

    def change_hover_scroll(self, enabled):
        self.controller.settings.hover_scroll = enabled
        self.controller.commit()

    def change_startup(self, enabled, control=None):
        try:
            set_startup(enabled, self.config_dir)
        except OSError as exc:
            if control:
                control.blockSignals(True)
                control.setChecked(not enabled)
                control.blockSignals(False)
            self.show_notice(str(exc))

    def confirm_reset(self, title, description):
        dialog = BackdropDialog(self)
        dialog.setMinimumWidth(500)
        dialog.setMaximumWidth(620)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)
        layout.addWidget(dialog.header(title))
        layout.addWidget(label(description, "Subtitle"))
        row = QHBoxLayout()
        cancel = button("Annuler", dialog.reject)
        cancel.setDefault(True)
        row.addWidget(cancel)
        confirm = button("Confirmer", dialog.accept)
        confirm.setObjectName("Danger")
        confirm.setAutoDefault(False)
        row.addWidget(confirm)
        layout.addLayout(row)
        result = dialog.exec() == BackdropDialog.Accepted
        dialog.deleteLater()
        return result

    def reset_all(self):
        if self.confirm_reset("Tout réinitialiser", "Remettre toutes les touches et les options à l’origine ?"):
            self.controller.reset_all()

    def open_options(self):
        dialog = OptionsDialog(self)
        dialog.exec()
        dialog.deleteLater()

    def closeEvent(self, event):
        if self.allow_close:
            event.accept()
        elif self.tray_available:
            self.hide()
            event.ignore()
        else:
            event.ignore()
            self.quit_requested.emit()


class OptionsDialog(BackdropDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.host, self.controller = parent, parent.controller
        self.setWindowTitle("Options")
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)
        layout.addWidget(self.header("Options"))
        aids = card()
        aids_layout = QVBoxLayout(aids)
        aids_layout.setContentsMargins(16, 14, 16, 14)
        aids_layout.setSpacing(10)
        aids_layout.addWidget(label("Aides de frappe", "CardTitle"))
        self.checks = []
        for text, name, general in [("Raccourcis une touche après l’autre", "sticky_modifiers", False),
                                    ("Une seule lettre par appui prolongé", "suppress_repeat", False)]:
            checkbox = Switch(text)
            checkbox.toggled.connect(lambda value, n=name, g=general: self.set_option(n, value, g))
            aids_layout.addWidget(checkbox)
            self.checks.append((checkbox, name, general))
        self.delay, self.speed = QComboBox(), QComboBox()
        for text, value in [("Non", 0), ("Faible", 100), ("Moyen", 250), ("Fort", 500)]:
            self.delay.addItem(text, value)
        for text, value in [("Lente", 3), ("Normale", 8), ("Rapide", 16)]:
            self.speed.addItem(text, value)
        for caption, control in [("Filtrer les appuis involontaires", self.delay), ("Vitesse de la souris au clavier", self.speed)]:
            row = QHBoxLayout()
            row.addWidget(label(caption), 1)
            control.setMinimumWidth(130)
            row.addWidget(control)
            aids_layout.addLayout(row)
        self.delay.currentIndexChanged.connect(lambda: self.set_option("debounce_ms", self.delay.currentData()))
        self.speed.currentIndexChanged.connect(lambda: self.set_option("pointer_speed", self.speed.currentData()))
        layout.addWidget(aids)
        startup_card = card()
        startup_layout = QVBoxLayout(startup_card)
        startup_layout.setContentsMargins(16, 12, 16, 12)
        startup_layout.addWidget(label("Au démarrage", "CardTitle"))
        self.startup = Switch("Démarrer avec Windows")
        self.startup.toggled.connect(lambda value: self.host.change_startup(value, self.startup))
        startup_layout.addWidget(self.startup)
        minimized = Switch("Démarrer avec la fenêtre masquée")
        minimized.toggled.connect(lambda value: self.set_option("start_minimized", value, True))
        self.checks.append((minimized, "start_minimized", True))
        startup_layout.addWidget(minimized)
        layout.addWidget(startup_card)
        backups = card()
        backups_layout = QVBoxLayout(backups)
        backups_layout.setContentsMargins(16, 14, 16, 16)
        backups_layout.setSpacing(12)
        backups_layout.addWidget(label("Sauvegardes", "CardTitle"))
        row = QHBoxLayout()
        row.addWidget(button("Sauvegarder mes réglages…", self.host.export_settings), 1)
        row.addWidget(button("Charger une sauvegarde…", self.host.import_settings), 1)
        backups_layout.addLayout(row)
        layout.addWidget(backups)
        row = QHBoxLayout()
        row.addWidget(button("Claviers enregistrés…", self.open_keyboards), 1)
        row.addWidget(button("Dépannage…", self.open_troubleshooting), 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Fermer", self.accept, True))
        layout.addLayout(row)
        self.controller.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        settings = self.controller.settings
        self.startup.blockSignals(True)
        try:
            self.startup.setChecked(startup_enabled())
        except OSError:
            self.startup.setEnabled(False)
        self.startup.blockSignals(False)
        for control, name, general in self.checks:
            control.blockSignals(True)
            control.setChecked(getattr(settings if general else settings.profile, name))
            control.blockSignals(False)
        for control, value in [(self.delay, settings.profile.debounce_ms), (self.speed, settings.profile.pointer_speed)]:
            control.blockSignals(True)
            if control.findData(value) < 0:
                control.addItem("Réglage actuel", value)
            control.setCurrentIndex(control.findData(value))
            control.blockSignals(False)

    def set_option(self, name, value, general=False):
        setattr(self.controller.settings if general else self.controller.settings.profile, name, value)
        self.controller.commit()

    def open_keyboards(self):
        dialog = KeyboardsDialog(self.host, self)
        dialog.exec()
        dialog.deleteLater()

    def open_troubleshooting(self):
        dialog = TroubleshootingDialog(self.host, self)
        dialog.exec()
        dialog.deleteLater()


class KeyboardsDialog(BackdropDialog):
    def __init__(self, host, parent=None):
        super().__init__(parent or host)
        self.host, self.controller = host, host.controller
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        layout.addWidget(self.header("Claviers enregistrés"))
        layout.addWidget(label("Gardez plusieurs réglages, par exemple pour écrire ou jouer.", "Subtitle"))
        layout.addWidget(label("Clavier à utiliser", "CardTitle"))
        self.profiles = QComboBox()
        self.profiles.currentTextChanged.connect(host.switch_profile)
        layout.addWidget(self.profiles)
        for actions in [[("Créer un clavier vide…", host.new_profile),
                         ("Copier ce clavier…", lambda: host.new_profile(host.profile))],
                        [("Changer son nom…", lambda: host.rename_profile(host.profile)),
                         ("Supprimer ce clavier…", self.delete_profile)]]:
            row = QHBoxLayout()
            for text, callback in actions:
                item = button(text, callback)
                row.addWidget(item, 1)
                if text.startswith("Supprimer"):
                    self.delete_button = item
            layout.addLayout(row)
        layout.addWidget(button("Terminé", self.accept, True))
        self.controller.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        settings = self.controller.settings
        self.profiles.blockSignals(True)
        self.profiles.clear()
        self.profiles.addItems([p.name for p in settings.profiles])
        self.profiles.setCurrentText(settings.active_profile)
        self.profiles.blockSignals(False)
        self.delete_button.setEnabled(len(settings.profiles) > 1)

    def delete_profile(self):
        if len(self.controller.settings.profiles) < 2:
            return
        profile = self.controller.settings.profile
        if self.host.confirm_reset("Supprimer ce clavier", "Supprimer les réglages « " + profile.name + " » ?"):
            try:
                self.controller.backup()
            except OSError as exc:
                self.host.show_notice(str(exc))
                return
            self.controller.settings.profiles.remove(profile)
            self.controller.settings.active_profile = self.controller.settings.profiles[0].name
            self.controller.commit()


class TroubleshootingDialog(BackdropDialog):
    def __init__(self, host, parent=None):
        super().__init__(parent or host)
        self.host, self.controller = host, host.controller
        self.setMinimumWidth(530)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        layout.addWidget(self.header("Dépannage"))
        layout.addWidget(label("Si une touche de clic ne répond plus :", "Subtitle"))
        layout.addWidget(button("Relancer les commandes souris", self.controller.repair_service))
        layout.addSpacing(6)
        layout.addWidget(label("Remises à zéro", "CardTitle"))
        layout.addWidget(button("Supprimer les réglages de la souris…", self.reset_mouse))
        layout.addWidget(button("Remettre ce clavier à zéro…", self.reset_profile))
        layout.addSpacing(6)
        layout.addWidget(button("Fermer", self.accept, True))

    def reset_profile(self):
        if self.host.confirm_reset("Remettre ce clavier à zéro", "Retirer toutes les modifications du clavier « " + self.host.profile.name + " » ?"):
            self.controller.reset_profile()

    def reset_mouse(self):
        if self.host.confirm_reset("Supprimer les réglages de la souris", "Retirer les touches de clic, de déplacement et de défilement ? Les autres touches seront conservées."):
            self.controller.reset_mouse()
