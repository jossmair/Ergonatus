from pathlib import Path
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PIL import Image

application = QGuiApplication([])
image = QImage(256, 256, QImage.Format_ARGB32)
image.fill(0)
painter = QPainter(image)
QSvgRenderer("assets/transcri.svg").render(painter)
painter.end()
Path("assets").mkdir(exist_ok=True)
image.save("assets/transcri.png")
Image.open("assets/transcri.png").save(
    "assets/transcri.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
)
