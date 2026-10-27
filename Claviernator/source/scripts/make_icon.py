import os
from pathlib import Path
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PIL import Image
from fortinatus.theme import icon_pixmap

app = QApplication([])
folder = Path(__file__).resolve().parents[1] / "assets"
folder.mkdir(exist_ok=True)
icon_pixmap().save(str(folder / "fortinatus.png"))
with Image.open(folder / "fortinatus.png") as image:
    image.save(folder / "fortinatus.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("Icônes PNG et ICO créées.")

