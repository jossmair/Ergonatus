"""Move the real orb with injected read-only monitor samples; no OS input."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.win32 import enable_dpi
enable_dpi()
from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication
from application import Application
from services.configuration import Configuration, Preferences
from ui.theme import configure_app

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
configure_app(app)
config = Configuration(ROOT / "docs/test-settings/monitors/settings.json")
config.save(Preferences(enabled=False))
controller = Application(app, config)
pairs = controller.screen_pairs()
if len(pairs) < 2:
    controller.close()
    raise SystemExit("Deux écrans sont nécessaires à cet essai.")
left, right = pairs[:2]
point = [left[1].bounds.x + 250, left[1].bounds.y + 250]
controller.desktop.pointer = lambda: tuple(point)
controller.position_orb(screen_name=left[0].name())
started = time.monotonic()
report = {"version": "1.0.7", "trace": "injected monitor samples; no OS pointer movement", "tests": {}}
stored = {}
steps = set()


def inspect_screen(pair):
    bounds = controller.desktop.window_rect(int(controller.orb.winId()))
    return pair[1].bounds.contains(bounds), str(bounds)


def tick():
    elapsed = time.monotonic() - started
    if elapsed > .3 and 0 not in steps:
        screen = left[0].availableGeometry()
        controller.orb.move(QPoint(screen.x() + 90, screen.y() + 90))
        controller.remember_orb()
        stored[left[0].name()] = (controller.orb.x(), controller.orb.y())
        point[:] = [right[1].bounds.x + 250, right[1].bounds.y + 250]
        steps.add(0)
    if elapsed > 1.4 and 1 not in steps:
        valid, bounds = inspect_screen(right)
        report["tests"]["real_orb_follows_to_secondary_while_lens_disabled"] = valid and controller.orb_screen_name == right[0].name()
        report["secondary_bounds"] = bounds
        screen = right[0].availableGeometry()
        controller.orb.move(QPoint(screen.x() + 160, screen.y() + 160))
        controller.remember_orb()
        stored[right[0].name()] = (controller.orb.x(), controller.orb.y())
        point[:] = [left[1].bounds.x + 250, left[1].bounds.y + 250]
        steps.add(1)
    if elapsed > 2.5 and 2 not in steps:
        valid, bounds = inspect_screen(left)
        report["tests"]["primary_position_restored"] = valid and (controller.orb.x(), controller.orb.y()) == stored[left[0].name()]
        report["primary_bounds"] = bounds
        point[:] = [right[1].bounds.x + 250, right[1].bounds.y + 250]
        steps.add(2)
    if elapsed > 3.6:
        timer.stop()
        valid, bounds = inspect_screen(right)
        report["tests"]["secondary_position_restored"] = valid and (controller.orb.x(), controller.orb.y()) == stored[right[0].name()]
        report["tests"]["positions_persisted_for_both_monitors"] = config.load().orb_positions == stored
        report["tests"]["no_capture_fault"] = not controller.fault
        report["result"] = "passed" if all(report["tests"].values()) else "failed"
        controller.close()
        (ROOT / "docs/validation/monitors-1.0.7.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
        app.exit(0 if report["result"] == "passed" else 1)


timer = QTimer()
timer.setInterval(50)
timer.timeout.connect(tick)
timer.start()
raise SystemExit(app.exec())
