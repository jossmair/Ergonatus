"""Preserve an external editing target while non-activating tools are clicked."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os

from PySide6.QtCore import QMimeData, QObject, QTimer
from PySide6.QtWidgets import QApplication

from .windows import WindowsInput


class TargetError(RuntimeError):
    pass


@dataclass(frozen=True)
class EditingTarget:
    window: int
    focus: int
    process: int
    title: str


@dataclass(frozen=True)
class ScrollTarget:
    window: int
    recipient: int
    process: int
    x: int
    y: int


class GUIInfo(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("active", wintypes.HWND), ("focus", wintypes.HWND),
                ("capture", wintypes.HWND), ("menu", wintypes.HWND),
                ("move", wintypes.HWND), ("caret", wintypes.HWND), ("rect", wintypes.RECT)]


class DesktopTarget:
    def __init__(self):
        self.adapter = WindowsInput()
        self.user = self.adapter.user
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, args, result in [
            ("GetForegroundWindow", [], wintypes.HWND),
            ("GetWindowThreadProcessId", [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            ("GetGUIThreadInfo", [wintypes.DWORD, ctypes.POINTER(GUIInfo)], wintypes.BOOL),
            ("GetWindowTextW", [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            ("GetClassNameW", [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            ("GetWindowLongPtrW", [wintypes.HWND, ctypes.c_int], ctypes.c_ssize_t),
            ("IsWindow", [wintypes.HWND], wintypes.BOOL),
            ("IsWindowEnabled", [wintypes.HWND], wintypes.BOOL),
            ("GetAncestor", [wintypes.HWND, wintypes.UINT], wintypes.HWND),
            ("SetForegroundWindow", [wintypes.HWND], wintypes.BOOL),
            ("SetFocus", [wintypes.HWND], wintypes.HWND),
            ("AttachThreadInput", [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL], wintypes.BOOL),
            ("GetAsyncKeyState", [ctypes.c_int], wintypes.SHORT),
            ("GetClipboardSequenceNumber", [], wintypes.DWORD),
            ("GetCursorPos", [ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            ("WindowFromPoint", [wintypes.POINT], wintypes.HWND),
            ("GetClientRect", [wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            ("ClientToScreen", [wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            ("PostMessageW", [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
        ]:
            function = getattr(self.user, name)
            function.argtypes, function.restype = args, result
        self.kernel.GetCurrentThreadId.restype = wintypes.DWORD

    def process(self, hwnd):
        value = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(value))
        return value.value

    def focused(self, window):
        info = GUIInfo()
        info.size = ctypes.sizeof(info)
        thread = self.user.GetWindowThreadProcessId(window, None)
        return int(info.focus or window) if self.user.GetGUIThreadInfo(thread, ctypes.byref(info)) else int(window)

    def capture(self):
        window = int(self.user.GetForegroundWindow() or 0)
        if not window or self.process(window) == os.getpid() or not self.user.IsWindowEnabled(window):
            return None
        focus = self.focused(window)
        if not self.user.IsWindowEnabled(focus):
            return None
        title = ctypes.create_unicode_buffer(256)
        self.user.GetWindowTextW(window, title, 256)
        return EditingTarget(window, focus, self.process(window), title.value or "Votre document")

    def capture_scroll(self, x, y):
        """Remember the exact pane clicked, independently of keyboard focus."""
        recipient = int(self.user.WindowFromPoint(wintypes.POINT(x, y)) or 0)
        window = int(self.user.GetAncestor(recipient, 2) or 0) if recipient else 0
        if not window:
            return None
        process = self.process(window)
        if process == os.getpid() or not self.user.IsWindowEnabled(recipient):
            return None
        name = ctypes.create_unicode_buffer(128)
        self.user.GetClassNameW(window, name, len(name))
        if name.value in {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                          "#32768", "tooltips_class32"}:
            return None
        # Ignore floating helpers such as Transcrinator's non-activating orb.
        if self.user.GetWindowLongPtrW(window, -20) & 0x08000000:
            return None
        rect, origin = wintypes.RECT(), wintypes.POINT()
        if not (self.user.GetClientRect(recipient, ctypes.byref(rect))
                and self.user.ClientToScreen(recipient, ctypes.byref(origin))
                and origin.x <= x < origin.x + rect.right
                and origin.y <= y < origin.y + rect.bottom):
            return None
        return ScrollTarget(window, recipient, process, x, y)

    def modifiers_held(self):
        return any(self.user.GetAsyncKeyState(vk) & 0x8000 for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C))

    def mouse_buttons_held(self):
        return any(self.user.GetAsyncKeyState(vk) & 0x8000 for vk in (1, 2, 4, 5, 6))

    def target_exists(self, target):
        return bool(target is not None and self.user.IsWindow(target.window)
                    and self.user.IsWindow(target.focus) and self.process(target.window) == target.process
                    and self.user.IsWindowEnabled(target.window) and self.user.IsWindowEnabled(target.focus)
                    and self.user.GetAncestor(target.focus, 2) == target.window)

    def pointer_over(self, target):
        point = wintypes.POINT()
        return bool(self.user.GetCursorPos(ctypes.byref(point))
                    and self.user.GetAncestor(self.user.WindowFromPoint(point), 2) == target.window)

    def prepare(self, target):
        if not self.target_exists(target):
            raise TargetError("Choisissez une zone de saisie pour insérer votre texte.")
        if self.modifiers_held():
            raise TargetError("Relâchez les touches Ctrl, Alt, Maj et Windows avant d’insérer.")
        foreground = int(self.user.GetForegroundWindow() or 0)
        if foreground != target.window:
            # Only restore a target if one of our own windows took foreground.
            # An explicit switch to another app must never receive a stale paste.
            if not foreground or self.process(foreground) != os.getpid():
                raise TargetError("La fenêtre a changé. Sélectionnez le champ où écrire, puis réessayez.")
            thread = self.kernel.GetCurrentThreadId()
            target_thread = self.user.GetWindowThreadProcessId(target.window, None)
            attached = thread != target_thread and self.user.AttachThreadInput(thread, target_thread, True)
            try:
                self.user.SetForegroundWindow(target.window)
                self.user.SetFocus(target.focus)
            finally:
                if attached:
                    self.user.AttachThreadInput(thread, target_thread, False)
        if self.user.GetForegroundWindow() != target.window or self.focused(target.window) != target.focus:
            raise TargetError("La zone de saisie a changé. Sélectionnez votre champ, puis réessayez.")

    def send_keys(self, target, keys):
        self.prepare(target)
        try:
            self.adapter.send([self.adapter.key(key, True) for key in keys]
                              + [self.adapter.key(key, False) for key in reversed(keys)])
        except Exception:
            # A partially accepted native batch must not leave our Ctrl/Alt held.
            try:
                self.adapter.send([self.adapter.key(key, False) for key in reversed(keys)])
            except Exception:
                pass
            raise

    def scroll(self, target, amount):
        """Scroll the last clicked pane without changing focus or cursor position."""
        if not (target and self.user.IsWindow(target.window) and self.user.IsWindow(target.recipient)
                and self.process(target.window) == target.process
                and self.process(target.recipient) == target.process
                and self.user.IsWindowEnabled(target.window) and self.user.IsWindowEnabled(target.recipient)
                and self.user.GetAncestor(target.recipient, 2) == target.window):
            return False
        return bool(self.user.PostMessageW(target.recipient, 0x020A, (amount & 0xFFFF) << 16,
                                          ((target.y & 0xFFFF) << 16) | (target.x & 0xFFFF)))

    def sequence(self):
        return self.user.GetClipboardSequenceNumber()

    def clipboard_ready(self, previous, current):
        # QClipboard.setText has no return value on Windows. Never paste stale
        # clipboard contents when another program prevented us taking ownership.
        return current != previous and QApplication.clipboard().ownsClipboard()


def clone_mime(source):
    result = QMimeData()
    if source is not None:
        for name in source.formats():
            result.setData(name, source.data(name))
    return result


class PasteDelivery(QObject):
    """Send one paste, then restore the clipboard unless somebody copied anew."""
    def __init__(self, desktop, parent=None):
        super().__init__(parent)
        self.desktop = desktop
        self.clipboard = QApplication.clipboard()
        self.snapshot = None
        self.owned_sequence = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.restore)

    @property
    def busy(self):
        return self.snapshot is not None

    def paste(self, target, text):
        if not text:
            return False
        if self.busy:
            raise TargetError("L’insertion est en cours. Patientez un instant.")
        self.desktop.prepare(target)
        self.snapshot = clone_mime(self.clipboard.mimeData())
        try:
            previous_sequence = self.desktop.sequence()
            self.clipboard.setText(text)
            current_sequence = self.desktop.sequence()
            if self.clipboard.text() != text or not self.desktop.clipboard_ready(previous_sequence, current_sequence):
                raise TargetError("Le presse-papiers est occupé. Réessayez Insérer dans un instant.")
            self.owned_sequence = current_sequence
            self.desktop.send_keys(target, [0xA2, 0x56])
        except Exception:
            self.restore()
            raise
        self.timer.start(450)
        return True

    def restore(self):
        self.timer.stop()
        if self.snapshot is None:
            return
        snapshot, self.snapshot = self.snapshot, None
        if self.owned_sequence is not None and self.desktop.sequence() == self.owned_sequence:
            self.clipboard.setMimeData(snapshot)
        else:
            snapshot.deleteLater()
        self.owned_sequence = None


def protect_tool_window(widget):
    """Qt flags plus native styles: clicks must not activate the keyboard."""
    if QApplication.platformName() == "offscreen":
        return
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    user.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    hwnd = int(widget.winId())
    style = user.GetWindowLongPtrW(hwnd, -20)
    user.SetWindowLongPtrW(hwnd, -20, style | 0x08000000 | 0x80)  # NOACTIVATE, TOOLWINDOW


def reject_mouse_activation(message):
    native = wintypes.MSG.from_address(int(message))
    return (True, 3) if native.message == 0x21 else (False, 0)  # MA_NOACTIVATE
