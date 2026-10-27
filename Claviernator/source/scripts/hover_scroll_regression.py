"""Verify hover-only scrolling and its saved switch in the compiled application."""
import ctypes
from ctypes import wintypes
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QPlainTextEdit, QWidget
from fortinatus import __version__
from fortinatus.config import Settings
from fortinatus.desktop_target import DesktopTarget
from fortinatus.windows import SingleInstance
from windows_integration import pump, wait_for_idle


def target_process(path):
    app = QApplication([])
    window = QWidget()
    window.setWindowTitle("Claviernator · Défilement de test isolé")
    layout = QHBoxLayout(window)
    editors = [QPlainTextEdit(window), QPlainTextEdit(window), QPlainTextEdit()]
    for index, editor in enumerate(editors):
        editor.setPlainText("\n".join(f"Ligne {i:03} — Zone {index}" for i in range(400)))
        editor.setReadOnly(True)
        editor.viewport().winId()
        if index < 2:
            layout.addWidget(editor)
    other = editors[2]
    other.setWindowTitle("Claviernator · Autre fenêtre de test")
    other.resize(250, 240)
    other.move(1000, 70)
    other.show()
    window.resize(900, 420)
    window.move(70, 70)
    window.show()
    activation = path.with_suffix('.activate')
    activation.unlink(missing_ok=True)

    def report():
        temporary = path.with_suffix('.tmp')
        if activation.exists():
            activation.unlink(missing_ok=True)
            other.raise_()
            other.activateWindow()
        data = dict(hwnd=int(window.winId()), other=int(other.winId()),
                    panes=[int(editor.viewport().winId()) for editor in editors],
                    scroll=[editor.verticalScrollBar().value() for editor in editors])
        temporary.write_text(json.dumps(data), encoding='utf-8')
        try:
            temporary.replace(path)
        except PermissionError:
            pass
    timer = QTimer(window)
    timer.timeout.connect(report)
    timer.start(30)
    def ready():
        window.raise_()
        window.activateWindow()
        editors[0].setFocus()
        for editor in editors:
            editor.verticalScrollBar().setValue(140)
    QTimer.singleShot(100, ready)
    return app.exec()


def run():
    import comtypes.client
    root = Path(__file__).resolve().parents[1]
    exe = root/'dist'/f'Claviernator-{__version__}'/'Claviernator.exe'
    guard = SingleInstance()
    assert guard.acquire(), "Une instance existante empêche le test isolé."
    guard.close()
    wait_for_idle()
    app = QApplication([])
    desktop = DesktopTarget()
    user = desktop.user
    cursor = QCursor.pos()
    folder = root/'docs/test-settings/hover-scroll'
    folder.mkdir(parents=True, exist_ok=True)
    state_file = folder/'state.json'
    state_file.unlink(missing_ok=True)
    config = folder/'settings.json'
    Settings(start_minimized=True).save(config)
    before = Settings.load(config)
    fixture = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--target', str(state_file)])
    frozen = None
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user.MonitorFromWindow.restype = wintypes.HANDLE
    user.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user.MonitorFromPoint.restype = wintypes.HANDLE

    def state():
        for _ in range(10):
            try:
                return json.loads(state_file.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                time.sleep(.005)
        return {}
    def until(predicate):
        deadline = time.monotonic()+6
        while time.monotonic() < deadline:
            pump(25)
            value = predicate()
            if value:
                return value
        raise AssertionError('Délai dépassé : '+repr(state()))
    def window_named(name):
        found = []
        def collect(hwnd, unused):
            title = ctypes.create_unicode_buffer(256)
            user.GetWindowTextW(hwnd, title, 256)
            if frozen and desktop.process(hwnd) == frozen.pid and title.value == name and user.IsWindowVisible(hwnd):
                found.append(int(hwnd))
            return True
        user.EnumWindows(callback_type(collect), 0)
        return found[0] if found else None
    def pointer_at(x, y, expected):
        user.SetCursorPos(x, y)
        pump(45)
        point = wintypes.POINT()
        user.GetCursorPos(ctypes.byref(point))
        assert user.GetAncestor(user.WindowFromPoint(point), 2) == expected, 'Une autre fenêtre couvre la cible de test.'
    def click_at(x, y, expected):
        pointer_at(x, y, expected)
        desktop.adapter.emit(('mouse','left',True))
        pump(20)
        desktop.adapter.emit(('mouse','left',False))
        pump(60)
    def point_in(hwnd, expected, click=False, vertical=.5):
        rect = wintypes.RECT()
        assert user.GetWindowRect(hwnd, ctypes.byref(rect))
        action = click_at if click else pointer_at
        action((rect.left+rect.right)//2, rect.top + round((rect.bottom-rect.top)*vertical), expected)
    try:
        target = until(lambda: state().get('hwnd'))
        until(lambda: state().get('scroll') == [140,140,140])
        user.SetWindowPos(target, -1, 0, 0, 0, 0, 0x13)
        rect = wintypes.RECT()
        user.GetWindowRect(target, ctypes.byref(rect))
        click_at(rect.left+90, rect.top+12, target)
        frozen = subprocess.Popen([str(exe),'--minimized','--config-dir',str(folder)])
        down = until(lambda: window_named('Claviernator · Défiler vers le bas'))
        up = until(lambda: window_named('Claviernator · Défiler vers le haut'))
        # Check that the larger targets keep their logical size at both DPIs.
        screens = []
        for screen in app.screens():
            QCursor.setPos(screen.availableGeometry().center())
            pump(450)
            point = wintypes.POINT()
            user.GetCursorPos(ctypes.byref(point))
            for arrow in (up, down):
                assert user.MonitorFromPoint(point, 2) == user.MonitorFromWindow(arrow, 2)
                user.GetWindowRect(arrow, ctypes.byref(rect))
                assert abs((rect.right-rect.left)/screen.devicePixelRatio()-54) <= 1
                assert abs((rect.bottom-rect.top)/screen.devicePixelRatio()-28) <= 1
            screens.append(dict(name=screen.name(), dpi=screen.devicePixelRatio()))
        # Click left, merely visit right: the left pane must keep the wheel.
        panes = state()['panes']
        point_in(panes[0], target, click=True)
        point_in(panes[1], target)
        pump(250)
        initial = state()['scroll'].copy()
        point_in(down, down)
        pump(100)
        assert state()['scroll'] == initial
        pump(750)
        lowered = state()['scroll'].copy()
        assert lowered[0] > initial[0] and lowered[1:] == initial[1:], (initial,lowered)
        assert user.GetForegroundWindow() == target
        # Both ends of the taller central hover area must keep scrolling.
        for vertical in (.4, .78):
            previous = state()['scroll'][0]
            point_in(down, down, vertical=vertical)
            pump(300)
            assert state()['scroll'][0] > previous
        point_in(panes[1], target)
        pump(150)
        stopped = state()['scroll'].copy()
        pump(400)
        assert state()['scroll'] == stopped
        # A new click chooses right. Passing over left must not undo that choice.
        point_in(panes[1], target, click=True)
        point_in(panes[0], target)
        pump(250)
        point_in(up, up)
        pump(850)
        raised = state()['scroll'].copy()
        assert raised[1] < stopped[1] and raised[0] == stopped[0] and raised[2] == stopped[2]
        assert user.GetForegroundWindow() == target
        point_in(panes[0], target)
        pump(100)
        # Keyboard-only activation of another window must not replace the last click.
        state_file.with_suffix('.activate').touch()
        other = state()['other']
        until(lambda: user.GetForegroundWindow() == other)
        point_in(down, down)
        pump(850)
        inactive = state()['scroll'].copy()
        assert inactive[1] > raised[1] and inactive[0] == raised[0] and inactive[2] == raised[2]
        assert user.GetForegroundWindow() == other
        # Opening our own keyboard also preserves that external scroll destination.
        orb = until(lambda: window_named('Claviernator · Orbe du clavier'))
        point_in(orb, orb, click=True)
        pump(200)
        before_keyboard = state()['scroll'].copy()
        point_in(up, up)
        pump(650)
        assert state()['scroll'][1] < before_keyboard[1]
        assert state()['scroll'][0] == before_keyboard[0] and state()['scroll'][2] == before_keyboard[2]
        assert user.GetForegroundWindow() == other
        point_in(orb, orb, click=True)
        # Open this same instance, turn the home switch off, then restart it.
        subprocess.run([str(exe),'--config-dir',str(folder)], check=True, timeout=6)
        main = until(lambda: window_named('Claviernator'))
        lib = comtypes.client.GetModule('UIAutomationCore.dll')
        uia = comtypes.client.CreateObject(lib.CUIAutomation, interface=lib.IUIAutomation)
        element = uia.ElementFromHandle(main)
        matches = element.FindAll(4,uia.CreatePropertyCondition(30005,'Flèches de défilement'))
        control = next((matches.GetElement(i) for i in range(matches.Length) if not matches.GetElement(i).CurrentIsOffscreen),None)
        assert control, 'Interrupteur introuvable sur l’accueil.'
        bounds = control.CurrentBoundingRectangle
        click_at((bounds.left+bounds.right)//2,(bounds.top+bounds.bottom)//2,main)
        until(lambda: not Settings.load(config).hover_scroll)
        assert not window_named('Claviernator · Défiler vers le haut')
        assert not window_named('Claviernator · Défiler vers le bas')
        after = Settings.load(config)
        assert after.profiles == before.profiles and after.virtual_keyboard
        frozen.terminate()
        frozen.wait(timeout=5)
        frozen = subprocess.Popen([str(exe),'--minimized','--config-dir',str(folder)])
        until(lambda: window_named('Claviernator · Orbe du clavier'))
        pump(500)
        assert not window_named('Claviernator · Défiler vers le haut')
        assert not window_named('Claviernator · Défiler vers le bas')
        report = dict(status='passed',version=__version__,scroll_values=[initial,lowered,raised],
                      exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                      arrow_size_logical=[54,28], screens=screens, tall_hover_zone=True,
                      hover_without_click=True,dwell_before_scroll=True,stops_on_leave=True,
                      last_clicked_pane=True,hover_does_not_retarget=True,
                      inactive_clicked_pane=True,keyboard_clicks_preserve_scroll_target=True,
                      focus_preserved=True,home_switch_hides_arrows=True,disabled_after_restart=True,
                      profiles_unchanged=True)
        (root/'docs/validation/hover-scroll-native.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
    finally:
        for process in (frozen,fixture):
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        QCursor.setPos(cursor)


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--target':
        raise SystemExit(target_process(Path(sys.argv[2])))
    run()
