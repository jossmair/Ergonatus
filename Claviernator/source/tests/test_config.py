from dataclasses import asdict
import json
from unittest.mock import patch
import pytest

from fortinatus.config import Mapping, Profile, Settings
from fortinatus.windows import Input, WindowsInput, startup_command
import ctypes


def test_settings_roundtrip_preserves_unicode_and_all_actions(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(profiles=[Profile(mappings=[Mapping(65, "text", text="Ça va ? 🌿\nOui !"),
                                                  Mapping(66, "mouse_hold", button="right")])])
    settings.save(path)
    assert Settings.load(path) == settings
    assert "Ça va" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("change", [
    {"version": 2}, {"profiles": []}, {"active_profile": "missing"},
    {"start_active": "yes"}, {"version": True}, {"unknown": 5},
    {"profiles": [{"name": ""}]}, {"profiles": [{"debounce_ms": -1}]},
    {"profiles": [{"pointer_speed": 100}]}, {"profiles": [{"sticky_modifiers": 1}]},
    {"profiles": [{"mappings": [{"source": 0x7B, "kind": "disabled"}]}]},
    {"profiles": [{"mappings": [{"source": 65, "keys": [0x7B]}]}]},
    {"profiles": [{"mappings": [{"source": 65, "keys": [66, 66]}]}]},
    {"profiles": [{"mappings": [{"source": 65, "kind": "shell"}]}]},
    {"profiles": [{"mappings": [{"source": 65, "kind": "text", "text": "x" * 501}]}]},
    {"profiles": [{"mappings": [{"source": 65, "keys": [66]}, {"source": 65, "keys": [67]}]}]},
])
def test_invalid_imports_are_rejected(change):
    data = asdict(Settings())
    data.update(change)
    with pytest.raises(ValueError):
        Settings.from_dict(data)


def test_invalid_file_is_preserved(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("invalid", encoding="utf-8")
    with pytest.raises(ValueError):
        Settings.load(path)
    assert path.read_text() == "invalid"


def test_failed_atomic_save_preserves_original(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings()
    settings.save(path)
    original = path.read_bytes()
    settings.profile.invert_numbers = True
    with patch("fortinatus.config.os.replace", side_effect=OSError("disk error")):
        with pytest.raises(OSError):
            settings.save(path)
    assert path.read_bytes() == original
    assert not path.with_suffix(".json.tmp").exists()


def test_windows_input_abi():
    assert ctypes.sizeof(Input) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_startup_command_quotes_paths_and_minimizes():
    command = startup_command(r"C:\Users\Prénom Nom\Fortinatus")
    assert "--minimized" in command
    assert '"C:\\Users\\Prénom Nom\\Fortinatus"' in command
    assert "run_claviernator.py" in command


def test_unicode_message_chunks_preserve_surrogate_order():
    assert list(WindowsInput.text_chunks("Ça va 🌿 Oui 😀!")) == ["Ça va ", "🌿", " Oui ", "😀", "!"]
    assert list(WindowsInput.text_chunks("Bonjour")) == ["Bonjour"]

