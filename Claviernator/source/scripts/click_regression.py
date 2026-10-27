"""Exercise the production editor/controller, then click a real Qt button with Ctrl."""
import ctypes
from ctypes import wintypes
import json
import argparse
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QDialog, QPushButton
from fortinatus.config import Mapping, Settings
from fortinatus.controller import Controller
from fortinatus.theme import configure_app
from fortinatus.ui import MainWindow
from fortinatus.windows import WindowsInput
from windows_integration import pump, wait_for_idle


class TargetButton(QPushButton):
    def __init__(self):
        super().__init__("Bouton de test du clic Ctrl")
        self.ctrl_received = False
        self.mouse_events = []
        self.key_events = []

    def mousePressEvent(self, event):
        self.mouse_events.append((event.button(), True))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.mouse_events.append((event.button(), False))
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        self.key_events.append(event.key())
        if event.key() == Qt.Key_Control:
            self.ctrl_received = True
        super().keyPressEvent(event)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path)
    args = parser.parse_args()
    wait_for_idle()
    app = QApplication([])
    configure_app(app)
    path = Path(__file__).resolve().parents[1] / "docs/test-settings/click-regression/settings.json"
    controller = Controller(Settings(), path)
    editor = MainWindow(controller)
    fixture = TargetButton()
    fixture.resize(450, 180)
    clicks = []
    fixture.clicked.connect(lambda: clicks.append(True))
    adapter = WindowsInput()
    user = adapter.user
    user.GetForegroundWindow.restype = wintypes.HWND
    user.SetForegroundWindow.argtypes = [wintypes.HWND]
    user.BringWindowToTop.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    cursor = wintypes.POINT()
    user.GetCursorPos(ctypes.byref(cursor))
    kernel = ctypes.WinDLL("kernel32")
    checks = []
    process = None
    held_sources = set()

    def key(source, down):
        adapter.send([adapter.key(source, down, tag=0x54455354)])
        if down:
            held_sources.add(source)
        else:
            held_sources.discard(source)

    try:
        for source in (0xA2, 0xA3):
            def save_editor():
                dialog = app.activeModalWidget()
                assert isinstance(dialog, QDialog)
                dialog.save()
            QTimer.singleShot(150, save_editor)
            editor.edit_mapping(source=source, kind="mouse_hold")
            pump(80)
            assert controller.active and controller.service.engine.enabled, "Le service est resté en pause après l’enregistrement"
        checks.append("Enregistrement par le vrai dialogue : service actif après fermeture")
        if args.frozen:
            controller.stop()
            # Reproduce an existing profile saved while the old app was paused.
            controller.settings.start_active = False
            controller.settings.save(path)
            process = subprocess.Popen([str(args.frozen.resolve()), "--minimized", "--config-dir", str(path.parent)], cwd=str(args.frozen.resolve().parent))
            pump(800)
            assert process.poll() is None, "L’exécutable s’est fermé"
            checks.append("Exécutable séparé démarré avec le profil Ctrl")
        fixture.show()
        pump(80)
        thread = kernel.GetCurrentThreadId()
        foreground_thread = user.GetWindowThreadProcessId(user.GetForegroundWindow(), None)
        attached = thread != foreground_thread and user.AttachThreadInput(thread, foreground_thread, True)
        try:
            user.BringWindowToTop(int(fixture.winId()))
            user.SetForegroundWindow(int(fixture.winId()))
        finally:
            if attached:
                user.AttachThreadInput(thread, foreground_thread, False)
        pump(100)
        point = fixture.mapToGlobal(fixture.rect().center())
        user.SetCursorPos(point.x(), point.y())
        pump(80)
        for source in (0xA2, 0xA3):
            # Test each physical button separately, outside Windows' double-click interval.
            pump(user.GetDoubleClickTime() + 50)
            assert user.GetForegroundWindow() == int(fixture.winId()), "Premier plan perdu : test interrompu"
            count = len(clicks)
            key(source, True)
            pump(100)
            assert fixture.isDown(), ("Aucun appui souris", source, controller.active, controller.service.engine.physical)
            key(source, False)
            pump(100)
            assert len(clicks) == count + 1, ("Aucun clic", source, clicks)
            checks.append(f"Ctrl {'gauche' if source == 0xA2 else 'droite'} : clic réel reçu")
        if args.frozen:
            checks.append("Profil précédemment en pause : adaptations actives dès le lancement")
        if process:
            adapter.send([adapter.key(0x7B, True, tag=0x54455354), adapter.key(0x7B, False, tag=0x54455354)])
            pump(80)
            process.terminate()
            process.wait(timeout=5)
            process = None
            controller.service = None
        assert controller.restore_key(0xA2)
        if args.frozen:
            process = subprocess.Popen([str(args.frozen.resolve()), "--minimized", "--config-dir", str(path.parent)])
            pump(700)
            assert process.poll() is None
        assert user.GetForegroundWindow() == int(fixture.winId()), "Premier plan perdu"
        count = len(clicks)
        key(0xA2, True)
        pump(100)
        assert fixture.ctrl_received and not fixture.isDown()
        key(0xA2, False)
        pump(80)
        assert len(clicks) == count
        key(0xA3, True)
        pump(80)
        key(0xA3, False)
        pump(80)
        assert len(clicks) == count + 1
        checks.append("Ctrl gauche restauré en vraie touche Ctrl, clic de Ctrl droite conservé")
        if process:
            adapter.send([adapter.key(0x7B, True, tag=0x54455354), adapter.key(0x7B, False, tag=0x54455354)])
            pump(80)
            process.terminate()
            process.wait(timeout=5)
            process = None
        controller.settings.profile.mappings = [Mapping(0xA2, "mouse_click"),
                                                 Mapping(0xA3, "mouse_click", button="right")]
        if args.frozen:
            controller.settings.save(path)
            process = subprocess.Popen([str(args.frozen.resolve()), "--minimized", "--config-dir", str(path.parent)])
            pump(700)
            assert process.poll() is None
        else:
            assert controller.commit()
        pump(550)
        for source, button, title in [(0xA2, Qt.LeftButton, "gauche"), (0xA3, Qt.RightButton, "droit")]:
            assert user.GetForegroundWindow() == int(fixture.winId()), "Premier plan perdu"
            fixture.mouse_events.clear()
            key(source, True)
            pump(100)
            assert fixture.mouse_events == [(button, True)], fixture.mouse_events
            if button == Qt.LeftButton:
                assert fixture.isDown()
            key(source, False)
            pump(80)
            assert fixture.mouse_events == [(button, True), (button, False)]
            checks.append(f"Clic {title} normal par Ctrl : maintenu jusqu’au relâchement de la touche")
        if process:
            adapter.send([adapter.key(0x7B, True, tag=0x54455354), adapter.key(0x7B, False, tag=0x54455354)])
            pump(80)
            process.terminate()
            process.wait(timeout=5)
            process = None
        controller.settings.profile.mappings = [Mapping(0x70, "sequence", sequence=[[65], [66], [67]], interval_ms=80)]
        if args.frozen:
            controller.settings.save(path)
            process = subprocess.Popen([str(args.frozen.resolve()), "--minimized", "--config-dir", str(path.parent)])
            pump(700)
            assert process.poll() is None
        else:
            assert controller.commit()
        fixture.key_events.clear()
        assert user.GetForegroundWindow() == int(fixture.winId()), "Premier plan perdu"
        key(0x70, True)
        key(0x70, False)
        pump(450)
        assert fixture.key_events == [Qt.Key_A, Qt.Key_B, Qt.Key_C], fixture.key_events
        assert Settings.load(path).profile.mappings[0].sequence == [[65], [66], [67]]
        checks.append("Suite A → B → C sauvegardée, relue au redémarrage et exécutée dans l’ordre")
    finally:
        for source in tuple(held_sources):
            key(source, False)
        if process:
            adapter.send([adapter.key(0x7B, True, tag=0x54455354), adapter.key(0x7B, False, tag=0x54455354)])
            pump(100)
            process.terminate()
            process.wait(timeout=5)
        controller.stop()
        user.SetCursorPos(cursor.x, cursor.y)
        editor.allow_close = True
        editor.close()
        fixture.close()
    result = {"status": "passed", "frozen": str(args.frozen) if args.frozen else None, "checks": checks}
    (path.parents[2] / "validation" / "click-regression.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    run()

