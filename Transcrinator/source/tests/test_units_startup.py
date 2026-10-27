from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from app.core import autostart
from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.core.text_options import TextPostprocessor
from app.ui.main_window import MainWindow


@pytest.mark.parametrize("raw,expected", [
    ("250 grammes", "250 g"), ("cinq kilogrammes", "5 kg"), ("une tonne", "1 t"),
    ("deux tonnes", "2 t"), ("un litre", "1 L"), ("vingt-cinq litres", "25 L"),
    ("50 centilitres", "50 cL"), ("cinq millilitres", "5 mL"), ("un mètre", "1 m"),
    ("deux kilomètres", "2 km"), ("trente centimètres", "30 cm"),
    ("trois mètres carrés", "3 m²"), ("3,5 mètres cubes", "3,5 m³"),
    ("deux hectares", "2 ha"), ("dix kilomètres par heure", "10 km/h"),
    ("cinq mètres par seconde", "5 m/s"), ("vingt degrés Celsius", "20 °C"),
    ("deux kilowatts-heures", "2 kWh"), ("moins trois kilogrammes", "-3 kg"),
    ("1 000 grammes", "1 000 g"), ("10kilogrammes", "10 kg"),
    ("le gramme étalon", "le gramme étalon"), ("le maître d’œuvre", "le maître d’œuvre"),
    ("un métré", "un métré"), ("le programme", "le programme"),
    ("https://exemple.fr/5-kilogrammes", "https://exemple.fr/5-kilogrammes"),
])
def test_measurement_abbreviations_and_non_measurements(raw, expected):
    assert TextPostprocessor().apply(raw) == expected


def test_units_option_is_independent_of_numbers_and_technical_dictionary():
    assert TextPostprocessor([], "words").apply("25 kilogrammes") == "vingt-cinq kg"
    assert TextPostprocessor([], "digits", False).apply("25 kilogrammes") == "25 kilogrammes"
    assert TextPostprocessor([], "words", False).apply("25 kilogrammes") == "vingt-cinq kilogrammes"
    entries = [{"name": "métré", "aliases": []}]
    assert TextPostprocessor(entries).apply("un mètre") == "1 m"
    assert TextPostprocessor(entries).apply("un métré") == "un métré"


def test_new_preferences_survive_automatic_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    settings = Settings(abbreviate_units=False, autostart=False)
    settings.configure_automatic()
    loaded = Settings.load()
    assert not loaded.abbreviate_units and not loaded.autostart


def fake_registry(monkeypatch):
    values = {"OtherApp": ("keep", 1)}
    class Key:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
    def query(key, name):
        if name not in values:
            raise FileNotFoundError
        return values[name]
    def delete(key, name):
        if name not in values:
            raise FileNotFoundError
        del values[name]
    monkeypatch.setattr(autostart, "winreg", SimpleNamespace(HKEY_CURRENT_USER=1, REG_SZ=1,
        OpenKey=lambda *args: Key(), CreateKey=lambda *args: Key(), QueryValueEx=query,
        SetValueEx=lambda key, name, reserved, kind, value: values.update({name: (value, kind)}),
        DeleteValue=delete))
    return values


def test_startup_toggle_owns_one_value_and_quotes_paths(monkeypatch):
    values = fake_registry(monkeypatch)
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart.sys, "executable", r"C:\Program Files\Transcri\Transcri.exe")
    assert not autostart.is_enabled()
    autostart.set_enabled(True)
    assert autostart.is_enabled()
    assert values[autostart.VALUE][0] == '"C:\\Program Files\\Transcri\\Transcri.exe" --minimized'
    autostart.set_enabled(False)
    autostart.set_enabled(False)
    assert not autostart.is_enabled() and values == {"OtherApp": ("keep", 1)}


def test_startup_rebrand_migrates_the_legacy_value_without_two_launches(monkeypatch):
    values = fake_registry(monkeypatch)
    values[autostart.LEGACY_VALUE] = ("legacy executable", 1)
    assert autostart.is_enabled()
    autostart.set_enabled(True)
    assert autostart.VALUE in values and autostart.LEGACY_VALUE not in values
    values[autostart.LEGACY_VALUE] = ("legacy executable", 1)
    autostart.set_enabled(False)
    assert values == {"OtherApp": ("keep", 1)}


def test_ui_saves_both_options_without_reloading_model(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    values = fake_registry(monkeypatch)
    app = QApplication.instance() or QApplication([])
    controller = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    window = MainWindow(controller)
    window.units.setChecked(False)
    kind, value = controller.commands.get_nowait()
    assert kind == "text_options" and value["abbreviate_units"] is False
    window.number_style.setChecked(False)
    kind, value = controller.commands.get_nowait()
    assert kind == "text_options" and value["number_style"] == "words"
    assert value["abbreviate_units"] is False and Settings.load().number_style == "words"
    assert TextPostprocessor([], value["number_style"], value["abbreviate_units"]).apply("25 kilogrammes") == "vingt-cinq kilogrammes"
    window.number_style.setChecked(True)
    assert controller.commands.get_nowait()[1]["number_style"] == "digits"
    assert Settings.load().number_style == "digits"
    window.startup.setChecked(True)
    assert autostart.VALUE in values and Settings.load().autostart
    assert not Settings.load().abbreviate_units
    window.startup.setChecked(False)
    assert autostart.VALUE not in values and not Settings.load().autostart
    window.deleteLater()
    app.processEvents()


def test_startup_failure_reverts_checkbox(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRI_DATA", str(tmp_path))
    def fail(enabled):
        raise PermissionError("fixture")
    monkeypatch.setattr(autostart, "set_enabled", fail)
    app = QApplication.instance() or QApplication([])
    controller = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    window = MainWindow(controller)
    window.startup.setChecked(True)
    assert not window.startup.isChecked() and not window.preferences.autostart
    assert not window.notice.isHidden()
    window.deleteLater()
    app.processEvents()
