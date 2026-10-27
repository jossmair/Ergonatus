"""End-to-end Qt + worker + real DXGI with an injected, read-only test trace.

The OS pointer is never moved. This is not a physical mouse/Fortinatus test.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.win32 import enable_dpi
enable_dpi()
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from application import Application
from services.configuration import Configuration, Preferences
from ui.theme import configure_app

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
configure_app(app)
config = Configuration(ROOT / "docs/test-settings/application/settings.json")
config.save(Preferences())
controller = Application(app, config)
controller.tracker.stop()
started = time.monotonic()
monitor = controller.monitors[-1]
screen = monitor.bounds
fast_speed = 1500 * monitor.scale  # Analyzer thresholds use logical px/s.
after_fast = max(100, 1100 - round(.4 * fast_speed))
point = [screen.x + 250, screen.y + 300]
controller.desktop.pointer = lambda: tuple(point)
original_probe = controller.make_probe
def capture_probe():
    probe = original_probe()
    import numpy as np
    from PySide6.QtGui import QImage
    ref = probe.reference
    QImage(ref.data, ref.shape[1], ref.shape[0], ref.strides[0], QImage.Format_ARGB32).save(str(ROOT / "docs/validation/probe-orbe.png"))
    return probe
controller.make_probe = capture_probe
report = {"version": "1.0.7", "trace": "injected positions; no OS input", "tests": {}}
checked_slow = False
checked_fast = False
checked_second = False
checked_idle = False
changed_diameter = False
checked_hold = False


def tick():
    global checked_slow, checked_fast, checked_second, checked_idle, changed_diameter, checked_hold
    elapsed = time.monotonic() - started
    if elapsed < 3:
        point[0] = screen.x + 200 + round(300 * elapsed)
    elif elapsed < 3.4:
        point[0] = screen.x + max(100, 1100 - round(fast_speed * (elapsed - 3)))
    elif elapsed < 5:
        point[0] = screen.x + after_fast + round(40 * (elapsed - 3.4))
    if elapsed > 1.8 and not changed_diameter:
        controller.settings.sliders["size"].setValue(2)
        changed_diameter = True
    controller.sample(time.monotonic(), *point)
    if elapsed > 2.8 and not checked_slow:
        report["tests"]["slow_motion_real_capture_displayed"] = controller.frames_rendered > 5 and not controller.fault
        report["frames_at_approach"] = controller.frames_rendered
        report["tests"]["diameter_changed_live"] = bool(controller.overlay and controller.desktop.window_rect(controller.overlay.hwnd).w == 440)
        checked_slow = True
    if elapsed > 3.35 and not checked_fast:
        report["tests"]["fast_motion_hides_overlay"] = not (controller.overlay and controller.overlay.visible)
        checked_fast = True
    if elapsed > 4.9 and not checked_second:
        report["tests"]["slow_motion_reappears"] = controller.frames_rendered > report.get("frames_at_approach", 0)
        checked_second = True
    if elapsed > 5.6 and not checked_hold:
        report["tests"]["still_visible_after_600ms_to_aim"] = bool(controller.overlay and controller.overlay.visible)
        checked_hold = True
    if elapsed > 7.4 and not checked_idle:
        report["tests"]["stationary_hides_overlay"] = not (controller.overlay and controller.overlay.visible)
        report["frames_at_idle"] = controller.frames_rendered
        checked_idle = True
    if elapsed > 10.5:
        timer.stop()
        report["tests"]["no_capture_when_idle"] = controller.frames_rendered == report.get("frames_at_idle")
        report["tests"]["idle_resources_released"] = controller.worker.needs_probe.is_set()
        report["tests"]["no_capture_fault"] = not controller.fault
        report["fault"] = controller.fault
        report["frames"] = controller.frames_rendered
        report["result"] = "passed" if all(report["tests"].values()) else "failed"
        controller.close()
        (ROOT / "docs/validation/application-1.0.7.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
        app.exit(0 if report["result"] == "passed" else 1)


timer = QTimer()
timer.setInterval(16)
timer.timeout.connect(tick)
timer.start()
raise SystemExit(app.exec())
