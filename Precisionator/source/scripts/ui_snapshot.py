"""Repeatable offscreen visual checks; no changes to Windows preferences."""
import os
from pathlib import Path
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QApplication
from services.configuration import Preferences
from ui.settings_window import SettingsWindow
from ui.orb import Orb, draw_orb
from ui.theme import configure_app
app = QApplication([])
configure_app(app)
folder = ROOT / "docs/validation"
folder.mkdir(exist_ok=True)
window = SettingsWindow(Preferences(), mouse_speed=10)
window.show()
app.processEvents()
window.grab().save(str(folder / "parametres.png"))
window.refresh(Preferences(enabled=False))
app.processEvents()
window.grab().save(str(folder / "desactive.png"))
orb = Orb()
orb.show()
app.processEvents()
orb.grab().save(str(folder / "orbe.png"))
orb.grab().save(str(folder / "orbe-active.png"))
orb.enabled = False
app.processEvents()
orb.grab().save(str(folder / "orbe-desactive.png"))

preview = QPixmap(480, 384)
preview.fill(QColor("#101d20"))
p = QPainter(preview)
p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
for row, background in enumerate(("#101d20", "#ffffff")):
    y = row * 192
    p.fillRect(QRectF(0, y, 480, 192), QColor(background))
    for index, (enabled, title) in enumerate(((False, "Désactivé"), (True, "Activé"))):
        x = index * 240
        p.setPen(QColor("#e4f4f1" if row == 0 else "#352b44"))
        p.drawText(QRectF(x, y + 10, 240, 24), Qt.AlignCenter, title)
        draw_orb(p, QRectF(x + 66, y + 36, 108, 108), enabled)
        draw_orb(p, QRectF(x + 102, y + 151, 36, 36), enabled)
p.end()
preview.save(str(folder / "orbes-etats.png"))
window.hide()
orb.hide()
print("Captures Qt enregistrées.")
