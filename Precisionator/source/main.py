"""Précisionator 1.0 — offline Windows visual assistance."""
import argparse
from logging.handlers import RotatingFileHandler
import logging
from pathlib import Path
import sys

VERSION = "1.0.7"


def main():
    parser = argparse.ArgumentParser(description="Précisionator · Loupe intelligente")
    parser.add_argument("--settings", action="store_true", help="Ouvrir les paramètres")
    parser.add_argument("--config", type=Path, help="Fichier de préférences distinct pour les essais")
    parser.add_argument("--exit-after", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "win32":
        print("Précisionator nécessite Windows 10 (2004+) ou Windows 11.")
        return 1
    from services.win32 import enable_dpi
    enable_dpi()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from services.configuration import config_path
    from services.lifecycle import InstanceServer, SingleInstance
    from ui.theme import configure_app
    app = QApplication(sys.argv[:1])
    # Shared Ergonatus surfaces; the original standalone projects are untouched.
    import runpy as _suite_runpy
    from pathlib import Path as _suite_path
    for _suite_root in (*_suite_path(__file__).resolve().parents,*_suite_path(sys.executable).resolve().parents):
        if (_suite_root/"suite_design.py").is_file() and (_suite_root/"Hub").is_dir():
            _suite_runpy.run_path(str(_suite_root/"suite_design.py"))["install"](app)
            break
    app.setApplicationName("Precisionator")
    app.setApplicationDisplayName("Précisionator")
    app.setApplicationVersion(VERSION)
    app.setQuitOnLastWindowClosed(False)
    instance = SingleInstance()
    try:
        if not instance.acquire():
            InstanceServer.notify()
            return 0
        folder = args.config.parent if args.config else config_path().parent
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(folder / "precisionator.log", maxBytes=256000, backupCount=2, encoding="utf-8")
        logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")
        logging.info("Précisionator %s · Python %s", VERSION, sys.version.split()[0])
        configure_app(app)
        from application import Application
        from services.configuration import Configuration
        controller = Application(app, Configuration(args.config))
        if args.settings:
            controller.open_settings()
        if args.exit_after:
            QTimer.singleShot(max(1, round(args.exit_after * 1000)), controller.quit)
        return app.exec()
    except Exception as error:
        logging.exception("Démarrage impossible")
        QMessageBox.critical(None, "Précisionator", "Démarrage impossible : " + str(error))
        return 1
    finally:
        instance.close()


if __name__ == "__main__":
    raise SystemExit(main())
