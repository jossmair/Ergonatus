"""Render the actual Qt Orb widgets, not a mockup."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QWidget, QGridLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer
from shared.ui.components import ErgoOrb
from shared.ui.theme import APP_THEMES, stylesheet

app=QApplication([])
window=QWidget();window.setStyleSheet(stylesheet(True));window.setWindowTitle('Ergonatus · 21 Orbs')
grid=QGridLayout(window);grid.setSpacing(16)
for i,(key,item) in enumerate(APP_THEMES.items()):
    cell=QWidget();column=QVBoxLayout(cell)
    orb=ErgoOrb(key);orb.setFixedSize(64,64);column.addWidget(orb,alignment=Qt.AlignCenter)
    label=QLabel(item['name']);label.setAlignment(Qt.AlignCenter);column.addWidget(label)
    color=QLabel(item['accent']);color.setAlignment(Qt.AlignCenter);column.addWidget(color)
    grid.addWidget(cell,i//7,i%7)
window.resize(1100,480);window.show()
def save():
    target=Path(__file__).resolve().parents[1]/'docs/validation/orbs-gallery.png'
    window.grab().save(str(target));window.close()
QTimer.singleShot(500,save)
app.exec()
