"""Render every keyboard page with no system input or foreground change."""
import os
from pathlib import Path
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtCore import QRect, QRectF
from PySide6.QtWidgets import QApplication, QPushButton
from fortinatus.config import Settings
from fortinatus.controller import Controller
from fortinatus.desktop_target import EditingTarget
from fortinatus.keyboard_orb import VirtualKeyboardManager, scroll_arrow_positions
from fortinatus.theme import configure_app

app = QApplication([])
configure_app(app)
root = Path(__file__).resolve().parents[1]
folder = root / "docs/validation"
controller = Controller(Settings(), root / "docs/test-settings/keyboard-preview/settings.json", no_hooks=True)
controller.active = True
manager = VirtualKeyboardManager(controller)
window = manager.panel
window.resize(900, 320)
window.set_target(EditingTarget(0, 0, 0, "Mon document"))
window.append_text("Bonjour, ça va ? ✨")
window.show()
app.processEvents()
print("Dimensions :", window.width(), window.height())
window.grab().save(str(folder / "clavier-virtuel.png"))
window.stack.setCurrentIndex(1)
app.processEvents()
window.grab().save(str(folder / "clavier-accents.png"))
window.characters_stack.setCurrentIndex(1)
app.processEvents()
window.grab().save(str(folder / "clavier-symboles.png"))
window.characters_stack.setCurrentIndex(3)
app.processEvents()
window.grab().save(str(folder / "clavier-unicode.png"))
window.stack.setCurrentIndex(2)
app.processEvents()
window.grab().save(str(folder / "clavier-touches.png"))
for caption, filename in [("F1–F24", "clavier-fonctions.png"), ("Pavé numérique", "clavier-pave-numerique.png"),
                          ("Média", "clavier-media.png")]:
    next(item for item in window.stack.widget(2).findChildren(QPushButton) if item.text() == caption).click()
    app.processEvents()
    window.grab().save(str(folder / filename))
manager.orb.grab().save(str(folder / "orbe-clavier.png"))
animation = QImage(240, 84, QImage.Format_ARGB32)
animation.fill(QColor("#0b1c21"))
frames = []
painter = QPainter(animation)
for index, phase in enumerate((0., 1., 2., 3.)):
    manager.orb.phase = phase
    frame = manager.orb.grab()
    frames.append(frame.toImage())
    painter.drawPixmap(index * 60 + 12, 24, frame)
painter.end()
assert all(frames[0] != frame for frame in frames[1:]), "L’orbe doit changer avec l’animation."
animation.save(str(folder / "orbe-animation.png"))
manager.orb.phase = 0.
image = QImage(120, 150, QImage.Format_ARGB32)
image.fill(QColor("#0b1c21"))
painter = QPainter(image)
painter.drawPixmap(42, 16, manager.orb.grab())
yellow = QPixmap(str(root.parent / "Transcri/assets/hud-orange/core-hub-v1.png"))
painter.drawPixmap(QRectF(42, 78, 36, 36), yellow, QRectF(yellow.rect()))
painter.end()
image.save(str(folder / "orbes-turquoise-et-jaune.png"))
dock = QImage(240, 154, QImage.Format_ARGB32)
dock.fill(QColor("#0b1c21"))
painter = QPainter(dock)
for index in range(2):
    x = 42 + index * 120
    for arrow in manager.arrows:
        arrow.hovered = index == 1 and arrow.direction < 0
        if arrow.hovered:
            arrow.elapsed.start()
            arrow.phase = 1.
    up, down = scroll_arrow_positions(QRect(x, 42, 36, 36))
    painter.drawPixmap(up, manager.arrows[0].grab())
    painter.drawPixmap(x, 42, manager.orb.grab())
    painter.drawPixmap(down, manager.arrows[1].grab())
    painter.drawPixmap(QRectF(x, 106, 36, 36), yellow, QRectF(yellow.rect()))
painter.end()
dock.save(str(folder / "orbe-fleches.png"))
manager.stop()
print("12 captures du clavier enregistrées, animation contrôlée sur quatre phases.")
