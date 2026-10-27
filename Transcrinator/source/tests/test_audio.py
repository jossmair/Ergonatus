import queue
import time
from types import SimpleNamespace

import numpy as np
import pytest

from app.core.audio_capture import AudioCapture


def test_no_microphone(monkeypatch):
    monkeypatch.setattr("app.core.audio_capture.sd.query_devices", lambda *args: {"max_input_channels": 0})
    with pytest.raises(RuntimeError, match="Aucun microphone"):
        AudioCapture().start()


def test_audio_overload_is_explicit():
    capture = AudioCapture()
    capture.queue = queue.Queue(maxsize=1)
    block = np.ones((512, 1), np.float32)
    capture._callback(block, 512, None, SimpleNamespace(input_overflow=False))
    capture._callback(block, 512, None, SimpleNamespace(input_overflow=False))
    with pytest.raises(RuntimeError, match="saturée"):
        capture.read()


def test_disconnect_timeout():
    capture = AudioCapture()
    capture.last_audio = time.monotonic() - 5
    with pytest.raises(RuntimeError, match="interrompu"):
        capture.read()


def test_stop_idempotent():
    capture = AudioCapture()
    assert capture.stop() == []
    assert capture.stop() == []


def test_stop_request_keeps_last_captured_block_before_stopping():
    import sounddevice as sd

    capture = AudioCapture()
    capture.request_stop()
    with pytest.raises(sd.CallbackStop):
        capture._callback(np.ones((512, 1), np.float32), 512, None, SimpleNamespace(input_overflow=False))
    last, _ = capture.queue.get_nowait()
    assert np.array_equal(last, np.ones(512, np.float32))
    capture._finished()
    assert not capture.failed.is_set()


def test_start_waits_for_first_callback_and_keeps_it(monkeypatch):
    import threading

    capture = AudioCapture()
    block = np.ones((512, 1), np.float32)
    monkeypatch.setattr("app.core.audio_capture.sd.query_devices", lambda *args: {
        "max_input_channels": 1, "default_samplerate": 16000
    })

    class Stream:
        def start(self):
            self.timer = threading.Timer(0.02, lambda: capture._callback(
                block, 512, None, SimpleNamespace(input_overflow=False)
            ))
            self.timer.start()

        def stop(self):
            self.timer.join()

        def close(self):
            pass

    monkeypatch.setattr("app.core.audio_capture.sd.InputStream", lambda **kwargs: Stream())
    capture.start()
    try:
        assert capture.audio_started.is_set()
        first, _ = capture.queue.get_nowait()
        assert np.array_equal(first, block[:, 0])
    finally:
        capture.stop()


def test_microphone_without_callbacks_is_closed_before_error(monkeypatch):
    capture = AudioCapture()
    calls = []
    monkeypatch.setattr("app.core.audio_capture.sd.query_devices", lambda *args: {
        "max_input_channels": 1, "default_samplerate": 16000
    })
    monkeypatch.setattr("app.core.audio_capture.sd.InputStream", lambda **kwargs: SimpleNamespace(
        start=lambda: None, stop=lambda: calls.append("stop"), close=lambda: calls.append("close")
    ))
    monkeypatch.setattr(capture.audio_started, "wait", lambda timeout: False)
    with pytest.raises(RuntimeError, match="ne fournit pas"):
        capture.start()
    assert capture.stream is None and calls == ["stop", "close"]
