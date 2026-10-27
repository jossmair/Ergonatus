"""Exercise the production injector only in this test's own disposable controls."""
import asyncio
import json
import multiprocessing as mp
import os
from pathlib import Path
import threading
import time

FIXTURE = "Dictée Transcrinator : oui oui, une phrase entière avec éàç et un emoji 😀."
STALE = "ANCIEN PRESSE-PAPIERS : ceci n'est pas la dictée."


def injection_worker(connection, hwnd, pid, legacy_source=None, legacy_working_shortcut=False):
    def work():
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        controller = None
        result = {"delivered": False}
        try:
            from app.core.controller import Controller
            from app.core.device_detector import Hardware
            from app.core.focus_manager import FocusManager, TargetError
            from app.core.settings import Settings
            from app.core.text import TextFormatter, TextLedger
            from app.core.text_injector import TextInjector
            from app.engines.base import Transcript
            if legacy_source:
                import importlib.util
                spec = importlib.util.spec_from_file_location("transcrinator_legacy_injector", legacy_source)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if legacy_working_shortcut:
                    from app.core.win32 import paste_inputs, send_paste
                    module.send = lambda inputs: send_paste(paste_inputs(hwnd))
                TextInjector = module.TextInjector

            class ProbeFocus(FocusManager):
                def locate(self):
                    target = super().locate()
                    if target.hwnd != hwnd or target.pid != pid:
                        self.target = None
                        raise TargetError("Disposable test window lost focus")
                    return target

            class ProbeInjector(TextInjector):
                def insert(self, text):
                    # Only the test fixture performs this ownership check.
                    # Production automatic paste never classifies the field.
                    self.focus.locate()
                    return super().insert(text)

            controller = Controller(Settings(), Hardware("fixture", 4, 16 * 2**30, 8 * 2**30))
            controller.focus = ProbeFocus()
            controller.injector = ProbeInjector(controller.focus)
            controller.ledger = TextLedger()
            controller.formatter = TextFormatter(Settings())
            controller.last_audio = 0
            event = Transcript("fixture", FIXTURE, True, time.monotonic())
            controller._transcript(event)
            controller._transcript(event)
            controller._finalize_text()
            asyncio.run(controller._finish_insertion())
            controller._transcript(event)
            controller._finalize_text()
            asyncio.run(controller._finish_insertion())
            result.update(delivered=not controller.ledger.pending,
                          acknowledged_once=controller.ledger.inserted == [FIXTURE],
                          last_failure=getattr(controller.injector, "last_failure", None),
                          method=controller.injector.last_method)
            import win32clipboard
            try:
                win32clipboard.OpenClipboard()
                result["clipboard_contains_dictation"] = win32clipboard.GetClipboardData(13) == FIXTURE + " "
                win32clipboard.CloseClipboard()
            except OSError:
                result["clipboard_contains_dictation"] = False
        except Exception as error:
            result["error_type"] = type(error).__name__
        finally:
            if controller:
                controller.injector = None
                if getattr(controller, "focus", None):
                    controller.focus.target, controller.focus.uia = None, None
                    controller.focus = None
            comtypes.CoUninitialize()
            connection.send(result)
            connection.close()

    import comtypes  # noqa: F401
    thread = threading.Thread(target=work)
    thread.start()
    thread.join()


def validate(output, delay_ms=0, legacy_source=None, legacy_working_shortcut=False):
    from PySide6.QtCore import QMimeData, QTimer
    from PySide6.QtGui import QKeySequence, QTextCursor
    from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget
    import win32gui

    class DelayedPaste:
        paste_count = 0

        def keyPressEvent(self, event):
            if not hasattr(self, "key_events"):
                self.key_events = []
            self.key_events.append([event.key(), event.modifiers().value,
                                    event.nativeVirtualKey(), event.nativeScanCode()])
            if event.matches(QKeySequence.Paste):
                self.paste_count += 1
                QTimer.singleShot(delay_ms, self.paste)
                event.accept()
            else:
                super().keyPressEvent(event)

    class Line(DelayedPaste, QLineEdit):
        pass

    class Document(DelayedPaste, QPlainTextEdit):
        pass

    app = QApplication([])
    original = app.clipboard().mimeData()
    backup = QMimeData()
    if original:
        for format_name in original.formats():
            backup.setData(format_name, original.data(format_name))
    window = QWidget()
    window.setWindowTitle("Transcrinator — validation isolée du collage")
    layout = QVBoxLayout(window)
    line, document = Line("avant "), Document("avant CIBLE après")
    layout.addWidget(line)
    layout.addWidget(document)
    window.resize(650, 230)
    window.show()
    rows, workers = [], []
    context = mp.get_context("spawn")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    def start(index):
        # This helper is restricted to the HWND just created by this fixture.
        from scripts.windows_integration import activate_fixture
        activate_fixture(int(window.winId()))
        control = (line, document)[index]
        control.setFocus()
        if index == 0:
            line.deselect()
            line.setCursorPosition(len(line.text()))
        else:
            cursor = document.textCursor()
            cursor.setPosition(6)
            cursor.setPosition(11, QTextCursor.KeepAnchor)
            document.setTextCursor(cursor)
        app.clipboard().setText(STALE)
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=injection_worker,
                                  args=(child, int(window.winId()), os.getpid(), legacy_source,
                                        legacy_working_shortcut))
        process.start()
        child.close()
        workers.append(process)
        deadline = time.monotonic() + 25

        def finish():
            result = parent.recv() if parent.poll() else {"delivered": False}
            parent.close()
            process.join(1)
            value = line.text() if index == 0 else document.toPlainText()
            expected = "avant " + FIXTURE + (" " if index == 0 else "  après")
            other_ok = (document.toPlainText() == "avant CIBLE après" if index == 0
                        else line.text() == "avant " + FIXTURE + " ")
            result.update(control="line_without_selection" if index == 0 else "document_with_selection",
                          exact_text=value == expected, other_field_untouched=other_ok,
                          key_events=getattr(control, "key_events", []),
                          paste_events=control.paste_count, pasted_stale_clipboard=STALE in value)
            rows.append(result)
            if index == 0 and not legacy_source:
                QTimer.singleShot(100, lambda: start(1))
            else:
                report = {"success": len(rows) == 2 and all(row.get("delivered") and row["exact_text"]
                          and row["other_field_untouched"] and row["paste_events"] == 1
                          and row.get("acknowledged_once") for row in rows),
                          "delay_before_clipboard_read_ms": delay_ms, "microphone_used": False,
                          "legacy_clipboard_policy_with_working_shortcut": legacy_working_shortcut,
                          "legacy_injector": bool(legacy_source), "fields": rows}
                output.write_text(json.dumps(report, indent=2), encoding="utf-8")
                app.clipboard().setMimeData(backup)
                app.quit()

        def check():
            if process.is_alive() and time.monotonic() < deadline:
                QTimer.singleShot(30, check)
                return
            if process.is_alive():
                process.terminate()
                process.join(3)
            # Let the target process its queued Ctrl+V and delayed clipboard read.
            QTimer.singleShot(delay_ms + 200, finish)

        QTimer.singleShot(30, check)

    QTimer.singleShot(400, lambda: start(0))
    try:
        app.exec()
    finally:
        for process in workers:
            if process.is_alive():
                process.terminate()
                process.join(3)
        if win32gui.IsWindow(int(window.winId())):
            window.close()
    report = json.loads(output.read_text(encoding="utf-8"))
    print(json.dumps(report), flush=True)
    return 0 if report["success"] else 1
