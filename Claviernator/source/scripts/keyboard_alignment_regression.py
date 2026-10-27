"""Check real Windows Qt layout without sending any input."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from fortinatus import __version__
from fortinatus.theme import configure_app
from fortinatus.virtual_keyboard import VirtualKeyboard
from fortinatus.windows import SingleInstance
app = QApplication([])
guard = SingleInstance()
assert guard.acquire(), "Quitter Claviernator avant ce contrôle."
configure_app(app)
window = VirtualKeyboard()
window.setFixedSize(900, 320)
window.reveal()
result = {}
def inspect():
    try:
        def center(widget):
            return widget.mapTo(window, widget.rect().center()).y()
        ctrl = window.modifier_buttons[0xA2][0]
        result.update(version=__version__, size=[window.width(), window.height()],
                      dpr=window.devicePixelRatioF(), ctrl_y=center(ctrl),
                      clear_y=center(window.clear_button), insert_y=center(window.insert_button),
                      pick_y=center(window.pick_button), stack_y=center(window.stack))
        assert result["size"] == [900, 320]
        assert abs(result["ctrl_y"]-result["clear_y"]) <= 2, result
        assert abs(result["ctrl_y"]-result["insert_y"]) <= 2, result
        assert abs(result["pick_y"]-result["stack_y"]) <= 6, result
        result["status"] = "passed"
        folder = Path(__file__).resolve().parents[1] / "docs/validation"
        window.grab().save(str(folder / "clavier-alignement-windows.png"))
        (folder / "keyboard-alignment.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    except Exception as error:
        result["error"] = str(error)
    finally:
        window.close()
        app.quit()
QTimer.singleShot(800, inspect)
app.exec()
guard.close()
print(json.dumps(result, indent=2))
assert result.get("status") == "passed", result
