from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from collections.abc import Callable


TRIGGER_KEYS = (("shift_left", "Maj gauche", 0xA0), ("shift_right", "Maj droite", 0xA1),
                ("ctrl_left", "Ctrl gauche", 0xA2), ("ctrl_right", "Ctrl droit", 0xA3)) + tuple(
                    (f"f{i}", f"F{i}", 0x6F + i) for i in range(1, 13))


def trigger_spec(identity):
    return next((item for item in TRIGGER_KEYS if item[0] == identity), TRIGGER_KEYS[0])


class ShiftGesture:
    """One complete, unaccompanied selected key. Repeats never toggle."""

    def __init__(self, double=False, clock=time.monotonic, key=0xA0):
        self.double, self.clock = double, clock
        self.key = key
        self.pressed = False
        self.contaminated = False
        self.held: set[int] = set()
        self.last_tap = -10.0
        self.last_fire = -10.0

    def event(self, vk: int, down: bool, injected: bool = False) -> bool:
        if injected:
            return False
        now = self.clock()
        if vk != self.key:
            if down:
                self.held.add(vk)
                if self.pressed:
                    self.contaminated = True
            else:
                self.held.discard(vk)
            return False
        if down:
            if not self.pressed:
                self.pressed = True
                self.contaminated = bool(self.held)
            return False
        if not self.pressed:
            return False
        self.pressed = False
        if self.contaminated:
            self.last_tap = -10
            return False
        if self.double:
            if now - self.last_tap > 0.4:
                self.last_tap = now
                return False
            self.last_tap = -10
        if now - self.last_fire < 0.25:
            return False
        self.last_fire = now
        return True


class GlobalHotkey:
    def __init__(self, callback: Callable[[], None], double=False, activity=None, trigger_key="shift_left"):
        self.callback = callback
        self.activity = activity
        self.lock = threading.RLock()
        self.double = double
        self.gesture = ShiftGesture(double, key=trigger_spec(trigger_key)[2])
        self.suppressed_keys = set()
        self.thread = None
        self.thread_id = 0
        self.ready = threading.Event()
        self.error = None

    def set_trigger(self, identity):
        with self.lock:
            self.gesture = ShiftGesture(self.double, key=trigger_spec(identity)[2])

    def handle_key(self, vk, down, injected=False, held=None):
        """Return (triggered, consume). Modifier shortcuts retain native behavior."""
        if injected:
            return False, False
        with self.lock:
            gesture = self.gesture
            if vk == gesture.key and down and not gesture.pressed:
                if held is not None:
                    gesture.held = set(held)
                if 0x70 <= vk <= 0x7B and not gesture.held:
                    self.suppressed_keys.add(vk)
            consume = vk in self.suppressed_keys
            fired = gesture.event(vk, down)
            if not down:
                self.suppressed_keys.discard(vk)
            return fired, consume

    def start(self):
        self.thread = threading.Thread(target=self._run, name="transcri-hotkey", daemon=True)
        self.thread.start()
        if not self.ready.wait(3) or self.error is not None:
            raise RuntimeError("Le raccourci Windows n’a pas pu être installé.")

    def _run(self):
        user = ctypes.WinDLL("user32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        pointer = ctypes.c_size_t
        hook_proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        class Keyboard(ctypes.Structure):
            _fields_ = [
                ("vk", wintypes.DWORD),
                ("scan", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("extra", pointer),
            ]

        user.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]

        class MouseEvent(ctypes.Structure):
            _fields_ = [
                ("point", wintypes.POINT),
                ("data", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("extra", pointer),
            ]

        user.CallNextHookEx.restype = ctypes.c_ssize_t
        user.SetWindowsHookExW.argtypes = [ctypes.c_int, hook_proc_type, wintypes.HINSTANCE, wintypes.DWORD]
        user.SetWindowsHookExW.restype = wintypes.HANDLE
        user.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
        kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel.GetModuleHandleW.restype = wintypes.HMODULE

        def procedure(code, message, address):
            if code >= 0:
                k = ctypes.cast(address, ctypes.POINTER(Keyboard)).contents
                vk = k.vk
                if vk == 0x10:  # LL hooks normally provide L/R, but map scan code defensively.
                    vk = 0xA0 if k.scan == 0x2A else 0xA1
                elif vk == 0x11:
                    vk = 0xA3 if k.flags & 1 else 0xA2
                if self.activity and vk != self.gesture.key and message in (0x100, 0x104) and not k.flags & 0x10:
                    self.activity()
                with self.lock:
                    held = None
                    if (vk == self.gesture.key and message in (0x100, 0x104)
                            and not self.gesture.pressed and not k.flags & 0x10):
                        held = {key for key in range(1, 256)
                                if key not in (0x10, 0x11, 0x12, self.gesture.key, 0xE7)
                                and user.GetAsyncKeyState(key) & 0x8000}
                    fired, consume = self.handle_key(vk, message in (0x100, 0x104), bool(k.flags & 0x10), held)
                    if fired:
                        self.callback()  # queues only; no COM or audio in this hook
                    if consume:
                        return 1
            return user.CallNextHookEx(None, code, message, address)

        self._procedure = hook_proc_type(procedure)

        def mouse_procedure(code, message, address):
            if code >= 0 and self.activity and message in (0x201, 0x204, 0x207, 0x20B):
                data = ctypes.cast(address, ctypes.POINTER(MouseEvent)).contents
                if not data.flags & 1:
                    self.activity()
            if code >= 0 and message in (0x201, 0x204, 0x207, 0x20B, 0x20A, 0x20E):
                with self.lock:
                    data = ctypes.cast(address, ctypes.POINTER(MouseEvent)).contents
                    if self.gesture.pressed and not data.flags & 1:
                        self.gesture.contaminated = True
            return user.CallNextHookEx(None, code, message, address)

        self._mouse_procedure = hook_proc_type(mouse_procedure)
        self.thread_id = kernel.GetCurrentThreadId()
        message = wintypes.MSG()
        user.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        hook = user.SetWindowsHookExW(13, self._procedure, kernel.GetModuleHandleW(None), 0)
        mouse_hook = user.SetWindowsHookExW(14, self._mouse_procedure, kernel.GetModuleHandleW(None), 0)
        if not hook or not mouse_hook:
            self.error = ctypes.get_last_error()
        self.ready.set()
        if not hook or not mouse_hook:
            if hook:
                user.UnhookWindowsHookEx(hook)
            if mouse_hook:
                user.UnhookWindowsHookEx(mouse_hook)
            return
        try:
            while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                user.TranslateMessage(ctypes.byref(message))
                user.DispatchMessageW(ctypes.byref(message))
        finally:
            user.UnhookWindowsHookEx(hook)
            user.UnhookWindowsHookEx(mouse_hook)

    def stop(self):
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x12, 0, 0)
        if self.thread:
            self.thread.join(2)
