"""Explicit local draft client, also useful for deployment verification."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import struct
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import win32con
import win32file
import win32pipe
from app.integration.fortinator import envelope, user_identity
from app.security.validation import MAX_FRAME, encode_frame, parse_json, validate_command


def receive(handle):
    def exact(count):
        output = bytearray()
        while len(output) < count:
            data = win32file.ReadFile(handle, count - len(output))[1]
            if not data: raise EOFError("Pipe fermé.")
            output.extend(data)
        return bytes(output)
    size = struct.unpack("<I", exact(4))[0]
    if not 2 <= size <= MAX_FRAME: raise ValueError("Frame invalide.")
    return parse_json(exact(size))


def connect(pid):
    name = rf"\\.\pipe\Redactor.v1.{user_identity()[1]}.redactor.{pid}"
    deadline = time.monotonic() + 5
    while True:
        try:
            win32pipe.WaitNamedPipe(name, 500)
            handle = win32file.CreateFile(name, win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                0, None, win32con.OPEN_EXISTING, 0, None)
            break
        except Exception:
            if time.monotonic() >= deadline: raise
            time.sleep(.05)
    native = ctypes.WinDLL("kernel32", use_last_error=True)
    native.GetNamedPipeServerProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    native.GetNamedPipeServerProcessId.restype = wintypes.BOOL
    actual = wintypes.ULONG()
    if not native.GetNamedPipeServerProcessId(int(handle), ctypes.byref(actual)) or actual.value != pid:
        handle.Close()
        raise ValueError("Le pipe n’appartient pas au processus choisi.")
    hello = envelope("Hello", {"minVersion": 1, "maxVersion": 1, "processId": os.getpid(), "role": "redactor-client"})
    win32file.WriteFile(handle, encode_frame(hello))
    response = receive(handle)
    if response.get("replyTo") != hello["id"] or response["payload"].get("processId") != pid:
        handle.Close()
        raise ValueError("Identité du serveur non confirmée.")
    capabilities = receive(handle)
    if capabilities.get("type") != "Capabilities":
        handle.Close()
        raise ValueError("Capacités absentes.")
    return handle


def request(pid, command="status", text="", style=None):
    payload = {"command": command}
    if text: payload["text"] = text
    if style: payload["style"] = style
    validate_command(payload)
    handle = connect(pid)
    try:
        message = envelope("Command", payload)
        win32file.WriteFile(handle, encode_frame(message))
        reply = receive(handle)
        if reply.get("replyTo") != message["id"]: raise ValueError("Réponse non corrélée.")
        return reply
    finally:
        handle.Close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pid", type=int)
    parser.add_argument("command", nargs="?", default="status")
    parser.add_argument("--text", default="")
    parser.add_argument("--style")
    args = parser.parse_args()
    print(json.dumps(request(args.pid, args.command, args.text, args.style), ensure_ascii=True))
