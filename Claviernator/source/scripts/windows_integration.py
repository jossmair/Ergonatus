"""Real WH_KEYBOARD_LL + SendInput checks, restricted to our own Qt fixture.

No user settings or startup registry values are changed. Input stops immediately
if the fixture loses the foreground. Synthetic test input has a distinct tag.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QPushButton
from fortinatus.config import Mapping, Profile
from fortinatus.theme import configure_app
from fortinatus.windows import HookService, WindowsInput


def pump(milliseconds):
    # QTest.qWait holds the Python GIL and starves Python low-level callbacks.
    # Mimic QApplication.exec: dispatch Qt, then release the GIL while waiting.
    deadline = time.monotonic() + milliseconds / 1000
    while time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.004)
    QApplication.processEvents()


class Target(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.events = []
        self.button_events = []
        self.key_events = []
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setWindowTitle("Claviernator · Vérification des entrées Windows")
        self.resize(600, 360)

    def keyPressEvent(self, event):
        self.key_events.append((event.text(), int(event.modifiers().value), event.key()))
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.events.append("mouse-down")
        self.button_events.append((event.button(), True))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.events.append("mouse-up")
        self.button_events.append((event.button(), False))
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.events.append("drag")
        if event.buttons() & Qt.RightButton:
            self.events.append("right-drag")
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.events.append("double-click")
        super().mouseDoubleClickEvent(event)


def wait_for_idle():
    # Do not take focus while the user is finishing a keystroke in another app.
    class LastInput(ctypes.Structure):
        _fields_ = [("size", wintypes.UINT), ("time", wintypes.DWORD)]
    idle_user = ctypes.WinDLL("user32")
    idle_kernel = ctypes.WinDLL("kernel32")
    idle_kernel.GetTickCount.restype = wintypes.DWORD
    information = LastInput(ctypes.sizeof(LastInput), 0)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        idle_user.GetLastInputInfo(ctypes.byref(information))
        if (idle_kernel.GetTickCount() - information.time) & 0xFFFFFFFF >= 1000:
            break
        time.sleep(.05)
    else:
        raise RuntimeError("Le clavier est en cours d’utilisation ; test interrompu sans envoyer d’entrée.")


def run():
    wait_for_idle()
    app = QApplication([])
    configure_app(app)
    target = Target()
    target.show()
    target.activateWindow()
    target.setFocus()
    adapter = WindowsInput()
    user = adapter.user
    user.GetForegroundWindow.restype = wintypes.HWND
    user.SetForegroundWindow.argtypes = [wintypes.HWND]
    user.BringWindowToTop.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype = wintypes.DWORD
    user.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    old_cursor = wintypes.POINT()
    user.GetCursorPos(ctypes.byref(old_cursor))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    current_thread = kernel.GetCurrentThreadId()
    foreground_thread = user.GetWindowThreadProcessId(user.GetForegroundWindow(), None)
    attached = foreground_thread != current_thread and user.AttachThreadInput(current_thread, foreground_thread, True)
    try:
        target.raise_()
        user.BringWindowToTop(int(target.winId()))
        user.SetForegroundWindow(int(target.winId()))
        target.setFocus()
    finally:
        if attached:
            user.AttachThreadInput(current_thread, foreground_thread, False)
    pump(200)
    states, notices, checks = [], [], []
    audit = []
    original_send = WindowsInput.send
    def audited_send(adapter, inputs):
        audit.append([(item.value.keyboard.vk, item.value.keyboard.scan, item.value.keyboard.flags) for item in inputs if item.type == 1])
        return original_send(adapter, inputs)
    WindowsInput.send = audited_send
    hook = HookService(states.append, notices.append)
    profile = Profile(mappings=[Mapping(0x75, keys=[90]), Mapping(0x76, keys=[0xA2, 65]),
                                Mapping(0x77, "mouse_hold"), Mapping(0x78, "mouse_toggle"),
                                Mapping(0x79, "double_click")])
    held = set()

    def guard():
        if user.GetForegroundWindow() != int(target.winId()):
            raise RuntimeError("La fenêtre de test a perdu le premier plan ; entrées interrompues.")

    def key(vk, down):
        guard()
        adapter.send([adapter.key(vk, down, tag=0x54455354)])
        if down:
            held.add(vk)
        else:
            held.discard(vk)
        pump(65)

    def tap(vk):
        key(vk, True)
        key(vk, False)

    try:
        guard()
        target.clear()
        adapter.emit(("text", "test"))
        pump(80)
        assert target.toPlainText() == "test", repr(target.toPlainText())
        target.clear()
        checks.append("SendInput natif vers la fenêtre de test")
        hook.start(profile, True)
        tap(0x75)
        assert target.toPlainText().lower() == "z", repr(target.toPlainText())
        checks.append("Remappage F6 → Z par hook Windows")
        tap(0x76)
        assert target.textCursor().selectedText().lower() == "z"
        checks.append("Combinaison F7 → Ctrl + A et relâchement des modificateurs")

        profile.invert_numbers = True
        hook.configure(profile, True)
        target.clear()
        tap(49)
        key(0xA0, True)
        tap(50)
        key(0xA0, False)
        assert target.toPlainText() == "1é", repr(target.toPlainText())
        checks.append("Inversion AZERTY : 1 sans Maj et é avec Maj")

        profile.mappings.append(Mapping(0x74, "text", text="Ça va 🌿"))
        hook.configure(profile, True)
        target.clear()
        tap(0x74)
        pump(120)
        assert target.toPlainText() == "Ça va 🌿", repr(target.toPlainText())
        checks.append("Texte Unicode et paire UTF-16 sans presse-papiers")

        point = target.viewport().mapToGlobal(QPoint(80, 80))
        QCursor.setPos(point)
        pump(80)
        target.events.clear()
        key(0x77, True)
        assert "mouse-down" in target.events, target.events
        adapter.emit(("move", 25, 0))
        pump(80)
        assert "drag" in target.events, target.events
        assert "mouse-up" not in target.events
        key(0x77, False)
        assert "mouse-up" in target.events, target.events
        checks.append("Clic maintenu, déplacement en glissant et relâchement réel")

        pump(550)
        target.events.clear()
        tap(0x78)
        assert "mouse-down" in target.events and "mouse-up" not in target.events, target.events
        tap(0x78)
        assert "mouse-up" in target.events, target.events
        checks.append("Clic verrouillé puis libéré au deuxième appui")

        pump(550)
        target.events.clear()
        tap(0x79)
        assert "double-click" in target.events, target.events
        checks.append("Double-clic en un appui")

        pump(550)
        target.events.clear()
        key(0x77, True)
        hook.configure(Profile(), True)
        pump(80)
        assert "mouse-up" in target.events
        key(0x77, False)
        checks.append("Changement de profil : clic immédiatement libéré")

        click_target = QPushButton("Tester le clic", target.viewport())
        click_target.setGeometry(330, 40, 220, 70)
        clicks = []
        click_target.clicked.connect(lambda: clicks.append(True))
        click_target.show()
        point = click_target.mapToGlobal(click_target.rect().center())
        QCursor.setPos(point)
        profile.mappings.extend([Mapping(0xA2, "mouse_hold"), Mapping(0xA3, "mouse_hold")])
        hook.configure(profile, True)
        pump(80)
        for source in (0xA2, 0xA3):
            count = len(clicks)
            key(source, True)
            assert click_target.isDown(), (source, target.events)
            key(source, False)
            assert len(clicks) == count + 1, (source, clicks, notices)
        checks.append("Ctrl gauche et Ctrl droite : activation réelle d’un bouton par clic")
        profile.mappings = [m for m in profile.mappings if m.source not in (0xA2, 0xA3)]
        QCursor.setPos(point.x() - 250, point.y() + 100)

        profile.sticky_modifiers = True
        hook.configure(profile, True)
        target.selectAll()
        tap(0xA2)
        tap(65)
        assert target.textCursor().selectedText() == target.toPlainText()
        checks.append("Modificateur séquentiel Ctrl, puis A")

        pump(550)
        target.events.clear()
        tap(0x78)
        tap(0x7B)
        assert "mouse-up" in target.events
        assert states[-1] is False
        assert notices[-1].startswith("Pause d’urgence")
        checks.append("F12 : libération du clic verrouillé et pause du service")

        profile = Profile(mappings=[Mapping(0x70, "mouse_click"), Mapping(0x71, "mouse_click", button="right"),
                                    Mapping(0x72, "mouse_hold", button="right")])
        hook.configure(profile, True)
        point = target.viewport().mapToGlobal(QPoint(80, 140))
        QCursor.setPos(point)
        pump(550)
        for source, button, title in [(0x70, Qt.LeftButton, "gauche"), (0x71, Qt.RightButton, "droit")]:
            target.button_events.clear()
            target.events.clear()
            key(source, True)
            assert target.button_events == [(button, True)], target.button_events
            key(source, True)
            assert target.button_events == [(button, True)], target.button_events
            adapter.emit(("move", 10, 0))
            pump(50)
            assert ("drag" if button == Qt.LeftButton else "right-drag") in target.events
            key(source, False)
            assert target.button_events == [(button, True), (button, False)], target.button_events
            checks.append(f"Clic {title} normal : reste enfoncé jusqu’au relâchement de la touche")
        pump(550)
        target.button_events.clear()
        target.events.clear()
        key(0x72, True)
        assert target.button_events == [(Qt.RightButton, True)], target.button_events
        adapter.emit(("move", 25, 0))
        pump(80)
        assert "right-drag" in target.events
        assert target.button_events == [(Qt.RightButton, True)]
        key(0x72, False)
        assert target.button_events[-1] == (Qt.RightButton, False)
        checks.append("Clic droit maintenu : glisser puis relâcher en relevant la touche")

        profile = Profile(mappings=[Mapping(0xA3, "sequence", sequence=[[0xA2, 65], [68], [69]], interval_ms=80)])
        hook.configure(profile, True)
        target.setPlainText("Texte à remplacer")
        target.setFocus()
        tap(0xA3)
        pump(450)
        assert target.toPlainText().lower() == "de", repr(target.toPlainText())
        checks.append("Suite par Ctrl droite : Ctrl + A puis D puis E, après relâchement de la touche")
    except Exception:
        print(json.dumps({"checks_completed": checks, "notices": notices, "text": target.toPlainText(), "keys": target.key_events[-30:], "audit": audit[-10:], "active": hook.engine.enabled if hook.engine else None}, ensure_ascii=True))
        raise
    finally:
        hook.stop()
        WindowsInput.send = original_send
        # Release only test keys whose downs were delivered by this fixture.
        for vk in held:
            try:
                adapter.send([adapter.key(vk, False)])
            except RuntimeError:
                pass
        user.SetCursorPos(old_cursor.x, old_cursor.y)
        target.close()
        app.processEvents()
    result = {"status": "passed", "checks": checks, "count": len(checks)}
    folder = Path(__file__).resolve().parents[1] / "docs" / "validation"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "windows-native.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    run()

