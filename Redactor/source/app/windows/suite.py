"""Observe companion windows; never move or modify another application."""
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication
from app import theme
from .work_area import available_area


def choose_position(area, companions=(), obstacles=()):
    """Fourth slot above third/second/first. All inputs in logical Qt pixels."""
    size, gap = theme.ORB_SIZE, theme.ORB_GAP
    rank = {"transcrinator": 0, "claviernator": 1, "precisionator": 2}
    if companions:
        family, (x, y, w, h) = max(companions, key=lambda item: rank[item[0]])
        x += (w - size) // 2
        y -= (3 - rank[family]) * (size + gap)
        same_column = [r for r in obstacles if r[0] < x + size + gap and x - gap < r[0] + r[2]]
        if same_column:
            y = min(y, min(r[1] for r in same_column) - size - gap)
    else:
        x = area.right() - size - 15
        y = area.bottom() - size - 15 - 3 * (size + gap)
    x = max(area.left(), min(x, area.right() - size + 1))
    y = max(area.top(), min(y, area.bottom() - size + 1))
    # If the pile meets the top edge, choose an adjacent free column.
    occupied = [r for _, r in companions] + list(obstacles)
    def overlaps(px, py):
        return any(px < rx + rw + 3 and rx - 3 < px + size and py < ry + rh + 3 and ry - 3 < py + size
                   for rx, ry, rw, rh in occupied)
    if overlaps(x, y):
        for candidate in (x - size - gap, x + size + gap):
            if area.left() <= candidate <= area.right() - size and not overlaps(candidate, y):
                return QPoint(candidate, y)
        for py in range(area.top(), area.bottom() - size, size + gap):
            if not overlaps(x, py):
                return QPoint(x, py)
    return QPoint(x, y)


def companion_layout():
    import win32api
    import win32gui
    found, obstacles = [], []
    def collect(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).casefold()
        family = next((f for names, f in ((("transcrinator", "transcri"), "transcrinator"),
                    (("claviernator", "fortinatus"), "claviernator"),
                    (("précisionator", "precisionator"), "precisionator")) if title.startswith(names)), None)
        if not family:
            return
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        is_obstacle = family == "claviernator" and ("défiler" in title or "defiler" in title)
        if not is_obstacle and not (24 <= width <= 144 and 24 <= height <= 144 and .85 <= width / height <= 1.18):
            return
        monitor = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd, 2))
        native_x, native_y = monitor["Monitor"][:2]
        screens = QApplication.screens()
        screen = (next((s for s in screens if s.name().casefold() == monitor["Device"].casefold()), None)
                  or next((s for s in screens if s.geometry().topLeft() == QPoint(native_x, native_y)), None))
        if screen is None:
            return
        scale = screen.devicePixelRatio()
        point = screen.geometry().topLeft()
        rect = (point.x() + round((left - native_x) / scale), point.y() + round((top - native_y) / scale),
                round(width / scale), round(height / scale))
        if is_obstacle:
            obstacles.append((rect, screen))
        elif "orb" in title or "orbe" in title:
            found.append((family, rect, screen))
    win32gui.EnumWindows(collect, None)
    return found, obstacles


def position_orb(orb, config):
    from .ergonatus_layout import managed_position
    managed = managed_position(orb, "redactor")
    if managed is not None and getattr(orb, "start", None) is None:
        orb.move(managed)
        return
    if getattr(orb, "start", None) is not None:
        return
    if not config.follow_suite:
        point = QPoint(config.orb_x or 0, config.orb_y or 0)
        screen = QApplication.screenAt(point) or QApplication.primaryScreen()
        area = available_area(screen)
        orb.move(max(area.left(), min(point.x(), area.right() - orb.width() + 1)),
                 max(area.top(), min(point.y(), area.bottom() - orb.height() + 1)))
        return
    try:
        companions, obstacles = companion_layout()
    except (ImportError, OSError):
        companions, obstacles = [], []
    anchor = next((r for r in companions if r[0] == "precisionator"), None) or next(iter(companions), None)
    screen = anchor[2] if anchor else QApplication.primaryScreen()
    group = [(name, rect) for name, rect, s in companions if s == screen]
    orb.move(choose_position(available_area(screen), group, [r for r, s in obstacles if s == screen]))
