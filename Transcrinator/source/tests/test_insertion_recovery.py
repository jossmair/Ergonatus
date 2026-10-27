from types import SimpleNamespace

import pytest

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.focus_manager import TargetError
from app.core.settings import Settings
from app.core.state_machine import State
from app.core.text import TextLedger
from app.core.text_injector import TextInjector


def controller(progressive=True):
    result = Controller(Settings(progressive=progressive), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    result.ledger = TextLedger()
    result.ledger.confirm("first", "Premier mot.")
    result.ledger.confirm("last", " Dernier mot.")
    result.focus = SimpleNamespace(valid=lambda: True)
    result.blocked = False
    return result


@pytest.mark.parametrize("progressive", [True, False])
async def test_final_words_retry_after_modifier_release_exactly_once(progressive):
    result = controller(progressive)
    calls, inserted = [], []

    def insert(text):
        calls.append(text)
        if len(calls) < 3:
            return False
        inserted.append(text)
        return True

    result.injector = SimpleNamespace(insert=insert)
    await result._finish_insertion(timeout=0.3)
    await result._finish_insertion(timeout=0.3)
    assert "".join(inserted) == "Premier mot. Dernier mot."
    assert not result.ledger.pending


async def test_field_validation_cannot_block_a_retry_before_any_paste_was_sent():
    result = controller()
    attempts = []

    def insert(text):
        attempts.append(text)
        result.focus.valid = lambda: False
        return len(attempts) == 2

    result.injector = SimpleNamespace(insert=insert)
    await result._finish_insertion(timeout=0.3)
    assert len(attempts) == 2
    assert not result.blocked and not result.stop_requested.is_set()
    assert not result.ledger.pending


async def test_held_modifier_timeout_retains_tail():
    result = controller()
    result.injector = SimpleNamespace(insert=lambda text: False)
    await result._finish_insertion(timeout=0)
    assert "".join(result.ledger.pending) == "Premier mot. Dernier mot."
    assert not result.ledger.inserted


async def test_editor_detection_is_never_called_for_automatic_paste():
    result = controller()
    checks, delivered = [], []
    def locate():
        checks.append(True)
        if len(checks) < 3:
            raise TargetError("Temporary editor transition")
    result.focus.locate = locate
    result.injector = SimpleNamespace(insert=lambda text: delivered.append(text) or True)
    await result._finish_insertion(timeout=.3)
    assert delivered == ["Premier mot. Dernier mot."]
    assert not checks and not result.ledger.pending


@pytest.mark.parametrize("progressive", [True, False])
async def test_insertion_error_keeps_tail_in_both_modes(progressive):
    result = controller(progressive)

    def insert(text):
        raise RuntimeError("Windows refuse l’insertion")

    result.injector = SimpleNamespace(insert=insert)
    await result._finish_insertion()
    assert result.blocked and result.stop_requested.is_set()
    assert "".join(result.ledger.pending) == "Premier mot. Dernier mot."


def test_manual_input_during_dictation_preparation_keeps_recording():
    result = controller()
    result.session_pending = True
    result.machine.transition(State.PREPARING)
    result.request("manual_input")
    assert not result.stop_requested.is_set() and not result.blocked


def test_manual_input_during_background_load_does_not_cancel():
    result = controller()
    result.machine.transition(State.PREPARING)
    result.request("manual_input")
    assert not result.stop_requested.is_set()


async def test_unavailable_target_keeps_loaded_model(monkeypatch, tmp_path):
    result = controller()
    closed = []

    async def close():
        closed.append(True)

    async def dictate():
        raise TargetError("Champ indisponible")

    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    monkeypatch.setattr("app.core.controller.EngineManager", lambda hardware: SimpleNamespace(close=close))
    monkeypatch.setattr("app.core.controller.FocusManager", lambda: result.focus)
    result._dictate = dictate
    result.commands.put(("toggle", None))
    result.commands.put(("quit", None))
    states = []
    errors = []
    result.status.connect(states.append)
    result.error.connect(errors.append)
    await result._run()
    assert closed == [True]  # shutdown only, never for an editor refusal
    assert State.ERROR.value not in states
    assert result.diagnostic.errors[0]["code"] == "target"
    assert errors == []  # no notification or error banner for a missing editor


@pytest.mark.parametrize("kind", ["Edit", "RichEdit50W", "RichEditD2DPT", "Chrome_WidgetWin_1"])
def test_automatic_insertion_uses_normal_paste_even_for_native_controls(monkeypatch, kind):
    focus = SimpleNamespace(valid=lambda: True, target=SimpleNamespace(native_hwnd=123))
    injector = TextInjector(focus)
    methods = []
    monkeypatch.setattr("app.core.text_injector.modifiers_held", lambda: False)
    monkeypatch.setattr("app.core.text_injector.win32gui.GetClassName", lambda hwnd: kind)
    monkeypatch.setattr("app.core.text_injector.send", lambda inputs: methods.append("unicode"))
    injector.paste = lambda text: methods.append("clipboard") or True
    injector.native_insert = lambda text: methods.append("native") or True
    assert injector.insert("Bonjour é😀")
    assert methods == ["clipboard"]
