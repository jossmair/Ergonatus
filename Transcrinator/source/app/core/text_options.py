"""Local, explicit vocabulary corrections and French number formatting."""
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from num2words import num2words
from text_to_num import alpha2digit
from app.core.units import abbreviate


VOCABULARY_CATEGORIES = (("proper_name", "Noms propres"), ("city", "Villes"),
                         ("product", "Produits"), ("technical", "Mots techniques"))
CATEGORY_LABELS = dict(VOCABULARY_CATEGORIES)


def folded(text):
    chars, starts, ends = [], [], []
    for index, char in enumerate(text):
        if unicodedata.combining(char):
            if ends:
                ends[-1] = index + 1
            continue
        char = char.replace("œ", "oe").replace("Œ", "OE").replace("’", "'")
        for value in unicodedata.normalize("NFKD", char).casefold():
            if unicodedata.combining(value):
                continue
            chars.append(" " if value.isspace() or value in "-‐‑–—" else value)
            starts.append(index)
            ends.append(index + 1)
    return "".join(chars), starts, ends


def key(text):
    return " ".join(folded(text)[0].split())


def normalize_vocabulary(entries):
    result = []
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, str):
            entry = {"name": entry, "aliases": []}
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            continue
        name = entry["name"].strip()
        if not name:
            continue
        aliases = entry.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = []
        normalized = {"name": name, "aliases": list(dict.fromkeys(
            alias.strip() for alias in aliases if isinstance(alias, str) and alias.strip()))}
        category = entry.get("category")
        if isinstance(category, str) and category in CATEGORY_LABELS:
            normalized["category"] = category
        result.append(normalized)
    return result


def pattern_for(terms):
    if not terms:
        return None
    alternatives = [r"\s+".join(re.escape(part) for part in term.split())
                    for term in sorted(terms, key=len, reverse=True)]
    return re.compile(r"(?<!\w)(?:" + "|".join(alternatives) + r")(?!\w)")


class Vocabulary:
    def __init__(self, entries):
        self.entries = normalize_vocabulary(entries)
        candidates = {}
        for entry in self.entries:
            for term in [entry["name"], *entry["aliases"]]:
                candidates.setdefault(key(term), set()).add(entry["name"])
        self.ambiguous = {term for term, names in candidates.items() if len(names) > 1}
        self.replacements = {term: next(iter(names)) for term, names in candidates.items()
                             if len(names) == 1 and term}
        self.pattern = pattern_for(self.replacements)
        self.names_pattern = pattern_for({key(entry["name"]) for entry in self.entries})

    @staticmethod
    def replace_matches(text, pattern, replacement):
        if pattern is None:
            return text
        normalized, starts, ends = folded(text)
        output, position = [], 0
        for match in pattern.finditer(normalized):
            start, end = starts[match.start()], ends[match.end() - 1]
            output.extend((text[position:start], replacement(text[start:end], key(match.group()))))
            position = end
        output.append(text[position:])
        return "".join(output)

    def correct(self, text):
        def replacement(original, term):
            canonical = self.replacements[term]
            # A technical term entered in lowercase must not remove the
            # capital supplied by the recognizer at the start of a sentence.
            if canonical[:1].islower() and original[:1].isupper():
                return canonical[0].upper() + canonical[1:]
            return canonical
        return self.replace_matches(text, self.pattern, replacement)

    def protect(self, text):
        saved = {}

        def mask(original, term):
            token = "\ue000" + chr(0xF0000 + len(saved)) + "\ue001"
            saved[token] = original
            return token

        return self.replace_matches(text, self.names_pattern, mask), saved


NUMERIC = re.compile(r"(?<!\w)[+-]?\d+(?:(?:[ \u00a0\u202f]+\d+)|(?:[.,:/-]\d+))*(?!\w)")
URL = re.compile(r"\b(?:https?://|www\.)[^\s<>]+|\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|\b[\w-]+(?:\.[\w-]+)*\.[a-zA-Z]{2,}(?:/[^\s<>]*)?")
MASK = re.compile(r"[\ue000\ue010][\U000f0000-\U000ffffd][\ue001\ue011]")


def protect_urls(text):
    saved = {}

    def mask(match):
        original = match.group().rstrip(".,;:!?…")
        suffix = match.group()[len(original):]
        token = "\ue010" + chr(0xF0000 + len(saved)) + "\ue011"
        saved[token] = original
        return token + suffix

    return URL.sub(mask, text), saved


def restore(text, saved):
    return MASK.sub(lambda match: saved.get(match.group(), match.group()), text)


def short_dictation(text):
    masked, saved = protect_urls(text)
    words = re.findall(r"\d+(?:[.,:]\d+)*|[^\W\d_]+(?:['’‐‑-][^\W\d_]+)*", masked)
    if len(words) + len(saved) >= 5:
        return text
    chars = []
    for index, char in enumerate(masked):
        previous = masked[index - 1] if index else ""
        following = masked[index + 1] if index + 1 < len(masked) else ""
        numeric = char in ".,:" and previous.isdigit() and following.isdigit()
        chars.append(" " if char in ".,;:!?…" and not numeric else char)
    return restore(re.sub(r"[ \t]+", " ", "".join(chars)).strip(), saved)


def number_in_words(match):
    original = match.group()
    unsigned = original.lstrip("+-")
    if ":" in unsigned or "/" in unsigned or "-" in unsigned:
        return original
    if unsigned.count(".") + unsigned.count(",") > 1:
        return original  # dates, versions and ambiguous numeric sequences
    whole = re.split(r"[.,]", unsigned)[0]
    if any(char.isspace() for char in whole) and not re.fullmatch(r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+", whole):
        return original
    compact = re.sub(r"\s", "", original).replace(",", ".")
    integer = compact.lstrip("+-").split(".")[0]
    if len(integer) > 1 and integer.startswith("0"):
        return original  # preserve leading-zero identifiers and telephone numbers
    try:
        return num2words(Decimal(compact), lang="fr")
    except (ValueError, InvalidOperation, OverflowError, TypeError):
        return original


class TextPostprocessor:
    def __init__(self, entries=(), number_style="digits", abbreviate_units=True):
        self.vocabulary = Vocabulary(entries)
        self.number_style = number_style
        self.abbreviate_units = abbreviate_units

    def apply(self, text):
        text, opaque = protect_urls(text)
        if self.abbreviate_units:
            text = abbreviate(text, self.number_style)
        text = self.vocabulary.correct(text)
        text, saved = self.vocabulary.protect(text)
        if self.number_style == "words":
            text = NUMERIC.sub(number_in_words, text)
        elif self.number_style == "digits":
            text = alpha2digit(text, "fr", threshold=2)
        text = restore(restore(text, saved), opaque)
        return short_dictation(text)
