"""The app owns only its per-user Windows Run value."""
from pathlib import Path
import subprocess
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "Transcrinator"
LEGACY_VALUE = "Transcri"


def command():
    args = [sys.executable]
    if not getattr(sys, "frozen", False):
        args.append(str(Path(__file__).resolve().parents[2] / "scripts/run_transcri.py"))
    return subprocess.list2cmdline([*args, "--minimized"])


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            for name in (VALUE, LEGACY_VALUE):
                try:
                    value, kind = winreg.QueryValueEx(key, name)
                    return kind == winreg.REG_SZ and bool(value)
                except FileNotFoundError:
                    continue
    except FileNotFoundError:
        pass
    return False


def set_enabled(enabled):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(key, VALUE)
            except FileNotFoundError:
                pass
        try:
            winreg.DeleteValue(key, LEGACY_VALUE)
        except FileNotFoundError:
            pass
