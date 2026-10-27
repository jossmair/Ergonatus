"""Only our HKCU Run value is ever modified; no elevation."""
from pathlib import Path
import subprocess
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "Precisionator"


def command():
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([str(executable)])
    pythonw = executable.with_name("pythonw.exe")
    return subprocess.list2cmdline([str(pythonw if pythonw.exists() else executable), str(Path(__file__).resolve().parents[1] / "main.py")])


def enabled():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, VALUE)[0] == command()
    except FileNotFoundError:
        return False


def set_enabled(value):
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if value:
            winreg.SetValueEx(key, VALUE, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(key, VALUE)
            except FileNotFoundError:
                pass
