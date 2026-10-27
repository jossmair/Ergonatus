"""Native Qt action regression; dispatch only to our widget, never OS input."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.win32 import enable_dpi
enable_dpi()
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from application import Application
from main import VERSION
from services.configuration import Configuration, Preferences
from services.lifecycle import SingleInstance
from services.mouse_speed import get_speed
from ui.theme import background, configure_app

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
configure_app(app)
instance = SingleInstance()
if not instance.acquire():
    raise SystemExit("Fermer Précisionator avant ce test natif isolé.")
config = Configuration(ROOT / "docs/test-settings/orb-click/settings.json")
config.save(Preferences(enabled=False))
controller = None
report = {"version": VERSION, "input": "Qt events to our own widget only; no OS input", "tests": {}}
try:
    controller = Application(app, config)
    orb = controller.orb
    app.processEvents()
    report["tests"]["quiet_start"] = orb.isVisible() and not controller.settings.isVisible()
    report["tests"]["pointer_speed_matches_windows"] = controller.settings.sliders["mouse_speed"].value() + 1 == get_speed()

    def dispatch(kind, local, global_position, button, buttons):
        event = QMouseEvent(kind, QPointF(local), QPointF(global_position), button, buttons, Qt.NoModifier)
        app.sendEvent(orb, event)

    def click(button=Qt.LeftButton):
        point = orb.rect().center()
        global_position = orb.mapToGlobal(point)
        dispatch(QEvent.MouseButtonPress, point, global_position, button, button)
        dispatch(QEvent.MouseButtonRelease, point, global_position, button, Qt.NoButton)

    for index, expected in enumerate((True, False, True, False), 1):
        click()
        report["tests"][f"click_{index}_toggles_and_saves"] = (
            controller.prefs.enabled == expected and orb.enabled == expected
            and config.load().enabled == expected
            and controller.settings.activation.isChecked() == expected
            and controller.tracker.timer.isActive() == expected)
        report["tests"][f"click_{index}_opens_no_window"] = (
            not controller.settings.isVisible() and not controller.tray.menu.isVisible())
        report["tests"][f"click_{index}_keeps_app_and_orb_running"] = (
            not controller.stopped and orb.isVisible() and controller.follow_timer.isActive())
        report["tests"][f"click_{index}_keeps_speed_control_available"] = controller.settings.sliders["mouse_speed"].isEnabled()
        controller.tracker.stop()
    click(Qt.RightButton)
    report["tests"]["right_mouse_button_does_not_toggle"] = not controller.prefs.enabled

    point = orb.rect().center()
    origin = orb.mapToGlobal(point)
    delta = point * 2
    dispatch(QEvent.MouseButtonPress, point, origin, Qt.LeftButton, Qt.LeftButton)
    dispatch(QEvent.MouseMove, point + delta, origin + delta, Qt.NoButton, Qt.LeftButton)
    dispatch(QEvent.MouseButtonRelease, point, origin + delta, Qt.LeftButton, Qt.NoButton)
    report["tests"]["drag_does_not_toggle"] = orb.dragged and not controller.prefs.enabled
    controller.tray.menu.actions()[0].trigger()
    app.processEvents()
    report["tests"]["settings_accessible_via_menu"] = controller.settings.isVisible()
    folder = ROOT / "docs/validation"
    controller.settings.grab().save(str(folder / f"parametres-natifs-{VERSION}.png"))
    report["tests"]["amethyst_asset_loaded"] = not background().isNull()
except Exception as error:
    report["error"] = str(error)
finally:
    if controller:
        controller.close()
    instance.close()
    report["result"] = "passed" if report["tests"] and all(report["tests"].values()) and "error" not in report else "failed"
    (ROOT / f"docs/validation/orb-click-{VERSION}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["result"] == "passed" else 1)
