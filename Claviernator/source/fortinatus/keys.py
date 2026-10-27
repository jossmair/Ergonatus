"""Windows virtual keys; display names follow a French AZERTY keyboard."""
KEYS = {
    0x08: "Retour arrière", 0x09: "Tabulation", 0x0D: "Entrée", 0x13: "Pause",
    0x14: "Verr. maj", 0x1B: "Échap", 0x20: "Espace", 0x21: "Page précédente",
    0x22: "Page suivante", 0x23: "Fin", 0x24: "Début", 0x25: "Flèche gauche",
    0x26: "Flèche haut", 0x27: "Flèche droite", 0x28: "Flèche bas",
    0x2C: "Impr. écran", 0x2D: "Insertion", 0x2E: "Suppr",
    0x5B: "Windows gauche", 0x5C: "Windows droite", 0x5D: "Menu",
    0x6A: "Pavé ×", 0x6B: "Pavé +", 0x6D: "Pavé −", 0x6E: "Pavé .", 0x6F: "Pavé /",
    0x90: "Verr. num", 0x91: "Arrêt défil.",
    0xA0: "Maj gauche", 0xA1: "Maj droite", 0xA2: "Ctrl gauche", 0xA3: "Ctrl droite",
    0xA4: "Alt gauche", 0xA5: "AltGr", 0xAD: "Muet", 0xAE: "Volume −", 0xAF: "Volume +",
    0xB0: "Piste suivante", 0xB1: "Piste précédente", 0xB2: "Arrêter média", 0xB3: "Lecture / pause",
    0xBA: "$ / £", 0xBB: "= / +", 0xBC: ", / ?", 0xBD: ") / °",
    0xBE: "; / .", 0xBF: ": / /", 0xC0: "ù / %", 0xDB: "^ / ¨",
    0xDC: "* / µ", 0xDD: "²", 0xDE: "! / §", 0xE2: "< / >",
}
KEYS.update({vk: chr(vk) for vk in range(65, 91)})
SYMBOLS = {ord(d): s for d, s in zip("1234567890", "&é\"'(-è_çà")}
KEYS.update({vk: f"{chr(vk)} / {symbol}" for vk, symbol in SYMBOLS.items()})
KEYS.update({0x60 + i: f"Pavé {i}" for i in range(10)})
KEYS.update({0x70 + i: f"F{i + 1}" for i in range(24)})
SHIFT = {0xA0, 0xA1}
CTRL = {0xA2, 0xA3}
ALT = {0xA4, 0xA5}
WIN = {0x5B, 0x5C}
MODIFIERS = SHIFT | CTRL | ALT | WIN
EMERGENCY = 0x7B  # F12 remains available regardless of the profile.
EXTENDED = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2C, 0x2D, 0x2E,
            0x5B, 0x5C, 0x5D, 0x6F, 0x90, 0xA3, 0xA5}


def key_name(vk):
    return KEYS.get(vk, f"Touche 0x{vk:02X}")


def combo_name(keys):
    short = {0xA0: "Maj", 0xA1: "Maj droite", 0xA2: "Ctrl", 0xA3: "Ctrl droit",
             0xA4: "Alt", 0xA5: "AltGr", 0x5B: "Win", 0x5C: "Win droit"}
    return " + ".join(short.get(vk, key_name(vk)) for vk in keys)


def normalize_key(vk, scan, flags=0):
    """Some drivers report generic Ctrl/Alt/Shift instead of a sided key."""
    if vk == 0x10:
        return 0xA1 if scan & 0xFF == 0x36 else 0xA0
    if vk == 0x11:
        return 0xA3 if flags & 1 else 0xA2
    if vk == 0x12:
        return 0xA5 if flags & 1 else 0xA4
    return vk

