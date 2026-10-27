"""Generate the app icon with the family's Qt sprite and vector icon system."""
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from PIL import Image
from ui.orb import draw_orb

app = QApplication.instance() or QApplication([])
pixmap = QPixmap(256, 256)
pixmap.fill(Qt.transparent)
painter = QPainter(pixmap)
painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
draw_orb(painter, QRectF(0, 0, 256, 256))
painter.end()
pixmap.save(str(ROOT / "assets/precisionator.png"))
with Image.open(ROOT / "assets/precisionator.png") as icon:
    icon.save(ROOT / "assets/precisionator.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("Icônes Précisionator générées à partir des composants de la famille.")
