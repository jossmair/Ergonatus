"""Native three-orb/white-desktop test and automatic fault recovery.

Original companion widgets are imported without starting their input services.
Pointer positions and two failures are injected internally; no OS input occurs.
"""
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent / "Transcri"), str(ROOT.parent / "Fortinatus")]
from services.win32 import enable_dpi, physical_to_logical
enable_dpi()
from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget
from app.ui import floating_hub
from fortinatus.keyboard_orb import KeyboardOrb, orb_position
from application import Application
from main import VERSION
from services.configuration import Configuration, Preferences
from ui.theme import configure_app

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
configure_app(app)
config = Configuration(ROOT / "docs/test-settings/recovery/settings.json")
config.save(Preferences(orb_positions={s.name(): (s.availableGeometry().right() - 50,
    s.availableGeometry().bottom() - 40) for s in app.screens()}))
controller = Application(app, config)
pairs = controller.screen_pairs()
if not pairs:
    controller.close()
    raise SystemExit("Aucun écran disponible pour cet essai.")
point = [pairs[0][1].bounds.x + 150, pairs[0][1].bounds.y + 300]
controller.desktop.pointer = lambda: tuple(point)


def current_pair():
    return next(pair for pair in pairs if pair[1].bounds.x <= point[0] < pair[1].bounds.x + pair[1].bounds.w)


class ReadOnlyCursor:
    @staticmethod
    def pos():
        screen, monitor = current_pair()
        return QPoint(*physical_to_logical(point, monitor, screen))


floating_hub.QCursor = ReadOnlyCursor
hub = floating_hub.FloatingHub(SimpleNamespace(hub_visible=True))
hub.setWindowTitle("Transcrinator · Validation des trois orbes")
hub.state, hub.compacted = "Prêt", True
hub.resize_for_state(animated=False)
hub.show()
hub.timer.start(40)
fort = KeyboardOrb()
fort.show()


def place_fort():
    area = current_pair()[0].availableGeometry()
    anchor = hub.geometry() if area.contains(hub.geometry().center()) else None
    fort.move(orb_position(area, companion=anchor))


place_fort()
fort_timer = QTimer()
fort_timer.setInterval(120)
fort_timer.timeout.connect(place_fort)
fort_timer.start()


class Background(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("white"))


background = Background(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
background.setAttribute(Qt.WA_ShowWithoutActivating)
background.resize(300, 360)


def place_background():
    area = current_pair()[0].availableGeometry()
    background.move(area.right() + 1 - 300, area.bottom() + 1 - 360)
    background.show()


place_background()
report = {"version": VERSION, "method": "native original companion widgets, white background, read-only injected positions and two injected failures",
          "monitor_count": len(pairs), "live_two_screen_test": "available" if len(pairs) >= 2 else "unavailable; one screen currently attached",
          "tests": {}, "capture_errors": []}
controller.worker.failed.connect(report["capture_errors"].append)
started = time.monotonic()
steps = set()
frames_at_fault = []


def stacked():
    p, f, t = controller.orb.geometry(), fort.geometry(), hub.geometry()
    area = current_pair()[0].availableGeometry()
    names = {name for name, _ in controller.desktop.companions()}
    return names == {"fortinatus", "transcrinator"} and area.contains(p) and p.bottom() < f.top() and f.bottom() < t.top() and abs(p.center().x() - f.center().x()) <= 1


def tick():
    elapsed = time.monotonic() - started
    index = 0 if elapsed < 3.7 else min(1, len(pairs) - 1)
    monitor = pairs[index][1]
    point[:] = [monitor.bounds.x + 150 + round(70 * (elapsed % 2)), monitor.bounds.y + 300]
    tests = report["tests"]
    if elapsed > .9 and 0 not in steps:
        tests["three_original_orbs_discovered_and_stacked_despite_old_saved_position"] = stacked()
        area = current_pair()[0].availableGeometry()
        hub.manual_position = hub.pos() - QPoint(0, 60)
        hub.manual_area = QRect(area)
        steps.add(0)
    if elapsed > 1.5 and 1 not in steps:
        tests["same_monitor_companion_movement_followed"] = stacked()
        frames_at_fault.append(controller.frames_rendered)
        controller.fail("injected transient capture failure 1")
        tests["failure_does_not_change_activation_or_saved_preference"] = controller.prefs.enabled and controller.orb.enabled and config.load().enabled
        steps.add(1)
    if elapsed > 3.2 and 2 not in steps:
        tests["automatic_real_capture_recovery_1"] = not controller.fault and controller.frames_rendered > frames_at_fault[0] + 5
        steps.add(2)
    if elapsed > 4.6 and 3 not in steps:
        tests["third_position_on_destination_screen"] = stacked()
        place_background()
        frames_at_fault.append(controller.frames_rendered)
        controller.fail("injected transient capture failure 2")
        steps.add(3)
    if elapsed > 6.6 and 4 not in steps:
        tests["automatic_real_capture_recovery_2_on_white_background"] = not controller.fault and controller.frames_rendered > frames_at_fault[1] + 5
        controller.set_enabled(False)
        controller.fail("injected stale failure after voluntary disable")
        steps.add(4)
    if elapsed > 7.2 and 5 not in steps:
        tests["voluntary_disable_is_respected"] = not controller.prefs.enabled and not controller.retry_timer.isActive() and not config.load().enabled
        controller.set_enabled(True)
        steps.add(5)
    if elapsed > 9.5:
        timer.stop()
        tests["real_capture_returns_after_voluntary_reactivation"] = not controller.fault and controller.prefs.enabled and controller.frames_rendered > frames_at_fault[1] + 20
        tests["no_unexpected_capture_errors"] = not report["capture_errors"]
        tests["final_third_position"] = stacked()
        report["frames_rendered"] = controller.frames_rendered
        report["result"] = "passed" if all(tests.values()) else "failed"
        fort_timer.stop()
        hub.timer.stop()
        hub.hide()
        fort.hide()
        background.hide()
        controller.close()
        (ROOT / f"docs/validation/recovery-stack-{VERSION}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
        app.exit(0 if report["result"] == "passed" else 1)


timer = QTimer()
timer.setInterval(16)
timer.timeout.connect(tick)
timer.start()
raise SystemExit(app.exec())
