"""Verify the real Windows clipboard through the connected Copy response button."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication
import win32clipboard
from app.config import Config
from app.controller import Controller
from app.ui.main_window import MainWindow


def main():
    app = QApplication([])
    clipboard = app.clipboard()
    original = QMimeData()
    mime = clipboard.mimeData()
    if mime:
        for kind in mime.formats():
            original.setData(kind, mime.data(kind))
    answer = "Bonjour Élodie,\nVoici la réponse relue et modifiée.\nMerci !"
    window = MainWindow(Config(animation="none"))
    controller = SimpleNamespace(app=app, window=window, inserting=False)
    window.copy_requested.connect(lambda: Controller.copy(controller))
    window.editor.setPlainText("Une demande qui ne doit pas être copiée")
    window.chat_history = [("assistant", "Ancienne réponse à exclure")]
    window.result.setPlainText(answer)
    try:
        window.copy.click()
        app.processEvents()
        win32clipboard.OpenClipboard()
        try:
            actual = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
        # Windows CF_UNICODETEXT represents line breaks as CRLF.
        assert actual.replace("\r\n", "\n") == answer, repr(actual)
        assert window.insert.isHidden() and window.target.isHidden()
        window.set_busy(True)
        window.result.setPlainText("Réponse inachevée")
        window.copy.click()
        assert clipboard.text() == answer
        report = {"native_windows_clipboard": True, "exact_edited_answer": True,
                  "history_excluded": True, "copy_blocked_during_generation": True,
                  "insertion_controls_hidden": True}
        output = Path(__file__).resolve().parents[1] / "docs/validation/clipboard.json"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        if clipboard.text() == answer:
            clipboard.setMimeData(original)
            app.processEvents()
        window.hide()


if __name__ == "__main__":
    main()
