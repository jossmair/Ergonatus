from types import SimpleNamespace

import numpy as np
import pytest

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.focus_manager import FocusManager, TargetError
from app.core.settings import Settings
from app.core.vad import Segmenter
from app.engines.base import Transcript


def test_breathing_pauses_do_not_finalize_a_dictation():
    detector = SimpleNamespace(probability=lambda frame: float(frame[0] > 0))
    segmenter = Segmenter(detector, silence_ms=360, max_seconds=30, end_on_silence=False)
    audio = np.concatenate([np.ones(4096, np.float32), np.zeros(8192, np.float32),
                            np.full(4096, 2, np.float32), np.zeros(16384, np.float32),
                            np.full(701, 3, np.float32)])
    assert segmenter.feed(audio) == []
    final = segmenter.flush()
    assert len(final) == 1 and np.array_equal(final[0], audio)
    assert segmenter.flush() == []


def test_whole_dictation_still_bounds_audio_and_rejects_silence():
    detector = SimpleNamespace(probability=lambda frame: float(frame[0] > 0))
    segmenter = Segmenter(detector, max_seconds=1, end_on_silence=False)
    assert segmenter.feed(np.zeros(16000, np.float32)) == []
    assert segmenter.flush() == []
    audio = np.ones(50021, np.float32)
    parts = segmenter.feed(audio) + segmenter.flush()
    assert np.array_equal(np.concatenate(parts), audio)
    assert all(len(part) <= 16000 for part in parts)


@pytest.mark.parametrize("has_editor", [True, False])
async def test_dictation_sends_once_at_stop_even_without_a_recognized_editor(monkeypatch, has_editor):
    controller = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    sent, errors, opened = [], [], []
    controller.error.connect(errors.append)

    def locate():
        if not has_editor:
            raise TargetError("No editor")

    target = SimpleNamespace(hwnd=1, pid=2, runtime_id=(), native_hwnd=3) if has_editor else None
    controller.focus = SimpleNamespace(locate=locate, valid=lambda: has_editor, anchor=lambda: None, target=target)
    controller.injector = SimpleNamespace(insert=lambda text: sent.append(text) or True)

    async def begin(emit):
        controller.emit_test = emit

    async def feed(audio):
        assert len(sent) == controller.capture.sent_before

    async def finish():
        controller.emit_test(Transcript("one", "Bonjour, je termine ma phrase.", True, 1))

    controller.manager = SimpleNamespace(is_prepared=lambda settings: True,
        active=SimpleNamespace(begin=begin, feed=feed, finish=finish))

    class Capture:
        def __init__(self, device):
            pass

        def start(self):
            opened.append(True)
            self.sent_before = len(sent)

        def read(self):
            assert len(sent) == self.sent_before
            controller.stop_requested.set()
            return np.ones(512, np.float32), 1

        def stop(self):
            return []

    monkeypatch.setattr("app.core.controller.AudioCapture", Capture)
    await controller._dictate()
    assert opened == [True] and errors == []
    assert sent == ["Bonjour, je termine ma phrase."] and not controller.retained
    assert controller.capture is None
    controller.stop_requested.clear()
    await controller._dictate()
    assert sent == ["Bonjour, je termine ma phrase."] * 2
    assert not controller.retained
    assert errors == []
    if has_editor:
        controller.request("manual_input")  # movement/edit invalidates the cached boundary
        controller.focus.previous_character = lambda: ""
        controller.stop_requested.clear()
        await controller._dictate()
        assert sent[-1] == "Bonjour, je termine ma phrase."


def test_writer_native_focus_without_uia_and_changed_focus_refused(monkeypatch):
    import app.core.focus_manager as module

    focus = object.__new__(FocusManager)
    focus.uia = SimpleNamespace(GetFocusedElement=lambda: None)
    focus.target = None
    focus._privileges = lambda pid: True
    info = SimpleNamespace(focus=20, caret=0)
    monkeypatch.setattr(module, "gui_info", lambda hwnd: info)
    monkeypatch.setattr(module.user, "GetForegroundWindow", lambda: 10)
    monkeypatch.setattr(module.user, "GetAncestor", lambda hwnd, flags: 10)
    monkeypatch.setattr(module.user, "IsWindow", lambda hwnd: True)

    def process(hwnd, pointer):
        pointer._obj.value = 12345
        return 1

    monkeypatch.setattr(module.user, "GetWindowThreadProcessId", process)
    monkeypatch.setattr(module.win32gui, "IsWindowEnabled", lambda hwnd: True)
    monkeypatch.setattr(module.win32gui, "GetClassName", lambda hwnd: "SALFRAME")
    monkeypatch.setattr(module.win32gui, "GetWindowText", lambda hwnd: "Sans nom 1 — LibreOffice Writer")
    monkeypatch.setattr(module.win32gui, "GetWindowRect", lambda hwnd: (0, 0, 600, 500))
    assert focus.locate().native_hwnd == 20
    assert focus.valid()
    info.focus = 21
    assert not focus.valid()
    info.focus = 20
    sensitive = SimpleNamespace(CurrentIsPassword=True)
    assert focus._native_target(sensitive) is None
    readonly = SimpleNamespace(CurrentIsPassword=False, CurrentControlType=50004,
                               GetCurrentPropertyValue=lambda key: key in (30043, 30046))
    focus.uia.ControlViewWalker = SimpleNamespace(GetParentElement=lambda element: None)
    assert focus._native_target(readonly) is None

