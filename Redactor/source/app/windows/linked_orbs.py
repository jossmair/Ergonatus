"""Move visible companion orbs after an explicit drag of Redactor."""
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication


def move_companions(orb):
    import win32api
    import win32con
    import win32gui

    origin = orb.origin
    if origin is None:
        return
    screen = QApplication.screenAt(orb.geometry().center()) or QApplication.primaryScreen()
    scale = screen.devicePixelRatio()
    delta = orb.pos() - origin
    dx, dy = round(delta.x() * scale), round(delta.y() * scale)
    windows = []

    def collect(hwnd, unused):
        if not win32gui.IsWindowVisible(hwnd) or hwnd == int(orb.winId()):
            return
        title = win32gui.GetWindowText(hwnd).casefold()
        if not title.startswith(("transcrinator", "transcri", "claviernator", "fortinatus", "precisionator", "précisionator")):
            return
        if not any(word in title for word in ("orb", "orbe", "défiler", "defiler")):
            return
        rect = win32gui.GetWindowRect(hwnd)
        if 0 < rect[2] - rect[0] <= 180 and 0 < rect[3] - rect[1] <= 180:
            windows.append((hwnd, rect))

    win32gui.EnumWindows(collect, None)
    if not windows:
        return
    own = win32gui.GetWindowRect(int(orb.winId()))
    proposed = [(l + dx, t + dy, r + dx, b + dy) for _, (l, t, r, b) in windows] + [own]
    left, top = min(r[0] for r in proposed), min(r[1] for r in proposed)
    right, bottom = max(r[2] for r in proposed), max(r[3] for r in proposed)
    work = win32api.GetMonitorInfo(win32api.MonitorFromWindow(int(orb.winId()), 2))["Work"]
    margin = round(16 * scale)
    adjust_x = max(work[0] - left, min(0, work[2] - right))
    adjust_y = max(work[1] - top, min(0, work[3] - margin - bottom))
    flags = win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER
    for hwnd, (l, t, _, _) in windows:
        win32gui.SetWindowPos(hwnd, 0, l + dx + adjust_x, t + dy + adjust_y, 0, 0, flags)
    if adjust_x or adjust_y:
        orb.move(orb.pos() + QPoint(round(adjust_x / scale), round(adjust_y / scale)))
