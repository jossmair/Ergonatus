import argparse
import os
from pathlib import Path
import sys
import time

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTimer, QTranslator
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from .config import Settings
from .controller import Controller
from .keyboard_orb import VirtualKeyboardManager
from .theme import app_icon, configure_app
from .tray_menu import TrayMenu, tray_icon
from .ui import MainWindow
from .windows import SERVER_NAME, SingleInstance, migrate_startup_name


def main(argv=None):
    parser = argparse.ArgumentParser(description="Claviernator · clavier adapté pour Windows")
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--minimized", action="store_true")
    parser.add_argument("--no-hooks", action="store_true", help="Aperçu sans interception du clavier")
    parser.add_argument("--smoke-test", action="store_true", help="Vérification de lancement, puis fermeture sans adaptations")
    args = parser.parse_args(argv)
    guard = SingleInstance()
    try:
        if not guard.acquire():
            application = QCoreApplication([sys.argv[0]])
            if not args.smoke_test:
                # The first process may still be creating its window/server.
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    socket = QLocalSocket()
                    socket.connectToServer(SERVER_NAME)
                    if socket.waitForConnected(150):
                        socket.write(b"show")
                        socket.waitForBytesWritten(500)
                        socket.disconnectFromServer()
                        break
                    time.sleep(.05)
            return 0
        return run_application(args)
    finally:
        guard.close()


def run_application(args):
    application = QApplication([sys.argv[0]])
    # Shared Ergonatus surfaces; the original standalone projects are untouched.
    import runpy as _suite_runpy
    from pathlib import Path as _suite_path
    for _suite_root in (*_suite_path(__file__).resolve().parents,*_suite_path(sys.executable).resolve().parents):
        if (_suite_root/"suite_design.py").is_file() and (_suite_root/"Hub").is_dir():
            _suite_runpy.run_path(str(_suite_root/"suite_design.py"))["install"](application)
            break
    application.setApplicationName("Claviernator")
    application.setOrganizationName("Claviernator")
    configure_app(application)
    application.setWindowIcon(app_icon())
    application.setQuitOnLastWindowClosed(False)
    translator = QTranslator(application)
    translator.load("qtbase_fr", QLibraryInfo.path(QLibraryInfo.TranslationsPath))
    application.installTranslator(translator)
    folder = (args.config_dir or Path(os.environ.get("APPDATA", str(Path.home()))) / "Fortinatus").resolve()
    config_path = folder / "settings.json"

    # The Windows mutex above protects every version and config directory.
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer(application)
    if not server.listen(SERVER_NAME):
        QMessageBox.critical(None, "Claviernator", "Impossible d’ouvrir le service local de l’application.")
        return 1
    try:
        settings = Settings.load(config_path)
        # Pausing applies to this session. Every ordinary launch resumes the
        # saved adaptations, including files written by older paused versions.
        settings.start_active = not args.smoke_test
        controller = Controller(settings, config_path, args.no_hooks)
    except Exception as exc:
        QMessageBox.critical(None, "Claviernator · lancement impossible", str(exc))
        server.close()
        return 1
    window = MainWindow(controller, folder if args.config_dir else None)
    if not args.config_dir and not args.smoke_test:
        migrate_startup_name()
    keyboard = VirtualKeyboardManager(controller, enabled=not args.smoke_test)

    def show_window():
        window.showNormal()
        window.raise_()
        window.activateWindow()

    def accept_connection():
        connection = server.nextPendingConnection()
        if connection:
            connection.disconnectFromServer()
            connection.deleteLater()
            show_window()

    server.newConnection.connect(accept_connection)
    tray = QSystemTrayIcon(app_icon(), application)
    tray.setToolTip("Claviernator")
    menu = TrayMenu()
    menu.add_command("Ouvrir Claviernator", "open", show_window)
    toggle = menu.add_command("Mettre en pause" if controller.active else "Activer",
                              "pause" if controller.active else "play", controller.toggle)
    menu.addSeparator()

    def shutdown():
        window.allow_close = True
        keyboard.stop()
        controller.stop()
        tray.hide()
        server.close()
        window.close()
        application.quit()

    window.quit_requested.connect(shutdown)
    menu.add_command("Quitter Claviernator", "quit", shutdown)
    tray.setContextMenu(menu)
    keyboard.orb.customContextMenuRequested.connect(lambda point: menu.popup(keyboard.orb.mapToGlobal(point)))
    tray.activated.connect(lambda reason: show_window() if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)

    def update_tray(active):
        toggle.setText("Mettre en pause" if active else "Activer")
        toggle.setIcon(tray_icon("pause" if active else "play"))
        tray.setToolTip("Claviernator · " + ("Actif" if active else "En pause"))

    controller.state.connect(update_tray)
    window.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    if window.tray_available:
        tray.hide()
    if not args.smoke_test and (not (args.minimized or settings.start_minimized) or not window.tray_available):
        window.show()
    if args.smoke_test:
        QTimer.singleShot(900, shutdown)
    application.aboutToQuit.connect(controller.stop)
    application.aboutToQuit.connect(keyboard.stop)
    result = application.exec()
    controller.stop()
    return result

