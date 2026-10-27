"""Read Windows' usable monitor bounds in Qt logical coordinates."""
import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication


def logical_work_area(origin, scale, monitor, work):
    left, top, right, bottom = work
    x, y = monitor[:2]
    return QRect(origin.x() + round((left - x) / scale),
                 origin.y() + round((top - y) / scale),
                 round((right - left) / scale), round((bottom - top) / scale))


def available_area(screen):
    fallback = screen.availableGeometry()
    if sys.platform != "win32" or QGuiApplication.platformName() == "offscreen":
        return fallback
    class MonitorInfo(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                    ("work", wintypes.RECT), ("flags", wintypes.DWORD)]
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user.MonitorFromPoint.restype = wintypes.HANDLE
    user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user.GetMonitorInfoW.restype = wintypes.BOOL
    origin = screen.geometry().topLeft()
    # Qt retains native monitor origins, including on mixed-DPI desktops.
    handle = user.MonitorFromPoint(wintypes.POINT(origin.x() + 1, origin.y() + 1), 2)
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    if not user.GetMonitorInfoW(handle, ctypes.byref(info)):
        return fallback
    rect = lambda r: (r.left, r.top, r.right, r.bottom)
    native = logical_work_area(origin, screen.devicePixelRatio(), rect(info.monitor), rect(info.work))
    # Retain any additional reservation known to Qt.
    area = fallback.intersected(native)
    return area if not area.isEmpty() else native
