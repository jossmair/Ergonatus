"""Launch twice with distinct paths/settings and verify one actual window."""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fortinatus.windows import SingleInstance
from windows_integration import wait_for_idle


def process_tree(pid):
    # The Windows venv launcher can start the GUI in a child python process.
    class ProcessEntry(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD),
                    ("pid", wintypes.DWORD), ("heap", ctypes.c_size_t),
                    ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                    ("parent", wintypes.DWORD), ("priority", wintypes.LONG),
                    ("flags", wintypes.DWORD), ("name", wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    parents = {}
    entry = ProcessEntry()
    entry.size = ctypes.sizeof(entry)
    try:
        valid = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while valid:
            parents[entry.pid] = entry.parent
            valid = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    children = {pid}
    while True:
        expanded = children | {child for child, parent in parents.items() if parent in children}
        if children == expanded:
            return children
        children = expanded


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--second-exe", type=Path)
    args = parser.parse_args()
    wait_for_idle()
    root = Path(__file__).resolve().parents[1]
    base = [str(args.frozen.resolve())] if args.frozen else [sys.executable, str(root / "run_fortinatus.py")]
    second_base = [str(args.second_exe.resolve())] if args.second_exe else base
    probe = SingleInstance()
    if not probe.acquire():
        raise SystemExit("Une instance existante empêche ce test isolé.")
    probe.close()
    first = subprocess.Popen([*base, "--no-hooks", "--minimized", "--config-dir", str(root / "docs/test-settings/instance-a")])
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            assert first.poll() is None, "La première instance s’est fermée"
            probe = SingleInstance()
            occupied = not probe.acquire()
            probe.close()
            if occupied:
                break
            time.sleep(.03)
        else:
            raise AssertionError("Verrou non créé")
        duplicate = subprocess.run([*second_base, "--no-hooks", "--config-dir", str(root / "docs/test-settings/instance-b")], timeout=8)
        assert duplicate.returncode == 0
        assert first.poll() is None
        user = ctypes.WinDLL("user32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user.IsWindowVisible.argtypes = [wintypes.HWND]
        windows = []
        def inspect(hwnd, unused):
            pid = wintypes.DWORD()
            user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in first_pids:
                title = ctypes.create_unicode_buffer(256)
                user.GetWindowTextW(hwnd, title, len(title))
                if title.value == "Claviernator":
                    windows.append(bool(user.IsWindowVisible(hwnd)))
            return True
        # The duplicate can connect before the first process finishes building
        # its UI. Wait for that process to drain the show request.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            assert first.poll() is None, "La première instance s’est fermée"
            first_pids = process_tree(first.pid)
            windows.clear()
            user.EnumWindows(callback_type(inspect), 0)
            if windows == [True]:
                break
            time.sleep(.03)
        assert windows == [True], windows
    finally:
        # Stop only the subprocess tree this test created.
        subprocess.run(["taskkill", "/PID", str(first.pid), "/T", "/F"], capture_output=True)
        first.wait(timeout=5)
    probe = SingleInstance()
    assert probe.acquire(), "Le verrou reste bloqué après fermeture"
    probe.close()
    report = {"status": "passed", "one_window": True, "second_launcher_exits": True,
              "different_config_dirs": True, "different_exe_paths": bool(args.second_exe), "lock_released_on_exit": True}
    (root / "docs/validation/single-instance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    run()
