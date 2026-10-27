from types import SimpleNamespace

import pywintypes
import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtWidgets import QApplication

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.focus_manager import FocusManager
from app.core.settings import Settings
from app.core.text import TextFormatter, TextLedger
from app.core.text_injector import TextInjector
from app.engines.base import Transcript
from app.ui.floating_hub import FloatingHub, bottom_center


def clipboard(monkeypatch, initial=None):
    import app.core.text_injector as module
    data = dict(initial or {13: "ancien texte", 49000: b"<b>ancien texte</b>"})
    sequence, sent = [1], []
    def empty():
        data.clear()
        sequence[0] += 1
    def put(fmt, value):
        data[fmt] = value
        sequence[0] += 1
    def enumerate_formats(previous):
        keys = list(data)
        i = keys.index(previous) + 1 if previous in keys else 0
        return keys[i] if i < len(keys) else 0
    monkeypatch.setattr(module.win32clipboard, "OpenClipboard", lambda: None)
    monkeypatch.setattr(module.win32clipboard, "CloseClipboard", lambda: None)
    monkeypatch.setattr(module.win32clipboard, "EnumClipboardFormats", enumerate_formats)
    def get_data(fmt):
        if fmt not in data:
            raise pywintypes.error(0, "GetClipboardData", "format unavailable in fixture")
        return data[fmt]
    monkeypatch.setattr(module.win32clipboard, "GetClipboardData", get_data)
    monkeypatch.setattr(module.win32clipboard, "EmptyClipboard", empty)
    monkeypatch.setattr(module.win32clipboard, "SetClipboardData", put)
    monkeypatch.setattr(module.win32clipboard, "SetClipboardText", lambda text, fmt: put(fmt, text))
    monkeypatch.setattr(module.win32clipboard, "GetClipboardSequenceNumber", lambda: sequence[0])
    monkeypatch.setattr(module, "modifiers_held", lambda: False)
    monkeypatch.setattr(module, "send", lambda inputs: sent.append((inputs, dict(data))))
    monkeypatch.setattr(module, "send_paste", lambda inputs: sent.append((inputs, dict(data))))
    focus = SimpleNamespace(valid=lambda: True, target=SimpleNamespace(native_hwnd=0))
    return TextInjector(focus), data, sent, put


def test_custom_editor_receives_only_the_dictation_and_keeps_it_on_the_clipboard(monkeypatch):
    injector, data, sent, _ = clipboard(monkeypatch)
    assert injector.insert("oui oui, éàç 😀")
    assert injector.last_method == "clipboard" and len(sent) == 1
    assert len(sent[0][0]) == 4 and sent[0][1] == {13: "oui oui, éàç 😀 "}
    assert data == {13: "oui oui, éàç 😀 "}


async def test_cleanup_failure_after_paste_never_delivers_twice(monkeypatch):
    injector, _, sent, _ = clipboard(monkeypatch)
    def fail(*args):
        raise pywintypes.error(5, "SetClipboardData", "fixture")
    monkeypatch.setattr("app.core.text_injector.win32clipboard.SetClipboardData", fail)
    result = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    result.ledger = TextLedger()
    result.ledger.confirm("one", "Bonjour oui oui")
    result.focus, result.injector = injector.focus, injector
    await result._finish_insertion()
    await result._finish_insertion()
    assert len(sent) == 1 and not result.ledger.pending


def test_a_new_user_copy_during_paste_is_preserved(monkeypatch):
    injector, data, sent, put = clipboard(monkeypatch)
    def send(inputs):
        sent.append(inputs)
        data.clear()
        put(13, "nouvelle copie")
    monkeypatch.setattr("app.core.text_injector.send_paste", send)
    assert injector.insert("dictée")
    assert len(sent) == 1 and data == {13: "nouvelle copie"}


def test_opaque_clipboard_keeps_one_real_paste_instead_of_unicode_keystrokes(monkeypatch):
    injector, data, sent, _ = clipboard(monkeypatch, {2: 98765})
    assert injector.insert("é😀")
    assert data == {13: "é😀 "} and injector.last_method == "clipboard"
    assert len(sent) == 1 and len(sent[0][0]) == 4


def test_previous_image_cannot_take_the_place_of_the_dictation(monkeypatch):
    injector, data, sent, _ = clipboard(monkeypatch, {2: 98765, 8: b"DIB fixture pixels"})
    assert injector.insert("phrase entière")
    assert injector.last_method == "clipboard" and len(sent) == 1
    assert sent[0][1] == {13: "phrase entière "}
    assert data == {13: "phrase entière "}


@pytest.mark.parametrize("strategy", ["native", "clipboard", "unicode"])
def test_consecutive_dictations_have_one_trailing_space_in_each_single_delivery(monkeypatch, strategy):
    import app.core.text_injector as module
    injector, _, sent, _ = clipboard(monkeypatch)
    injector.strategy = strategy
    payloads = []
    if strategy == "native":
        monkeypatch.setattr(injector, "native_insert", lambda text: payloads.append(text) or True)
    elif strategy == "unicode":
        original = module.unicode_inputs
        monkeypatch.setattr(module, "unicode_inputs", lambda text: payloads.append(text) or original(text))
    assert injector.insert("première dictée")
    assert injector.insert("deuxième dictée  ")
    if strategy == "clipboard":
        payloads = [snapshot[13] for inputs, snapshot in sent]
    assert payloads == ["première dictée ", "deuxième dictée "]
    assert "".join(payloads) == "première dictée deuxième dictée "
    assert len(sent) == (0 if strategy == "native" else 2)


def test_empty_dictation_delivers_nothing(monkeypatch):
    injector, data, sent, _ = clipboard(monkeypatch)
    assert not injector.insert("  ")
    assert not sent and data[13] == "ancien texte"


def test_paste_does_not_inspect_or_validate_the_receiving_field(monkeypatch):
    injector, data, sent, _ = clipboard(monkeypatch)
    def forbidden():
        pytest.fail("Automatic paste must not inspect the receiving field")
    injector.focus.valid = forbidden
    injector.focus.locate = forbidden
    monkeypatch.setattr("app.core.text_injector.win32clipboard.GetClipboardData", forbidden)
    assert injector.insert("dictée")
    assert len(sent) == 1 and data[13] == "dictée "


def test_finalization_and_late_final_callback_do_not_reopen_delivery():
    result = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    result.ledger, result.formatter, result.last_audio = TextLedger(), TextFormatter(Settings()), 0
    result._transcript(Transcript("one", "oui oui.", True, 1))
    result._finalize_text()
    result.ledger.acknowledge("oui oui")
    result._transcript(Transcript("two", "oui oui.", True, 2))
    result._finalize_text()
    assert not result.ledger.pending and result.ledger.inserted == ["oui oui"]


def test_legacy_edit_role_is_accepted_without_uia_edit_type():
    focus = object.__new__(FocusManager)
    legacy = SimpleNamespace(CurrentRole=42, CurrentState=0)
    focus.lib = SimpleNamespace(IUIAutomationLegacyIAccessiblePattern=object())
    focus.uia = SimpleNamespace(ControlViewWalker=SimpleNamespace(GetParentElement=lambda element: None))
    element = SimpleNamespace(CurrentIsEnabled=True, CurrentIsOffscreen=False, CurrentProcessId=-1,
        CurrentIsPassword=False, CurrentControlType=50025,
        GetCurrentPattern=lambda id: SimpleNamespace(QueryInterface=lambda interface: legacy))
    assert focus._safe(element)
    legacy.CurrentState = 0x40
    assert not focus._safe(element)
    legacy.CurrentState = 0x20000000
    assert not focus._safe(element)


@pytest.mark.parametrize("kind,process", [("MozillaWindowClass", "firefox.exe"),
                                        ("Chrome_WidgetWin_1", "msedge.exe"),
                                        ("CustomCanvas", "custom.exe"), ("QtWindow", "qt.exe")])
def test_browser_focus_is_available_without_native_caret(monkeypatch, kind, process):
    import app.core.focus_manager as module
    focus = object.__new__(FocusManager)
    focus._privileges = lambda pid: True
    monkeypatch.setattr(module.user, "GetForegroundWindow", lambda: 100)
    monkeypatch.setattr(module.user, "GetAncestor", lambda hwnd, level: 100)
    def pid(hwnd, value):
        value._obj.value = 321
    monkeypatch.setattr(module.user, "GetWindowThreadProcessId", pid)
    monkeypatch.setattr(module, "gui_info", lambda hwnd: SimpleNamespace(focus=123, caret=0))
    monkeypatch.setattr(module.win32gui, "IsWindowEnabled", lambda hwnd: True)
    monkeypatch.setattr(module.win32gui, "GetClassName", lambda hwnd: kind)
    monkeypatch.setattr(module.win32gui, "GetWindowRect", lambda hwnd: (0, 0, 800, 600))
    target = focus._native_target(None)
    assert target.hwnd == 100 and target.pid == 321 and target.native_hwnd == 123


def test_unknown_editor_keeps_dictation_available_for_delayed_clipboard_read(monkeypatch):
    injector, data, sent, _ = clipboard(monkeypatch)
    assert injector.insert("texte complet")
    assert len(sent) == 1 and data == {13: "texte complet "}


def test_each_paste_republishes_the_dictation_after_an_unrelated_copy(monkeypatch):
    injector, data, sent, put = clipboard(monkeypatch)
    assert injector.copy_dictation("texte complet")
    put(13, "autre copie, pas la dictée")
    assert injector.insert("texte complet")
    assert len(sent) == 1 and sent[0][1] == {13: "texte complet "}


def test_unconfirmed_paste_is_never_replaced_by_old_clipboard_or_sent_twice(monkeypatch):
    injector, data, sent, _ = clipboard(monkeypatch)
    assert injector.insert("texte complet")
    assert len(sent) == 1 and data == {13: "texte complet "}


def test_previous_file_copy_cannot_replace_the_dictated_text(monkeypatch):
    injector, data, sent, _ = clipboard(monkeypatch, {15: ("C:\\exemple.txt", "C:\\autre.txt")})
    assert injector.insert("texte complet") and len(sent) == 1
    assert data == {13: "texte complet "}


async def test_no_recognized_editor_still_sends_one_paste_without_notification(monkeypatch):
    from app.core.focus_manager import TargetError
    injector, data, sent, _ = clipboard(monkeypatch)
    def missing():
        raise TargetError("No text editor")
    injector.focus.locate = missing
    result = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    result.ledger = TextLedger()
    result.ledger.confirm("one", "Dictée conservée sans champ actif")
    result.injector, result.focus = injector, injector.focus
    errors = []
    result.error.connect(errors.append)
    await result._finish_insertion(timeout=0)
    assert data == {13: "Dictée conservée sans champ actif "}
    assert len(sent) == 1 and not errors and not result.ledger.pending
    await result._finish_insertion(timeout=0)
    assert len(sent) == 1


async def test_automatic_service_does_not_construct_an_accessibility_provider(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    async def close():
        pass
    def forbidden():
        pytest.fail("Automatic dictation must not depend on UI Automation")
    monkeypatch.setattr("app.core.controller.FocusManager", forbidden)
    monkeypatch.setattr("app.core.controller.EngineManager", lambda hardware: SimpleNamespace(close=close))
    result = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    result.commands.put(("quit", None))
    await result._run()
    assert result.focus is None


def mouse(point):
    return SimpleNamespace(button=lambda: Qt.LeftButton,
        globalPosition=lambda: QPointF(point), accept=lambda: None)


def test_drag_stays_put_and_wake_returns_to_bottom_center(monkeypatch):
    import app.ui.floating_hub as module
    app = QApplication.instance() or QApplication([])
    area = QRect(0, 0, 1920, 1040)
    monkeypatch.setattr(module.QGuiApplication, "screenAt", lambda p: SimpleNamespace(availableGeometry=lambda: area))
    now = [0.]
    hub = FloatingHub(Settings(), clock=lambda: now[0])
    hub.set_state("Écoute…")
    opened = []
    hub.open_requested.connect(lambda: opened.append(True))
    origin = hub.pos() + QPoint(20, 20)
    hub.mousePressEvent(mouse(origin))
    hub.mouseMoveEvent(mouse(origin + QPoint(230, -180)))
    hub.mouseReleaseEvent(mouse(origin + QPoint(230, -180)))
    moved = hub.pos()
    hub.animate()
    assert hub.pos() == moved and moved != bottom_center(hub.size(), area)
    assert not opened
    hub.set_state("Traitement…")
    hub.set_state("Prêt")
    assert hub.compacted
    now[0] = 21
    hub.animate()
    assert hub.compacted
    first = hub.grab().toImage()
    for _ in range(12):
        hub.animate()
    assert first != hub.grab().toImage() and hub.display_level == 0
    hub.set_state("Préparation…")
    assert hub.pos() == bottom_center(hub.size(), area)
    hub.mousePressEvent(mouse(hub.pos() + QPoint(15, 15)))
    hub.mouseReleaseEvent(mouse(hub.pos() + QPoint(15, 15)))
    assert opened == [True]
    hub.set_state("Fermé")
    hub.deleteLater()
    app.processEvents()
