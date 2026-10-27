"""Versioned same-user named pipes. No ports, remote clients or write commands.

Fortinator supervision protocol v1 + Redactor's documented draft commands.
Transport authenticates SID, session and declared client PID before dispatch.
"""
import ctypes
from ctypes import wintypes
import hashlib
import os
import re
import struct
import threading
import time
import uuid
from collections import deque
from app.security.validation import MAX_FRAME, encode_frame, parse_json, validate_command


def user_identity():
    import win32api
    import win32con
    import win32security
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        sid_text = win32security.ConvertSidToStringSid(sid)
    finally:
        token.Close()
    return sid_text, hashlib.sha256(sid_text.encode("utf-8")).hexdigest()[:16]


def pipe_name(prefix="Fortinator.v1"):
    if prefix not in ("Fortinator.v1", "Redactor.v1"):
        raise ValueError("Préfixe IPC inconnu.")
    return rf"\\.\pipe\{prefix}.{user_identity()[1]}.redactor.{os.getpid()}"


def envelope(kind, payload, reply_to=None):
    return dict(version=1, id=uuid.uuid4().hex, module="redactor", type=kind, payload=payload, replyTo=reply_to)


def validate_envelope(message):
    if set(message) != {"version", "id", "module", "type", "payload", "replyTo"}:
        raise ValueError("Enveloppe invalide.")
    if type(message["version"]) is not int or message["version"] != 1 or message["module"] != "redactor":
        raise ValueError("Version ou module invalide.")
    if not isinstance(message["id"], str) or not re.fullmatch("[0-9a-f]{32}", message["id"]):
        raise ValueError("Identifiant invalide.")
    if message["replyTo"] is not None or not isinstance(message["payload"], dict) or not isinstance(message["type"], str):
        raise ValueError("Requête invalide.")
    return message


class PipeServer(threading.Thread):
    def __init__(self, dispatch, status, prefix="Fortinator.v1"):
        super().__init__(name="Redactor-local-IPC", daemon=True)
        self.dispatch, self.status = dispatch, status
        self.stopping = threading.Event()
        self.ready = threading.Event()
        self.handle = None
        self.error = ""
        self.name = pipe_name(prefix)
        self.sid = user_identity()[0]

    def check_client(self, handle, declared_pid):
        import win32api
        import win32con
        import win32security
        native = ctypes.WinDLL("kernel32", use_last_error=True)
        native.GetNamedPipeClientProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
        native.GetNamedPipeClientProcessId.restype = wintypes.BOOL
        actual = wintypes.ULONG()
        if not native.GetNamedPipeClientProcessId(int(handle), ctypes.byref(actual)) or actual.value != declared_pid:
            raise ValueError("Client PID invalide.")
        native.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        ours, theirs = wintypes.DWORD(), wintypes.DWORD()
        if not native.ProcessIdToSessionId(os.getpid(), ctypes.byref(ours)) or not native.ProcessIdToSessionId(declared_pid, ctypes.byref(theirs)) or ours.value != theirs.value:
            raise ValueError("Session Windows différente.")
        process = win32api.OpenProcess(0x1000, False, declared_pid)
        try:
            token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
            try:
                sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
                if win32security.ConvertSidToStringSid(sid) != self.sid:
                    raise ValueError("Compte Windows différent.")
            finally:
                token.Close()
        finally:
            process.Close()

    def wait_io(self, handle, overlap, deadline):
        import win32event
        import win32file
        while not self.stopping.is_set():
            result = win32event.WaitForSingleObject(overlap.hEvent, 100)
            if result == win32event.WAIT_OBJECT_0:
                return win32file.GetOverlappedResult(handle, overlap, False)
            if time.monotonic() > deadline:
                break
        win32file.CancelIo(handle)
        # Keep OVERLAPPED and its buffer alive until the kernel confirms cancellation.
        win32event.WaitForSingleObject(overlap.hEvent, 1000)
        raise TimeoutError("IPC annulé ou expiré.")

    def read_exact(self, handle, size, deadline):
        import pywintypes
        import win32event
        import win32file
        data = bytearray()
        while len(data) < size:
            overlap = pywintypes.OVERLAPPED()
            overlap.hEvent = win32event.CreateEvent(None, True, False, None)
            try:
                _, buffer = win32file.ReadFile(handle, size - len(data), overlap)
                length = self.wait_io(handle, overlap, deadline)
                if not length:
                    raise EOFError()
                data.extend(bytes(buffer[:length]))
            finally:
                overlap.hEvent.Close()
        return bytes(data)

    def read(self, handle, seconds=45):
        deadline = time.monotonic() + seconds
        size = struct.unpack("<I", self.read_exact(handle, 4, deadline))[0]
        if not 2 <= size <= MAX_FRAME:
            raise ValueError("Frame hors limites.")
        return validate_envelope(parse_json(self.read_exact(handle, size, deadline)))

    def write(self, handle, value):
        import pywintypes
        import win32event
        import win32file
        data = encode_frame(value)
        overlap = pywintypes.OVERLAPPED()
        overlap.hEvent = win32event.CreateEvent(None, True, False, None)
        try:
            win32file.WriteFile(handle, data, overlap)
            count = self.wait_io(handle, overlap, time.monotonic() + 3)
            if count != len(data):
                raise OSError("Écriture IPC incomplète.")
        finally:
            overlap.hEvent.Close()

    def session(self, handle):
        hello = self.read(handle, 3)
        p = hello["payload"]
        if hello["type"] != "Hello" or set(p) != {"minVersion", "maxVersion", "processId", "role"}:
            raise ValueError("Hello attendu.")
        if type(p["minVersion"]) is not int or type(p["maxVersion"]) is not int or not p["minVersion"] <= 1 <= p["maxVersion"] or p["role"] not in ("fortinator", "redactor-client") or type(p["processId"]) is not int:
            raise ValueError("Négociation invalide.")
        self.check_client(handle, p["processId"])
        self.write(handle, envelope("Hello", {"minVersion": 1, "maxVersion": 1, "processId": os.getpid(), "role": "module"}, hello["id"]))
        self.write(handle, envelope("Capabilities", {"capabilities": ["status.read", "settings.open"],
            "commands": ["open", "compose", "rewrite", "correct", "summarize", "status", "cancel"]}))
        recent, seen, order = [], set(), deque()
        while not self.stopping.is_set():
            message = self.read(handle)
            now = time.monotonic()
            recent = [t for t in recent if now - t < 1]
            recent.append(now)
            if len(recent) > 32 or message["id"] in seen:
                raise ValueError("Cadence ou identifiant invalide.")
            if len(order) == 128:
                seen.discard(order.popleft())
            order.append(message["id"])
            seen.add(message["id"])
            kind, payload = message["type"], message["payload"]
            try:
                if kind == "Heartbeat" and not payload:
                    response = {}
                elif kind == "Status" and not payload:
                    response = {"state": self.status()}
                elif kind == "OpenSettings" and not payload:
                    self.dispatch({"command": "open"})
                    response = {}
                elif kind == "Command":
                    accepted = validate_command(payload)
                    if accepted["command"] == "status":
                        response = {"state": self.status()}
                    else:
                        self.dispatch(accepted)
                        response = {"accepted": True, "localValidationRequired": True}
                else:
                    raise ValueError("Commande non prise en charge.")
                self.write(handle, envelope(kind, response, message["id"]))
            except ValueError:
                self.write(handle, envelope("Error", {"code": "NOT_SUPPORTED"}, message["id"]))

    def run(self):
        import pywintypes
        import win32event
        import win32file
        import win32pipe
        import win32security
        descriptor = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(f"D:P(A;;GA;;;{self.sid})", 1)
        security = pywintypes.SECURITY_ATTRIBUTES()
        security.SECURITY_DESCRIPTOR = descriptor
        try:
            while not self.stopping.is_set():
                handle = win32pipe.CreateNamedPipe(self.name, 3 | 0x40000000 | 0x00080000, 0x00000008,
                                                  1, MAX_FRAME + 4, MAX_FRAME + 4, 0, security)
                self.handle = handle
                self.ready.set()
                overlap = pywintypes.OVERLAPPED()
                overlap.hEvent = win32event.CreateEvent(None, True, False, None)
                try:
                    connected = False
                    try:
                        win32pipe.ConnectNamedPipe(handle, overlap)
                    except pywintypes.error as exc:
                        if exc.winerror == 535:  # ERROR_PIPE_CONNECTED
                            connected = True
                        elif exc.winerror != 997:  # ERROR_IO_PENDING (pywin32 may raise it)
                            raise
                    if not connected:
                        self.wait_io(handle, overlap, float("inf"))
                    self.session(handle)
                except (OSError, ValueError, EOFError, TimeoutError, pywintypes.error):
                    pass  # No text, document title or request body is logged.
                finally:
                    overlap.hEvent.Close()
                    try: win32pipe.DisconnectNamedPipe(handle)
                    except (OSError, pywintypes.error): pass
                    handle.Close()
                    self.handle = None
        except Exception as exc:
            self.error = type(exc).__name__
            self.last_exception = exc
            self.ready.set()

    def close(self):
        self.stopping.set()
        # The owning IO thread observes this flag within 100 ms and cancels its
        # own pending operation with CancelIo (available on all supported builds).
        if self.is_alive():
            self.join(2)
