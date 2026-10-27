import numpy as np
import pytest
from pathlib import Path
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QSignalSpy, QTest

from services.screen_following import FOLLOW_INTERVAL_MS
from ui.orb import Orb, draw_core, draw_orb


def render(enabled=True, seconds=0., background=None):
    image = QImage(36, 36, QImage.Format_ARGB32_Premultiplied)
    image.fill(QColor(background) if background else Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    draw_orb(painter, QRectF(0, 0, 36, 36), enabled, seconds)
    painter.end()
    image = image.convertToFormat(QImage.Format_RGBA8888)
    return np.frombuffer(image.constBits(), np.uint8).reshape(36, 36, 4).copy()


@pytest.mark.parametrize("phase", [0., .14, .5, .9, 1.])
def test_sprite_honours_caller_opacity_and_restores_painter(app, phase):
    alpha_sums = []
    for opacity in (1., .4):
        image = QImage(36, 36, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setOpacity(opacity)
        mode = painter.compositionMode()
        draw_core(painter, QRectF(0, 0, 36, 36), phase)
        assert painter.opacity() == opacity
        assert painter.compositionMode() == mode
        painter.end()
        rgba = image.convertToFormat(QImage.Format_RGBA8888)
        alpha_sums.append(np.frombuffer(rgba.constBits(), np.uint8).reshape(36, 36, 4)[:, :, 3].sum())
    assert .38 < alpha_sums[1] / alpha_sums[0] < .42


def test_activation_is_visible_without_waiting_for_animation(app):
    for seconds in (0., 2., 4., 6., 9.):
        active, inactive = render(True, seconds), render(False, seconds)
        assert active[:, :, 3].sum() > inactive[:, :, 3].sum() * 2
        assert inactive[:, :, 3].max() > 90
        assert active[0, 0, 3] == inactive[0, 0, 3] == 0


@pytest.mark.parametrize("background", ["#ffffff", "#101d20"])
def test_old_light_orb_retains_amethyst_tint_on_both_backgrounds(app, background):
    active, inactive = render(True, 0., background), render(False, 0., background)
    core = render(True)[:, :, 3] > 180
    rgb = active[:, :, :3].astype(float)
    assert rgb[core].mean(axis=0)[2] - rgb[core].mean(axis=0)[1] > 15
    assert np.mean(np.abs(rgb - inactive[:, :, :3].astype(float))[core]) > 8


@pytest.mark.parametrize("enabled,state", [(True, "active"), (False, "inactive")])
def test_user_requested_generated_orb_matches_v2_visual_reference(app, enabled, state):
    image = QImage(str(Path(__file__).parent / "fixtures" / f"orb-ergonatus-v2-{state}.png")).convertToFormat(QImage.Format_RGBA8888)
    reference = np.frombuffer(image.constBits(), np.uint8).reshape(36, 36, 4)
    current = render(enabled)
    assert np.max(np.abs(reference.astype(int) - current.astype(int))) <= 1


def test_animations_are_quiet_and_inactive_is_much_quieter(app):
    variations = []
    for enabled in (True, False):
        frames = np.stack([render(enabled, t / 4, "#101d20")[:, :, :3]
                           for t in range(49)]).astype(float)
        variations.append(np.ptp(frames, axis=0).mean())
    assert .3 < variations[0] < 8
    assert variations[1] < variations[0] / 3
    assert variations[1] < 1


def test_inactive_orb_keeps_its_controls_and_pauses_when_hidden(app):
    orb = Orb()
    orb.enabled = False
    orb.show()
    app.processEvents()
    assert orb.isEnabled()
    assert "Désactivé" in orb.accessibleName()
    assert orb.timer.isActive()
    inactive_interval = orb.timer.interval()
    orb.enabled = True
    assert "Activé" in orb.accessibleName()
    assert orb.timer.interval() < inactive_interval
    assert orb.size().width() == orb.size().height() == 36
    orb.hide()
    assert not orb.timer.isActive()


def test_screen_following_matches_compact_transcrinator_cadence():
    assert FOLLOW_INTERVAL_MS == 40


def test_right_button_does_not_emit_primary_action(app):
    orb = Orb()
    activated = QSignalSpy(orb.activated)
    QTest.mouseClick(orb, Qt.RightButton)
    assert activated.count() == 0
    QTest.mouseClick(orb, Qt.LeftButton)
    assert activated.count() == 1
