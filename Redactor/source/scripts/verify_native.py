"""Real isolated Windows fixture: capture, insert, stale target and IPC checks."""
from pathlib import Path
import json
import os
import struct
import subprocess
import sys
import time
import pywintypes
import ctypes
import win32api
import win32process
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import win32con
import win32file
import win32gui
import win32pipe
from app.integration.fortinator import PipeServer, envelope
from app.security.validation import encode_frame, parse_json
from app.windows.accessibility import Accessibility


def receive(handle):
    size = struct.unpack("<I", win32file.ReadFile(handle, 4)[1])[0]
    return parse_json(win32file.ReadFile(handle, size)[1])


def ipc_check():
    dispatched = []
    server = PipeServer(dispatched.append, lambda: "ready")
    server.start()
    assert server.ready.wait(5), "Serveur IPC absent"
    assert not server.error, server.error
    def connect(pid):
        deadline = time.monotonic() + 3
        while True:
            try:
                win32pipe.WaitNamedPipe(server.name, 3000)
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise AssertionError(f"Pipe indisponible : {server.error} {getattr(server, 'last_exception', '')}")
                time.sleep(.05)
        h = win32file.CreateFile(server.name, win32con.GENERIC_READ | win32con.GENERIC_WRITE, 0, None, win32con.OPEN_EXISTING, 0, None)
        hello = envelope("Hello", {"minVersion": 1, "maxVersion": 1, "processId": pid, "role": "redactor-client"})
        # Fragmented framing, including one byte of the uint32 length at a time.
        data = encode_frame(hello)
        for chunk in (data[:1], data[1:3], data[3:8], data[8:]):
            win32file.WriteFile(h, chunk)
        return h, hello
    try:
        h, hello = connect(os.getpid())
        try:
            assert receive(h)["replyTo"] == hello["id"]
            capabilities = receive(h)
            assert "insert" not in capabilities["payload"]["commands"]
            status = envelope("Status", {})
            win32file.WriteFile(h, encode_frame(status))
            assert receive(h)["payload"]["state"] == "ready"
            win32file.WriteFile(h, encode_frame(envelope("Command", {"command": "insert", "text": "INTERDIT"})))
            assert receive(h)["type"] == "Error" and not dispatched
            win32file.WriteFile(h, encode_frame(envelope("Command", {"command": "correct", "text": "Un texte"})))
            assert receive(h)["payload"]["localValidationRequired"]
            assert dispatched == [{"command": "correct", "text": "Un texte"}]
        finally:
            h.Close()
        time.sleep(.15)
        h, _ = connect(os.getpid() + 123456)
        try:
            try:
                receive(h)
                raise AssertionError("PID usurpé accepté")
            except (OSError, pywintypes.error):
                pass
        finally:
            h.Close()
    finally:
        server.close()
    assert not server.is_alive(), "Le worker IPC n’a pas été libéré"
    return True


def main():
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen([sys.executable, str(root / "scripts" / "native_fixture.py")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    bridge = Accessibility()
    report = {}
    def focus_fixture(info):
        # Test harness only: temporarily attach this test thread's input queue
        # to bring its own disposable fixture forward, without any click/key.
        foreground = win32gui.GetForegroundWindow()
        owner = win32process.GetWindowThreadProcessId(foreground)[0]
        current = win32api.GetCurrentThreadId()
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.AttachThreadInput.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int]
        attached = current != owner and bool(user.AttachThreadInput(current, owner, True))
        try:
            win32gui.SetForegroundWindow(info["hwnd"])
        finally:
            if attached: user.AttachThreadInput(current, owner, False)
        win32gui.PostMessage(info["hwnd"], win32con.WM_APP + 1, 0, 0)
        time.sleep(.2)
    def edit_value(hwnd):
        element = bridge.client.ElementFromHandle(hwnd)
        return element.GetCurrentPattern(bridge.api.UIA_ValuePatternId).QueryInterface(bridge.api.IUIAutomationValuePattern).CurrentValue
    try:
        info = json.loads(process.stdout.readline())
        focus_fixture(info)
        target = bridge.capture(info["hwnd"])
        print("CAPTURE", target, flush=True)
        assert target.selected == "fautes", repr(target.selected)
        assert target.writable, "Le contrôle EDIT de test doit supporter ValuePattern et TextPattern"
        bridge.insert(target, "corrigé")
        assert edit_value(info["edit"]) == "Avant. corrigé Après."
        report["uia_capture_and_insert"] = True
        try:
            bridge.insert(target, "INTERDIT")
            raise AssertionError("Cible utilisée deux fois")
        except ValueError:
            report["one_shot_target"] = True
        focus_fixture(info)
        stale = bridge.capture(info["hwnd"])
        win32gui.PostMessage(info["hwnd"], win32con.WM_APP + 2, 0, 0)
        time.sleep(.15)
        assert edit_value(info["edit"]) == "Modifié dans l’application", "La fixture n’a pas changé son texte"
        try:
            bridge.insert(stale, "INTERDIT")
            raise AssertionError("Texte modifié écrasé")
        except ValueError:
            assert edit_value(info["edit"]) == "Modifié dans l’application"
            report["changed_text_refused"] = True
        win32gui.PostMessage(info["hwnd"], win32con.WM_CLOSE, 0, 0)
        process.wait(5)
        try:
            bridge.validate(stale)
            raise AssertionError("Fenêtre disparue acceptée")
        except ValueError:
            report["disappeared_target_refused"] = True
    finally:
        bridge.close()
        if process.poll() is None:
            process.terminate()
            process.wait(5)
    report["ipc_handshake_commands_pid_and_shutdown"] = ipc_check()
    (root / "docs" / "validation" / "windows-native.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
