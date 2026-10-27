"""Abbreviate explicit measured quantities, without changing their magnitude."""
import re
import unicodedata

from text_to_num import alpha2digit


def unaccented(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


UNITS = {}


def register(name, symbol, plural=None):
    for word in (name, plural or name + "s"):
        UNITS[word.lower()] = UNITS[unaccented(word).lower()] = symbol


for prefix, symbol in (("micro", "µ"), ("milli", "m"), ("centi", "c"), ("déci", "d"),
                       ("", ""), ("déca", "da"), ("hecto", "h"), ("kilo", "k")):
    register(prefix + "gramme", symbol + "g")
    register(prefix + "litre", symbol + "L")
    register(prefix + "mètre", symbol + "m")
    for suffix, power in (("carré", "²"), ("cube", "³")):
        register(prefix + "mètre " + suffix, symbol + "m" + power,
                 prefix + "mètres " + suffix + "s")
register("kilo", "kg")
register("tonne", "t")
register("hectare", "ha")
register("are", "a")
register("seconde", "s")
register("milliseconde", "ms")
register("minute", "min")
register("heure", "h")
register("kilomètre par heure", "km/h", "kilomètres par heure")
register("mètre par seconde", "m/s", "mètres par seconde")
register("degré Celsius", "°C", "degrés Celsius")
register("kelvin", "K")
for prefix, symbol in (("", ""), ("milli", "m"), ("kilo", "k"), ("méga", "M")):
    register(prefix + "watt", symbol + "W")
    register(prefix + "wattheure", symbol + "Wh")
    register(prefix + "watt heure", symbol + "Wh", prefix + "watts heures")
    register(prefix + "watt-heure", symbol + "Wh", prefix + "watts-heures")
register("volt", "V")
register("ampère", "A")
register("milliampère", "mA")

# Accept a missing space after a digit, never a suffix inside another word.
UNIT = re.compile(r"(?<![^\W\d_])(?:" + "|".join(
    re.escape(name).replace(r"\ ", r"[ \t]+") for name in sorted(UNITS, key=len, reverse=True))
    + r")(?!\w)", re.IGNORECASE)
NUMERIC = re.compile(r"(?<![\w.,:/])[-+]?\d+(?:[ \u00a0\u202f]\d{3})*(?:[.,]\d+)?[ \t]*$")
WORDS = ("zéro un une deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze "
         "quinze seize vingt trente quarante cinquante soixante septante huitante octante nonante "
         "cent cents mille million millions milliard milliards moins et virgule").split()
SPOKEN = re.compile(r"(?<!\w)(?:" + "|".join(WORDS) + r")(?:[ \t‐‑-]+(?:" + "|".join(WORDS) + r"))*[ \t]*$",
                    re.IGNORECASE)


def abbreviate(text, number_style="digits"):
    output, position = [], 0
    for unit in UNIT.finditer(text):
        prefix = text[position:unit.start()]
        quantity = NUMERIC.search(prefix) or SPOKEN.search(prefix)
        if not quantity:
            continue
        original = quantity.group().strip()
        converted = original
        if not re.match(r"[-+]?\d", original):
            spoken = original.lower().replace("‐", "-").replace("‑", "-")
            converted = "1" if spoken in ("un", "une") else alpha2digit(spoken, "fr", threshold=0)
            if converted.startswith("moins "):
                converted = "-" + converted[6:]
            if not re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", converted):
                continue
        start = position + quantity.start()
        value = converted if number_style == "digits" else original
        name = re.sub(r"[ \t]+", " ", unit.group().lower())
        output.extend((text[position:start], value, " ", UNITS[name]))
        position = unit.end()
    output.append(text[position:])
    return "".join(output)
