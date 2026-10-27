import subprocess
import sys
import winreg
from pathlib import Path


def set_autostart(enabled):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        try:
            winreg.DeleteValue(key, "Transcri")
        except FileNotFoundError:
            pass
        if enabled:
            if getattr(sys, "frozen", False):
                command = [sys.executable]
            else:
                pythonw = Path(sys.executable).with_name("pythonw.exe")
                launcher = Path(__file__).resolve().parents[2] / "scripts" / "run_transcri.py"
                command = [str(pythonw), str(launcher)]
            command += ["--minimized"]
            winreg.SetValueEx(key, "Transcrinator", 0, winreg.REG_SZ, subprocess.list2cmdline(command))
        else:
            try:
                winreg.DeleteValue(key, "Transcrinator")
            except FileNotFoundError:
                pass
