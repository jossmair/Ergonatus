import argparse
import hashlib
import json
import multiprocessing
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLockFile, QPoint, QTimer, QTranslator, Qt
from PySide6.QtGui import QContextMenuEvent, QIcon, QCursor, QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from app.core.controller import Controller
from app.core.device_detector import detect
from app.core.hotkeys import GlobalHotkey, trigger_spec
from app import __version__
from app.core.settings import Settings, data_root, directory
from app.core import autostart
from app.ui.floating_hub import FloatingHub, bottom_center
from app.ui.main_window import MainWindow
from app.ui.premium import STYLE
from app.ui.retained_action import RetainedTextAction
from app.ui.tray_menu import TrayMenu, menu_icon


def asset(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets" / name


def main():
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimized", action="store_true")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--quit-running", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--validate-engine", choices=("parakeet",))
    parser.add_argument("--acceleration", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument("--test-audio", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--probe-parakeet-runtime", type=Path)
    parser.add_argument("--ui-snapshot", type=Path)
    parser.add_argument("--check-text-options", type=Path)
    parser.add_argument("--check-insertion", type=Path)
    parser.add_argument("--insertion-delay-ms", type=int, default=0)
    args = parser.parse_args()
    if args.check_insertion:
        from app.services.insertion_validation import validate
        return validate(args.check_insertion, max(0, min(args.insertion_delay_ms, 5000)))
    if args.check_text_options:
        from app.services.text_options_probe import probe
        return probe(args.check_text_options)
    if args.probe_parakeet_runtime:
        from app.services.runtime_probe import probe

        return probe(args.probe_parakeet_runtime)
    if args.validate_engine:
        if not args.test_audio or not args.report:
            parser.error("--test-audio et --report requis")
        import asyncio
        from app.services.validation import validate

        return asyncio.run(validate(args.validate_engine, args.acceleration, args.test_audio, args.report))
    application = QApplication(sys.argv)
    # Shared Ergonatus surfaces; the original standalone projects are untouched.
    import runpy as _suite_runpy
    from pathlib import Path as _suite_path
    for _suite_root in (*_suite_path(__file__).resolve().parents,*_suite_path(sys.executable).resolve().parents):
        if (_suite_root/"suite_design.py").is_file() and (_suite_root/"Hub").is_dir():
            _suite_runpy.run_path(str(_suite_root/"suite_design.py"))["install"](application)
            break
    application.setApplicationName("Transcrinator")
    application.setApplicationVersion(__version__)
    application.setOrganizationName("Transcrinator")
    translator = QTranslator(application)
    translation = asset("qtbase_fr.qm")
    if not translation.exists():
        translation = Path(QLibraryInfo.path(QLibraryInfo.TranslationsPath)) / "qtbase_fr.qm"
    if translator.load(str(translation)):
        application.installTranslator(translator)
    application.setQuitOnLastWindowClosed(False)
    server_name = "Transcri-" + hashlib.sha256(str(data_root().resolve()).lower().encode()).hexdigest()[:24]

    def send_command(command):
        connection = QLocalSocket()
        connection.connectToServer(server_name)
        if not connection.waitForConnected(500):
            return False
        connection.write(command.encode())
        connection.waitForBytesWritten(500)
        connection.disconnectFromServer()
        return True

    if args.quit_running:
        return 0 if send_command("quit") else 1
    lock = QLockFile(str(directory("cache") / "application.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        send_command("show")
        return 0
    # Accept commands before hardware detection/model preparation: a second launch
    # can arrive as soon as the session lock exists. Qt drains it once UI is ready.
    server = QLocalServer(application)
    server.setSocketOptions(QLocalServer.UserAccessOption)
    QLocalServer.removeServer(server_name)
    if not server.listen(server_name):
        lock.unlock()
        return 1
    application.setStyle("Fusion")
    application.setStyleSheet(STYLE)
    settings = Settings.load()
    first_launch = settings.configure_automatic()
    if not (args.smoke_test or args.ui_snapshot):
        try:
            settings.autostart = autostart.is_enabled()
            settings.save()
        except OSError:
            pass
    # The shell must appear before GPU/system subprocesses finish probing.
    hardware = detect(quick=True)
    controller = Controller(settings, hardware)
    hub = FloatingHub(settings)
    window = MainWindow(controller)

    def show_window():
        window.showNormal()
        window.raise_()
        window.activateWindow()
    icon = QIcon(str(asset("transcri.svg")))
    application.setWindowIcon(icon)
    tray = QSystemTrayIcon(icon, application)
    tray.setToolTip(f"Transcrinator — {trigger_spec(settings.trigger_key)[1]} pour dicter")
    menu = TrayMenu()
    menu.add_command("Ouvrir Transcrinator", "open", show_window)
    menu.add_command("Afficher le hub", "hub", hub.reveal)
    retained_action = RetainedTextAction(controller, menu)
    retained_action.setIcon(menu_icon("copy"))
    retained_action.setIconVisibleInMenu(True)
    menu.addAction(retained_action)
    menu.addSeparator()
    quitting = False

    def quit_app():
        nonlocal quitting
        if quitting:
            return
        quitting = True
        hub.hide()
        window.hide()
        hotkey.stop()
        controller.request("quit")

        # Keep event loop responsive while capture, finalization and runtimes close.
        def poll():
            if not controller.thread.is_alive():
                server.close()
                tray.hide()
                lock.unlock()
                application.quit()
            else:
                QTimer.singleShot(100, poll)

        poll()

    menu.add_command("Quitter Transcrinator", "quit", quit_app)
    tray.setContextMenu(menu)
    hub.setContextMenuPolicy(Qt.CustomContextMenu)
    hub.customContextMenuRequested.connect(lambda position: menu.popup(hub.mapToGlobal(position)))
    tray.activated.connect(lambda reason: show_window() if reason == QSystemTrayIcon.DoubleClick else None)
    tray.hide()
    hub.open_requested.connect(show_window)
    controller.status.connect(hub.set_state)
    controller.level.connect(hub.set_level)
    controller.partial.connect(hub.set_partial)
    controller.anchor_changed.connect(hub.place)

    def report_error(message):
        window.show_error(message)

    controller.error.connect(report_error)
    hotkey = GlobalHotkey(lambda: controller.request("toggle"), settings.hotkey == "double",
                          trigger_key=settings.trigger_key)

    def change_trigger(identity):
        hotkey.set_trigger(identity)
        settings.trigger_key = identity
        controller.settings.trigger_key = identity
        tray.setToolTip(f"Transcrinator — {trigger_spec(identity)[1]} pour dicter")

    window.trigger_changed.connect(change_trigger)
    snapshot_saved = False

    def snapshot_when_ready(ready):
        nonlocal snapshot_saved
        if ready and args.ui_snapshot and not snapshot_saved:
            snapshot_saved = True

            def capture():
                nonlocal snapshot_saved
                args.ui_snapshot.parent.mkdir(parents=True, exist_ok=True)
                main_saved = window.grab().save(str(args.ui_snapshot))
                window.preferences_panel.grab().save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-options.png")))
                window.trigger_key.showPopup()
                popup = window.trigger_key.popup
                menu_picture = popup.grab()
                menu_saved = menu_picture.save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-keys.png")))
                menu_transparent = menu_picture.toImage().pixelColor(0, 0).alpha() == 0
                menu_compact = popup.width() == 322 and popup.height() < 270 and len(popup.buttons) == 16
                window.trigger_key.hidePopup()
                application.sendEvent(hub, QContextMenuEvent(
                    QContextMenuEvent.Mouse, QPoint(18, 18), hub.mapToGlobal(QPoint(18, 18))))
                application.processEvents()
                orb_menu_shared = tray.contextMenu() is menu and menu.isVisible()
                menu.grab().save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-tray-menu.png")))
                menu.close()
                hub_saved = hub.grab().save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-hub.png")))
                normal_position = [hub.x(), hub.y()]
                screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
                area = screen.availableGeometry()
                hub_state = hub.state
                ready_compacted = hub.compacted and hub.width() == hub.height() == 36
                hub.last_active -= 21
                hub.animate()
                compact_saved = hub.grab().save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-halo.png")))
                compact_position = [hub.x(), hub.y()]
                compact_size = [hub.width(), hub.height()]
                compact_frame = hub.grab().toImage()
                hub.phase += .9
                hub.animate()
                compact_animated = compact_frame != hub.grab().toImage()
                hub.set_state("Préparation…")
                restored = (not hub.compacted and hub.width() == 172 and hub.height() == 44
                            and hub.pos() == bottom_center(hub.size(), area))
                hub.unfold_started -= .14
                hub.activation_started -= .14
                activation_saved = hub.grab().save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-activation.png")))
                hub.unfold_started -= 1
                hub.set_state("Écoute…")
                hub.activation_started -= 1
                hub.set_level(.03)
                for _ in range(20):
                    hub.animate()
                speech_saved = hub.grab().save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-speech.png")))
                hub.set_state("Traitement…")
                hub.activation_started -= 1
                hub.phase = .75
                processing_frame = hub.grab().toImage()
                processing_saved = processing_frame.save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-processing.png")))
                hub.phase = 1.3
                density = processing_frame.devicePixelRatio()
                region = (int(50 * density), int(12 * density), int(100 * density), int(18 * density))
                processing_animated = processing_frame.copy(*region) != hub.grab().toImage().copy(*region)
                processing_quiet = hub.level == 0 and hub.display_level == 0
                from app.ui.vocabulary_dialog import VocabularyDialog
                dictionary = VocabularyDialog([], window)
                dictionary.show()
                application.processEvents()
                dictionary_saved = dictionary.grab().save(str(args.ui_snapshot.with_name(args.ui_snapshot.stem + "-dictionary.png")))
                dictionary.table.item(0, 0).setText("Modification de validation")
                dictionary.close_button.click()
                dictionary_closed_without_saving = not dictionary.isVisible() and dictionary.entries == []
                dictionary.deleteLater()
                snapshot_saved = main_saved and hub_saved and hub.isVisible()
                args.ui_snapshot.with_name(args.ui_snapshot.stem + "-ui.json").write_text(
                    json.dumps({"hub_visible": hub.isVisible(), "hub_state": hub_state,
                                "orb_uses_tray_context_menu": orb_menu_shared,
                                "window_translucent": window.testAttribute(Qt.WA_TranslucentBackground),
                                "normal_position": normal_position, "compact_position": compact_position,
                                "ready_compacted_immediately": ready_compacted and hub_state == "Prêt",
                                "compact_size": compact_size, "compact_saved": compact_saved,
                                "compact_animated": compact_animated,
                                "activation_saved": activation_saved, "speech_saved": speech_saved,
                                "units_option_checked": window.units.isChecked(),
                                "number_toggle_checked": window.number_style.isChecked(),
                                "main_window_size": [window.width(), window.height()],
                                "application_name": application.applicationName(),
                                "options_fully_visible": window.preferences_panel.visibleRegion().boundingRect() == window.preferences_panel.rect(),
                                "trigger_menu_saved": menu_saved,
                                "trigger_menu_transparent": menu_transparent,
                                "trigger_menu_compact": menu_compact,
                                "caption_icons": len(window.caption_buttons) == 2 and all(not button.text() for button in window.caption_buttons),
                                "dictionary_saved": dictionary_saved,
                                "dictionary_closed_without_saving": dictionary_closed_without_saving,
                                "processing_saved": processing_saved,
                                "processing_animated": processing_animated,
                                "processing_without_microphone_energy": processing_quiet,
                                "startup_option_checked": window.startup.isChecked(),
                                "trigger_key": window.trigger_key.currentData(),
                                "transcript_panel_absent": not hasattr(window, "recovery"),
                                "restored_on_preparation": restored,
                                "screen": [area.x(), area.y(), area.width(), area.height()]}),
                    encoding="utf-8",
                )
                quit_app()

            QTimer.singleShot(260, capture)

    controller.ready_changed.connect(snapshot_when_ready)

    def receive_command():
        connection = server.nextPendingConnection()
        received = bytearray()

        def read():
            received.extend(bytes(connection.readAll()))
            if bytes(received) == b"quit":
                quit_app()
            elif bytes(received) == b"show":
                show_window()
        connection.readyRead.connect(read)
        connection.disconnected.connect(connection.deleteLater)
        if connection.bytesAvailable():
            read()

    server.newConnection.connect(receive_command)
    controller.start()
    try:
        if not (args.smoke_test or args.ui_snapshot):
            hotkey.start()
    except RuntimeError as error:
        report_error(str(error))
    if args.ui_snapshot:
        window.show()
        QTimer.singleShot(45000, quit_app)
    elif args.smoke_test:
        QTimer.singleShot(1800, quit_app)
    elif args.show or first_launch or not (args.minimized or settings.start_minimized):
        window.show()
    controller.request("load")
    code = application.exec()
    return (0 if snapshot_saved else 1) if args.ui_snapshot else code


if __name__ == "__main__":
    sys.exit(main())
