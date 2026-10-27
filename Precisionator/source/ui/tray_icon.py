"""The same three-command tray convention as the companion programs."""
from PySide6.QtWidgets import QSystemTrayIcon
from .theme import app_icon
from .tray_menu import TrayMenu


class TrayIcon(QSystemTrayIcon):
    def __init__(self, opened, toggled, quit_app):
        super().__init__(app_icon())
        self.setToolTip("Précisionator · Loupe intelligente")
        self.menu = TrayMenu()
        self.menu.add_command("Ouvrir Précisionator", "open", opened)
        self.activation = self.menu.add_command("Désactiver", "pause", toggled)
        self.menu.addSeparator()
        self.menu.add_command("Quitter", "quit", quit_app)
        self.setContextMenu(self.menu)
        self.activated.connect(lambda reason: opened() if reason == self.ActivationReason.Trigger else None)

    def refresh(self, enabled):
        self.activation.setText("Désactiver" if enabled else "Activer")
