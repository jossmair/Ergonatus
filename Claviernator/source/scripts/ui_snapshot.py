"""Render the simplified UI without installing a keyboard hook."""
import os
from pathlib import Path
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication
from fortinatus.config import Mapping, Settings
from fortinatus.controller import Controller
from fortinatus.dialog import MappingDialog
from fortinatus.theme import configure_app
from fortinatus.tray_menu import TrayMenu
from fortinatus.ui import KeyboardsDialog, MainWindow, OptionsDialog, TroubleshootingDialog

app = QApplication([])
configure_app(app)
root = Path(__file__).resolve().parents[1]
folder = root / "docs/validation"
folder.mkdir(parents=True, exist_ok=True)
settings = Settings()
settings.profile.mappings = [Mapping(0xA2, "mouse_hold"), Mapping(0xA3, "mouse_toggle"),
                             Mapping(0x70, "sequence", sequence=[[0xA2, 65], [9], [13]])]
controller = Controller(settings, root / "docs/test-settings/ui/settings.json", no_hooks=True)
controller.active = True
window = MainWindow(controller)
window.resize(680, 550)
window.show()
app.processEvents()
window.grab().save(str(folder / "simple.png"))
window.resize(600, 480)
app.processEvents()
window.grab().save(str(folder / "simple-compact.png"))
options = OptionsDialog(window)
options.show()
app.processEvents()
options.grab().save(str(folder / "options-simples.png"))
options.close()
for cls, filename in [(KeyboardsDialog, "claviers-enregistres.png"),
                      (TroubleshootingDialog, "depannage.png")]:
    extra = cls(window)
    extra.show()
    app.processEvents()
    assert extra.windowFlags() & Qt.FramelessWindowHint
    assert extra.grab().toImage().pixelColor(0, 0).alpha() == 0
    extra.grab().save(str(folder / filename))
    extra.close()

window.set_state(False)
app.processEvents()
window.grab().save(str(folder / "en-pause.png"))
window.set_state(True)

def save_modal(filename):
    modal = app.activeModalWidget()
    assert modal is not None
    assert modal.windowFlags() & Qt.FramelessWindowHint
    modal.grab().save(str(folder / filename))
    modal.reject()

QTimer.singleShot(40, lambda: save_modal("nom-clavier.png"))
window.ask_name("Créer un clavier", "Nouveau clavier")
QTimer.singleShot(40, lambda: save_modal("confirmation.png"))
window.confirm_reset("Tout réinitialiser", "Remettre toutes les touches et les options à l’origine ?")
dialog = MappingDialog(window, mapping=settings.profile.mappings[0])
dialog.show()
app.processEvents()
dialog.grab().save(str(folder / "touche-simple.png"))
dialog.kind.showPopup()
app.processEvents()
dialog.kind.view().window().grab().save(str(folder / "actions-clics.png"))
dialog.kind.hidePopup()
dialog.close()
sequence = MappingDialog(window, mapping=settings.profile.mappings[-1])
sequence.show()
app.processEvents()
sequence.grab().save(str(folder / "suite-de-touches.png"))
sequence.close()
menu = TrayMenu()
menu.add_command("Ouvrir Claviernator", "open", lambda: None)
pause = menu.add_command("Mettre en pause", "pause", lambda: None)
menu.addSeparator()
menu.add_command("Quitter Claviernator", "quit", lambda: None)
menu.show()
menu.setActiveAction(pause)
app.processEvents()
assert menu.grab().toImage().pixelColor(0, 0).alpha() == 0
menu.grab().save(str(folder / "menu-clic-droit.png"))
menu.close()
window.allow_close = True
window.close()
print("12 captures enregistrées.")
