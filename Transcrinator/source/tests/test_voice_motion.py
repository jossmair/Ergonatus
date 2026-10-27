import math

from app.ui.premium import audio_activity, wave_heights
from app.ui.floating_hub import FloatingHub
from app.core.settings import Settings
from PySide6.QtWidgets import QApplication


def test_dragged_hub_keeps_margin_above_taskbar():
    from PySide6.QtCore import QPoint, QRect
    app = QApplication.instance() or QApplication([])
    hub = FloatingHub(Settings())
    hub.set_state("Prêt")
    assert hub.bounded(QPoint(1900, 1060), QRect(0, 0, 1920, 1040)).y() == 988
    hub.set_state("Fermé")
    hub.deleteLater()
    app.processEvents()


def test_hub_remains_visible_after_preparation_and_dictation():
    app = QApplication.instance() or QApplication([])
    hub = FloatingHub(Settings(hub_visible=True))
    for state in ("Préparation…", "Prêt", "Écoute…", "Traitement…", "Prêt", "Erreur"):
        hub.set_state(state)
        app.processEvents()
        assert hub.isVisible()
    hub.set_state("Prêt")
    hub.finish_transition()
    resting_width = hub.width()
    hub.set_state("Écoute…")
    hub.finish_transition()
    assert resting_width == 36 and hub.width() == 172
    speaking_height = hub.height()
    hub.set_partial("Texte de validation")
    hub.finish_transition()
    assert hub.height() == speaking_height == 44
    hub.hide()
    hub.reveal()
    assert hub.isVisible()
    hub.set_state("Fermé")
    assert not hub.isVisible() and not hub.timer.isActive()
    hub.deleteLater()


def test_quiet_speech_is_visible_without_animating_silence():
    assert audio_activity(0) == audio_activity(.002) == 0
    assert .2 < audio_activity(.008) < audio_activity(.025) < 1
    assert audio_activity(1) == 1
    assert audio_activity(float("nan")) == 0
    assert wave_heights(0, 0) == wave_heights(0, 12)
    assert max(wave_heights(audio_activity(.025), 2)) > 20
    assert wave_heights(.8, 1) != wave_heights(.8, 2)
    assert all(math.isfinite(h) and 2.5 <= h <= 42.5 for h in wave_heights(1, 7))


def test_activation_pulse_and_unfold_change_frames_without_microphone_energy():
    app = QApplication.instance() or QApplication([])
    now = [0.]
    hub = FloatingHub(Settings(), clock=lambda: now[0])
    hub.set_state("Prêt")
    now[0] = 21
    hub.animate()
    assert hub.compacted
    hub.set_state("Préparation…")
    assert not hub.compacted
    first = hub.grab().toImage()
    now[0] += .12
    second = hub.grab().toImage()
    now[0] += .6
    assert first != second and second != hub.grab().toImage()
    assert hub.display_level == 0 and hub.level == 0
    hub.set_state("Fermé")
    hub.deleteLater()
    app.processEvents()


def test_finished_paste_compacts_immediately_and_only_activity_unfolds(monkeypatch):
    from PySide6.QtCore import QPoint, QRect, QSize
    from types import SimpleNamespace
    import app.ui.floating_hub as module
    app = QApplication.instance() or QApplication([])
    now = [0.]
    area = QRect(0, 0, 1920, 1040)
    monkeypatch.setattr(module.QGuiApplication, "screenAt", lambda point:
                        SimpleNamespace(availableGeometry=lambda: area))
    hub = FloatingHub(Settings(), clock=lambda: now[0])
    hub.set_state("Prêt")
    hub.set_state("Préparation…")
    hub.set_state("Écoute…")
    hub.set_state("Traitement…")
    hub.set_state("Prêt")
    assert hub.compacted and hub.size() == QSize(36, 36)
    assert hub.pos() == QPoint(1920 - 36 - 16, 1040 - 36 - 16)
    now[0] = 1
    hub.set_partial("")
    hub.set_state("Prêt")
    assert hub.compacted
    hub.set_state("Préparation…")
    assert not hub.compacted and hub.size() == QSize(172, 44)
    assert hub.x() == (1920 - 172) // 2 and hub.y() == 1040 - 44 - 16
    hub.set_state("Fermé")
    hub.deleteLater()
    app.processEvents()
