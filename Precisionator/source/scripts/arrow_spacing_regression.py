"""Real Claviernator widgets, no Transcrinator, no input services or OS input."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent / "Fortinatus")]
from services.win32 import enable_dpi, discover_companions, discover_companion_obstacles
enable_dpi()
from PySide6.QtCore import QPoint, QRectF, QTimer, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from fortinatus.keyboard_orb import KeyboardOrb, orb_position, scroll_arrow_positions
from fortinatus.hover_scroll import HoverScrollArrow
from application import Application
from main import VERSION
from services.configuration import Configuration, Preferences
from ui.theme import configure_app

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
configure_app(app)
config = Configuration(ROOT / "docs/test-settings/arrow-spacing/settings.json")
config.save(Preferences(enabled=False))
controller = Application(app, config)
pairs = controller.screen_pairs()
if not pairs:
    controller.close()
    raise SystemExit("Aucun écran disponible.")
point = [pairs[0][1].bounds.x + 200, pairs[0][1].bounds.y + 200]
controller.desktop.pointer = lambda: tuple(point)


def own_layout():
    windows = [w for w in controller.desktop.windows() if w[1] == os.getpid()]
    return discover_companions(windows), discover_companion_obstacles(windows)


controller.desktop.family_layout = own_layout
fort = KeyboardOrb()
fort.show()
arrows = [HoverScrollArrow(1), HoverScrollArrow(-1)]
# scroll_requested is intentionally unconnected: these are display-only tests.
stages = [("without_arrows", 0, False, 0), ("with_arrows", 0, True, 0),
          ("moved_with_arrows", 0, True, -80), ("arrows_hidden_again", 0, False, -80)]
if len(pairs) >= 2:
    stages.append(("secondary_with_arrows", 1, True, 0))
stage_index = 0
stage_started = time.monotonic()
report = {"version": VERSION, "monitor_count": len(pairs), "method": "native original KeyboardOrb and HoverScrollArrow, no Transcrinator widget, injected read-only pointer",
          "tests": {}, "stages": []}


def place():
    _, screen_index, visible, offset = stages[stage_index]
    screen, monitor = pairs[screen_index]
    point[:] = [monitor.bounds.x + 200, monitor.bounds.y + 200]
    fort.move(orb_position(screen.availableGeometry(), scroll_arrows=visible) + QPoint(0, offset))
    for arrow, position in zip(arrows, scroll_arrow_positions(fort.geometry())):
        arrow.move(position)
        arrow.setVisible(visible)


def snapshot():
    widgets = [controller.orb, fort, *arrows]
    bounds = controller.orb.geometry()
    for widget in widgets[1:]:
        bounds = bounds.united(widget.geometry())
    bounds.adjust(-10, -10, 10, 10)
    image = QPixmap(bounds.size())
    image.fill(Qt.white)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    for widget in widgets:
        pixmap = widget.grab()
        painter.drawPixmap(QRectF(widget.geometry().translated(-bounds.topLeft())), pixmap, QRectF(pixmap.rect()))
    painter.end()
    image.save(str(ROOT / f"docs/validation/orbes-sans-transcrinator-{VERSION}.png"))


def tick():
    global stage_index, stage_started
    if time.monotonic() - stage_started < .75:
        return
    name, screen_index, visible, _ = stages[stage_index]
    screen, monitor = pairs[screen_index]
    p = controller.desktop.window_rect(int(controller.orb.winId()))
    f = controller.desktop.window_rect(int(fort.winId()))
    top = controller.desktop.window_rect(int(arrows[0].winId())) if visible else f
    gap = top.y - (p.y + p.h)
    valid = abs(gap - round(10 * monitor.scale)) <= 2 and monitor.bounds.contains(p) and abs(p.x + p.w / 2 - f.x - f.w / 2) <= 2
    families, obstacles = own_layout()
    valid = valid and [n for n, _ in families] == ["fortinatus"] and len(obstacles) == (2 if visible else 0)
    report["tests"][name] = valid
    report["stages"].append({"name": name, "screen": screen.name(), "scale": monitor.scale, "gap_physical_pixels": gap,
                             "precisionator": str(p), "fortinatus": str(f)})
    if name == "with_arrows":
        snapshot()
    if stage_index + 1 < len(stages):
        stage_index += 1
        place()
        stage_started = time.monotonic()
    else:
        timer.stop()
        placement.stop()
        report["result"] = "passed" if all(report["tests"].values()) else "failed"
        controller.close()
        fort.hide()
        for arrow in arrows:
            arrow.hide()
        (ROOT / f"docs/validation/arrow-spacing-{VERSION}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
        app.exit(0 if report["result"] == "passed" else 1)


place()
placement = QTimer()
placement.setInterval(120)
placement.timeout.connect(place)
placement.start()
timer = QTimer()
timer.setInterval(25)
timer.timeout.connect(tick)
timer.start()
raise SystemExit(app.exec())
