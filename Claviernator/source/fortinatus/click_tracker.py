"""Observe mouse presses, including accessible remapped clicks, without consuming them."""
import ctypes
from ctypes import wintypes
import threading

from PySide6.QtCore import QObject, Signal


class MouseData(ctypes.Structure):
    _fields_ = [("point", wintypes.POINT), ("data", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class ClickTracker(QObject):
    clicked = Signal(object)

    def __init__(self, desktop, parent=None):
        super().__init__(parent)
        self.desktop = desktop
        self.thread = None
        self.thread_id = 0
        self.ready = threading.Event()
        self.error = None

    def start(self):
        self.thread = threading.Thread(target=self.run, name="claviernator-click-target", daemon=True)
        self.thread.start()
        if not self.ready.wait(3):
            raise RuntimeError("Le suivi du clic ne répond pas.")
        if self.error:
            raise RuntimeError(str(self.error))

    def run(self):
        hook = None
        user = ctypes.WinDLL("user32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        procedure_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        user.SetWindowsHookExW.argtypes = [ctypes.c_int, procedure_type, wintypes.HINSTANCE, wintypes.DWORD]
        user.SetWindowsHookExW.restype = wintypes.HANDLE
        user.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user.CallNextHookEx.restype = ctypes.c_ssize_t
        user.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
        user.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user.GetMessageW.restype = ctypes.c_int
        user.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                     wintypes.UINT, wintypes.UINT, wintypes.UINT]
        kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel.GetModuleHandleW.restype = wintypes.HMODULE
        kernel.GetCurrentThreadId.restype = wintypes.DWORD

        def observe(code, message, address):
            if code >= 0 and message in (0x201, 0x204, 0x207, 0x20B):
                try:
                    point = ctypes.cast(address, ctypes.POINTER(MouseData)).contents.point
                    target = self.desktop.capture_scroll(point.x, point.y)
                    if target:
                        self.clicked.emit(target)
                except Exception:
                    # Observation must never interfere with the original click.
                    pass
            return user.CallNextHookEx(None, code, message, address)

        procedure = procedure_type(observe)
        try:
            self.thread_id = kernel.GetCurrentThreadId()
            hook = user.SetWindowsHookExW(14, procedure, kernel.GetModuleHandleW(None), 0)
            if not hook:
                raise ctypes.WinError(ctypes.get_last_error())
            message = wintypes.MSG()
            user.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
            self.ready.set()
            while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                pass
        except Exception as exc:
            self.error = exc
        finally:
            self.ready.set()
            if hook:
                user.UnhookWindowsHookEx(hook)

    def stop(self):
        if self.thread and self.thread.is_alive():
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user.PostThreadMessageW(self.thread_id, 0x12, 0, 0)  # WM_QUIT
            self.thread.join(3)
