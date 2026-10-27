from dataclasses import replace
import json

import numpy as np
import pytest
from PySide6.QtGui import QImage
from core.motion_analyzer import MotionThresholds
from services.configuration import Configuration, Preferences
from services.screen_following import ScreenFollower
from tests.test_motion import run, LEGACY
from ui.magnifier_overlay import paint_lens, radial_alpha
from ui.settings_window import SettingsWindow
from services.simple_settings import CHOICES, closest_choice
from PySide6.QtWidgets import QSpinBox, QLabel


def test_new_defaults_start_at_higher_speed():
    _, legacy, _, _ = run([(300, .7)])
    _, current, _, _ = run([(300, .7)], thresholds=MotionThresholds())
    assert not any(s.active for _, s in legacy)
    assert current[-1][1].active


def test_minimum_speed_and_trigger_speed_both_change_detection():
    _, allowed, _, _ = run([(50, .7)], thresholds=MotionThresholds())
    _, too_slow, _, _ = run([(50, .7)], thresholds=replace(MotionThresholds(), minimum_speed=80))
    assert allowed[-1][1].active
    assert not any(s.active for _, s in too_slow)
    _, default, _, _ = run([(850, .7)], thresholds=MotionThresholds())
    _, earlier, _, _ = run([(850, .7)], thresholds=replace(MotionThresholds(), trigger_speed=950))
    assert not any(s.active for _, s in default)
    assert earlier[-1][1].active


def test_default_hold_leaves_time_to_aim():
    _, states, _, _ = run([(100, .8), (0, 2.4)], thresholds=MotionThresholds())
    assert all(s.active for t, s in states if .9 < t < 2.7)
    assert not states[-1][1].active


def test_exit_threshold_is_independent_of_appearance():
    _, states, _, _ = run([(300, .6), (900, .6), (2200, .3)], thresholds=MotionThresholds())
    assert all(s.active for t, s in states if .5 < t < 1.2)
    assert not states[-1][1].active


def test_selected_appearance_delay_changes_when_lens_starts():
    _, fast, _, _ = run([(100, .6)], thresholds=replace(MotionThresholds(), activation_delay_ms=50))
    _, slow, _, _ = run([(100, .6)], thresholds=replace(MotionThresholds(), activation_delay_ms=500))
    assert next(t for t, s in fast if s.active) < .25
    assert not any(s.active for t, s in slow if t < .5)


@pytest.mark.parametrize("delay", [300, 1200, 3000])
def test_selected_hold_time_is_respected(delay):
    _, states, _, _ = run([(100, .8), (0, delay / 1000 + .3)],
                         thresholds=replace(MotionThresholds(), idle_delay_ms=delay))
    assert all(s.active for t, s in states if .9 < t < .8 + delay / 1000 - .06)
    assert not states[-1][1].active


def test_tuning_and_per_monitor_positions_survive_restart(tmp_path):
    config = Configuration(tmp_path / "settings.json")
    p = Preferences(lens_diameter=480, trigger_speed=600, exit_speed=1100,
                    activation_delay_ms=60, idle_delay_ms=2400,
                    orb_positions={"left": (-1700, 40), "right": (3700, 500)})
    config.save(p)
    assert config.load() == p


def test_old_preferences_receive_new_behavior_defaults(tmp_path):
    config = Configuration(tmp_path / "settings.json")
    config.path.write_text('{"enabled":true,"magnification":1.8,"orb_position":[10,20]}')
    p = config.load()
    assert p.magnification == 1.8
    assert p.orb_position == (10, 20)
    assert (p.trigger_speed, p.idle_delay_ms, p.lens_diameter) == (650, 2000, 300)


def test_bad_tuning_cannot_reverse_hysteresis_or_allocate_huge_images(tmp_path):
    config = Configuration(tmp_path / "settings.json")
    config.path.write_text(json.dumps({"lens_diameter": 99999, "minimum_speed": 200,
        "trigger_speed": -5, "exit_speed": 10, "idle_delay_ms": False,
        "orb_positions": {"bad": [True, 10], "good": [-1800, 12]}}))
    p = config.load()
    assert p.lens_diameter == 600
    assert p.minimum_speed < p.trigger_speed < p.exit_speed
    assert p.idle_delay_ms == 2000
    assert p.orb_positions == {"good": (-1800, 12)}


@pytest.mark.parametrize("diameter", [120, 300, 600])
def test_resizing_keeps_real_optical_center_and_transparent_edges(diameter):
    size = diameter + 4
    pixels = np.zeros((size, size, 4), np.uint8)
    pixels[:, :, 3] = 255
    center = size // 2
    pixels[center - 2:center + 2, center - 2:center + 2, :3] = [30, 90, 230]
    source = QImage(pixels.data, size, size, size * 4, QImage.Format_ARGB32)
    image = QImage(diameter, diameter, QImage.Format_ARGB32_Premultiplied)
    mask_data = np.zeros((diameter, diameter, 4), np.uint8)
    mask_data[:, :, 3] = radial_alpha(diameter)
    mask = QImage(mask_data.data, diameter, diameter, diameter * 4, QImage.Format_ARGB32_Premultiplied)
    paint_lens(image, source, 2.5, mask)
    assert image.pixelColor(diameter // 2, diameter // 2).red() == 230
    assert image.pixelColor(diameter // 2, diameter // 2).alpha() == 255
    assert image.pixelColor(0, 0).alpha() == 0


def test_simple_sliders_apply_real_settings_without_refresh_feedback(app):
    window = SettingsWindow(Preferences())
    changes = []
    window.tuning_changed.connect(changes.append)
    window.sliders["size"].setValue(2)
    window.sliders["appearance"].setValue(1)
    window.sliders["aim"].setValue(2)
    assert changes == [{"lens_diameter": 440}, {"trigger_speed": 450, "activation_delay_ms": 80},
                       {"idle_delay_ms": 4000, "exit_speed": 1600}]
    count = len(changes)
    window.refresh(Preferences(lens_diameter=440, idle_delay_ms=4000, exit_speed=1600))
    assert len(changes) == count
    assert window.sliders["size"].value() == 2
    assert window.sliders["aim"].value() == 2
    window.hide()


def test_settings_have_no_technical_numeric_controls(app):
    window = SettingsWindow(Preferences())
    assert not window.findChildren(QSpinBox)
    assert not any("px/s" in item.text() or " ms" in item.text() for item in window.findChildren(QLabel))
    assert window.sliders["appearance"].value() == 0
    assert window.sliders["aim"].value() == 1
    assert all(slider.height() >= 34 for slider in window.sliders.values())


def test_presets_keep_their_meaning_and_never_invert_thresholds():
    appearance = CHOICES["appearance"]
    assert appearance[0][2]["trigger_speed"] > appearance[1][2]["trigger_speed"] > appearance[2][2]["trigger_speed"]
    aim = CHOICES["aim"]
    assert aim[0][2]["idle_delay_ms"] < aim[1][2]["idle_delay_ms"] < aim[2][2]["idle_delay_ms"]
    for _, _, start in appearance:
        for _, _, end in aim:
            p = Preferences(**start, **end)
            assert p.minimum_speed < p.trigger_speed < p.exit_speed
            assert closest_choice("appearance", p) == next(c[0] for c in appearance if c[2] == start)


def test_orb_changes_monitor_on_first_sample_like_transcrinator():
    follow = ScreenFollower()
    assert follow.update(0, "right", "left") == "right"
    assert follow.update(.04, "right", "right") is None
    assert follow.update(.08, "left", "right") == "left"


def test_orb_stays_put_on_same_monitor_or_unavailable_pointer():
    follow = ScreenFollower()
    for i in range(30):
        assert follow.update(i * .1, "left", "left") is None
        assert follow.update(i * .1, None, "left") is None


def test_orb_does_not_jump_while_dragging_or_locked():
    follow = ScreenFollower()
    for i in range(20):
        assert follow.update(i * .2, "right", "left", blocked=True) is None
    assert follow.update(5, "right", "left") == "right"
