import json
from types import SimpleNamespace

import numpy as np
import pytest

from app.core.audio_capture import AudioCapture
from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.core.state_machine import State
from app.core.text import TextFormatter, TextLedger
from app.core.vad import Segmenter
from app.engines.base import Transcript
from app.engines.parakeet_ultra import sanitize_transcript
from app.services.model_manager import MODELS


@pytest.mark.parametrize("raw, expected", [
    ("Teste pour voir si ça marche.Bien,.......Okay,...........Non,..............", "Teste pour voir si ça marche. Bien. Okay. Non."),
    ("... , ... . ,", ""), (". . . . . .", ""), ("……", ""),
    ("Oui, oui, je répète.", "Oui, oui, je répète."),
    ("Il coûte 3.14 euros.", "Il coûte 3.14 euros."),
    ("Visitez example.fr.", "Visitez example.fr."),
    ("Vraiment?!", "Vraiment?!"),
])
def test_decoder_punctuation_without_deleting_words(raw, expected):
    assert sanitize_transcript(raw) == expected


def test_confirmed_parakeet_segments_append_without_caret_replacement():
    c = Controller(Settings(progressive=True), Hardware("test", 4, 16*2**30, 8*2**30))
    c.ledger, c.formatter = TextLedger(), TextFormatter(c.settings)
    c.blocked, c.last_audio = False, 0
    c.focus = SimpleNamespace(valid=lambda: True)  # no TextPattern/selection API
    sent = []
    c.injector = SimpleNamespace(insert=lambda text: sent.append(text) or True)
    for identity, text in [("a", "Premier mot."), ("b", "Dernier mot."), ("b", "Dernier mot.")]:
        c._transcript(Transcript(identity, text, True, 1))
    assert sent == []
    c._insert_pending(force=True)
    assert sent == ["Premier mot. Dernier mot."]
    assert not c.blocked and not c.ledger.pending


def test_last_vad_frame_is_preserved_when_stopping_immediately():
    detector = SimpleNamespace(probability=lambda frame: 1.0)
    segmenter = Segmenter(detector)
    audio = np.arange(700, dtype=np.float32)/1000
    assert segmenter.feed(audio) == []
    assert np.array_equal(segmenter.flush()[0], audio)


def test_preroll_keeps_audio_before_delayed_speech_detection():
    count = [0]
    def probability(frame):
        count[0] += 1
        return float(count[0] >= 13)
    segmenter = Segmenter(SimpleNamespace(probability=probability))
    audio = np.arange(15*512, dtype=np.float32)/10000
    assert segmenter.feed(audio) == []
    assert np.array_equal(segmenter.flush()[0], audio)


def test_audio_tail_drains_once_and_normal_stop_is_not_disconnect():
    capture = AudioCapture()
    capture.resampler = SimpleNamespace(resample_chunk=lambda audio, last=False: np.array([.9], np.float32) if last else audio)
    capture.queue.put((np.array([.1, .2], np.float32), 1))
    blocks = capture.stop()
    assert np.allclose(np.concatenate([b[0] for b in blocks]), [.1, .2, .9])
    capture._finished()
    assert not capture.failed.is_set()
    assert capture.stop() == []


def test_fast_toggle_reserves_one_session_and_cancels_before_start():
    c = Controller(Settings(), Hardware("test", 4, 16*2**30, 8*2**30))
    c.request("toggle")
    c.request("toggle")
    assert c.commands.qsize() == 1
    assert c.session_pending and c.stop_requested.is_set()


@pytest.mark.parametrize("flushing", [False, True])
def test_manual_edit_keeps_dictation_until_shortcut_is_pressed(flushing):
    c = Controller(Settings(), Hardware("test", 4, 16*2**30, 8*2**30))
    c.machine.transition(State.PREPARING)
    c.machine.transition(State.LISTENING)
    if flushing:
        c.machine.transition(State.FLUSHING)
    calls = []
    c.capture = SimpleNamespace(request_stop=lambda: calls.append(True))
    c.request("manual_input")
    assert not c.blocked and not c.stop_requested.is_set() and calls == []


def test_only_ultra_and_vad_are_distributed_and_old_settings_migrate(tmp_path, monkeypatch):
    assert set(MODELS) == {"parakeet", "silero"}
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    path = tmp_path / "preferences/settings.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"engine": "voxtral", "acceleration": "cpu", "experience_revision": 2, "microphone": 3}))
    settings = Settings.load()
    assert settings.engine == "parakeet" and settings.microphone == 3
    assert settings.experience_revision == 3 and settings.segment_seconds == 30
