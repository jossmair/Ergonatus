import re


class TextLedger:
    """Deduplicate by event identity, never by word equality: 'oui oui' is valid."""

    def __init__(self):
        self.seen = set()
        self.confirmed = []
        self.inserted = []
        self.pending = []
        self.finalized = False

    def confirm(self, identity, text):
        if identity in self.seen or not text:
            return False
        self.seen.add(identity)
        self.confirmed.append(text)
        self.pending.append(text)
        return True

    def acknowledge(self, text):
        if not self.pending or self.pending[0] != text:
            raise RuntimeError("Ordre d’insertion invalide.")
        self.inserted.append(self.pending.pop(0))


class TextFormatter:
    def __init__(self, settings):
        self.settings = settings
        self.last = ""

    def preview(self, text):
        previous = self.last
        try:
            return self.format(text)
        finally:
            self.last = previous

    def format(self, text):
        text = text.strip()
        if not text:
            return ""
        if self.settings.voice_commands:
            # Explicit whole utterances only: never reinterpret 'le point de vue'.
            command = {"point": ".", "virgule": ",", "nouvelle ligne": "\n"}
            if text.casefold().rstrip(".?!") in command:
                text = command[text.casefold().rstrip(".?!")]
        if self.settings.typography:
            text = re.sub(r"\s*([;:!?])", "\u202f\\1", text)
        if self.settings.capitals and text and (not self.last or self.last in ".!?\n"):
            text = text[0].upper() + text[1:]
        prefix = "" if not self.last or self.last.isspace() or text[:1] in ".,;:!?\n" else " "
        if text:
            self.last = text[-1]
        return prefix + text
