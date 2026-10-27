import numpy as np
import pytest
from PySide6.QtCore import QRect, QSize

from app.core.settings import Settings
from app.core.state_machine import State, StateMachine
from app.core.text import TextFormatter, TextLedger
from app.core.vad import Segmenter
from app.core.win32 import Input, unicode_inputs
from app.ui.floating_hub import bottom_center


def test_state_lifecycle_and_concurrency():
    machine = StateMachine()
    for state in (State.PREPARING, State.LISTENING, State.FLUSHING, State.IDLE):
        machine.transition(state)
    machine.transition(State.PREPARING)
    with pytest.raises(RuntimeError):
        machine.transition(State.PREPARING)
    machine.transition(State.ERROR)
    machine.transition(State.IDLE)


def test_ledger_keeps_intentional_repetition_and_ignores_duplicate_event():
    ledger = TextLedger()
    assert ledger.confirm("1", "oui oui")
    assert not ledger.confirm("1", "oui oui")
    assert ledger.confirm("2", "oui oui")
    ledger.acknowledge("oui oui")
    assert ledger.pending == ["oui oui"]


def test_commands_not_arbitrary():
    formatter = TextFormatter(Settings(voice_commands=True))
    assert formatter.format("le point de vue") == "le point de vue"
    assert formatter.format("point") == "."
    assert formatter.format("nouvelle ligne") == "\n"


def test_unicode_non_bmp():
    import ctypes

    assert ctypes.sizeof(Input) == 40
    assert len(unicode_inputs("é😀")) == 6
    assert unicode_inputs("é")[0].value.keyboard.scan == 233


class Detector:
    def probability(self, frame):
        return float(frame[0] > 0)


def test_silence_never_transcribed():
    segmenter = Segmenter(Detector())
    assert segmenter.feed(np.zeros(16000, np.float32)) == []
    assert segmenter.flush() == []


def test_segments_disjoint_ordered_and_tail_flushed():
    segmenter = Segmenter(Detector(), silence_ms=64, max_seconds=1)
    audio = np.concatenate(
        [
            np.ones(1024, np.float32),
            np.zeros(1024, np.float32),
            np.full(1024, 2, np.float32),
            np.full(100, 3, np.float32),
        ]
    )
    segments = segmenter.feed(audio) + segmenter.flush()
    assert len(segments) == 2
    assert np.array_equal(np.concatenate(segments), audio)


def test_max_segment_has_no_audio_overlap_or_loss():
    segmenter = Segmenter(Detector(), max_seconds=1)
    audio = np.ones(50000, np.float32)
    segments = segmenter.feed(audio) + segmenter.flush()
    assert sum(len(s) for s in segments) == len(audio)


@pytest.mark.parametrize(
    "screen", [QRect(0, 0, 1920, 1080), QRect(-1920, 0, 1920, 1080), QRect(1920, 0, 1280, 720)]
)
def test_hub_bounds_multiple_monitors(screen):
    size = QSize(210, 76)
    point = bottom_center(size, screen)
    assert screen.contains(QRect(point, size))
    assert abs((point.x() + size.width() / 2) - (screen.left() + screen.width() / 2)) <= .5
    assert point.y() + size.height() == screen.bottom() + 1 - 16


def test_typography_opt_in():
    assert TextFormatter(Settings()).format("bonjour !") == "bonjour !"
    assert TextFormatter(Settings(typography=True)).format("bonjour !") == "bonjour\u202f!"
