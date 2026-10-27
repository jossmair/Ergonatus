"""Windows input adapter. The hook owns the engine on a dedicated message thread."""
import ctypes
from ctypes import wintypes
from copy import deepcopy
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from .engine import Engine
from .branding import APP_NAME, LEGACY_NAME
from .keys import EXTENDED, normalize_key

TAG = 0x464F5254  # Only our own synthetic events bypass remapping.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
INSTANCE_NAME = r"Local\Fortinatus.SingleInstance.v1"
SERVER_NAME = "Fortinatus.SingleInstance.v1"


class SingleInstance:
    """A session-wide Windows handle, independent of executable/config location."""
    def __init__(self, name=INSTANCE_NAME):
        self.name, self.handle = name, None
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL

    def acquire(self):
        ctypes.set_last_error(0)
        handle = self.kernel.CreateMutexW(None, False, self.name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:
            self.kernel.CloseHandle(handle)
            return False
        self.handle = handle
        return True

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class Mouse(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("data", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class Keyboard(ctypes.Structure):
    _fields_ = [("vk", wintypes.WORD), ("scan", wintypes.WORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class Hardware(ctypes.Structure):
    _fields_ = [("message", wintypes.DWORD), ("low", wintypes.WORD), ("high", wintypes.WORD)]


class InputUnion(ctypes.Union):
    _fields_ = [("mouse", Mouse), ("keyboard", Keyboard), ("hardware", Hardware)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("value", InputUnion)]


class HookData(ctypes.Structure):
    _fields_ = [("vk", wintypes.DWORD), ("scan", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


class WindowsInput:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("Claviernator nécessite Windows 10 ou 11.")
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.user.SendInput.restype = wintypes.UINT

    def send(self, inputs):
        array = (Input * len(inputs))(*inputs)
        count = self.user.SendInput(len(array), array, ctypes.sizeof(Input))
        if count != len(array):
            raise RuntimeError("Windows a bloqué une action. Vérifiez si l’application cible est exécutée en administrateur.")

    @staticmethod
    def key(vk, down, tag=TAG):
        flags = (0 if down else 2) | (1 if vk in EXTENDED else 0)
        return Input(1, InputUnion(keyboard=Keyboard(vk, 0, flags, 0, tag)))

    @staticmethod
    def text_chunks(text):
        """Separate supplementary code points from WM_CHAR-translated BMP text.

        Qt dispatches surrogate packets before pending BMP WM_CHAR messages if
        they share one SendInput batch. Separate message-loop turns retain order.
        """
        normal = []
        for character in text:
            if ord(character) > 0xFFFF:
                if normal:
                    yield "".join(normal)
                    normal.clear()
                yield character
            else:
                normal.append(character)
        if normal:
            yield "".join(normal)

    def emit(self, event):
        kind, *args = event
        if kind == "key":
            self.send([self.key(*args)])
        elif kind == "text":
            raw = args[0].replace("\r\n", "\n").replace("\n", "\r").encode("utf-16-le")
            inputs = []
            for index in range(0, len(raw), 2):
                code = int.from_bytes(raw[index:index + 2], "little")
                for flags in (4, 6):
                    inputs.append(Input(1, InputUnion(keyboard=Keyboard(0, code, flags, 0, TAG))))
            if inputs:
                self.send(inputs)
        elif kind == "mouse":
            button, down = args
            flags = {"left": (2, 4), "right": (8, 16), "middle": (32, 64)}[button][not down]
            self.send([Input(0, InputUnion(mouse=Mouse(0, 0, 0, flags, 0, TAG)))])
        elif kind == "double_click":
            pair = [Input(0, InputUnion(mouse=Mouse(0, 0, 0, flags, 0, TAG))) for flags in (2, 4)]
            self.send(pair)
            # Distinct timestamps also let Qt recognize WM_LBUTTONDBLCLK.
            # This runs on the action worker, never on the keyboard hook.
            time.sleep(.03)
            self.send(pair)
        elif kind == "wheel":
            self.send([Input(0, InputUnion(mouse=Mouse(0, 0, args[0] & 0xFFFFFFFF, 0x800, 0, TAG)))])
        elif kind == "move":
            self.send([Input(0, InputUnion(mouse=Mouse(args[0], args[1], 0, 1, 0, TAG)))])


class TextDispatcher:
    """Send Unicode off the hook thread and allow pause to cancel pending text."""
    def __init__(self, adapter, on_error):
        self.adapter, self.on_error = adapter, on_error
        self.jobs = queue.Queue()
        self.generation = 0
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self.run, name="fortinatus-text", daemon=True)
        self.thread.start()

    def submit(self, text):
        if self.jobs.qsize() > 100:
            raise RuntimeError("Trop de textes en attente. Les adaptations ont été suspendues.")
        self.jobs.put((self.generation, text))

    def cancel(self):
        self.generation += 1

    def run(self):
        while not self.closed.is_set():
            job = self.jobs.get()
            if job is None:
                return
            generation, text = job
            try:
                for chunk in self.adapter.text_chunks(text):
                    if self.closed.is_set() or generation != self.generation:
                        break
                    self.adapter.emit(("text", chunk))
                    self.closed.wait(.02)
            except Exception as exc:
                self.cancel()
                self.on_error(str(exc))

    def stop(self):
        self.cancel()
        self.closed.set()
        self.jobs.put(None)
        self.thread.join(2)


class ActionDispatcher:
    """Deliver mouse/key effects after returning from the low-level callback.

    A physical modifier must be consumed by the keyboard hook before its mouse
    action enters Windows. Never make SendInput part of that callback's lifetime.
    """
    def __init__(self, adapter, on_error):
        self.adapter, self.on_error = adapter, on_error
        self.jobs = queue.Queue()
        self.thread = threading.Thread(target=self.run, name="fortinatus-actions", daemon=True)
        self.thread.start()

    def submit(self, event):
        self.jobs.put(event)

    def run(self):
        while True:
            event = self.jobs.get()
            if event is None:
                return
            try:
                self.adapter.emit(event)
            except Exception as exc:
                self.on_error(str(exc))

    def stop(self):
        # Key/button releases queued by Engine.pause must finish before exit.
        self.jobs.put(None)
        self.thread.join(3)


class HookService:
    def __init__(self, on_state=lambda enabled: None, on_notice=lambda text: None):
        self.on_state, self.on_notice = on_state, on_notice
        self.commands = queue.Queue()
        self.ready = threading.Event()
        self.thread = None
        self.thread_id = 0
        self.error = None
        self.engine = None

    def start(self, profile, enabled):
        self.initial = (deepcopy(profile), enabled)
        self.thread = threading.Thread(target=self._run, daemon=True, name="fortinatus-keyboard")
        self.thread.start()
        if not self.ready.wait(5):
            raise RuntimeError("Le service clavier ne répond pas.")
        if self.error:
            raise RuntimeError(str(self.error))

    def configure(self, profile, enabled, wait=True):
        if not self.thread or not self.thread.is_alive():
            raise RuntimeError("Le service clavier est arrêté. Relancez Claviernator.")
        done = threading.Event()
        result = []
        self.commands.put((deepcopy(profile), enabled, done, result))
        if wait:
            if not done.wait(3):
                raise RuntimeError("Le service clavier ne répond pas. Les réglages n’ont pas été appliqués.")
            if result:
                raise RuntimeError(result[0])

    def _run(self):
        hook = timer = dispatcher = actions = None
        try:
            adapter = WindowsInput()
            user = adapter.user
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            procedure_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
            user.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
            user.CallNextHookEx.restype = ctypes.c_ssize_t
            user.SetWindowsHookExW.argtypes = [ctypes.c_int, procedure_type, wintypes.HINSTANCE, wintypes.DWORD]
            user.SetWindowsHookExW.restype = wintypes.HANDLE
            user.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
            user.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
            user.SetTimer.restype = ctypes.c_size_t
            user.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
            user.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
            user.GetMessageW.restype = wintypes.BOOL
            user.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
            kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            kernel.GetModuleHandleW.restype = wintypes.HMODULE
            self.thread_id = kernel.GetCurrentThreadId()
            text_errors = queue.Queue()
            dispatcher = TextDispatcher(adapter, text_errors.put)
            actions = ActionDispatcher(adapter, text_errors.put)

            def emit(event):
                if event[0] == "text":
                    dispatcher.submit(event[1])
                else:
                    actions.submit(event)

            self.engine = Engine(emit, self.on_notice)
            self.engine.configure(*self.initial)

            def procedure(code, message, address):
                if code >= 0 and message in (0x100, 0x101, 0x104, 0x105):
                    data = ctypes.cast(address, ctypes.POINTER(HookData)).contents
                    if data.extra != TAG:
                        try:
                            previous = self.engine.enabled
                            vk = normalize_key(data.vk, data.scan, data.flags)
                            swallowed = self.engine.event(vk, message in (0x100, 0x104))
                            if previous != self.engine.enabled:
                                if not self.engine.enabled:
                                    dispatcher.cancel()
                                self.on_state(self.engine.enabled)
                            if swallowed:
                                return 1
                        except Exception as exc:
                            dispatcher.cancel()
                            self.engine.pause()
                            self.on_state(False)
                            self.on_notice(str(exc))
                            # Consume the current event after a partial synthetic action.
                            if message in (0x100, 0x104):
                                self.engine.drain.add(normalize_key(data.vk, data.scan, data.flags))
                            return 1
                return user.CallNextHookEx(None, code, message, address)

            self._procedure = procedure_type(procedure)
            msg = wintypes.MSG()
            user.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
            hook = user.SetWindowsHookExW(13, self._procedure, kernel.GetModuleHandleW(None), 0)
            if not hook:
                raise ctypes.WinError(ctypes.get_last_error())
            timer = user.SetTimer(None, 0, 20, None)
            if not timer:
                raise ctypes.WinError(ctypes.get_last_error())
            self.ready.set()
            self.on_state(self.engine.enabled)
            while True:
                status = user.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if status == 0:
                    break
                if status == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if msg.message == 0x113:
                    if not text_errors.empty():
                        error = text_errors.get_nowait()
                        dispatcher.cancel()
                        self.engine.pause()
                        self.on_state(False)
                        self.on_notice(error)
                    while not self.commands.empty():
                        profile, enabled, done, result = self.commands.get_nowait()
                        try:
                            dispatcher.cancel()
                            self.engine.configure(profile, enabled)
                            self.on_state(self.engine.enabled)
                        except Exception as exc:
                            result.append(str(exc))
                            self.engine.pause()
                            self.on_state(False)
                            self.on_notice(str(exc))
                        finally:
                            done.set()
                    self.engine.tick()
                user.TranslateMessage(ctypes.byref(msg))
                user.DispatchMessageW(ctypes.byref(msg))
        except Exception as exc:
            self.error = exc
            self.on_state(False)
            self.on_notice(str(exc))
        finally:
            self.ready.set()
            if dispatcher:
                dispatcher.cancel()
            if self.engine:
                self.engine.pause()
            if hook:
                user.UnhookWindowsHookEx(hook)
            if timer:
                user.KillTimer(None, timer)
            if dispatcher:
                dispatcher.stop()
            if actions:
                actions.stop()
            self.thread_id = 0

    def stop(self):
        if self.thread_id:
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user.PostThreadMessageW(self.thread_id, 0x12, 0, 0)
        if self.thread:
            self.thread.join(3)


def startup_command(config_dir=None):
    args = [sys.executable]
    if not getattr(sys, "frozen", False):
        args.append(str(Path(__file__).resolve().parents[1] / "run_claviernator.py"))
    args.append("--minimized")
    if config_dir:
        args.extend(["--config-dir", str(config_dir)])
    return subprocess.list2cmdline(args)


def startup_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            for name in (APP_NAME, LEGACY_NAME):
                try:
                    value, kind = winreg.QueryValueEx(key, name)
                    if kind == winreg.REG_SZ and value:
                        return True
                except FileNotFoundError:
                    pass
            return False
    except FileNotFoundError:
        return False


def set_startup(enabled, config_dir=None):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command(config_dir))
        for name in ((LEGACY_NAME,) if enabled else (APP_NAME, LEGACY_NAME)):
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass


def migrate_startup_name():
    """Rename an existing entry without enabling startup or changing its command."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
            value, kind = winreg.QueryValueEx(key, LEGACY_NAME)
            try:
                winreg.QueryValueEx(key, APP_NAME)
            except FileNotFoundError:
                winreg.SetValueEx(key, APP_NAME, 0, kind, value)
            winreg.DeleteValue(key, LEGACY_NAME)
    except OSError:
        pass

