"""Native Windows entry point. No networking or model download on startup."""
import argparse
import os
from pathlib import Path
import sys


def main():
    if sys.platform != "win32":
        raise SystemExit("Redactor nécessite Windows 10 ou Windows 11.")
    parser = argparse.ArgumentParser(description="REDACTOR · Assistant de rédaction local")
    parser.add_argument("--minimized", action="store_true", help="Démarrer dans l’orbe")
    parser.add_argument("--show", action="store_true", help="Ouvrir l’instance existante")
    parser.add_argument("--no-model", action="store_true", help="Ouvrir les réglages sans charger de modèle")
    parser.add_argument("--link-suite", action="store_true", help="Lier les orbes de la suite")
    args = parser.parse_args()
    from PySide6.QtCore import QTimer
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication
    from app.integration.fortinator import user_identity
    from app import theme
    import win32api
    import win32event
    app = QApplication(sys.argv[:1])
    # Shared Ergonatus surfaces; the original standalone projects are untouched.
    import runpy as _suite_runpy
    from pathlib import Path as _suite_path
    for _suite_root in (*_suite_path(__file__).resolve().parents,*_suite_path(sys.executable).resolve().parents):
        if (_suite_root/"suite_design.py").is_file() and (_suite_root/"Hub").is_dir():
            _suite_runpy.run_path(str(_suite_root/"suite_design.py"))["install"](app)
            break
    app.setApplicationName("Redactor")
    app.setOrganizationName("Suite Fortinator")
    app.setQuitOnLastWindowClosed(False)
    theme.configure_app(app)
    server_name = "Redactor.Instance.v1." + user_identity()[1]
    # An isolated namespace is used only by disposable package verification.
    test_instance = os.environ.get("REDACTOR_TEST_INSTANCE", "")
    if test_instance:
        import re
        if not re.fullmatch(r"qa-[a-z0-9-]{1,24}", test_instance):
            raise SystemExit("Identifiant de test invalide.")
        server_name += "." + test_instance
    mutex = win32event.CreateMutex(None, False, "Local\\" + server_name)
    if win32api.GetLastError() == 183:
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if socket.waitForConnected(1500):
            socket.write(b"link" if args.link_suite else b"open")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        mutex.Close()
        return 0
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.UserAccessOption)
    if not server.listen(server_name):
        mutex.Close()
        raise SystemExit("L’instance locale ne peut pas être créée.")
    from app.controller import Controller
    controller = Controller(app, minimized=args.minimized, no_model=args.no_model)
    if args.link_suite:
        controller.follow_suite()
    connections = set()
    def accept():
        socket = server.nextPendingConnection()
        connections.add(socket)
        def read():
            if socket.bytesAvailable() > 16:
                socket.abort()
                return
            command = bytes(socket.readAll())
            if command == b"link":
                controller.follow_suite()
            elif command == b"open":
                controller.show()
            socket.disconnectFromServer()
        socket.readyRead.connect(read)
        socket.disconnected.connect(lambda: (connections.discard(socket), socket.deleteLater()))
        QTimer.singleShot(1500, socket.abort)
        if socket.bytesAvailable():
            read()
    server.newConnection.connect(accept)
    try:
        return app.exec()
    finally:
        server.close()
        mutex.Close()


if __name__ == "__main__":
    sys.exit(main())
