import ctypes
import time
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt
from core.screen_capture import ROIProcessor
from services.configuration import Preferences
from ui.magnifier_overlay import radial_alpha
from ui.settings_window import SettingsWindow
from ui.orb import Orb


def test_radial_mask_is_circular_and_feathered():
    mask = radial_alpha()
    assert mask.shape == (220, 220)
    assert mask[110, 110] == 255
    assert mask[110, 0] < 2
    assert 0 < mask[110, 12] < 255
    assert mask[0, 0] == 0
    assert np.array_equal(mask, mask.T)
    assert np.array_equal(mask, mask[::-1])


def test_roi_processor_uses_correct_pitched_texture():
    class Mapped:
        pass
    pixels = np.zeros((100, 128, 4), np.uint8)
    pixels[20:30, 10:40, :] = [15, 80, 220, 255]
    mapped = Mapped()
    mapped.Pitch = 128 * 4
    mapped.pBits = pixels.ctypes.data
    result = ROIProcessor().process(mapped, 120, 100, (10, 20, 40, 30), 0)
    assert result.shape == (10, 30, 4)
    assert np.all(result == [15, 80, 220, 255])
    pixels.fill(0)
    assert result[0, 0, 0] == 15  # Worker owns its cropped pixels.


def test_settings_and_orb_are_separate_family_surfaces(app):
    window = SettingsWindow(Preferences())
    orb = Orb()
    window.show()
    orb.show()
    app.processEvents()
    assert window.windowFlags() & Qt.FramelessWindowHint
    assert window.width() == 420
    assert orb.width() == orb.height() == 36
    assert len(window.sliders) == 5
    assert window.grab().toImage().pixelColor(0, 0).alpha() == 0
    assert window.sliders["zoom"].value() == 1
    window.hide()
    orb.hide()


def test_production_sources_have_no_input_injection_or_hooks():
    root = Path(__file__).resolve().parents[1]
    forbidden = ("SendInput", "SetCursorPos", "mouse_event", "keybd_event", "SetWindowsHookEx", "RegisterHotKey", "BlockInput", "ClipCursor", "SetCapture(")
    for folder in ("core", "services", "ui"):
        for path in (root / folder).glob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert all(word not in source for word in forbidden), path
