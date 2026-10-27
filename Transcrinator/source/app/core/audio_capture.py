import queue
import threading
import time

import numpy as np
import sounddevice as sd
import soxr


class AudioCapture:
    """PortAudio callback copies only; resampling and network run in the worker."""

    def __init__(self, device=None, latency="low"):
        self.device = device
        self.latency = latency
        self.queue = queue.Queue(maxsize=100)
        self.failed = threading.Event()
        self.stop_signal = threading.Event()
        self.audio_started = threading.Event()
        self.stream = None
        self.last_audio = time.monotonic()

    def start(self):
        device = sd.query_devices(self.device, "input")
        if device["max_input_channels"] < 1:
            raise RuntimeError("Aucun microphone disponible.")
        self.rate = int(device["default_samplerate"])
        self.resampler = soxr.ResampleStream(self.rate, 16000, 1, dtype="float32")
        self.stream = sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.rate,
            dtype="float32",
            latency=self.latency,
            blocksize=max(1, int(self.rate * 0.032)),
            callback=self._callback,
            finished_callback=self._finished,
        )
        self.last_audio = time.monotonic()
        self.stream.start()
        # Some Windows drivers start callbacks well after stream.start() returns.
        # Advertise listening only once audio is actually arriving; keep this first block.
        if not self.audio_started.wait(3):
            self.stop()
            raise RuntimeError("Le microphone ne fournit pas d’audio. Vérifiez le périphérique choisi.")

    def _callback(self, data, frames, timestamp, status):
        if status.input_overflow:
            self.failed.set()  # loss is explicit; never silently discard audio
        self.last_audio = time.monotonic()
        try:
            self.queue.put_nowait((data[:, 0].copy(), self.last_audio))
        except queue.Full:
            self.failed.set()
        self.audio_started.set()
        # This block contains audio captured BEFORE the stop request as well.
        # Keep it, then stop PortAudio. The resampler tail is drained by stop().
        if self.stop_signal.is_set():
            raise sd.CallbackStop

    def _finished(self):
        if not self.stop_signal.is_set():
            self.failed.set()

    def request_stop(self):
        # Nonblocking from the UI/hotkey thread; PortAudio stops at the next callback.
        self.stop_signal.set()

    def read(self):
        if self.failed.is_set() or time.monotonic() - self.last_audio > 3:
            raise RuntimeError("Microphone interrompu ou file audio saturée. Dictée arrêtée.")
        try:
            audio, timestamp = self.queue.get_nowait()
        except queue.Empty:
            return None
        result = self.resampler.resample_chunk(audio)
        return result, timestamp

    def stop(self):
        if getattr(self, "stopped", False):
            return []
        self.stopped = True
        self.stop_signal.set()
        if self.stream:
            try:
                self.stream.stop()
            except (sd.PortAudioError, OSError):
                self.failed.set()
            finally:
                try:
                    self.stream.close()
                except (sd.PortAudioError, OSError):
                    self.failed.set()
                self.stream = None
        remaining = []
        while not self.queue.empty():
            audio, timestamp = self.queue.get_nowait()
            remaining.append((self.resampler.resample_chunk(audio), timestamp))
        if hasattr(self, "resampler"):
            tail = self.resampler.resample_chunk(np.empty(0, np.float32), last=True)
            if len(tail):
                remaining.append((tail, time.monotonic()))
        return remaining


def pcm16(audio):
    return (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
