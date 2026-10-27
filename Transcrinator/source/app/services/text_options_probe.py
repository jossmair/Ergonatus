"""Explicit frozen-runtime probe; all text here is a synthetic fixture."""
import json
import time
from pathlib import Path

from app.core.text_options import TextPostprocessor, normalize_vocabulary, VOCABULARY_CATEGORIES
from app.core import autostart
from app.core.hotkeys import GlobalHotkey, TRIGGER_KEYS
import sys
import subprocess


def probe(output):
    vocabulary = [{"name": "Josselin", "aliases": ["Jocelyn"]}, {"name": "Les Deux Alpes", "aliases": []}]
    checks = {}
    from app.core import text_injector
    from types import SimpleNamespace

    class DeliveryProbe(text_injector.TextInjector):
        def native_insert(self, payload):
            self.payload = payload
            return True

    original_modifiers = text_injector.modifiers_held
    text_injector.modifiers_held = lambda: False
    try:
        delivery = DeliveryProbe(SimpleNamespace(valid=lambda: True), "native")
        checks["trailing_space_in_delivery"] = delivery.insert("Premier texte  ") and delivery.payload == "Premier texte "
    finally:
        text_injector.modifiers_held = original_modifiers
    for mode, text, expected in (
        ("digits", "Jocelyn souhaite acheter vingt-cinq pommes.", "Josselin souhaite acheter 25 pommes."),
        ("words", "Jocelyn souhaite acheter 25 pommes.", "Josselin souhaite acheter vingt-cinq pommes."),
        ("digits", "Jocelyn, demain !", "Josselin demain"),
        ("digits", "Les Deux Alpes !", "Les Deux Alpes"),
        ("words", "https://exemple.fr?q=25 !", "https://exemple.fr?q=25"),
    ):
        checks[str(len(checks))] = TextPostprocessor(vocabulary, mode).apply(text) == expected
    for text, expected in (("250 grammes", "250 g"), ("une tonne", "1 t"),
                           ("trois mètres carrés", "3 m²"), ("cinq litres", "5 L"),
                           ("vingt degrés Celsius", "20 °C")):
        checks["units_" + str(len(checks))] = TextPostprocessor().apply(text) == expected
    checks["units_disabled"] = TextPostprocessor([], "digits", False).apply("25 grammes") == "25 grammes"
    checks["units_with_word_numbers"] = TextPostprocessor([], "words").apply("25 kilogrammes") == "vingt-cinq kg"
    categorized = [{"name": f"Projet{i}", "aliases": [f"Project{i}"], "category": identity}
                   for i, (identity, name) in enumerate(VOCABULARY_CATEGORIES)]
    checks["dictionary_categories_preserved"] = normalize_vocabulary(categorized) == categorized
    checks["categories_keep_correction_behavior"] = TextPostprocessor(categorized).apply("Project0") == "Projet0"
    for identity, name, vk in TRIGGER_KEYS:
        hotkey = GlobalHotkey(lambda: None, trigger_key=identity)
        consumed = 0x70 <= vk <= 0x7B
        checks["trigger_" + identity] = (
            hotkey.handle_key(vk, True, held=set()) == (False, consumed)
            and hotkey.handle_key(vk, False) == (True, consumed))
    hotkey.set_trigger("shift_left")
    checks["trigger_live_change"] = (hotkey.handle_key(0xA0, True, held=set()) == (False, False)
                                     and hotkey.handle_key(0xA0, False) == (True, False))
    if getattr(sys, "frozen", False):
        checks["startup_frozen_command"] = autostart.command() == subprocess.list2cmdline([sys.executable, "--minimized"])
    entries = vocabulary + [{"name": f"Projet{i:04}", "aliases": [f"Project{i:04}"]} for i in range(498)]
    started = time.perf_counter()
    processor = TextPostprocessor(entries)
    compiled_ms = (time.perf_counter() - started) * 1000
    fixture = "Jocelyn souhaite acheter vingt-cinq pommes."
    started = time.perf_counter()
    for _ in range(100):
        processor.apply(fixture)
    processing_ms = (time.perf_counter() - started) * 10
    report = {"success": all(checks.values()), "checks": checks, "dictionary_entries": len(entries),
              "compile_ms": round(compiled_ms, 3), "mean_processing_ms": round(processing_ms, 3),
              "iterations": 100}
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["success"] else 1
