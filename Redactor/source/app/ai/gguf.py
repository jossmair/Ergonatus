"""Bounded GGUF metadata reader; tensor data is never parsed or executed."""
import re
import struct


def metadata(path, wanted=("tokenizer.chat_template", "general.architecture")):
    formats = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "?", 10: "Q", 11: "q", 12: "d"}
    result = {}
    with open(path, "rb") as stream:
        def read(size):
            if stream.tell() + size > 64 * 1024**2:
                raise ValueError("Les métadonnées GGUF dépassent la limite autorisée.")
            data = stream.read(size)
            if len(data) != size:
                raise ValueError("Métadonnées GGUF incomplètes.")
            return data
        def number(fmt):
            return struct.unpack("<" + fmt, read(struct.calcsize("<" + fmt)))[0]
        def string(keep=True):
            size = number("Q")
            if size > 16 * 1024**2:
                raise ValueError("Chaîne GGUF trop longue.")
            data = read(size)
            return data.decode("utf-8", errors="strict") if keep else None
        def value(kind, keep=False, level=0):
            if level > 3:
                raise ValueError("Structure GGUF trop profonde.")
            if kind in formats:
                v = number(formats[kind])
                return v if keep else None
            if kind == 8:
                return string(keep)
            if kind == 9:
                element, count = number("I"), number("Q")
                if count > 2_000_000:
                    raise ValueError("Table GGUF trop grande.")
                output = [] if keep else None
                for _ in range(count):
                    item = value(element, keep, level + 1)
                    if keep: output.append(item)
                return output
            raise ValueError("Type de métadonnée GGUF inconnu.")
        if read(4) != b"GGUF" or number("I") not in (2, 3):
            raise ValueError("En-tête GGUF invalide.")
        number("Q")  # tensor count
        count = number("Q")
        if count > 10000:
            raise ValueError("Trop de métadonnées GGUF.")
        for _ in range(count):
            key, kind = string(), number("I")
            item = value(kind, key in wanted)
            if key in wanted:
                result[key] = item
    return result


def luciole_template(template):
    """Remove Transformers-only generation markers, preserving prompt tokens.

    Bind the publisher's enable_thinking flag, rather than assuming ChatML.
    Only used for the hash-verified official Luciole catalog entry.
    """
    clean = re.sub(r"{%-?\s*(?:endgeneration|generation)\s*-?%}", "", template)
    return "{% set enable_thinking = false %}\n" + clean
