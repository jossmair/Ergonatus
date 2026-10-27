"""Actual DXGI, DWM, click-through, resource and performance verification.

Only opens our own test surfaces. Never moves the pointer or generates input.
An optional --interactive leaves a click target for a human/GUI test.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.win32 import Desktop, enable_dpi
enable_dpi()
from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget
import numpy as np
from core.screen_capture import DXCapture, ExclusionProbe, Request, verify_exclusion
from ui.magnifier_overlay import MagnifierOverlay
from ui.orb import Orb
from ui.theme import configure_app

parser = argparse.ArgumentParser()
parser.add_argument("--interactive", action="store_true")
parser.add_argument("--seconds", type=float, default=8)
parser.add_argument("--monitor-index", type=int, default=-1)
parser.add_argument("--diameter", type=int, choices=[120, 180, 220, 300, 400, 440, 600], default=300)
args = parser.parse_args()
app = QApplication([])
configure_app(app)
desktop = Desktop()
folder = ROOT / "docs/validation"
folder.mkdir(exist_ok=True)
report = {"version": "1.0.7", "diameter": args.diameter, "os": str(sys.getwindowsversion()), "python": sys.version, "monitors": [str(m) for m in desktop.monitors()], "tests": {}, "clicks": []}


class Target(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Précisionator · Cible de validation")
        self.resize(640, 460)
        self.clicks = []

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#101d20"))
        for x in range(20, self.width(), 20):
            for y in range(20, self.height(), 20):
                p.fillRect(x, y, 10, 10, QColor("#707982"))
        p.fillRect(30, 30, 580, 70, QColor("#112024"))
        p.setPen(QColor("#e4f4f1"))
        p.drawText(QRectF(50, 40, 530, 50), Qt.AlignVCenter, "Précisionator · Cible de validation sans action")
        p.setPen(QPen(QColor("#B59AFF"), 2))
        p.drawEllipse(QPointF(320, 240), 45, 45)
        p.drawText(QRectF(100, 330, 440, 80), Qt.AlignCenter, f"Clics reçus : {len(self.clicks)}\nAucune action n’est exécutée.")

    def mousePressEvent(self, event):
        self.clicks.append({"t": time.time(), "x": event.position().x(), "y": event.position().y(), "button": str(event.button())})
        report["clicks"] = self.clicks
        self.update()
        save()


def save():
    (folder / f"windows-1.0.7-{args.monitor_index}-{args.diameter}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


target = Target()
screen = app.screens()[args.monitor_index]
area = screen.availableGeometry()
target.move(area.x() + 160, area.y() + 140)
target.show()
orb = Orb()
orb.move(target.x() + 580, target.y() + 30)
orb.show()
overlay = None


def validate():
    global overlay
    capture = None
    try:
        capture = DXCapture()
        image = orb.grab().toImage().convertToFormat(QImage.Format_ARGB32)
        reference = np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine())[:, :image.width() * 4].reshape(image.height(), image.width(), 4).copy()
        bounds = desktop.window_rect(int(orb.winId()))
        probe = ExclusionProbe(int(orb.winId()), bounds.x + bounds.w // 2, bounds.y + bounds.h // 2, reference)
        verify_exclusion(capture, probe)
        report["tests"]["dxgi_orb_exclusion"] = "passed"
        bounds = desktop.window_rect(int(target.winId()))
        x, y = bounds.x + bounds.w // 2, bounds.y + bounds.h // 2
        diameter = args.diameter
        size = diameter + 4
        baseline = capture.grab(x, y, diameter).copy()
        overlay = MagnifierOverlay(desktop, diameter)
        desktop.user.GetForegroundWindow.restype = W.HWND
        foreground = desktop.user.GetForegroundWindow()
        source = QImage(baseline.data, size, size, baseline.strides[0], QImage.Format_ARGB32).copy()
        overlay.render(Request(0, x, y, 2.5, 1, diameter=diameter), source)
        desktop.dwm.DwmFlush()
        time.sleep(.04)
        assert desktop.user.GetForegroundWindow() == foreground
        report["tests"]["no_focus_activation"] = "passed"
        extent = desktop.window_rect(overlay.hwnd)
        assert extent.w == extent.h == diameter
        report["tests"]["selected_physical_diameter"] = "passed"
        desktop.user.WindowFromPoint.argtypes = [W.POINT]
        desktop.user.WindowFromPoint.restype = W.HWND
        assert desktop.user.WindowFromPoint(W.POINT(x, y)) != overlay.hwnd
        report["tests"]["native_click_through_hit_test"] = "passed"
        after = capture.grab(x, y, diameter).copy()
        assert np.mean(np.abs(after[:, :, :3].astype(int) - baseline[:, :, :3].astype(int))) < .5
        report["tests"]["no_overlay_in_actual_dxgi_capture"] = "passed"
        overlay.image.save(str(folder / "loupe-rendu-reel.png"))
        # Sample both outputs including negative origins when present.
        outputs = []
        for _, _, device, (left, top, right, bottom) in capture.outputs:
            frame = capture.grab((left + right) // 2, (top + bottom) // 2, diameter)
            assert frame.shape == (size, size, 4)
            outputs.append(device)
        report["tests"]["all_attached_dxgi_outputs"] = outputs
        durations = []
        render_durations = []
        cpu = time.process_time()
        started = time.perf_counter()
        count = 0
        while time.perf_counter() - started < args.seconds:
            a = time.perf_counter()
            pixels = capture.grab(x, y, diameter)
            durations.append(time.perf_counter() - a)
            image = QImage(pixels.data, size, size, pixels.strides[0], QImage.Format_ARGB32)
            b = time.perf_counter()
            overlay.render(Request(0, x, y, 2.5, 1, diameter=diameter), image)
            render_durations.append(time.perf_counter() - b)
            count += 1
            app.processEvents()
            delay = started + count / 60 - time.perf_counter()
            if delay > 0:
                time.sleep(min(delay, .02))
        elapsed = time.perf_counter() - started
        report["performance"] = {"seconds": elapsed, "frames": count, "fps": count / elapsed,
            "capture_median_ms": statistics.median(durations) * 1000,
            "capture_p95_ms": sorted(durations)[int(len(durations) * .95)] * 1000,
            "render_median_ms": statistics.median(render_durations) * 1000,
            "cpu_one_core_percent": 100 * (time.process_time() - cpu) / elapsed}
        report["tests"]["no_spontaneous_clicks_during_render"] = len(target.clicks) == 0
        target.grab().save(str(folder / "cible-validation.png"))
        report["result"] = "passed"
    except Exception as error:
        import traceback
        report["result"] = "failed"
        report["error"] = str(error)
        report["traceback"] = traceback.format_exc()
    finally:
        if capture:
            capture.close()
        if overlay:
            overlay.close()
            overlay = None
        save()
        print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)
        if not args.interactive:
            app.exit(0 if report.get("result") == "passed" else 1)


QTimer.singleShot(600, validate)
raise SystemExit(app.exec())
