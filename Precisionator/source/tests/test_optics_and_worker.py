import ctypes
import time
import threading
import numpy as np
import pytest
from PySide6.QtGui import QImage
from core import screen_capture
from core.screen_capture import CaptureWorker, Request, ROIProcessor
from ui.magnifier_overlay import paint_lens, radial_alpha


@pytest.mark.parametrize("zoom", [1, 1.8, 2.5, 3])
@pytest.mark.parametrize("offset", [(0, 0), (5, -3)])
def test_real_optical_center_stays_under_real_pointer(zoom, offset):
    pixels = np.zeros((224, 224, 4), np.uint8)
    pixels[:, :, 3] = 255
    dx, dy = offset
    pixels[110 + dy:114 + dy, 110 + dx:114 + dx, :3] = [30, 90, 230]
    source = QImage(pixels.data, 224, 224, 896, QImage.Format_ARGB32)
    destination = QImage(220, 220, QImage.Format_ARGB32_Premultiplied)
    mask_data = np.zeros((220, 220, 4), np.uint8)
    mask_data[:, :, 3] = radial_alpha()
    mask = QImage(mask_data.data, 220, 220, 880, QImage.Format_ARGB32_Premultiplied)
    paint_lens(destination, source, zoom, mask, offset)
    center = destination.pixelColor(110, 110)
    assert center.red() == 230
    assert center.green() == 90
    assert center.alpha() == 255
    assert destination.pixelColor(0, 0).alpha() == 0


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_rotated_pitched_monitor_preserves_roi(rotation):
    expected = np.arange(7 * 11 * 4, dtype=np.uint8).reshape(7, 11, 4)
    native = np.rot90(expected, {0: 0, 90: 1, 180: 2, 270: 3}[rotation])
    pitched = np.zeros((native.shape[0], 16, 4), np.uint8)
    pitched[:, :native.shape[1], :] = native
    class Mapped:
        Pitch = 16 * 4
        pBits = pitched.ctypes.data
    result = ROIProcessor().process(Mapped(), 11, 7, (2, 1, 9, 6), rotation)
    assert np.array_equal(result, expected[1:6, 2:9, :])


def pump_until(app, condition, timeout=2):
    until = time.monotonic() + timeout
    while not condition() and time.monotonic() < until:
        app.processEvents()
        time.sleep(.005)
    assert condition()


def test_capture_mailbox_bounds_queue_and_sleeps_when_hidden(app, monkeypatch):
    calls = []
    released = []
    class Fake:
        def grab(self, x, y):
            calls.append((x, y))
            return np.full((224, 224, 4), 255, np.uint8)
        def close(self):
            released.append(True)
    monkeypatch.setattr(screen_capture, "verify_exclusion", lambda c, p: None)
    worker = CaptureWorker(Fake)
    frames = []
    worker.frame_ready.connect(lambda *args: frames.append(args))
    try:
        worker.submit(Request(1, 0, 0, 2.5, 1))
        pump_until(app, lambda: len(frames) == 1)
        for i in range(100):
            worker.submit(Request(i + 2, i, 0, 2.5, 1))
        time.sleep(.03)
        app.processEvents()
        assert len(frames) == 1  # Only one unacknowledged image can exist.
        worker.acknowledge()
        pump_until(app, lambda: len(frames) == 2)
        assert frames[-1][0].x == 99
        worker.acknowledge()
        before = len(calls)
        time.sleep(.05)
        assert len(calls) == before
        worker.release()
        pump_until(app, lambda: bool(released))
    finally:
        worker.close()
    assert not worker.thread.is_alive()


def test_failed_exclusion_delivers_no_frame_and_releases_capture(app, monkeypatch):
    closed = []
    class Fake:
        def close(self):
            closed.append(True)
    def refused(*_):
        raise OSError("Exclusion refusée")
    monkeypatch.setattr(screen_capture, "verify_exclusion", refused)
    worker = CaptureWorker(Fake)
    errors, frames = [], []
    worker.failed.connect(errors.append)
    worker.frame_ready.connect(lambda *args: frames.append(args))
    try:
        worker.submit(Request(1, 100, 100, 2.5, 1))
        pump_until(app, lambda: bool(errors))
        assert not frames
        assert closed
        assert worker.needs_probe.is_set()
    finally:
        worker.close()


def test_monitor_change_cancels_stale_probe_without_disabling_lens(app, monkeypatch):
    entered, continue_probe = threading.Event(), threading.Event()
    closed = []
    class Fake:
        def close(self):
            closed.append(True)
    def probe(*_):
        entered.set()
        assert continue_probe.wait(1)
        raise OSError("Ancien emplacement de l’orbe")
    monkeypatch.setattr(screen_capture, "verify_exclusion", probe)
    worker = CaptureWorker(Fake)
    failures = []
    worker.failed.connect(failures.append)
    try:
        worker.submit(Request(1, 100, 100, 2.5, 1))
        pump_until(app, entered.is_set)
        worker.release()
        continue_probe.set()
        pump_until(app, lambda: bool(closed))
        app.processEvents()
        assert not failures
        assert worker.needs_probe.is_set()
    finally:
        continue_probe.set()
        worker.close()
