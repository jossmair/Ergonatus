"""Render the production tray menu without starting audio or global hotkeys."""
# ruff: noqa: E402 -- prepare the standalone script path/platform before Qt.
# ruff: noqa: E402 -- standalone script bootstrap precedes application imports
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from app.ui.premium import STYLE
from app.ui.retained_action import RetainedTextAction
from app.ui.tray_menu import TrayMenu, menu_icon


class Controller(QObject):
    retained_changed = Signal(str)

    def request(self, command):
        self.command = command


app = QApplication([])
if not QFontDatabase.families():
    for name in ("segoeui.ttf", "segoeuib.ttf"):
        QFontDatabase.addApplicationFont(str(Path(os.environ["SystemRoot"]) / "Fonts" / name))
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
controller = Controller()
menu = TrayMenu()
menu.add_command("Ouvrir Transcrinator", "open", lambda: None)
hub = menu.add_command("Afficher le hub", "hub", lambda: None)
retained = RetainedTextAction(controller, menu)
retained.setIcon(menu_icon("copy"))
retained.setIconVisibleInMenu(True)
menu.addAction(retained)
menu.addSeparator()
menu.add_command("Quitter Transcrinator", "quit", lambda: None)
menu.show()
app.processEvents()
menu.setActiveAction(hub)
destination = root / "docs/validation/tray-menu.png"
assert menu.grab().save(str(destination))
controller.retained_changed.emit("Texte conservé")
assert retained.isEnabled()
retained.trigger()
assert app.clipboard().text() == "Texte conservé"
assert not retained.isEnabled()
assert controller.command == "clear_retained"
assert menu.grab().toImage().pixelColor(0, 0).alpha() == 0
menu.close()
print(f"Menu vérifié : {destination}")
