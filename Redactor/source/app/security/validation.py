"""Pure checks used before every native write and every IPC dispatch."""
import hashlib
import json
import re
import struct

MAX_FRAME = 65536
COMMANDS = {"open", "compose", "rewrite", "correct", "summarize", "status", "cancel"}


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def splice_text(original, start, end, selected, replacement):
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(original):
        raise ValueError("Le point d’insertion ne peut pas être établi avec fiabilité.")
    if original[start:end] != selected:
        raise ValueError("La sélection a changé. Choisissez à nouveau le champ de destination.")
    return original[:start] + replacement + original[end:]


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Propriété JSON dupliquée.")
        result[key] = value
    return result


def parse_json(data):
    if not 2 <= len(data) <= MAX_FRAME:
        raise ValueError("Message trop volumineux ou vide.")
    def depth(value, level=0):
        if level > 16:
            raise ValueError("JSON trop profond.")
        if isinstance(value, dict):
            for x in value.values(): depth(x, level + 1)
        elif isinstance(value, list):
            for x in value: depth(x, level + 1)
    value = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates,
                       parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Constante JSON invalide.")))
    depth(value)
    if not isinstance(value, dict):
        raise ValueError("Un objet JSON est attendu.")
    return value


def validate_command(payload):
    if not isinstance(payload, dict) or set(payload) - {"command", "text", "style"}:
        raise ValueError("Paramètres inconnus.")
    command = payload.get("command")
    if not isinstance(command, str) or command not in COMMANDS:
        raise ValueError("Commande interdite. L’insertion distante n’existe pas.")
    text = payload.get("text", "")
    if not isinstance(text, str) or len(text) > 24000:
        raise ValueError("Texte invalide ou trop long.")
    from app.ai.prompts import STYLES
    if payload.get("style", "Naturel") not in STYLES:
        raise ValueError("Style invalide.")
    if command in ("open", "status", "cancel") and (text or "style" in payload):
        raise ValueError("Cette commande n’accepte pas de texte ni de style.")
    return payload


class FrameDecoder:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        if len(self.buffer) + len(data) > 2 * MAX_FRAME + 8:
            raise ValueError("File de messages trop grande.")
        self.buffer.extend(data)
        frames = []
        while len(self.buffer) >= 4:
            size = struct.unpack_from("<I", self.buffer)[0]
            if not 2 <= size <= MAX_FRAME:
                raise ValueError("Taille de message invalide.")
            if len(self.buffer) < size + 4:
                break
            frames.append(parse_json(bytes(self.buffer[4:size + 4])))
            del self.buffer[:size + 4]
        return frames


def encode_frame(value):
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if not 2 <= len(data) <= MAX_FRAME:
        raise ValueError("Taille de message invalide.")
    return struct.pack("<I", len(data)) + data
