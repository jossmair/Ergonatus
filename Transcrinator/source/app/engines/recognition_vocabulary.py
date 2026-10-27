"""Optional native decoder guidance. Compile once; keep audio inference single-pass."""
import ctypes
import unicodedata

from app.core.text_options import normalize_vocabulary


def recognition_phrases(entries):
    """Bound native work and prioritize recently added personal names over cities."""
    normalized = normalize_vocabulary(entries)
    selected = []
    seen = set()
    size = 0
    for category in ("proper_name", "city"):
        for entry in normalized:
            if entry.get("category") != category:
                continue
            name = unicodedata.normalize("NFC", entry["name"])
            if len(name) > 96 or any(unicodedata.category(c).startswith("C") for c in name):
                continue
            if sum(c.isalpha() for c in name) < 3:
                continue
            for variant in (name, name.lower(), name.title()):
                if variant in seen:
                    continue
                extra = len(variant.encode("utf-8")) + 1
                if len(selected) >= 768 or size + extra > 24000:
                    return tuple(selected)
                selected.append(variant)
                seen.add(variant)
                size += extra
    return tuple(selected)


class NativeRecognitionVocabulary:
    """Use the original C API when the extension is unavailable or cannot compile."""
    def __init__(self, library, context):
        self.library, self.context = library, context
        self.original = library.parakeet_capi_transcribe_pcm
        self.transcribe = self.original
        self.phrases = None
        self.supported = all(hasattr(library, name) for name in (
            "transcrinator_context_set", "transcrinator_transcribe_guided"
        ))
        self.status = {"supported": self.supported, "enabled": False, "phrases": 0}
        if self.supported:
            ptr = ctypes.c_void_p
            library.transcrinator_context_set.argtypes = [ptr, ctypes.c_char_p, ctypes.c_float, ctypes.c_int]
            library.transcrinator_context_set.restype = ctypes.c_int
            library.transcrinator_transcribe_guided.argtypes = [
                ptr, ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.c_int, ctypes.c_int
            ]
            library.transcrinator_transcribe_guided.restype = ptr

    def configure(self, phrases):
        phrases = tuple(phrases)
        if phrases == self.phrases:
            return self.status
        if not self.supported:
            self.phrases = phrases
            return self.status
        # Native compilation is transactional; disable the previous graph after
        # rejection so deleted vocabulary cannot remain active accidentally.
        payload = "\n".join(phrases).encode("utf-8")
        code = self.library.transcrinator_context_set(self.context, payload, 2.0, 3)
        enabled = bool(phrases) and code == 0
        if code and self.library.transcrinator_context_set(self.context, b"", 0.0, 3):
            raise RuntimeError("Le dictionnaire de reconnaissance n’a pas pu être désactivé.")
        self.transcribe = self.library.transcrinator_transcribe_guided if enabled else self.original
        self.phrases = phrases
        self.status = {"supported": True, "enabled": enabled, "phrases": len(phrases) if enabled else 0}
        return self.status
