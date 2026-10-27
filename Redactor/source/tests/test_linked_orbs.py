import sys
from types import SimpleNamespace

from PySide6.QtCore import QPoint, QRect
from app.windows import linked_orbs
from app.windows.work_area import logical_work_area


def test_companion_monitor_with_friendly_qt_name(monkeypatch):
    from app.windows import suite
    screen = SimpleNamespace(name=lambda: "VC279", geometry=lambda: QRect(-2560, 0, 1707, 960),
                             devicePixelRatio=lambda: 1.5)
    monkeypatch.setattr(suite.QApplication, "screens", lambda: [screen])
    monkeypatch.setitem(sys.modules, "win32api", SimpleNamespace(
        MonitorFromWindow=lambda *args: 1,
        GetMonitorInfo=lambda h: {"Device": "DISPLAY2", "Monitor": (-2560, 0, 0, 1440)}))
    monkeypatch.setitem(sys.modules, "win32gui", SimpleNamespace(
        IsWindowVisible=lambda h: True, GetWindowText=lambda h: "Transcrinator · Orbe",
        GetWindowRect=lambda h: (-100, 1300, -46, 1354),
        EnumWindows=lambda callback, arg: callback(1, arg)))
    companions, obstacles = suite.companion_layout()
    assert companions == [("transcrinator", (-920, 867, 36, 36), screen)]
    assert obstacles == []


def test_work_area_preserves_taskbar_reservation_at_mixed_dpi():
    area = logical_work_area(QPoint(-2560, 0), 1.5,
                             (-2560, 0, 0, 1440), (-2560, 0, 0, 1380))
    assert area == QRect(-2560, 0, 1707, 920)


def test_drag_moves_pile_and_keeps_lowest_orb_above_taskbar(monkeypatch):
    bounds = {1: (900, 700, 936, 736), 2: (900, 900, 936, 936),
              3: (900, 836, 936, 872), 4: (0, 0, 600, 400)}
    titles = {1: "Redactor · Orbe", 2: "Transcrinator · Orbe",
              3: "Claviernator · Orbe du clavier", 4: "Transcrinator"}
    moved = []
    gui = SimpleNamespace(IsWindowVisible=lambda h: True,
                          GetWindowText=lambda h: titles[h],
                          GetWindowRect=lambda h: bounds[h],
                          EnumWindows=lambda cb, arg: [cb(h, arg) for h in bounds],
                          SetWindowPos=lambda h, z, x, y, w, ht, flags: moved.append((h, x, y)))
    monkeypatch.setitem(sys.modules, "win32gui", gui)
    monkeypatch.setitem(sys.modules, "win32api", SimpleNamespace(
        MonitorFromWindow=lambda *args: 1, GetMonitorInfo=lambda h: {"Work": (0, 0, 1000, 950)}))
    monkeypatch.setitem(sys.modules, "win32con", SimpleNamespace(SWP_NOSIZE=1, SWP_NOACTIVATE=2, SWP_NOZORDER=4))
    screen = SimpleNamespace(devicePixelRatio=lambda: 1)
    monkeypatch.setattr(linked_orbs.QApplication, "screenAt", lambda p: screen)
    own_moves = []
    orb = SimpleNamespace(origin=QPoint(900, 600), pos=lambda: QPoint(900, 700),
                          geometry=lambda: QRect(900, 700, 36, 36), winId=lambda: 1,
                          move=own_moves.append)
    linked_orbs.move_companions(orb)
    assert moved == [(2, 900, 898), (3, 900, 834)]
    assert moved[0][2] + 36 == 950 - 16
    assert own_moves == [QPoint(900, 598)]
