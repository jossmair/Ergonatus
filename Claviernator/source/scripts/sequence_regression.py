"""Test saved sequences and automatic activation in a separate frozen process."""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QLineEdit
from fortinatus.config import Mapping, Profile, Settings
from fortinatus.theme import configure_app
from fortinatus.windows import SingleInstance, WindowsInput
from windows_integration import pump, wait_for_idle


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    args = parser.parse_args()
    probe = SingleInstance()
    if not probe.acquire():
        raise SystemExit("Une instance existante empêche ce test isolé.")
    probe.close()
    wait_for_idle()
    app = QApplication([])
    configure_app(app)
    target = QLineEdit("Texte de test")
    target.setWindowTitle("Claviernator · Vérification de la suite")
    target.resize(520, 90)
    target.show()
    adapter = WindowsInput()
    user = adapter.user
    user.GetForegroundWindow.restype = wintypes.HWND
    user.SetForegroundWindow.argtypes = [wintypes.HWND]
    user.BringWindowToTop.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    kernel = ctypes.WinDLL("kernel32")
    thread = kernel.GetCurrentThreadId()
    foreground_thread = user.GetWindowThreadProcessId(user.GetForegroundWindow(), None)
    attached = thread != foreground_thread and user.AttachThreadInput(thread, foreground_thread, True)
    try:
        user.BringWindowToTop(int(target.winId()))
        user.SetForegroundWindow(int(target.winId()))
        target.setFocus()
    finally:
        if attached:
            user.AttachThreadInput(thread, foreground_thread, False)
    pump(100)
    root = Path(__file__).resolve().parents[1]
    folder = root / "docs/test-settings/sequence-release"
    path = folder / "settings.json"
    settings = Settings(start_active=False, profiles=[Profile(invert_numbers=True, mappings=[
        Mapping(0xA3, "sequence", sequence=[[0xA2, 65], [68], [69]], interval_ms=80)
    ])])
    settings.save(path)
    checks = []
    process = None
    try:
        for iteration in range(2):
            process = subprocess.Popen([str(args.frozen.resolve()), "--minimized", "--config-dir", str(folder)])
            pump(900)
            assert process.poll() is None, "L’exécutable s’est fermé"
            assert user.GetForegroundWindow() == int(target.winId()), "Premier plan perdu : aucune entrée envoyée"
            target.setText("Texte de test")
            adapter.send([adapter.key(0xA3, True, tag=0x54455354), adapter.key(0xA3, False, tag=0x54455354)])
            for _ in range(100):
                if user.GetForegroundWindow() != int(target.winId()):
                    raise RuntimeError("Premier plan perdu pendant la suite")
                pump(6)
            assert target.text().lower() == "de", repr(target.text())
            assert Settings.load(path).profile == settings.profile
            checks.append("Suite Ctrl + A → D → E exécutée dès le lancement" if iteration == 0 else
                          "Suite et options conservées, adaptations actives après relancement")
            process.terminate()
            process.wait(timeout=5)
            process = None
    finally:
        if process:
            process.terminate()
            process.wait(timeout=5)
            # Release the only modifier produced by this test if interrupted.
            adapter.send([adapter.key(0xA2, False, tag=0x54455354)])
        target.close()
        app.processEvents()
    report = {"status": "passed", "frozen": str(args.frozen), "legacy_start_active_was_false": True,
              "relaunches": 2, "checks": checks}
    (root / "docs/validation/sequence-release.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    run()
