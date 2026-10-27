from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.core.text_options import TextPostprocessor, Vocabulary, short_dictation
from app.core.state_machine import State
from app.engines.base import Transcript
from app.ui.floating_hub import FloatingHub, bottom_center
from app.ui.vocabulary_dialog import VocabularyDialog


@pytest.mark.parametrize("raw,expected", [
    ("Bonjour, Paris !", "Bonjour Paris"),
    ("Je veux ces pommes.", "Je veux ces pommes"),
    ("Je veux acheter ces pommes.", "Je veux acheter ces pommes."),
    ("Saint-Brieuc, demain ?", "Saint-Brieuc demain"),
    ("Prix 3,14.", "Prix 3,14"),
    ("https://exemple.fr/recherche?q=25 !", "https://exemple.fr/recherche?q=25"),
])
def test_short_search_text_has_no_sentence_punctuation(raw, expected):
    assert short_dictation(raw) == expected


def test_explicit_vocabulary_accents_aliases_boundaries_and_no_cascade():
    vocabulary = Vocabulary([{"name": "Josselin", "aliases": ["Jocelyn", "Joselin"]},
                             {"name": "Saint-Brieuc", "aliases": []}])
    assert vocabulary.correct("jocelyn va à saint brieuc, pas Joselinville.") == "Josselin va à Saint-Brieuc, pas Joselinville."
    assert Vocabulary([{"name": "Élodie", "aliases": []}]).correct("e\u0301lodie") == "Élodie"
    conflicting = Vocabulary([{"name": "Alice", "aliases": ["test"]}, {"name": "Alicia", "aliases": ["test"]}])
    assert "test" in conflicting.ambiguous and conflicting.correct("test") == "test"


def test_technical_vocabulary_keeps_sentence_capitalization():
    vocabulary = Vocabulary([{"name": "maçonnerie", "aliases": []}, {"name": "ABF", "aliases": []}])
    assert vocabulary.correct("Maconnerie traditionnelle, abf.") == "Maçonnerie traditionnelle, ABF."


def test_imported_json_and_text_merge_without_losing_existing_entries(tmp_path):
    import json
    from scripts.import_vocabulary import import_paths
    source = tmp_path / "lexique.json"
    source.write_text(json.dumps({"entrees": [
        {"forme": "Saint-Brieuc", "variantes_de_detection": ["saint brieuc", "saint brieu"]},
        {"forme": "maçonnerie", "mode": "orthographe_uniquement"}]}), encoding="utf-8-sig")
    lines = tmp_path / "mots.txt"
    lines.write_text("Saint-Brieuc\nmaçonnerie\nABF\n", encoding="utf-8")
    settings = Settings(vocabulary=[{"name": "Josselin", "aliases": ["Jocelyn"]}])
    report = import_paths(settings, [source, lines])
    assert report["dictionary_entries"] == 4 and report["ambiguous_terms"] == 0
    assert Vocabulary(settings.vocabulary).correct("Jocelyn à saint brieu") == "Josselin à Saint-Brieuc"
    assert report == import_paths(Settings(vocabulary=settings.vocabulary), [source, lines]) | {"previous_entries": 1}
    separate = Settings()
    excluded = import_paths(separate, [source, lines], exclude=("ABF",))
    assert excluded["dictionary_entries"] == 2 and excluded["excluded_ambiguous_entries"] == 1


@pytest.mark.parametrize("mode,raw,expected", [
    ("digits", "Je veux acheter vingt-cinq pommes.", "Je veux acheter 25 pommes."),
    ("words", "Je veux acheter 25 pommes.", "Je veux acheter vingt-cinq pommes."),
    ("words", "25", "vingt-cinq"),
    ("words", "06 12 34 56 78", "06 12 34 56 78"),
    ("words", "Version 1.3.2.", "Version 1.3.2"),
    ("words", "https://exemple.fr?q=25", "https://exemple.fr?q=25"),
    ("digits", "Un article pour une recherche.", "Un article pour une recherche."),
])
def test_number_style(mode, raw, expected):
    assert TextPostprocessor([], mode).apply(raw) == expected


@pytest.mark.parametrize("mode", ["digits", "words"])
def test_registered_names_are_protected_from_number_conversion(mode):
    entries = [{"name": "Les Deux Alpes", "aliases": []}, {"name": "Studio 54", "aliases": ["Studio cinquante-quatre"]}]
    processor = TextPostprocessor(entries, mode)
    assert processor.apply("Les Deux Alpes !") == "Les Deux Alpes"
    assert processor.apply("Studio cinquante-quatre.") == "Studio 54"


def test_text_preferences_persist_and_automatic_setup_preserves_them(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    settings = Settings(number_style="words", vocabulary=[{"name": "Élodie", "aliases": ["Elodi"]}])
    settings.configure_automatic()
    loaded = Settings.load()
    assert loaded.number_style == "words" and loaded.vocabulary == settings.vocabulary


def test_dictionary_can_save_delete_and_reject_ambiguous_aliases():
    app = QApplication.instance() or QApplication([])
    dialog = VocabularyDialog([])
    dialog.table.setItem(0, 0, QTableWidgetItem("Josselin"))
    dialog.table.setItem(0, 1, QTableWidgetItem("Jocelyn, Joselin"))
    dialog.save_entries()
    assert dialog.entries == [{"name": "Josselin", "aliases": ["Jocelyn", "Joselin"], "category": "proper_name"}]
    dialog.add_row("Autre", "Jocelyn")
    assert dialog.table.item(0, 0).text() == "Autre"
    dialog.save_entries()
    assert not dialog.notice.isHidden()
    dialog.table.selectRow(0)
    dialog.remove_rows()
    assert dialog.table.rowCount() == 1
    dialog.deleteLater()
    app.processEvents()


def test_resting_orb_follows_mouse_screen_and_shift_state_restores(monkeypatch):
    import app.ui.floating_hub as module
    app = QApplication.instance() or QApplication([])
    now = [0.]
    area = [QRect(0, 0, 1920, 1040)]
    screen = SimpleNamespace(availableGeometry=lambda: area[0])
    monkeypatch.setattr(module.QGuiApplication, "screenAt", lambda point: screen)
    hub = FloatingHub(Settings(), clock=lambda: now[0])
    hub.set_state("Prêt")
    assert hub.compacted and hub.size() == QSize(36, 36)
    assert hub.pos() == QPoint(1920 - 36 - 16, 1040 - 36 - 16)
    area[0] = QRect(-1280, 0, 1280, 984)
    hub.animate()
    assert hub.x() == -52
    hub.set_state("Préparation…")  # left Shift starts dictation with this state
    assert not hub.compacted and hub.size() == QSize(172, 44)
    assert hub.pos() == bottom_center(hub.size(), area[0])
    now[0] = 100
    hub.set_state("Écoute…")
    now[0] = 200
    hub.animate()
    assert not hub.compacted
    hub.set_state("Fermé")
    hub.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("initial", [None, "first"])
async def test_clicks_and_late_field_change_insert_only_at_final_selection(monkeypatch, initial):
    controller = Controller(Settings(vocabulary=[{"name": "Josselin", "aliases": ["Jocelyn"]}]),
                            Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    selected, located, inserted = [initial], [], []
    controller.focus = SimpleNamespace(locate=lambda: located.append(selected[0]), valid=lambda: True)
    controller.injector = SimpleNamespace(insert=lambda text: inserted.append((selected[0], text)) or True)

    async def begin(emit):
        controller.emit_fixture = emit

    async def feed(audio):
        assert not located and not inserted

    async def finish():
        selected[0] = "last"
        controller.request("manual_input")
        controller.emit_fixture(Transcript("one", "Jocelyn, demain !", True, 1))

    controller.manager = SimpleNamespace(is_prepared=lambda settings: True,
        active=SimpleNamespace(begin=begin, feed=feed, finish=finish))

    class Capture:
        def __init__(self, device):
            pass

        def start(self):
            pass

        def read(self):
            assert controller.machine.state == State.LISTENING
            selected[0] = "second"
            controller.request("manual_input")
            assert not controller.stop_requested.is_set()
            controller.stop_requested.set()
            return np.ones(512, np.float32), 1

        def stop(self):
            return []

    monkeypatch.setattr("app.core.controller.AudioCapture", Capture)
    await controller._dictate()
    assert not located  # Windows routes the paste; no field detection is needed.
    assert inserted == [("last", "Josselin demain")]
    assert not controller.retained
