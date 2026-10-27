import ctypes
from ctypes import wintypes
import win32gui

import win32clipboard
import win32con
import pywintypes

from app.core.win32 import modifiers_held, paste_inputs, send, send_paste, unicode_inputs, user


class TextInjector:
    def __init__(self, focus, strategy="auto"):
        self.focus = focus
        self.strategy = strategy
        self.last_method = None
        self.last_failure = None

    def insert(self, text):
        if not text.strip():
            return False
        # Keep the separator inside the single delivery payload.
        text = text.rstrip(" ") + " "
        if self.strategy in ("auto", "clipboard"):
            self.last_method = "clipboard"
            return self.paste(text)
        if not self.focus.valid():
            return False  # controller reacquires the current selection before retrying
        if modifiers_held():
            return False  # defer instead of typing into an active shortcut
        if self.strategy == "native":
            self.last_method = "native"
            return self.native_insert(text)
        # One atomic SendInput batch; UTF-16 surrogate pairs support all Unicode.
        if not self.focus.valid() or modifiers_held():
            return False
        self.last_method = "unicode"
        send(unicode_inputs(text))
        return True

    def native_available(self):
        hwnd = self.focus.target.native_hwnd
        # Windows 11 Notepad uses RichEditD2DPT; it supports EM_REPLACESEL too.
        kind = win32gui.GetClassName(hwnd).lower() if hwnd else ""
        return kind == "edit" or kind.startswith("richedit")

    def native_insert(self, text):
        hwnd = self.focus.target.native_hwnd
        if not self.native_available():
            raise RuntimeError("Insertion par contrôle non disponible pour ce champ. Choisissez Unicode.")
        if not self.focus.valid():
            return False
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.SendMessageTimeoutW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
            wintypes.UINT,
            wintypes.UINT,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        user.SendMessageTimeoutW.restype = wintypes.LPARAM
        buffer = ctypes.create_unicode_buffer(text.replace("\r\n", "\n").replace("\n", "\r\n"))
        result = ctypes.c_size_t()
        if not user.SendMessageTimeoutW(
            hwnd, 0xC2, 1, ctypes.addressof(buffer), 2, 500, ctypes.byref(result)
        ):
            raise RuntimeError("Le contrôle Windows n’a pas accepté l’insertion dans le délai autorisé.")
        return True

    def paste(self, text):
        """Paste at Windows' current focus without inspecting the receiving field."""
        self.last_failure = "modifier_held_before_copy"
        if modifiers_held():
            return False
        inputs = paste_inputs(user.GetForegroundWindow())
        # Publish immediately before sending: no focus, accessibility or result
        # inspection can delay the dictation or substitute a different target.
        self.last_failure = "clipboard_locked_before_send"
        if not self.copy_dictation(text):
            return False
        self.last_failure = "sending_paste"
        if send_paste(inputs) is False:
            self.last_failure = "control_intercepted"
            return False
        self.last_failure = None
        return True

    def copy_dictation(self, text):
        """Publish even without an editor; no old clipboard restoration timer."""
        text = text.rstrip(" ") + " "
        try:
            win32clipboard.OpenClipboard()
        except pywintypes.error:
            return False
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
            return True
        except pywintypes.error:
            return False
        finally:
            win32clipboard.CloseClipboard()
