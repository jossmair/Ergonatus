import numpy as np
import pytest
from core import screen_capture
from core.screen_capture import ExclusionProbe, verify_exclusion
from services import win32
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from ui.orb import draw_orb


@pytest.mark.parametrize("effective", [True, False])
def test_real_backend_confirmation_fails_closed(app, monkeypatch, effective):
    class Capture:
        excluded = False
        count = 0
        def grab(self, x, y):
            self.count += 1
            image = np.zeros((224, 224, 4), np.uint8)
            if self.count > 2 and not (self.excluded and effective):
                image[:, :, :] = [240, 140, 190, 255]
            return image
    capture = Capture()
    history = []
    class Dwm:
        def DwmFlush(self):
            pass
    class Desktop:
        dwm = Dwm()
        def exclude(self, hwnd, enabled=True):
            capture.excluded = enabled
            history.append(enabled)
            return True
    monkeypatch.setattr(win32, "Desktop", Desktop)
    monkeypatch.setattr(screen_capture.time, "sleep", lambda _: None)
    reference = np.full((36, 36, 4), [240, 140, 190, 255], dtype=np.uint8)
    probe = ExclusionProbe(1, 100, 100, reference)
    if effective:
        verify_exclusion(capture, probe)
    else:
        with pytest.raises(OSError, match="confirmée"):
            verify_exclusion(capture, probe)
    assert history == [False, True, False]
    assert not capture.excluded


@pytest.mark.parametrize("background", [(255, 255, 255), (16, 28, 30), (230, 210, 245), (160, 70, 210)])
@pytest.mark.parametrize("effective", [True, False])
def test_actual_orb_alpha_is_verified_on_bright_and_purple_desktops(app, monkeypatch, background, effective):
    image = QImage(36, 36, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    draw_orb(painter, QRectF(0, 0, 36, 36), True, 2.)
    painter.end()
    image = image.convertToFormat(QImage.Format_ARGB32)
    reference = np.frombuffer(image.constBits(), np.uint8).reshape(36, 36, 4).copy()
    alpha = reference[:, :, 3:4] / 255.
    composed = np.rint(reference[:, :, :3] * alpha + np.array(background) * (1 - alpha)).astype(np.uint8)
    class Capture:
        excluded = False
        def grab(self, *_):
            frame = np.full((224, 224, 4), 255, np.uint8)
            frame[:, :, :3] = background
            if not (self.excluded and effective):
                frame[94:130, 94:130, :3] = composed
            return frame
    capture = Capture()
    class Desktop:
        dwm = type("Dwm", (), {"DwmFlush": lambda *_: None})()
        def exclude(self, hwnd, enabled=True):
            capture.excluded = enabled
            return True
    monkeypatch.setattr(win32, "Desktop", Desktop)
    monkeypatch.setattr(screen_capture.time, "sleep", lambda _: None)
    if effective:
        verify_exclusion(capture, ExclusionProbe(1, 100, 100, reference))
    else:
        with pytest.raises(OSError, match="confirmée"):
            verify_exclusion(capture, ExclusionProbe(1, 100, 100, reference))
    assert not capture.excluded
