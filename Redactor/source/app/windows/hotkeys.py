"""RegisterHotKey only, no keyboard hook. All shortcuts can be changed or disabled."""
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QAbstractNativeEventFilter


def parse_hotkey(text):
    if not text.strip():
        return None
    parts = [p.strip().upper() for p in text.split("+")]
    modifiers = {"CTRL": 2, "ALT": 1, "SHIFT": 4, "WIN": 8}
    mods = 0
    for item in parts[:-1]:
        if item not in modifiers or mods & modifiers[item]:
            raise ValueError("Utilisez Ctrl, Alt, Shift ou Win et une lettre ou F1 à F24.")
        mods |= modifiers[item]
    key = parts[-1]
    if len(key) == 1 and key.isascii() and key.isalnum():
        vk = ord(key)
    elif key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    else:
        raise ValueError("La touche doit être une lettre, un chiffre ou F1 à F24.")
    if not mods or (len(key) == 1 and not (mods & (1 | 2 | 8))):
        raise ValueError("Ajoutez Ctrl, Alt ou Win pour éviter de détourner la saisie normale.")
    return mods | 0x4000, vk  # MOD_NOREPEAT


class GlobalHotkey(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback, self.registered = callback, False
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.user.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user.RegisterHotKey.restype = wintypes.BOOL
        self.user.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]

    def configure(self, text):
        parsed = parse_hotkey(text)
        self.close()
        if parsed:
            if not self.user.RegisterHotKey(None, 0x5244, *parsed):
                raise ValueError("Ce raccourci est déjà utilisé par une autre application. Choisissez-en un autre ; l’orbe reste disponible.")
            self.registered = True

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == 0x5244:
            self.callback()
            return True, 0
        return False, 0

    def close(self):
        if self.registered:
            self.user.UnregisterHotKey(None, 0x5244)
            self.registered = False
