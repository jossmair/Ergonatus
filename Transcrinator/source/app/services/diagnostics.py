import json
import time
from collections import deque

from app.core.settings import directory


class Diagnostics:
    def __init__(self):
        self.errors = deque(maxlen=30)
        self.latencies = deque(maxlen=100)
        self.load_seconds = None
        self.backend = "non chargé"
        self.model = "non chargé"
        self.microphone = "inactif"
        self.fallback_reason = ""

    def error(self, code, exception):
        # Only class/code, never exception payload, paths, audio, transcription or window title.
        record = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "code": code, "type": type(exception).__name__}
        self.errors.append(record)
        try:
            path = directory("logs") / "diagnostic.json"
            path.write_text(json.dumps(list(self.errors), indent=2), encoding="utf-8")
        except OSError:
            pass  # Keep the bounded in-memory diagnostic; logging must never stop dictation.

    def snapshot(self):
        return {
            "moteur": self.model,
            "backend": self.backend,
            "microphone": self.microphone,
            "repli": self.fallback_reason,
            "chargement_s": self.load_seconds,
            "délai_depuis_dernier_bloc_audio_ms": list(self.latencies),
            "erreurs": list(self.errors),
        }
