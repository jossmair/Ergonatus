import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from app.core.audio_capture import AudioCapture
from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.core.state_machine import State
from app.engines.base import Transcript
from app.services.diagnostics import Diagnostics
from app.ui.main_window import MainWindow
from app.ui.vocabulary_dialog import VocabularyDialog


WORDS = [{"name": "Auditville", "aliases": ["audit ville"], "category": "city"}]


@pytest.mark.parametrize("field,value", [
    ("experience_revision", "invalid"), ("silence_ms", []), ("segment_seconds", None),
    ("vad_threshold", "nan"), ("vad_threshold", float("inf")), ("trigger_key", {}),
    ("number_style", []), ("abbreviate_units", "false"), ("autostart", []),
    ("acceleration", {}), ("microphone", "invalid"),
])
def test_one_invalid_preference_preserves_the_dictionary(tmp_path, monkeypatch, field, value):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    settings = Settings(vocabulary=WORDS, number_style="words", trigger_key="f8")
    settings.configure_automatic()
    path = tmp_path / "preferences/settings.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record[field] = value
    path.write_text(json.dumps(record), encoding="utf-8")
    restored = Settings.load()
    restored.configure_automatic()
    assert Settings.load().vocabulary == WORDS
    if field != "number_style":
        assert Settings.load().number_style == "words"


@pytest.mark.parametrize("contents", ["{broken", "[]", "null", '\ufffd'])
def test_corrupt_settings_restore_latest_backup_and_keep_original(tmp_path, monkeypatch, contents):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    Settings(vocabulary=WORDS, number_style="words", trigger_key="f8").save()
    path = tmp_path / "preferences/settings.json"
    path.write_text(contents, encoding="utf-8")
    restored = Settings.load()
    assert restored.vocabulary == WORDS and restored.trigger_key == "f8"
    restored.configure_automatic()
    assert Settings.load().vocabulary == WORDS
    archives = list(path.parent.glob("settings.corrupt-*.json"))
    assert len(archives) == 1 and archives[0].read_text(encoding="utf-8") == contents


def test_invalid_vocabulary_type_uses_backup_and_empty_dictionary_stays_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    Settings(vocabulary=WORDS).save()
    path = tmp_path / "preferences/settings.json"
    path.write_text(json.dumps({"vocabulary": {}, "experience_revision": 7}), encoding="utf-8")
    assert Settings.load().vocabulary == WORDS
    Settings(vocabulary=[]).save()
    assert Settings.load().vocabulary == []


def test_non_utf8_corruption_is_archived_without_losing_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    Settings(vocabulary=WORDS).save()
    path = tmp_path / "preferences/settings.json"
    original = b"\xff\xfe\x00unreadable fixture"
    path.write_bytes(original)
    settings = Settings.load()
    settings.configure_automatic()
    assert Settings.load().vocabulary == WORDS
    assert next(path.parent.glob("settings.corrupt-*.json")).read_bytes() == original


def test_failed_primary_save_keeps_previous_primary_and_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    Settings(vocabulary=WORDS).save()
    original = Path.replace

    def fail_primary(source, destination):
        if Path(destination).name == "settings.json":
            raise PermissionError("synthetic write denial")
        return original(source, destination)

    monkeypatch.setattr(Path, "replace", fail_primary)
    with pytest.raises(PermissionError):
        Settings(vocabulary=[]).save()
    for name in ("settings.json", "settings.backup.json"):
        assert json.loads((tmp_path / "preferences" / name).read_text(encoding="utf-8"))["vocabulary"] == WORDS
    assert not list((tmp_path / "preferences").glob("*.tmp"))
    assert Settings.load().vocabulary == WORDS


def test_read_only_automatic_configuration_does_not_prevent_startup(monkeypatch):
    def fail(*_):
        raise PermissionError("synthetic write denial")
    monkeypatch.setattr(Settings, "save", fail)
    settings = Settings(vocabulary=WORDS)
    settings.configure_automatic()
    assert settings.vocabulary == WORDS and settings.experience_revision == 7


def test_microphone_stop_drains_audio_even_if_driver_stop_and_close_fail():
    import sounddevice as sd
    calls = []
    def fail(name):
        calls.append(name)
        raise sd.PortAudioError("synthetic disconnection")
    capture = AudioCapture()
    capture.stream = SimpleNamespace(stop=lambda: fail("stop"), close=lambda: fail("close"))
    capture.resampler = SimpleNamespace(resample_chunk=lambda audio, **kw: audio)
    capture.queue.put((np.ones(512, np.float32), 1))
    remaining = capture.stop()
    assert calls == ["stop", "close"] and capture.stream is None and capture.failed.is_set()
    assert len(remaining) == 1 and len(remaining[0][0]) == 512
    assert capture.stop() == []


@pytest.mark.parametrize("failure", ["capture", "capture_start", "engine_feed", "engine_finish", "recovery_finish"])
async def test_capture_failure_recovers_buffer_without_replaying_engine_errors(tmp_path, monkeypatch, failure):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    controller = Controller(Settings(vocabulary=WORDS), Hardware("fixture", 4, 16 * 2**30, 8 * 2**30))
    samples, finishes, deliveries = [], [], []

    async def begin(emit):
        controller.fixture_emit = emit

    async def feed(audio):
        samples.extend(audio.tolist())
        if failure == "engine_feed":
            raise RuntimeError("engine_feed")

    async def finish():
        finishes.append(True)
        controller.fixture_emit(Transcript("final", "audit ville", True, 1))
        if failure in ("engine_finish", "recovery_finish"):
            raise RuntimeError(failure)

    class Capture:
        def __init__(self, *_):
            self.reads = 0
            self.stopped = False
        def start(self):
            if failure == "capture_start":
                raise RuntimeError("capture_start")
        def read(self):
            self.reads += 1
            if self.reads == 1:
                if failure == "engine_finish":
                    controller.stop_requested.set()
                return np.full(512, 1, np.float32), 1
            raise RuntimeError("capture")
        def stop(self):
            if self.stopped:
                return []
            self.stopped = True
            return [(np.full(512, 2, np.float32), 2)]

    controller.manager = SimpleNamespace(is_prepared=lambda *_: True,
        active=SimpleNamespace(begin=begin, feed=feed, finish=finish))
    controller.injector = SimpleNamespace(strategy="auto", insert=lambda text: deliveries.append(text) or True)
    monkeypatch.setattr("app.core.controller.AudioCapture", Capture)
    with pytest.raises(RuntimeError):
        await controller._dictate()
    assert controller.capture is None and not deliveries
    if failure == "engine_feed":
        assert samples == [1] * 512 and not finishes and not controller.retained
    else:
        assert len(finishes) == 1 and controller.retained == ["Auditville"]
        assert samples == ([2] * 512 if failure == "capture_start" else [1] * 512 + [2] * 512)


@pytest.mark.parametrize("location", ["directory", "write"])
async def test_logging_denial_keeps_error_in_memory_and_controller_closes(tmp_path, monkeypatch, location):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    def fail(*args, **kwargs):
        raise PermissionError("private fixture must never be logged")
    if location == "directory":
        monkeypatch.setattr("app.services.diagnostics.directory", fail)
    else:
        monkeypatch.setattr(Path, "write_text", fail)
    diagnostic = Diagnostics()
    diagnostic.error("fixture", RuntimeError("private fixture must never be logged"))
    assert diagnostic.errors[-1]["type"] == "RuntimeError"
    assert "private" not in json.dumps(diagnostic.snapshot())

    closed = []
    class Manager:
        def __init__(self, *_):
            pass
        def is_prepared(self, *_):
            return False
        async def prepare(self, *_):
            raise RuntimeError("synthetic load failure")
        async def close(self):
            closed.append(True)
    monkeypatch.setattr("app.core.controller.EngineManager", Manager)
    monkeypatch.setattr("app.core.controller.FocusManager", lambda: SimpleNamespace(target=None))
    monkeypatch.setattr("app.core.controller.TextInjector", lambda *_: None)
    controller = Controller(Settings(), Hardware("fixture", 4, 16 * 2**30, 8 * 2**30))
    controller.commands.put(("load", None))
    controller.commands.put(("quit", None))
    await asyncio.wait_for(controller._run(), 1)
    assert controller.machine.state == State.CLOSED and len(closed) == 2
    assert controller.diagnostic.errors[-1]["code"] == "load"


def test_failed_option_saves_revert_toggles_and_keep_dictionary_editor(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    controller = Controller(Settings(vocabulary=WORDS), Hardware("fixture", 4, 16 * 2**30, 8 * 2**30))
    window = MainWindow(controller)
    original = Settings.save
    def fail(*_):
        raise PermissionError("synthetic write denial")
    monkeypatch.setattr(Settings, "save", fail)
    window.number_style.setChecked(False)
    window.units.setChecked(False)
    assert window.number_style.isChecked() and window.units.isChecked()
    assert controller.commands.empty() and window.preferences.vocabulary == WORDS
    dialog = VocabularyDialog(WORDS, save_callback=lambda entries: window.save_text_options(vocabulary=entries))
    dialog.show()
    dialog.add_row("Nouveau", "Nouveaux", "proper_name")
    dialog.save_entries()
    assert dialog.isVisible() and dialog.table.item(0, 0).text() == "Nouveau"
    assert dialog.entries == WORDS and controller.commands.empty()
    monkeypatch.setattr(Settings, "save", original)
    dialog.table.setItem(0, 1, QTableWidgetItem("Nouveaux"))
    dialog.save_entries()
    assert not dialog.isVisible() and Settings.load().vocabulary[0]["name"] == "Nouveau"
    assert controller.commands.get_nowait()[0] == "text_options" and controller.commands.empty()
    dialog.deleteLater()
    window.deleteLater()
    app.processEvents()
