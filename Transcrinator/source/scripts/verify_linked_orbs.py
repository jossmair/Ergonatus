"""Native regression probe, restricted to windows created by this process."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT.parent / "Redactor" / "app"))

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QWidget
import win32gui
from app.core.settings import Settings
from app.ui.floating_hub import FloatingHub
from app.ui.work_area import available_area
from windows.linked_orbs import move_companions

app = QApplication([])
hub = FloatingHub(Settings())
hub.set_state("Prêt")
hub.timer.stop()
area = available_area(app.primaryScreen())
companions = []
base = QPoint(area.right() - 100, area.bottom() - 90)
hub.move(base)
for rank, name in ((1, "Claviernator"), (2, "Précisionator"), (3, "Redactor")):
    widget = QWidget()
    widget.setWindowTitle(name + " · Orbe")
    widget.setFixedSize(36, 36)
    widget.move(base - QPoint(0, rank * 64))
    widget.show()
    companions.append(widget)
app.processEvents()
redactor = companions[-1]
redactor.origin = redactor.pos()
redactor.move(redactor.pos() + QPoint(-50, 180))
app.processEvents()
handles = [int(widget.winId()) for widget in [hub] + companions]
original_enum = win32gui.EnumWindows
try:
    win32gui.EnumWindows = lambda callback, arg: [callback(handle, arg) for handle in handles]
    move_companions(redactor)
    app.processEvents()
    moved = hub.pos()
    assert moved != base, (moved, base)
    assert hub.manual_position is not None, "Native move was not retained by Transcrinator"
    hub.clamp_to_screen()
    assert hub.pos() == moved, (hub.pos(), moved)
    assert hub.geometry().bottom() <= area.bottom() - 16
    assert abs(hub.geometry().center().x() - redactor.geometry().center().x()) <= 1
    print("PASS: linked native drag retained; bottom orb above taskbar; centres aligned")
finally:
    win32gui.EnumWindows = original_enum
    for widget in [hub] + companions:
        widget.close()
