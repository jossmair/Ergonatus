from collections import deque

import numpy as np
import onnxruntime as ort


class SileroVAD:
    def __init__(self, path):
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
        self.reset()

    def reset(self):
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros(64, dtype=np.float32)

    def probability(self, frame):
        if len(frame) != 512:
            raise ValueError("Silero attend 512 échantillons à 16 kHz.")
        data = np.concatenate((self.context, frame))[None, :].astype(np.float32)
        out, self.state = self.session.run(
            None, {"input": data, "state": self.state, "sr": np.array(16000, dtype=np.int64)}
        )
        self.context = frame[-64:].copy()
        return float(out[0][0])


class Segmenter:
    """Disjoint audio segments. Pre-roll is consumed exactly once at speech onset."""

    def __init__(self, detector, threshold=0.5, silence_ms=400, max_seconds=15, end_on_silence=True):
        self.detector, self.threshold = detector, threshold
        self.end_on_silence = end_on_silence
        self.silence_frames = max(1, int(silence_ms / 32))
        self.max_frames = int(max_seconds / 0.032)
        self.pending = np.empty(0, np.float32)
        self.pre = deque(maxlen=16)  # 512 ms: keep consonants before Silero's onset.
        self.active = []
        self.quiet = 0
        self.continuing = False
        self.voiced_frames = 0

    def feed(self, audio):
        self.pending = np.concatenate((self.pending, audio))
        segments = []
        while len(self.pending) >= 512:
            frame, self.pending = self.pending[:512].copy(), self.pending[512:]
            speech = self.detector.probability(frame) >= self.threshold
            if not self.active:
                if speech or self.continuing:
                    self.active = list(self.pre) + [frame]
                    self.pre.clear()
                else:
                    self.pre.append(frame)
                    continue
            else:
                self.active.append(frame)
            self.quiet = 0 if speech else self.quiet + 1
            self.voiced_frames += int(speech)
            if ((self.end_on_silence and self.quiet >= self.silence_frames)
                    or len(self.active) >= self.max_frames):
                was_continuing = self.continuing
                self.continuing = self.quiet < self.silence_frames
                if self.voiced_frames >= 2 or self.continuing or (was_continuing and self.voiced_frames > 0):
                    segments.append(np.concatenate(self.active))
                self.active = []
                self.quiet = 0
                self.voiced_frames = 0
        return segments

    def flush(self):
        if self.active:
            result = np.concatenate(self.active + [self.pending])
        else:
            result = np.empty(0, np.float32)
        self.active.clear()
        self.pre.clear()
        self.pending = np.empty(0, np.float32)
        self.continuing = False
        self.voiced_frames = 0
        return [result] if len(result) else []
