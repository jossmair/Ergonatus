"""Characters stay Unicode; navigation and shortcuts are separate target actions."""
import unicodedata
from PySide6.QtCore import QTextBoundaryFinder

# Base, Shift, AltGr, Windows virtual key. Digits need only one click.
NUMBER_KEYS = [("1", "&", "", 49), ("2", "é", "~", 50), ("3", '"', "#", 51),
               ("4", "'", "{", 52), ("5", "(", "[", 53), ("6", "-", "|", 54),
               ("7", "è", "`", 55), ("8", "_", "\\", 56), ("9", "ç", "^", 57),
               ("0", "à", "@", 48), (")", "°", "]", 0xDB), ("=", "+", "}", 0xBB)]
LETTER_ROWS = ["AZERTYUIOP", "QSDFGHJKLM", "WXCVBN"]
CHARACTERS = {
    "Accents": list("éèêëàâäùûüîïôöçœæÉÈÊËÀÂÄÙÛÜÎÏÔÖÇŒÆñÑáíóúßøå"),
    "Signes": list("@#€£$¥¢%‰&§©®™°µ±×÷=≠≤≥∞√²³¼½¾«»“”‘’…–—_|\\{}[]<>~^`"),
    "Émojis": ["🙂", "😊", "😂", "❤️", "👍", "🙏", "👋", "✨", "🎉", "💡", "☀️", "🌙", "🌿", "🌸", "⭐", "✅",
               "❌", "💬", "📌", "📅", "⏰", "✉️", "📞", "🏠", "☕", "🎵", "🎮", "🐱", "🐶", "🚗", "✈️", "🌍"],
}
SPECIAL_KEYS = [
    [(f"F{i}", 0x6F + i) for i in range(1, 13)],
    [("Échap", 0x1B), ("Tab", 9), ("Entrée", 13), ("Retour", 8), ("Suppr", 0x2E), ("Inser", 0x2D)],
    [("Début", 0x24), ("Fin", 0x23), ("Page ↑", 0x21), ("Page ↓", 0x22), ("Impr. écran", 0x2C)],
    [("←", 0x25), ("↑", 0x26), ("↓", 0x28), ("→", 0x27), ("Espace", 0x20)],
]


def unicode_character(code):
    code = code.strip().upper().removeprefix("U+")
    if not code or len(code) > 6 or any(char not in "0123456789ABCDEF" for char in code):
        raise ValueError("Choisissez un code Unicode, par exemple 20AC pour €.")
    value = int(code, 16)
    if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF or unicodedata.category(chr(value)) in ("Cc", "Cs"):
        raise ValueError("Ce code ne correspond pas à un caractère utilisable.")
    return chr(value)


def erase_character(text):
    """Remove one complete Unicode grapheme, including complex emoji sequences."""
    if not text:
        return text
    finder = QTextBoundaryFinder(QTextBoundaryFinder.BoundaryType.Grapheme, text)
    finder.toEnd()
    boundary = finder.toPreviousBoundary()
    # Qt positions count UTF-16 units, Python slices count Unicode codepoints.
    return text.encode("utf-16-le")[:max(0, boundary) * 2].decode("utf-16-le")
