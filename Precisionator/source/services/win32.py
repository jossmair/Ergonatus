"""Typed, pointer-size-safe Windows desktop APIs. No input injection APIs."""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import sys

from .orb_positioning import Rect


@dataclass(frozen=True)
class Monitor:
    handle: int
    device: str
    bounds: Rect
    work: Rect
    scale: float


class MonitorInfo(C.Structure):
    _fields_ = [("size", W.DWORD), ("monitor", W.RECT), ("work", W.RECT),
                ("flags", W.DWORD), ("device", W.WCHAR * 32)]


def rect(value):
    return Rect(value.left, value.top, value.right - value.left, value.bottom - value.top)


def discover_companions(windows):
    """Recognise legacy/current names and prefer the named orb over tooltips."""
    families = {"fortinatus": ("fortinatus", "claviernator"),
                "transcrinator": ("transcrinator", "transcri")}
    result = []
    for family, prefixes in families.items():
        owners = {pid for _, pid, title, _, _ in windows if title.startswith(prefixes)}
        candidates = []
        for _, pid, title, bounds, visible in windows:
            if not visible or pid not in owners or not (24 <= bounds.w <= 144 and 24 <= bounds.h <= 144):
                continue
            if not .85 <= bounds.w / bounds.h <= 1.18:
                continue
            if any(title.startswith(names) for name, names in families.items() if name != family):
                continue
            score = (4 if title.startswith(prefixes) else 0) + (2 if "orb" in title else 0)
            candidates.append((score, bounds))
        if candidates:
            best = max(score for score, _ in candidates)
            result.extend((family, bounds) for score, bounds in candidates if score == best)
    return result


def discover_companion_obstacles(windows):
    """Visible scroll-arrow windows occupy space, but are never orb anchors."""
    prefixes = ("fortinatus", "claviernator")
    owners = {pid for _, pid, title, _, _ in windows if title.startswith(prefixes)}
    return [bounds for _, pid, title, bounds, visible in windows
            if visible and pid in owners and title.startswith(prefixes)
            and ("défiler" in title or "defiler" in title)
            and 24 <= bounds.w <= 512 and 12 <= bounds.h <= 256]


class Desktop:
    def __init__(self):
        if sys.platform != "win32":
            raise OSError("Précisionator nécessite Windows 10 ou 11.")
        self.user = C.WinDLL("user32", use_last_error=True)
        self.dwm = C.WinDLL("dwmapi", use_last_error=True)
        self.shcore = C.WinDLL("shcore", use_last_error=True)
        self.enum_proc = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        self.monitor_proc = C.WINFUNCTYPE(W.BOOL, W.HANDLE, W.HDC, C.POINTER(W.RECT), W.LPARAM)
        declarations = {
            "GetCursorPos": ([C.POINTER(W.POINT)], W.BOOL),
            "GetWindowRect": ([W.HWND, C.POINTER(W.RECT)], W.BOOL),
            "GetWindowTextW": ([W.HWND, W.LPWSTR, C.c_int], C.c_int),
            "GetWindowThreadProcessId": ([W.HWND, C.POINTER(W.DWORD)], W.DWORD),
            "IsWindowVisible": ([W.HWND], W.BOOL),
            "EnumWindows": ([self.enum_proc, W.LPARAM], W.BOOL),
            "EnumDisplayMonitors": ([W.HDC, C.POINTER(W.RECT), self.monitor_proc, W.LPARAM], W.BOOL),
            "GetMonitorInfoW": ([W.HANDLE, C.POINTER(MonitorInfo)], W.BOOL),
            "SetWindowDisplayAffinity": ([W.HWND, W.DWORD], W.BOOL),
            "GetWindowDisplayAffinity": ([W.HWND, C.POINTER(W.DWORD)], W.BOOL),
            "SetWindowPos": ([W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT], W.BOOL),
            "GetWindowLongPtrW": ([W.HWND, C.c_int], C.c_ssize_t),
            "SetWindowLongPtrW": ([W.HWND, C.c_int, C.c_ssize_t], C.c_ssize_t),
        }
        for name, (args, result) in declarations.items():
            function = getattr(self.user, name)
            function.argtypes, function.restype = args, result
        self.shcore.GetDpiForMonitor.argtypes = [W.HANDLE, C.c_int, C.POINTER(W.UINT), C.POINTER(W.UINT)]
        self.shcore.GetDpiForMonitor.restype = C.c_long
        self.dwm.DwmIsCompositionEnabled.argtypes = [C.POINTER(W.BOOL)]
        self.dwm.DwmFlush.argtypes = []

    def pointer(self):
        point = W.POINT()
        if not self.user.GetCursorPos(C.byref(point)):
            raise C.WinError(C.get_last_error())
        return point.x, point.y

    def monitors(self):
        found = []
        def collect(handle, hdc, bounds, data):
            info = MonitorInfo()
            info.size = C.sizeof(info)
            if self.user.GetMonitorInfoW(handle, C.byref(info)):
                dx, dy = W.UINT(96), W.UINT(96)
                self.shcore.GetDpiForMonitor(handle, 0, C.byref(dx), C.byref(dy))
                found.append(Monitor(int(handle), info.device, rect(info.monitor), rect(info.work), dx.value / 96))
            return True
        if not self.user.EnumDisplayMonitors(None, None, self.monitor_proc(collect), 0):
            raise C.WinError(C.get_last_error())
        return found

    def window_rect(self, hwnd):
        value = W.RECT()
        if not self.user.GetWindowRect(hwnd, C.byref(value)):
            raise C.WinError(C.get_last_error())
        return rect(value)

    def exclude(self, hwnd, enabled=True):
        composed = W.BOOL()
        if sys.getwindowsversion().build < 19041 or self.dwm.DwmIsCompositionEnabled(C.byref(composed)) != 0 or not composed.value:
            return False
        wanted = 0x11 if enabled else 0
        affinity = W.DWORD()
        return bool(self.user.SetWindowDisplayAffinity(hwnd, wanted) and self.user.GetWindowDisplayAffinity(hwnd, C.byref(affinity)) and affinity.value == wanted)

    def protect_overlay(self, hwnd):
        # WS_EX_TRANSPARENT + LAYERED passes mouse hit-testing across threads;
        # NOACTIVATE keeps the focused target (and Fortinatus) undisturbed.
        extended = self.user.GetWindowLongPtrW(hwnd, -20)
        wanted = extended | 0x20 | 0x80000 | 0x8000000 | 0x80
        self.user.SetWindowLongPtrW(hwnd, -20, wanted)
        actual = self.user.GetWindowLongPtrW(hwnd, -20)
        if actual & wanted != wanted:
            raise OSError("Windows a refusé la transparence aux entrées.")
        if not self.exclude(hwnd):
            raise OSError("L’exclusion de capture n’est pas disponible. Loupe désactivée.")

    def windows(self):
        found = []
        def collect(hwnd, unused):
            title, pid, bounds = C.create_unicode_buffer(512), W.DWORD(), W.RECT()
            self.user.GetWindowTextW(hwnd, title, len(title))
            self.user.GetWindowThreadProcessId(hwnd, C.byref(pid))
            if self.user.GetWindowRect(hwnd, C.byref(bounds)):
                found.append((int(hwnd), pid.value, title.value.casefold(), rect(bounds), bool(self.user.IsWindowVisible(hwnd))))
            return True
        self.user.EnumWindows(self.enum_proc(collect), 0)
        return found

    def companions(self):
        return discover_companions(self.windows())

    def family_layout(self):
        windows = self.windows()
        return discover_companions(windows), discover_companion_obstacles(windows)


def enable_dpi():
    if sys.platform == "win32":
        user = C.WinDLL("user32", use_last_error=True)
        user.SetProcessDpiAwarenessContext.argtypes = [C.c_void_p]
        user.SetProcessDpiAwarenessContext(C.c_void_p(-4))


def physical_to_logical(point, monitor, screen):
    origin = screen.geometry().topLeft()
    scale = screen.devicePixelRatio()
    return (origin.x() + round((point[0] - monitor.bounds.x) / scale),
            origin.y() + round((point[1] - monitor.bounds.y) / scale))
