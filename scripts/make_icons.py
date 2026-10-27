"""Convert the generated Orb artwork into Windows ICO resources."""
from pathlib import Path
from PySide6.QtGui import QImage
from PySide6.QtCore import Qt
root=Path(__file__).resolve().parents[1]
for path in (root/'assets/orbs').glob('*.png'):
    image=QImage(str(path)).scaled(256,256,Qt.KeepAspectRatio,Qt.SmoothTransformation)
    if image.isNull() or not image.save(str(path.with_suffix('.ico')),'ICO'):raise RuntimeError('Icône non créée : '+path.name)
print('Icônes Windows mises à jour depuis les images générées.')
