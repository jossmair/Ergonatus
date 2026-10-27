"""End-to-end check of the compiled keyboard using Windows accessibility."""
import ctypes
from ctypes import wintypes
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comtypes.client  # Optional native test dependency; not used by Claviernator.
from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication
from fortinatus import __version__
from fortinatus.config import Mapping, Settings
from fortinatus.desktop_target import DesktopTarget, clone_mime
from fortinatus.windows import SingleInstance
from windows_integration import pump, wait_for_idle


def run():
    root = Path(__file__).resolve().parents[1]
    exe = root / "dist" / f"Claviernator-{__version__}" / "Claviernator.exe"
    guard = SingleInstance()
    assert guard.acquire(), "Une instance existante empêche le test isolé."
    guard.close()
    wait_for_idle()
    lib = comtypes.client.GetModule("UIAutomationCore.dll")
    uia = comtypes.client.CreateObject(lib.CUIAutomation, interface=lib.IUIAutomation)
    app = QApplication([])
    desktop = DesktopTarget()
    user = desktop.user
    clipboard = app.clipboard()
    original_clipboard = clone_mime(clipboard.mimeData())
    original_cursor = QCursor.pos()
    folder = root / "docs/test-settings/frozen-keyboard"
    folder.mkdir(parents=True, exist_ok=True)
    state_file = folder / "state.json"
    state_file.unlink(missing_ok=True)
    config = folder / "settings.json"
    settings = Settings(start_minimized=True)
    settings.profile.mappings = [Mapping(0xA2, "mouse_hold"), Mapping(0xA3, "mouse_hold"),
                                 Mapping(0x56, "disabled"), Mapping(0x08, "disabled")]
    settings.save(config)
    before_settings = config.read_bytes()
    fixture = subprocess.Popen([sys.executable, str(root / "scripts/virtual_keyboard_regression.py"), "--target", str(state_file)])
    frozen = None
    physical_held = set()
    paste_payload = " — collé ✓"

    def state():
        # Windows can briefly deny opening the file during the atomic replace.
        # Retry reads, rather than treating a transient file lock as app output.
        for _ in range(10):
            try:
                return json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                time.sleep(.005)
        return {}

    def until(predicate):
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            pump(25)
            value = predicate()
            if value:
                return value
        raise AssertionError("Délai du test compilé dépassé : " + repr(state()))

    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]

    def window_named(name):
        found = []
        def collect(hwnd, unused):
            text = ctypes.create_unicode_buffer(256)
            user.GetWindowTextW(hwnd, text, 256)
            if frozen and desktop.process(hwnd) == frozen.pid and text.value == name:
                found.append(int(hwnd))
            return True
        user.EnumWindows(callback_type(collect), 0)
        return found[0] if found else None

    user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.WindowFromPoint.argtypes = [wintypes.POINT]
    user.WindowFromPoint.restype = wintypes.HWND
    user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user.MonitorFromPoint.restype = wintypes.HANDLE
    user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user.MonitorFromWindow.restype = wintypes.HANDLE

    def click_at(x, y, expected_root, button="left"):
        user.SetCursorPos(x, y)
        pump(50)
        point = wintypes.POINT()
        user.GetCursorPos(ctypes.byref(point))
        hit = user.GetAncestor(user.WindowFromPoint(point), 2)
        if hit != expected_root:
            hit_title = ctypes.create_unicode_buffer(256)
            expected_title = ctypes.create_unicode_buffer(256)
            user.GetWindowTextW(hit, hit_title, 256)
            user.GetWindowTextW(expected_root, expected_title, 256)
            raise AssertionError(("Une autre fenêtre recouvre le contrôle de test.", (x,y), hit_title.value, expected_title.value))
        desktop.adapter.emit(("mouse", button, True))
        pump(25)
        desktop.adapter.emit(("mouse", button, False))
        pump(80)

    def menu_item(name):
        handles = []
        def collect(hwnd, unused):
            if frozen and desktop.process(hwnd) == frozen.pid and user.IsWindowVisible(hwnd):
                handles.append(int(hwnd))
            return True
        user.EnumWindows(callback_type(collect), 0)
        for hwnd in handles:
            try:
                root_element = uia.ElementFromHandle(hwnd)
                item = root_element.FindFirst(4, uia.CreatePropertyCondition(30005, name))
                if item and not item.CurrentIsOffscreen:
                    return hwnd, item
            except Exception:
                pass
        return None

    def right_click_orb():
        user.GetWindowRect(orb, ctypes.byref(rect))
        click_at((rect.left+rect.right)//2, (rect.top+rect.bottom)//2, orb, button="right")

    def choose_menu_item(name):
        hwnd, item = until(lambda: menu_item(name))
        bounds = item.CurrentBoundingRectangle
        click_at((bounds.left+bounds.right)//2, (bounds.top+bounds.bottom)//2, hwnd)

    def physical_key(vk, down):
        if down:
            assert user.GetForegroundWindow() == target, "Le premier plan a changé ; essai physique interrompu."
        desktop.adapter.send([desktop.adapter.key(vk, down, tag=0x54455354)])
        physical_held.add(vk) if down else physical_held.discard(vk)
        pump(50)

    try:
        target = until(lambda: state().get("hwnd"))
        # Activate our own title without changing the editor's selection.
        user.SetWindowPos(target, -1, 0, 0, 0, 0, 0x13)
        title = state()["title_point"]
        # Qt's title point is logical; use the native frame for a DPI-safe click.
        rect = wintypes.RECT()
        user.GetWindowRect(target, ctypes.byref(rect))
        click_at(rect.left + 90, rect.top + 12, target)
        until(lambda: user.GetForegroundWindow() == target)
        frozen = subprocess.Popen([str(exe), "--minimized", "--config-dir", str(folder)])
        orb = until(lambda: window_named("Claviernator · Orbe du clavier"))
        assert user.GetForegroundWindow() == target, "Le démarrage de l’orbe a pris le focus."
        screens = []
        for screen in app.screens():
            QCursor.setPos(screen.availableGeometry().center())
            pump(450)
            point = wintypes.POINT()
            user.GetCursorPos(ctypes.byref(point))
            assert user.MonitorFromPoint(point, 2) == user.MonitorFromWindow(orb, 2)
            user.GetWindowRect(orb, ctypes.byref(rect))
            assert abs(rect.right - rect.left - 36 * screen.devicePixelRatio()) <= 1
            assert user.GetForegroundWindow() == target and state()["selection"] == "cible"
            screens.append(dict(name=screen.name(), dpi=screen.devicePixelRatio(), orb_width=rect.right - rect.left))
        user.GetWindowRect(orb, ctypes.byref(rect))
        click_at((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2, orb)
        panel = until(lambda: window_named("Claviernator · Clavier virtuel"))
        assert user.GetForegroundWindow() == target and state()["selection"] == "cible", (target, desktop.capture(), state())
        user.GetWindowRect(panel, ctypes.byref(rect))
        start_x, start_y = rect.left, rect.top
        pointer_x, pointer_y = start_x + 100, start_y + 28
        user.SetCursorPos(pointer_x, pointer_y)
        pump(40)
        point = wintypes.POINT(pointer_x, pointer_y)
        assert user.GetAncestor(user.WindowFromPoint(point), 2) == panel, (
            "La barre de déplacement du clavier est recouverte.", pointer_x, pointer_y,
            user.GetAncestor(user.WindowFromPoint(point), 2), panel, desktop.capture())
        desktop.adapter.emit(("mouse", "left", True))
        try:
            for step in range(1, 7):
                user.SetCursorPos(pointer_x - step * 10, pointer_y - step * 5)
                pump(30)
                assert user.GetForegroundWindow() == target
        finally:
            desktop.adapter.emit(("mouse", "left", False))
        pump(120)
        user.GetWindowRect(panel, ctypes.byref(rect))
        assert (rect.left, rect.top) != (start_x, start_y), "Le clavier compilé ne s’est pas déplacé."
        assert state()["selection"] == "cible" and user.GetForegroundWindow() == target
        for screen in app.screens():
            user.GetWindowRect(panel, ctypes.byref(rect))
            user.SetCursorPos(rect.left + 100, rect.top + 28)
            pump(40)
            desktop.adapter.emit(("mouse", "left", True))
            try:
                QCursor.setPos(screen.availableGeometry().topLeft() + QPoint(300, 140))
                pump(250)
            finally:
                desktop.adapter.emit(("mouse", "left", False))
            pump(200)
            point = wintypes.POINT()
            user.GetCursorPos(ctypes.byref(point))
            assert user.MonitorFromPoint(point, 2) == user.MonitorFromWindow(panel, 2)
            user.GetWindowRect(panel, ctypes.byref(rect))
            assert abs((rect.right - rect.left) / screen.devicePixelRatio() - 900) <= 2
            assert abs((rect.bottom - rect.top) / screen.devicePixelRatio() - 320) <= 2
            assert state()["selection"] == "cible" and user.GetForegroundWindow() == target
        element = uia.ElementFromHandle(panel)

        def press(name):
            assert user.GetForegroundWindow() == target, "Le premier plan a changé."
            # Qt exposes checkable tabs as a different accessible control type.
            condition = uia.CreatePropertyCondition(30005, name)
            matches = element.FindAll(4, condition)
            button = next((matches.GetElement(i) for i in range(matches.Length)
                           if not matches.GetElement(i).CurrentIsOffscreen
                           and matches.GetElement(i).CurrentControlType in (50000, 50002)), None)
            if not button:
                descendants = element.FindAll(4, uia.CreateTrueCondition())
                # The native property-condition path can mismatch UTF-16
                # supplementary emoji. Compare the returned BSTR names locally.
                button = next((descendants.GetElement(i) for i in range(descendants.Length)
                               if descendants.GetElement(i).CurrentName == name
                               and not descendants.GetElement(i).CurrentIsOffscreen
                               and descendants.GetElement(i).CurrentControlType in (50000, 50002)), None)
            if not button:
                descendants = element.FindAll(4, uia.CreateTrueCondition())
                details = [(descendants.GetElement(i).CurrentName, descendants.GetElement(i).CurrentControlType,
                            bool(descendants.GetElement(i).CurrentIsOffscreen)) for i in range(descendants.Length)]
                raise AssertionError("Bouton accessible introuvable : " + name + " : " + repr(details))
            bounds = button.CurrentBoundingRectangle
            click_at((bounds.left + bounds.right) // 2, (bounds.top + bounds.bottom) // 2, panel)
            assert user.GetForegroundWindow() == target, (name, desktop.capture(), state())

        for caption in ("a", "z", "Caractères", "é", "Signes", "€", "Émojis", "❤️", "Clavier", "⌫",
                        "Caractères", "Émojis", "😊"):
            press(caption)
        assert state()["selection"] == "cible"
        clipboard.setText("Claviernator compiled clipboard")
        press("Insérer dans la zone de saisie précédente")
        expected = "Début azé€😊 fin"
        until(lambda: state().get("first") == expected)
        pump(600)
        assert state()["first"] == expected and state()["second"] == "Deuxième champ"
        assert clipboard.text() == "Claviernator compiled clipboard"
        press("Clavier")
        press("b")
        # Reproduce the reported obstruction: put our keyboard over field two.
        user.GetWindowRect(state()["second_hwnd"], ctypes.byref(rect))
        field_x, field_y = (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
        user.SetWindowPos(panel, -1, rect.left - 60, rect.top - 120, 0, 0, 0x11)
        pump(400)
        assert user.GetAncestor(user.WindowFromPoint(wintypes.POINT(field_x, field_y)), 2) == panel
        press("Choisir où écrire")
        until(lambda: not user.IsWindowVisible(panel))
        user.SetCursorPos(field_x, field_y)
        pump(60)
        assert user.GetAncestor(user.WindowFromPoint(wintypes.POINT(field_x, field_y)), 2) == target
        desktop.adapter.emit(("mouse", "left", True))
        try:
            pump(350)
            assert not user.IsWindowVisible(panel), "Le clavier est revenu pendant l’appui souris."
        finally:
            desktop.adapter.emit(("mouse", "left", False))
        until(lambda: user.IsWindowVisible(panel))
        # Qt may keep native focus on the top-level HWND and route editing to
        # its focused child internally. The paste below verifies field two.
        assert desktop.capture().window == target
        assert user.GetForegroundWindow() == target
        press("Insérer dans la zone de saisie précédente")
        until(lambda: state().get("second") == "Deuxième champb")
        pump(550)
        assert state()["first"] == expected and clipboard.text() == "Claviernator compiled clipboard"
        # This footer control edits the document, including with an empty draft
        # and on pages where the local composition backspace is not present.
        press("Caractères")
        press("Effacer")
        until(lambda: state().get("second") == "Deuxième champ")
        press("Clavier")
        press("c")
        press("Touches")
        press("Effacer")
        until(lambda: state().get("second") == "Deuxième cham")
        assert state()["first"] == expected
        press("Insérer dans la zone de saisie précédente")
        until(lambda: state().get("second") == "Deuxième chamc")
        pump(550)
        assert clipboard.text() == "Claviernator compiled clipboard"
        press("Clavier")
        press("Ctrl")
        press("a")
        until(lambda: state().get("second_selection") == "Deuxième chamc")
        assert config.read_bytes() == before_settings
        # Send non-bypass Ctrl+V events through the real keyboard hook. V is
        # disabled in this profile; both Ctrl keys still serve as mouse clicks.
        press("Masquer le clavier virtuel")
        until(lambda: not user.IsWindowVisible(panel))
        user.GetWindowRect(state()["second_hwnd"], ctypes.byref(rect))
        click_at((rect.left+rect.right)//2, (rect.top+rect.bottom)//2, target)
        clipboard.setText(paste_payload)
        expected_second = "Deuxième chamc"
        for control in (0xA2, 0xA3):
            pump(550)  # Separate real clicks from Qt's double-click interval.
            physical_key(control, True)
            until(lambda: user.GetAsyncKeyState(1) & 0x8000)
            for _ in range(2 if control == 0xA2 else 1):
                physical_key(0x56, True)
                expected_second += paste_payload
                until(lambda: state().get("second") == expected_second)
                physical_key(0x56, False)
                assert not user.GetAsyncKeyState(1) & 0x8000
            physical_key(control, False)
            assert not any(user.GetAsyncKeyState(vk) & 0x8000 for vk in (0xA2,0xA3,0x56,1))
        assert state()["first"] == expected and clipboard.text() == paste_payload
        clipboard.setText("Claviernator compiled clipboard")
        user.GetWindowRect(orb, ctypes.byref(rect))
        click_at((rect.left+rect.right)//2, (rect.top+rect.bottom)//2, orb)
        until(lambda: user.IsWindowVisible(panel))
        # The orb opens the exact tray menu, without toggling the keyboard.
        right_click_orb()
        until(lambda: menu_item("Quitter Claviernator"))
        assert user.IsWindowVisible(panel)
        choose_menu_item("Ouvrir Claviernator")
        until(lambda: (main := window_named("Claviernator")) and user.IsWindowVisible(main))
        right_click_orb()
        choose_menu_item("Mettre en pause")
        right_click_orb()
        until(lambda: menu_item("Activer"))
        choose_menu_item("Quitter Claviernator")
        until(lambda: frozen.poll() is not None)
        assert frozen.returncode == 0 and config.read_bytes() == before_settings
        report = dict(status="passed", version=__version__, executable=str(exe),
                      executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                      screens=screens, follows_available_monitors=True, follows_both_monitors=len(screens) > 1,
                      header_drag_preserves_focus=True, compact_size_verified=True,
                      compact_after_monitor_changes=len(screens) > 1, new_field_after_open_receives_paste=True,
                      hidden_field_was_covered=True, choose_field_hides_keyboard=True,
                      picker_waits_for_mouse_release=True, picker_auto_returns=True,
                      picker_preserves_draft=True,
                      erase_edits_selected_field=True, erase_available_across_pages=True,
                      erase_works_with_empty_draft=True, erase_preserves_prepared_text=True,
                      remapped_backspace_bypassed=True,
                      physical_ctrl_v_pastes_with_mouse_mapping=True,
                      left_and_right_ctrl_paste=True, repeated_paste_without_releasing_ctrl=True,
                      paste_overrides_disabled_v=True, paste_releases_mouse=True,
                      paste_releases_all_keys=True,
                      orb_right_click_opens_tray_menu=True, right_click_keeps_keyboard_open=True,
                      orb_menu_open_pause_quit_work=True, orb_menu_pause_label_updates=True,
                      graceful_quit_from_orb=True,
                      shortcut_follows_new_field=True,
                      startup_preserves_focus=True, real_orb_and_key_clicks=True,
                      composed_emoji_erased_as_one_character=True,
                      selection_preserved_until_insert=True, unicode_inserted_once=True,
                      remapped_ctrl_and_disabled_v_bypassed=True,
                      clipboard_restored=True, saved_settings_unchanged=True)
        (root / "docs/validation/frozen-keyboard.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        for vk in tuple(physical_held):
            desktop.adapter.send([desktop.adapter.key(vk, False, tag=0x54455354)])
        if physical_held:
            pump(150)
        if frozen and frozen.poll() is None:
            frozen.terminate()
            frozen.wait(timeout=5)
        if fixture.poll() is None:
            fixture.terminate()
            fixture.wait(timeout=5)
        if clipboard.text() in ("Claviernator compiled clipboard", paste_payload):
            clipboard.setMimeData(original_clipboard)
        else:
            original_clipboard.deleteLater()
        QCursor.setPos(original_cursor)


if __name__ == "__main__":
    run()
