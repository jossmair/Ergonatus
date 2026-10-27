"""Exercise the real injector against disposable controls owned by this probe.

The separate MTA process can only send the fixed fixture to the exact probe
window/pid. It never activates another application or inspects user documents.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

FIXTURE = "Test Transcri : oui oui, une phrase entière avec des accents éàç et un emoji 😀."


def worker(args):
    import comtypes
    comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
    from app.core.controller import Controller
    from app.core.device_detector import Hardware
    from app.core.focus_manager import FocusManager, TargetError
    from app.core.settings import Settings
    from app.core.text import TextFormatter, TextLedger
    from app.core.text_injector import TextInjector
    from app.engines.base import Transcript

    report = {"delivered": False}
    controller = None
    try:
        class ProbeFocus(FocusManager):
            def locate(self):
                target = super().locate()
                if target.hwnd != args.window or target.pid != args.pid:
                    self.target = None
                    raise TargetError("Disposable probe lost focus; no input sent")
                return target

        controller = Controller(Settings(), Hardware("fixture", 4, 16 * 2**30, 8 * 2**30))
        controller.focus = ProbeFocus()
        controller.injector = TextInjector(controller.focus)
        controller.ledger, controller.formatter, controller.last_audio = TextLedger(), TextFormatter(Settings()), 0
        event = Transcript("fixture", FIXTURE, True, time.monotonic())
        controller._transcript(event)
        controller._transcript(event)
        controller._finalize_text()
        asyncio.run(controller._finish_insertion())
        controller._transcript(event)
        controller._finalize_text()
        asyncio.run(controller._finish_insertion())
        report.update(delivered=not controller.ledger.pending,
                      method=controller.injector.last_method,
                      acknowledged_once=controller.ledger.inserted == [FIXTURE])
    except Exception as error:
        report.update(error_type=type(error).__name__, error=str(error))
    finally:
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if controller:
            controller.injector = None
            if getattr(controller, "focus", None):
                controller.focus.target, controller.focus.uia = None, None
                controller.focus = None
        comtypes.CoUninitialize()


def fixture(args):
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget
    from scripts.windows_integration import activate_fixture

    app = QApplication([])
    window = QWidget()
    window.setWindowTitle("Transcri — test d’insertion jetable")
    layout = QVBoxLayout(window)
    line, document = QLineEdit("avant CIBLE après"), QPlainTextEdit("avant CIBLE après")
    layout.addWidget(line)
    layout.addWidget(document)
    window.resize(600, 230)
    window.show()
    window.activateWindow()
    rows, processes = [], []
    report = args.report.resolve()

    def start(index):
        control = (line, document)[index]
        activate_fixture(int(window.winId()))
        control.setFocus()
        if index == 0:
            line.setSelection(6, 5)
        else:
            cursor = document.textCursor()
            cursor.setPosition(6)
            cursor.setPosition(11, QTextCursor.KeepAnchor)
            document.setTextCursor(cursor)
        result_path = report.with_name(report.stem + f"-field-{index}.json")
        command = [sys.executable, "-m", "scripts.insertion_probe", "--worker", "--window", str(int(window.winId())),
                   "--pid", str(os.getpid()), "--report", str(result_path)]
        processes.append(subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        deadline = time.monotonic() + 20

        def check():
            if processes[-1].poll() is None and time.monotonic() < deadline:
                QTimer.singleShot(50, check)
                return
            if processes[-1].poll() is None:
                processes[-1].terminate()
            result = json.loads(result_path.read_text()) if result_path.exists() else {}
            _, stderr = processes[-1].communicate(timeout=3)
            if stderr:
                result["worker_error"] = stderr.decode("utf-8", errors="replace")[-2500:]
            expected = "avant " + FIXTURE + "  après"
            value = line.text() if index == 0 else document.toPlainText()
            result.update(control="line" if index == 0 else "document", exact_selection_replacement=value == expected,
                          other_field_untouched=document.toPlainText() == "avant CIBLE après" if index == 0 else line.text() == expected)
            if value != expected:
                result.update(fixture_actual=value, fixture_expected=expected)
            rows.append(result)
            if index == 0 and result.get("exact_selection_replacement"):
                QTimer.singleShot(100, lambda: start(1))
            else:
                report.write_text(json.dumps({"success": len(rows) == 2 and all(
                    row.get("delivered") and row["exact_selection_replacement"] and row["other_field_untouched"]
                    and row.get("acknowledged_once") for row in rows), "fields": rows}, indent=2), encoding="utf-8")
                app.quit()
        QTimer.singleShot(50, check)

    QTimer.singleShot(500, lambda: start(0))
    app.exec()
    data = json.loads(report.read_text())
    print(json.dumps(data), flush=True)
    return 0 if data["success"] else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--window", type=int)
    parser.add_argument("--pid", type=int)
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.worker:
        # comtypes initializes the importing thread as STA. Import it here so
        # the dedicated probe worker can initialize its own MTA explicitly.
        import comtypes  # noqa: F401
        task = threading.Thread(target=worker, args=(args,))
        task.start()
        task.join()
        return 0
    return fixture(args)


if __name__ == "__main__":
    raise SystemExit(main())
