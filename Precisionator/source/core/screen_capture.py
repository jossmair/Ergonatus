"""DXGI capture owned by a sleeping worker, with a one-frame mailbox."""
from dataclasses import dataclass
import ctypes
import logging
import threading
import time

import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage


class ROIProcessor:
    """Crop a view of the mapped texture before copying (DXcam copies it all)."""
    def process(self, mapped, width, height, region, rotation_angle):
        rows = height if rotation_angle in (0, 180) else width
        pitch = int(mapped.Pitch)
        pointer = ctypes.cast(mapped.pBits, ctypes.POINTER(ctypes.c_ubyte))
        view = np.ctypeslib.as_array(pointer, shape=(rows * pitch,)).reshape(rows, pitch // 4, 4)
        view = view[:, :width if rotation_angle in (0, 180) else height, :]
        if rotation_angle:
            view = np.rot90(view, k={90: 3, 180: 2, 270: 1}[rotation_angle])
        l, t, r, b = region
        return view[t:b, l:r, :].copy()


@dataclass(frozen=True)
class Request:
    serial: int
    x: int
    y: int
    zoom: float
    opacity: float
    probe: object = None
    diameter: int = 220


@dataclass(frozen=True)
class ExclusionProbe:
    hwnd: int
    x: int
    y: int
    reference: object


def verify_exclusion(capture, probe):
    """Verify actual DXGI exclusion using the already visible, unchanged orb.

    No test window is flashed or hidden. Only the orb's capture affinity changes
    briefly. Ambiguous/occluded evidence fails closed before displaying a lens.
    """
    from services.win32 import Desktop
    desktop = Desktop()
    if probe is None:
        raise OSError("Vérification de l’exclusion indisponible.")
    reference = probe.reference
    h, w, _ = reference.shape
    colors = reference[:, :, :3].astype(float)
    valid = reference[:, :, 3] > 150
    if np.count_nonzero(valid) < 15:
        raise OSError("L’orbe ne fournit pas une référence de capture vérifiable.")
    if not desktop.exclude(probe.hwnd, False):
        raise OSError("L’affinité de l’orbe est temporairement indisponible.")
    def sample():
        frame = capture.grab(probe.x, probe.y)
        return frame[112 - h // 2:112 - h // 2 + h, 112 - w // 2:112 - w // 2 + w, :3].copy()
    alpha = reference[:, :, 3:4].astype(float) / 255
    lower = colors * alpha - 16
    upper = colors * alpha + 255 * (1 - alpha) + 16
    before = None
    # A new duplication can expose an initial empty staging texture. Allow a
    # bounded compositor warm-up on the worker instead of accepting black data.
    for _ in range(6):
        desktop.dwm.DwmFlush()
        time.sleep(.02)
        try:
            before = sample()
        except OSError:
            continue  # The first DXGI image can arrive after duplication creation.
        fits_reference = np.mean(((before >= lower) & (before <= upper)).all(axis=2)[valid])
        if fits_reference >= .60:
            break
    else:
        raise OSError("Référence de capture temporairement indisponible.")
    if not desktop.exclude(probe.hwnd):
        raise OSError("Le pilote n’autorise pas l’exclusion de capture.")
    affinity_restored = False
    try:
        for _ in range(5):
            desktop.dwm.DwmFlush()
            time.sleep(.02)
            after = sample()
            # Use the real alpha-compositing equation, not an assumed purple
            # hue. A bright/white desktop legitimately desaturates the orb.
            expected = colors * alpha + after.astype(float) * (1 - alpha)
            contrast = np.abs(expected - after).max(axis=2)
            informative = valid & (contrast > 18)
            if np.count_nonzero(informative) < 15:
                continue
            residual = np.abs(before.astype(float) - expected).max(axis=2)
            difference = np.abs(before.astype(float) - after).max(axis=2)
            if np.mean(residual[informative] < 20) >= .70 and np.mean(difference[informative]) > 15:
                break
        else:
            raise OSError("L’exclusion DXGI n’a pas encore été confirmée.")
        # Confirm the change follows the affinity rather than unrelated motion
        # behind the orb. The visible window itself never hides or flashes.
        if not desktop.exclude(probe.hwnd, False):
            raise OSError("L’affinité de capture doit être réinitialisée.")
        affinity_restored = True
        for _ in range(5):
            desktop.dwm.DwmFlush()
            time.sleep(.02)
            restored = sample()
            if np.mean(np.abs(restored.astype(float) - before).max(axis=2)[informative] < 20) >= .70:
                return
        raise OSError("Le contrôle de retour de capture doit être réessayé.")
    finally:
        if not affinity_restored:
            desktop.exclude(probe.hwnd, False)


class DXCapture:
    """Match DXGI device names, never assume display enumeration order."""
    def __init__(self):
        import dxcam
        self.dxcam = dxcam
        self.cameras = {}
        self.outputs = []
        # Version-pinned DXcam 0.0.5 exposes output descriptors on its factory.
        # Refuse unknown layouts instead of capturing a different monitor.
        self.factory = dxcam.__dict__["__factory"]
        self.factory.__init__()  # Re-enumerate attached adapters after hotplug.
        # Refresh descriptors after hotplug; retain factory device ownership.
        for device_index, outputs in enumerate(self.factory.outputs):
            for output_index, output in enumerate(outputs):
                output.update_desc()
                desc = output.desc
                b = desc.DesktopCoordinates
                if desc.AttachedToDesktop:
                    self.outputs.append((device_index, output_index, str(desc.DeviceName), (b.left, b.top, b.right, b.bottom)))
        if not self.outputs:
            raise OSError("Aucun écran DXGI capturable.")
        self.buffer = np.zeros((224, 224, 4), dtype=np.uint8)

    def grab(self, x, y, diameter=220):
        """Physical pixels centred on the exact pointer; pad screen edges.

        Stitch neighbouring outputs so negative origins and mixed DPI never
        change the optical centre. Desktop duplication does not draw a cursor.
        """
        size = diameter + 4
        if self.buffer.shape[0] != size:
            self.buffer = np.zeros((size, size, 4), dtype=np.uint8)
        left, top = x - size // 2, y - size // 2
        self.buffer.fill(0)
        used = False
        for di, oi, name, (ox, oy, right, bottom) in self.outputs:
            l, t = max(left, ox), max(top, oy)
            r, b = min(left + size, right), min(top + size, bottom)
            if r <= l or b <= t:
                continue
            key = (di, oi)
            if key not in self.cameras:
                from dxcam.dxcam import DXCamera
                class BoundedCamera(DXCamera):
                    def _on_output_change(self):
                        raise OSError("Écran modifié ou pilote réinitialisé ; capture suspendue.")
                    def release(self):
                        # DXcam's destructor also runs after a failed constructor.
                        if hasattr(self, "is_capturing"):
                            self.stop()
                        for name in ("_duplicator", "_stagesurf"):
                            resource = getattr(self, name, None)
                            if resource:
                                resource.release()
                self.cameras[key] = BoundedCamera(output=self.factory.outputs[di][oi], device=self.factory.devices[di], region=None, output_color="BGRA", max_buffer_len=2)
                self.cameras[key]._processor = ROIProcessor()
                self.cameras[key]._precisionator_ready = False
            camera = self.cameras[key]
            # A moved ROI needs fresh pixels even if no desktop pixels changed.
            # DXcam's latest frame is cached at full output size in this wrapper.
            frame = camera.grab(region=(l - ox, t - oy, r - ox, b - oy))
            if frame is not None:
                camera._precisionator_ready = True
            if frame is None:
                if not camera._precisionator_ready:
                    raise OSError("Aucune première image DXGI disponible.")
                # DXGI may report no changes while the ROI moved. Acquire via
                # the pinned camera's existing staging texture (no extra capture).
                mapped = camera._stagesurf.map()
                try:
                    frame = camera._processor.process(mapped, camera.width, camera.height,
                                                      (l - ox, t - oy, r - ox, b - oy), camera.rotation_angle)
                finally:
                    camera._stagesurf.unmap()
            if frame is None or frame.shape[:2] != (b - t, r - l):
                raise OSError("Image DXGI indisponible ou dimensions incohérentes.")
            self.buffer[t - top:b - top, l - left:r - left, :3] = frame[:, :, :3]
            self.buffer[t - top:b - top, l - left:r - left, 3] = 255
            used = True
        if not used:
            raise OSError("Le pointeur ne se trouve sur aucun écran capturable.")
        return self.buffer

    def close(self):
        for camera in self.cameras.values():
            try:
                camera.release()
            except Exception:
                logging.exception("Libération DXGI")
        self.cameras.clear()


class CaptureWorker(QObject):
    frame_ready = Signal(object, object, float)
    failed = Signal(str)

    def __init__(self, factory=DXCapture):
        super().__init__()
        self.factory = factory
        self.condition = threading.Condition()
        self.pending = None
        self.closed = False
        self.release_requested = False
        self.outstanding = False
        self.generation = 0
        self.needs_probe = threading.Event()
        self.needs_probe.set()
        self.thread = threading.Thread(target=self.run, name="precisionator-dxgi", daemon=True)
        self.thread.start()

    def submit(self, request):
        with self.condition:
            if not self.closed:
                self.pending = request
                self.condition.notify()

    def acknowledge(self):
        with self.condition:
            self.outstanding = False
            self.condition.notify()

    def release(self):
        with self.condition:
            self.generation += 1
            self.pending = None
            self.release_requested = True
            self.needs_probe.set()
            self.condition.notify()

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            logging.error("Le pilote DXGI n’a pas terminé en trois secondes.")

    def run(self):
        ole = ctypes.WinDLL("ole32")
        ole.CoInitializeEx(None, 2)  # Match comtypes' STA initialization.
        capture = None
        last_used = time.monotonic()
        try:
            while True:
                with self.condition:
                    timeout = max(.01, min(2., 2 - (time.monotonic() - last_used))) if capture else 2.
                    self.condition.wait_for(lambda: self.closed or self.release_requested or (self.pending is not None and not self.outstanding), timeout=timeout)
                    if self.closed:
                        break
                    if self.release_requested or (capture and time.monotonic() - last_used > 2 and self.pending is None):
                        if capture:
                            capture.close()
                            capture = None
                        self.needs_probe.set()
                        self.release_requested = False
                    if self.pending is None or self.outstanding:
                        continue
                    request, self.pending = self.pending, None
                    generation = self.generation
                try:
                    if capture is None:
                        capture = self.factory()
                        verify_exclusion(capture, request.probe)
                        with self.condition:
                            if generation == self.generation and not self.release_requested:
                                self.needs_probe.clear()
                    with self.condition:
                        if generation != self.generation or self.closed:
                            continue
                    started = time.perf_counter()
                    pixels = capture.grab(request.x, request.y) if request.diameter == 220 else capture.grab(request.x, request.y, request.diameter)
                    image = QImage(pixels.data, pixels.shape[1], pixels.shape[0], pixels.strides[0], QImage.Format_ARGB32).copy()
                    elapsed = time.perf_counter() - started
                    last_used = time.monotonic()
                    with self.condition:
                        if generation != self.generation or self.closed:
                            continue
                        self.outstanding = True
                    self.frame_ready.emit(request, image, elapsed)
                except Exception as error:
                    with self.condition:
                        superseded = generation != self.generation or self.release_requested or self.closed
                    if not superseded:
                        logging.exception("Capture interrompue")
                    if capture:
                        capture.close()
                        capture = None
                    self.needs_probe.set()
                    with self.condition:
                        if not superseded:
                            self.pending = None
                    if not superseded:
                        self.failed.emit("Capture indisponible : " + str(error))
        finally:
            if capture:
                capture.close()
            ole.CoUninitialize()
