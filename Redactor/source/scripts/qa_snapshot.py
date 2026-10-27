"""Offscreen native Qt screenshots and geometric checks, no desktop automation."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from app import theme
from app.config import Config
from app.ui.main_window import MainWindow
from app.ui.orb import draw_orb
from app.ui.settings import SettingsDialog
from app.ai.prompts import Request


def main():
    app = QApplication([])
    theme.configure_app(app)
    root = Path(__file__).resolve().parents[1]
    output = root / "docs" / "validation"
    output.mkdir(parents=True, exist_ok=True)
    # Reusable app icon is painted by the exact same procedural orb renderer.
    icon = QPixmap(256, 256)
    icon.fill(Qt.transparent)
    painter = QPainter(icon)
    draw_orb(painter, QRectF(0, 0, 256, 256), "ready")
    painter.end()
    icon.save(str(root / "assets" / "redactor.png"))
    icon.save(str(root / "assets" / "redactor.ico"))
    window = MainWindow(Config(animation="none"))
    window.show()
    app.processEvents()
    window.grab().save(str(output / "redactor-accueil.png"))
    window.set_engine(True, "IA locale prête")
    window.select_action("correct")
    window.editor.setPlainText("Bonjours Madame Dupont, je vous envoi les document demain.")
    window.begin_turn(Request("correct", window.editor.toPlainText()))
    window.result.setPlainText("Bonjour Madame Dupont, je vous envoie les documents demain.")
    window.complete_turn()
    window.set_busy(False)
    window.set_state("ready")
    window.target_label.setText("Bloc-notes · Document de travail")
    window.message("Proposition prête. Relisez et modifiez le texte, puis cliquez Copier la réponse.")
    app.processEvents()
    window.grab().save(str(output / "redactor-resultat.png"))
    issues = []
    for item in [*window.action_buttons.values(), window.generate, window.regenerate, window.copy, window.settings]:
        if item.width() < item.fontMetrics().horizontalAdvance(item.text()) + 12:
            issues.append(f"Bouton trop étroit : {item.text()}")
    if window.width() != theme.WIDTH or window.height() != theme.HEIGHT:
        issues.append(f"Dimensions inattendues : {window.width()} × {window.height()}")
    window.resize(600, 500)
    app.processEvents()
    window.grab().save(str(output / "redactor-compact.png"))
    window.apply_config(Config(animation="none", text_size=20))
    window.resize(900, 720)
    app.processEvents()
    window.grab().save(str(output / "redactor-grand-texte.png"))
    settings = SettingsDialog(Config(animation="none"), window)
    settings.show()
    app.processEvents()
    settings.grab().save(str(output / "redactor-reglages.png"))
    print({"output": str(output), "issues": issues}, flush=True)
    settings.close()
    window.hide()
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
