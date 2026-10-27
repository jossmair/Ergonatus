"""Compare real native orbs using Transcrinator's unmodified source widget.

Only read-only position providers are substituted. No system input is generated
and neither existing application nor its preferences are started or modified.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT.parent / "Transcri"
source = REFERENCE / "app/ui/floating_hub.py"
if not source.exists():
    raise SystemExit("Placer les sources Transcri à côté du projet pour cet essai comparatif.")
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(ROOT))
from services.win32 import enable_dpi, physical_to_logical
enable_dpi()
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import QApplication
from app.ui import floating_hub
from application import Application
from main import VERSION
from services.configuration import Configuration, Preferences
from ui.theme import configure_app

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
configure_app(app)
config = Configuration(ROOT / "docs/test-settings/twins/settings.json")
config.save(Preferences(enabled=False))
controller = Application(app, config)
pairs = controller.screen_pairs()
if len(pairs) < 2:
    controller.close()
    raise SystemExit("Deux écrans sont nécessaires à cet essai.")
point = [pairs[0][1].bounds.x + 100, pairs[0][1].bounds.y + 100]
controller.desktop.pointer = lambda: tuple(point)


class ReadOnlyCursor:
    @staticmethod
    def pos():
        pair = next(pair for pair in pairs if pair[1].bounds.x <= point[0] < pair[1].bounds.x + pair[1].bounds.w)
        return QPoint(*physical_to_logical(point, pair[1], pair[0]))


floating_hub.QCursor = ReadOnlyCursor
hub = floating_hub.FloatingHub(SimpleNamespace(hub_visible=True))
hub.setWindowTitle("Transcrinator · Comparaison des orbes")
hub.state = "Prêt"
hub.compacted = True
hub.resize_for_state(animated=False)
hub.show()
# Actual geometry is used, including when the other timer has not fired yet.
controller.desktop.companions = lambda: [("transcrinator", controller.desktop.window_rect(int(hub.winId())))]
controller.desktop.family_layout = lambda: (controller.desktop.companions(), [])
controller.position_orb(screen_name=pairs[0][0].name())
QTimer.singleShot(17, lambda: hub.timer.start(40))
report = {"version": VERSION, "method": "native Qt windows, injected read-only positions; no OS input",
          "reference": str(source), "reference_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "tests": {}, "warmup": [], "trials": []}
started = time.monotonic()
next_crossing = .35
pending = None
crossings = 0


def finish():
    timer.stop()
    tests = report["tests"]
    tests["six_crossings_measured_after_two_warmups"] = len(report["trials"]) == 6 and len(report["warmup"]) == 2
    tests["same_40ms_precise_timer"] = controller.follow_timer.interval() == hub.timer.interval() == 40 and controller.follow_timer.timerType() == hub.timer.timerType() == Qt.PreciseTimer
    tests["no_added_half_second_delay"] = all(t["precisionator_ms"] < 110 for t in report["trials"])
    tests["latency_difference_under_60ms"] = all(abs(t["precisionator_ms"] - t["transcrinator_ms"]) < 60 for t in report["trials"])
    tests["both_activation_states_checked"] = {t["enabled"] for t in report["trials"]} == {False, True}
    tests["aligned_without_overlap_on_each_crossing"] = all(t["aligned"] and t["native_bounds_inside_screen"] for t in report["trials"])
    tests["no_capture_fault"] = not controller.fault
    report["result"] = "passed" if all(tests.values()) else "failed"
    hub.timer.stop()
    hub.hide()
    controller.close()
    (ROOT / f"docs/validation/twins-{VERSION}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    app.exit(0 if report["result"] == "passed" else 1)


def tick():
    global next_crossing, pending, crossings
    now = time.monotonic()
    elapsed = now - started
    if pending is None and crossings < 8 and elapsed >= next_crossing:
        pair = pairs[(crossings + 1) % 2]
        if crossings == 5:
            controller.set_enabled(True)
        pending = {"start": time.monotonic(), "pair": pair, "enabled": controller.prefs.enabled}
        point[:] = [pair[1].bounds.x + 100, pair[1].bounds.y + 100]
        crossings += 1
    if pending:
        area = pending["pair"][0].availableGeometry()
        for key, widget in (("precisionator_ms", controller.orb), ("transcrinator_ms", hub)):
            if key not in pending and area.contains(widget.geometry().center()):
                pending[key] = round((time.monotonic() - pending["start"]) * 1000, 2)
        if now - pending["start"] >= .20:
            for key in ("precisionator_ms", "transcrinator_ms"):
                pending.setdefault(key, 9999)
            f, t = controller.orb.geometry(), hub.geometry()
            native = controller.desktop.window_rect(int(controller.orb.winId()))
            report["warmup" if crossings <= 2 else "trials"].append({"screen": pending["pair"][0].name(), "enabled": pending["enabled"],
                "precisionator_ms": pending["precisionator_ms"], "transcrinator_ms": pending["transcrinator_ms"],
                "aligned": abs(f.x() - t.x()) <= 1 and f.bottom() < t.top(),
                "native_bounds_inside_screen": pending["pair"][1].bounds.contains(native)})
            pending = None
            next_crossing = elapsed + .15
    if crossings == 8 and pending is None:
        finish()


timer = QTimer()
timer.setTimerType(Qt.PreciseTimer)
timer.setInterval(2)
timer.timeout.connect(tick)
timer.start()
raise SystemExit(app.exec())
