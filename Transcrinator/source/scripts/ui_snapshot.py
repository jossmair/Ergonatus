from pathlib import Path
from PySide6.QtWidgets import QApplication
from app.core.controller import Controller
from app.core.settings import Settings
from app.core.device_detector import detect
from app.ui.floating_hub import FloatingHub
from app.ui.main_window import MainWindow
from app.ui.premium import STYLE

application = QApplication([])
application.setStyle("Fusion")
application.setStyleSheet(STYLE)
settings = Settings(progressive=True)
hardware = detect()
controller = Controller(settings, hardware)
window = MainWindow(controller)
window.show()
controller.status.emit("Prêt")
hub = FloatingHub(settings)
hub.set_state("Écoute…")
hub.set_level(.025)
for _ in range(12):
    hub.animate()
hub.set_partial("Bonjour, ceci est un test de dictée en français…")
hub.finish_transition()
application.processEvents()
folder = Path("docs/validation")
folder.mkdir(parents=True, exist_ok=True)
window.grab().save(str(folder / "home-premium.png"))
hub.grab().save(str(folder / "hub-premium.png"))
window.resize(620, 580)
application.processEvents()
window.grab().save(str(folder / "home-small.png"))
controller.retained_changed.emit("Bonjour, voici votre texte conservé si le champ ne permet pas l’insertion.")
window.resize(760, 800)
application.processEvents()
window.grab().save(str(folder / "recovery-premium.png"))
window.hide()
hub.hide()
