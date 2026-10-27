"""Smoke-test the portable EXE and second-launch IPC, without OS input."""
import json
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.win32 import Desktop, enable_dpi
from services.configuration import Configuration, Preferences
enable_dpi()
desktop = Desktop()
exe = ROOT / "dist/Precisionator-1.0.7/Precisionator.exe"
config = ROOT / "docs/test-settings/frozen/settings.json"
config.parent.mkdir(parents=True, exist_ok=True)
# This interval measures idle overhead, independently of the real pointer
# movement during the test. Never reuse an enabled test profile here.
Configuration(config).save(Preferences(enabled=False))
report = {"tests": {}, "executable": str(exe)}
first = subprocess.Popen([str(exe), "--config", str(config), "--exit-after", "7"])
try:
    deadline = time.monotonic() + 12
    orb = None
    while time.monotonic() < deadline and first.poll() is None:
        orb = next((w for w in desktop.windows() if w[1] == first.pid and "orbe" in w[2] and w[4]), None)
        if orb:
            break
        time.sleep(.05)
    report["tests"]["native_orb_visible"] = bool(orb)
    if orb:
        report["orb_physical_rect"] = str(orb[3])
        report["tests"]["quiet_start_settings_hidden"] = not any(w[1] == first.pid and w[2] == "précisionator" and w[4] for w in desktop.windows())
        kernel = C.WinDLL("kernel32", use_last_error=True)
        kernel.GetProcessTimes.argtypes = [W.HANDLE, C.POINTER(W.FILETIME), C.POINTER(W.FILETIME), C.POINTER(W.FILETIME), C.POINTER(W.FILETIME)]
        def cpu_time():
            created, exited, system, user = W.FILETIME(), W.FILETIME(), W.FILETIME(), W.FILETIME()
            if not kernel.GetProcessTimes(int(first._handle), C.byref(created), C.byref(exited), C.byref(system), C.byref(user)):
                raise C.WinError(C.get_last_error())
            return ((system.dwHighDateTime << 32) + system.dwLowDateTime + (user.dwHighDateTime << 32) + user.dwLowDateTime) / 10000000
        begin = time.perf_counter()
        cpu = cpu_time()
        time.sleep(2)
        duration = time.perf_counter() - begin
        report["idle_measurement"] = {"seconds": duration, "cpu_one_core_percent": 100 * (cpu_time() - cpu) / duration}
        second = subprocess.run([str(exe), "--config", str(config), "--exit-after", "2"], timeout=5)
        report["tests"]["second_launch_exits_without_duplicate"] = second.returncode == 0 and first.poll() is None
        time.sleep(.25)
        report["tests"]["second_launch_opens_existing_settings"] = any(w[1] == first.pid and w[2] == "précisionator" and w[4] for w in desktop.windows())
        settings = next((w for w in desktop.windows() if w[1] == first.pid and w[2] == "précisionator" and w[4]), None)
        if settings:
            bounds = settings[3]
            monitor = next((m for m in desktop.monitors() if m.bounds.contains(bounds)), None)
            report["settings_physical_rect"] = str(bounds)
            report["tests"]["compact_native_settings_size"] = bool(monitor and
                abs(bounds.w - round(420 * monitor.scale)) <= 2 and
                abs(bounds.h - round(456 * monitor.scale)) <= 2)
        else:
            report["tests"]["compact_native_settings_size"] = False
        report["tests"]["single_visible_orb"] = sum(1 for w in desktop.windows() if w[1] == first.pid and "orbe" in w[2] and w[4]) == 1
    code = first.wait(timeout=12)
    report["tests"]["clean_timed_shutdown"] = code == 0
    report["tests"]["no_windows_after_shutdown"] = not any(w[1] == first.pid and w[4] for w in desktop.windows())
    report["result"] = "passed" if all(report["tests"].values()) else "failed"
except Exception as error:
    report["result"] = "failed"
    report["error"] = str(error)
finally:
    if first.poll() is None:
        first.terminate()
        first.wait(timeout=5)
    (ROOT / "docs/validation/frozen-1.0.7.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
raise SystemExit(0 if report.get("result") == "passed" else 1)
