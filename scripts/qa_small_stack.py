from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel
from PySide6.QtCore import Qt,QTimer
from shared.ui.components import ErgoOrb
from shared.ui.theme import stylesheet,APP_THEMES
app=QApplication([]);window=QWidget();window.setStyleSheet(stylesheet(True));layout=QVBoxLayout(window)
layout.addWidget(QLabel('Orbs sélectionnées · 36 px'));layout.setSpacing(10)
for key in ['lector','calculinator','corrector']:
    row=QHBoxLayout();orb=ErgoOrb(key);orb.setFixedSize(36,36);orb.setFocusPolicy(Qt.NoFocus);row.addWidget(orb);row.addWidget(QLabel(APP_THEMES[key]['name']),1);layout.addLayout(row)
window.resize(260,200);window.show()
def save():window.grab().save(str(Path(__file__).resolve().parents[1]/'docs/validation/orbs-stack-36.png'));window.close()
QTimer.singleShot(600,save);app.exec()
