import ctypes
import time
from ctypes import wintypes

user = ctypes.WinDLL("user32", use_last_error=True)
user.GetForegroundWindow.restype = wintypes.HWND
user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user.GetAncestor.restype = wintypes.HWND
user.IsWindow.argtypes = [wintypes.HWND]
user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user.GetWindowThreadProcessId.restype = wintypes.DWORD
user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user.GetKeyboardLayout.argtypes = [wintypes.DWORD]
user.GetKeyboardLayout.restype = wintypes.HANDLE
user.MapVirtualKeyExW.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.HANDLE]
user.MapVirtualKeyExW.restype = wintypes.UINT


class Mouse(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("data", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("extra", ctypes.c_size_t),
    ]


class Keyboard(ctypes.Structure):
    _fields_ = [
        ("vk", wintypes.WORD),
        ("scan", wintypes.WORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("extra", ctypes.c_size_t),
    ]


class InputUnion(ctypes.Union):
    _fields_ = [("mouse", Mouse), ("keyboard", Keyboard)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("value", InputUnion)]


user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
user.SendInput.restype = wintypes.UINT


def send(inputs):
    array = (Input * len(inputs))(*inputs)
    count = user.SendInput(len(array), array, ctypes.sizeof(Input))
    if count != len(array):
        raise RuntimeError("Windows a bloqué ou interrompu l’insertion. Vérifiez les privilèges.")


def unicode_inputs(text):
    result = []
    raw = text.replace("\r\n", "\n").replace("\n", "\r").encode("utf-16-le")
    for i in range(0, len(raw), 2):
        code = int.from_bytes(raw[i : i + 2], "little")
        result.extend(
            [
                Input(1, InputUnion(keyboard=Keyboard(0, code, 4, 0, 0))),
                Input(1, InputUnion(keyboard=Keyboard(0, code, 6, 0, 0))),
            ]
        )
    return result


def paste_inputs(hwnd=0):
    """Use physical right Ctrl/V scan codes, including their matching key-ups.

    Generic VK_CONTROL with scan code zero is not consistently recognized as
    a modifier by Qt and some keyboard hooks; the target can receive a bare V.
    Map against the receiving thread's keyboard layout before sending anything.
    """
    thread = user.GetWindowThreadProcessId(hwnd, None) if hwnd else 0
    layout = user.GetKeyboardLayout(thread)
    control = user.MapVirtualKeyExW(0xA3, 0, layout)
    letter = user.MapVirtualKeyExW(0x56, 0, layout)
    if not control or not letter:
        raise RuntimeError("Windows ne peut pas préparer le raccourci de collage.")
    return [Input(1, InputUnion(keyboard=Keyboard(0, scan & 0xFF, flags, 0, 0)))
            for scan, flags in ((control, 9), (letter, 8), (letter, 10), (control, 11))]


def send_paste(inputs):
    """Keep Ctrl held while the receiver processes V, then always release it."""
    try:
        send(inputs[:1])
        time.sleep(.025)
        if not user.GetAsyncKeyState(0x11) & 0x8000:
            return False  # No V delivered: quiet retry remains safe.
        send(inputs[1:3])
        time.sleep(.04)
        return True
    finally:
        send(inputs[3:])


def modifiers_held():
    return any(user.GetAsyncKeyState(vk) & 0x8000 for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C))
