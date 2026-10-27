"""Real orb/key clicks and clipboard insertion into a separate disposable editor."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QMimeData, QPoint, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QVBoxLayout, QWidget
from fortinatus.config import Mapping, Settings
from fortinatus import __version__
from fortinatus.controller import Controller
from fortinatus.desktop_target import DesktopTarget, clone_mime
from fortinatus.keyboard_orb import VirtualKeyboardManager, transcrinator_anchor
from fortinatus.theme import configure_app
from windows_integration import pump, wait_for_idle


def target_process(path):
    app = QApplication([])
    window = QWidget()
    window.setWindowTitle("Claviernator · Éditeur de test isolé")
    window.resize(620, 170)
    window.move(70, 70)
    layout = QVBoxLayout(window)
    first, second = QLineEdit("Début cible fin"), QLineEdit("Deuxième champ")
    layout.addWidget(first)
    layout.addWidget(second)
    first.winId()
    second.winId()
    window.show()
    first.setFocus()
    first.setSelection(6, 5)

    def report():
        state = dict(hwnd=int(window.winId()), first=first.text(), second=second.text(),
                     selection=first.selectedText(), cursor=first.cursorPosition(),
                     first_hwnd=int(first.winId()), second_hwnd=int(second.winId()),
                     second_selection=second.selectedText(),
                     rect=[window.x(), window.y(), window.width(), window.height()],
                     title_point=[window.frameGeometry().left() + 90, window.frameGeometry().top() + 12])
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        try:
            temporary.replace(path)
        except PermissionError:
            # A simultaneous Windows reader may briefly deny FILE_SHARE_DELETE.
            # Keep the previous complete state; the next timer tick retries.
            pass

    timer = QTimer(window)
    timer.timeout.connect(report)
    timer.start(30)
    QTimer.singleShot(80, lambda: (window.raise_(), window.activateWindow(), first.setFocus(), first.setSelection(6, 5)))
    return app.exec()


def run():
    wait_for_idle()
    app = QApplication([])
    configure_app(app)
    root = Path(__file__).resolve().parents[1]
    folder = root / "docs/test-settings/virtual-keyboard"
    folder.mkdir(parents=True, exist_ok=True)
    state_file = folder / "editor-state.json"
    state_file.unlink(missing_ok=True)
    desktop = DesktopTarget()
    previous_window = desktop.user.GetForegroundWindow()
    previous_cursor = QCursor.pos()
    clipboard = app.clipboard()
    previous_clipboard = clone_mime(clipboard.mimeData())
    settings = Settings()
    settings.profile.mappings = [Mapping(0xA2, "mouse_hold"), Mapping(0x56, "disabled")]
    controller = Controller(settings, folder / "settings.json", no_hooks="--hooks" not in sys.argv)
    manager = VirtualKeyboardManager(controller, desktop=desktop)
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--target", str(state_file)])
    expected_window = 0
    checks = []

    def state():
        for _ in range(10):
            try:
                return json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                time.sleep(.005)
        return {}

    def until(predicate, seconds=3):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            pump(20)
            if predicate():
                return
        raise AssertionError("Délai de la fenêtre de test dépassé : " + repr(state()))

    def foreground():
        assert desktop.user.GetForegroundWindow() == expected_window, "Le premier plan a changé ; aucune autre entrée n’est envoyée."

    def click(widget):
        foreground()
        # A companion orb can finish following Transcrinator after a monitor
        # change. Wait for its final location before sending the actual click.
        for attempt in range(3):
            point = widget.mapToGlobal(widget.rect().center())
            QCursor.setPos(point)
            pump(160 if widget is manager.orb else 35)
            if point == widget.mapToGlobal(widget.rect().center()):
                break
        user = desktop.user
        user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user.WindowFromPoint.argtypes = [wintypes.POINT]
        user.WindowFromPoint.restype = wintypes.HWND
        user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        native_point = wintypes.POINT()
        user.GetCursorPos(ctypes.byref(native_point))
        hit = user.GetAncestor(user.WindowFromPoint(native_point), 2)
        native_frame = wintypes.RECT()
        user.GetWindowRect(int(widget.window().winId()), ctypes.byref(native_frame))
        assert hit == int(widget.window().winId()), ("La souris de test n’est pas sur le contrôle.",
            widget.window().geometry().getRect(), (point.x(), point.y()),
            (native_point.x, native_point.y), hit, int(widget.window().winId()),
            (native_frame.left, native_frame.top, native_frame.right, native_frame.bottom),
            widget.window().devicePixelRatio(), widget.window().screen().name())
        foreground()
        desktop.adapter.emit(("mouse", "left", True))
        pump(20)
        desktop.adapter.emit(("mouse", "left", False))
        pump(70)

    try:
        until(lambda: bool(state().get("hwnd")))
        expected_window = state()["hwnd"]
        desktop.user.SetForegroundWindow(expected_window)
        if desktop.user.GetForegroundWindow() != expected_window:
            # Windows may reject a programmatic foreground request. Raise only
            # our own fixture without activation, then click its verified title.
            user = desktop.user
            user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
            user.SetWindowPos(expected_window, -1, 0, 0, 0, 0, 0x13)
            QCursor.setPos(QPoint(*state()["title_point"]))
            pump(60)
            user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
            user.WindowFromPoint.argtypes = [wintypes.POINT]
            user.WindowFromPoint.restype = wintypes.HWND
            point = wintypes.POINT()
            user.GetCursorPos(ctypes.byref(point))
            assert user.GetAncestor(user.WindowFromPoint(point), 2) == expected_window, "La fenêtre de test n’est pas sous le pointeur."
            desktop.adapter.emit(("mouse", "left", True))
            pump(20)
            desktop.adapter.emit(("mouse", "left", False))
        until(lambda: desktop.user.GetForegroundWindow() == expected_window)
        assert state()["selection"] == "cible"
        screens = []
        for screen in app.screens():
            QCursor.setPos(screen.availableGeometry().center())
            pump(450)
            assert screen.availableGeometry().contains(manager.orb.geometry())
            assert manager.orb.size().width() == manager.orb.size().height() == 36
            foreground()
            anchor = transcrinator_anchor(screen)
            if anchor:
                assert manager.orb.geometry().bottom() < anchor[1].top()
            screens.append(dict(name=screen.name(), geometry=screen.geometry().getRect(), dpi=screen.devicePixelRatio()))
        checks.append("L’orbe 36 × 36 suit le pointeur sur les écrans réels, y compris avec des DPI différents")
        click(manager.orb)
        assert manager.panel.isVisible()
        foreground()
        assert state()["selection"] == "cible"
        checks.append("L’orbe et l’ouverture du clavier conservent le premier plan et la sélection")
        start = manager.panel.pos()
        point = manager.panel.handle.mapToGlobal(QPoint(90, 16))
        QCursor.setPos(point)
        pump(40)
        desktop.adapter.emit(("mouse", "left", True))
        try:
            for step in range(1, 7):
                QCursor.setPos(point + QPoint(-step * 10, -step * 5))
                pump(25)
                foreground()
        finally:
            desktop.adapter.emit(("mouse", "left", False))
        pump(100)
        assert manager.panel.pos() != start and state()["selection"] == "cible"
        position = manager.panel.pos()
        manager.panel.hide_keyboard()
        click(manager.orb)
        assert manager.panel.pos() == position and state()["selection"] == "cible"
        checks.append("Glisser la barre du clavier conserve le focus et la sélection ; sa position est retrouvée à la réouverture")
        if len(app.screens()) > 1:
            destination = app.screens()[0]
            point = manager.panel.handle.mapToGlobal(QPoint(90, 16))
            QCursor.setPos(point)
            pump(50)
            desktop.adapter.emit(("mouse", "left", True))
            try:
                QCursor.setPos(destination.availableGeometry().topLeft() + QPoint(300, 140))
                pump(120)
                foreground()
            finally:
                desktop.adapter.emit(("mouse", "left", False))
            pump(150)
            assert destination.availableGeometry().contains(manager.panel.geometry())
            assert manager.panel.size().width() == 900 and manager.panel.size().height() == 320
            assert state()["selection"] == "cible"
            checks.append("Le clavier peut aussi être glissé vers l’autre écran sans perdre la sélection")
        manager.panel.grab().save(str(root / "docs/validation/clavier-natif-dpi-150.png"))
        for base in ("a", "z"):
            item = next(item for item, data in manager.panel.character_buttons if data[0] == base)
            click(item)
            foreground()
        assert manager.panel.text == "az"
        assert state()["selection"] == "cible"
        checks.append("Les clics sur les touches ne prennent pas le focus du document")
        manager.panel.append_text(" é € 😀")
        sentinel = QMimeData()
        sentinel.setText("Claviernator clipboard test")
        sentinel.setHtml("<b>Claviernator clipboard test</b>")
        clipboard.setMimeData(sentinel)
        click(manager.panel.insert_button)
        expected = "Début az é € 😀 fin"
        until(lambda: state().get("first") == expected)
        pump(550)
        assert state()["first"] == expected and state()["second"] == "Deuxième champ"
        assert manager.panel.text == ""
        assert clipboard.text() == "Claviernator clipboard test"
        assert clipboard.mimeData().html() == "<b>Claviernator clipboard test</b>"
        checks.append("Insérer remplace exactement la sélection du premier champ, accents et emoji inclus")
        checks.append("Le presse-papiers texte et HTML est restauré après un seul collage")
        click(manager.panel.modifier_buttons[0xA2][0])
        assert manager.panel.modifiers == {0xA2}, ("Ctrl non sélectionné", manager.panel.text, manager.panel.error.text())
        letter_a = next(item for item, data in manager.panel.character_buttons if data[0] == "a")
        click(letter_a)
        try:
            until(lambda: state().get("selection") == expected)
        except AssertionError as exc:
            raise AssertionError((str(exc), manager.panel.text, manager.panel.error.text(), manager.target)) from exc
        assert manager.panel.text == ""
        foreground()
        checks.append("Ctrl puis A agit sur le document sans ajouter de texte au brouillon")
        # Choose a different field AFTER opening and composing, without closing
        # or reopening the keyboard. Only that new field may receive the paste.
        manager.panel.append_text(" Nouveau champ ✓")
        user = desktop.user
        user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        user.SetWindowPos(expected_window, -1, 0, 0, 0, 0, 0x13)
        field = wintypes.RECT()
        user.GetWindowRect(state()["second_hwnd"], ctypes.byref(field))
        user.SetCursorPos((field.left + field.right) // 2, (field.top + field.bottom) // 2)
        pump(30)
        point = wintypes.POINT()
        user.GetCursorPos(ctypes.byref(point))
        assert user.GetAncestor(user.WindowFromPoint(point), 2) == expected_window
        desktop.adapter.emit(("mouse", "left", True))
        pump(20)
        desktop.adapter.emit(("mouse", "left", False))
        pump(30)
        click(manager.panel.insert_button)
        second_expected = "Deuxième champ Nouveau champ ✓"
        until(lambda: state().get("second") == second_expected)
        pump(500)
        assert state()["first"] == expected and manager.panel.text == ""
        checks.append("Choisir un nouveau champ après ouverture redirige Insérer vers ce champ, sans rouvrir le clavier")
        anchor = transcrinator_anchor()
        if anchor:
            assert manager.orb.geometry().bottom() < anchor[1].top()
            checks.append("L’orbe turquoise reste au-dessus de l’orbe de Transcrinator détectée")
        manager.panel.append_text("À conserver")
        process.terminate()
        process.wait(timeout=5)
        pump(50)
        manager.insert(manager.panel.text)
        assert manager.panel.text == "À conserver"
        assert manager.panel.error.text()
        checks.append("Un champ fermé empêche le collage et conserve le brouillon")
        report = dict(status="passed", version=__version__, hooks_active=controller.service is not None,
                      screens=screens, header_drag_preserves_focus=True, manual_position_restored=True,
                      new_field_after_open_receives_paste=True, compact_after_monitor_change=True,
                      remapped_ctrl_and_disabled_v_bypassed="--hooks" in sys.argv,
                      checks=checks, selection_replaced_once=True,
                      no_activation=True, unicode=True, clipboard_restored=True,
                      closed_target_preserves_draft=True)
        (root / "docs/validation/virtual-keyboard-native.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        manager.stop()
        controller.stop()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        if clipboard.text() == "Claviernator clipboard test":
            clipboard.setMimeData(previous_clipboard)
        else:
            previous_clipboard.deleteLater()
        QCursor.setPos(previous_cursor)
        current = desktop.user.GetForegroundWindow()
        if previous_window and desktop.user.IsWindow(previous_window) and (not current or desktop.process(current) == __import__("os").getpid()):
            desktop.user.SetForegroundWindow(previous_window)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--target":
        raise SystemExit(target_process(Path(sys.argv[2])))
    run()
