import json
import pytest
from services.configuration import Configuration, Preferences


def test_roundtrip_negative_coordinates(tmp_path):
    c = Configuration(tmp_path / "sub" / "settings.json")
    p = Preferences(False, 1.8, True, (-1900, 100), "DISPLAY2")
    c.save(p)
    assert c.load() == p
    assert not list(c.path.parent.glob("*.tmp"))


@pytest.mark.parametrize("content", ["broken", "null", "[]", '{"enabled":"false","magnification":18,"startup":1,"orb_position":[true,4]}'])
def test_invalid_settings_recover_defaults(tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_text(content)
    assert Configuration(path).load() == Preferences()


def test_missing_file_defaults(tmp_path):
    assert Configuration(tmp_path / "absent").load() == Preferences()


def test_unrelated_fields_are_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"enabled": False, "unknown": 12}))
    assert not Configuration(path).load().enabled
