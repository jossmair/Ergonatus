"""Qt controller: UI thread never loads models, generates tokens or calls UIA."""
from dataclasses import replace
from pathlib import Path
import os
import threading
import time
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon
from app.ai.engine import LlamaEngine
from app.config import Config
from app.integration.fortinator import PipeServer
from app.ui.main_window import MainWindow
from app.ui.orb import DesktopOrb
from app.ui.settings import SettingsDialog
from app.windows.hotkeys import GlobalHotkey
from app.windows.suite import position_orb
from app import theme


class EngineWorker(QObject):
    loaded = Signal(object)
    piece = Signal(str)
    finished = Signal(object)
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    @Slot(object)
    def load(self, config):
        try:
            path = config.model()
            if path is None:
                raise ValueError("Aucun modèle local. Choisissez un GGUF inférieur à 2 Go dans Réglages.")
            metrics = self.engine.load(path, config.threads, config.context)
            self.loaded.emit((path.name, metrics))
        except Exception as exc:
            self.failed.emit(readable_error(exc))

    @Slot(object)
    def generate(self, payload):
        request, tokens = payload
        try:
            pending, last = [], time.monotonic()
            for chunk in self.engine.stream(request, tokens):
                pending.append(chunk)
                if time.monotonic() - last >= .045:
                    self.piece.emit("".join(pending))
                    pending.clear()
                    last = time.monotonic()
            if pending:
                self.piece.emit("".join(pending))
            self.finished.emit(self.engine.metrics)
        except Exception as exc:
            self.failed.emit(readable_error(exc))

    @Slot()
    def shutdown(self):
        self.engine.close()
        self.stopped.emit()


def readable_error(exc):
    if isinstance(exc, (ValueError, PermissionError)):
        return str(exc)
    if isinstance(exc, MemoryError):
        return "Mémoire insuffisante. Fermez des applications ou choisissez un modèle plus petit."
    if isinstance(exc, ImportError):
        return "Une dépendance locale manque. Relancez scripts\\install.ps1 pour réparer l’environnement."
    return f"Le moteur n’a pas pu terminer ({type(exc).__name__}). Vérifiez la compatibilité du GGUF dans docs/MODELS.md."


class WindowsWorker(QObject):
    captured = Signal(object)
    selection_ready = Signal(str)
    inserted = Signal()
    failed = Signal(str)
    stopped = Signal()

    def __init__(self):
        super().__init__()
        self.bridge = None

    def service(self):
        if self.bridge is None:
            from app.windows.accessibility import Accessibility
            self.bridge = Accessibility()
        return self.bridge

    @Slot(int)
    def capture(self, expected):
        try:
            self.captured.emit(self.service().capture(expected))
        except Exception as exc:
            self.failed.emit(str(exc) if isinstance(exc, ValueError) else "L’application ne fournit pas de champ identifiable. Utilisez Copier puis un collage manuel.")

    @Slot(object)
    def selection(self, target):
        try:
            self.selection_ready.emit(self.service().selection(target))
        except Exception as exc:
            self.failed.emit(str(exc) if isinstance(exc, ValueError) else "La sélection n’est plus disponible. Choisissez à nouveau le champ.")

    @Slot(object)
    def insert(self, payload):
        try:
            self.service().insert(*payload)
            self.inserted.emit()
        except Exception as exc:
            self.failed.emit(str(exc) if isinstance(exc, ValueError) else "Windows ou l’application a refusé l’insertion. Vérifiez le champ avant de réessayer.")

    @Slot()
    def shutdown(self):
        if self.bridge:
            self.bridge.close()
        self.stopped.emit()


class Controller(QObject):
    load_engine = Signal(object)
    generate_text = Signal(object)
    capture_target = Signal(int)
    read_selection = Signal(object)
    insert_text = Signal(object)
    shutdown_engine = Signal()
    shutdown_windows = Signal()
    external_command = Signal(object)

    def __init__(self, app, minimized=False, no_model=False):
        super().__init__()
        self.app = app
        self.config, notice = Config.load()
        self.window = MainWindow(self.config)
        self.orb = DesktopOrb()
        self.orb.configure(self.config.animation, self.config.orb_color)
        self.engine = LlamaEngine()
        self.target = None
        self.source_target = None
        self.selecting = False
        self.capture_pending = False
        self.inserting = False
        self.last_request = None
        self.closing = False
        self.loading = False
        self.public_state = "paused"
        self.engine_thread = QThread(self)
        self.engine_thread.setObjectName("Redactor-inference")
        self.engine_worker = EngineWorker(self.engine)
        self.engine_worker.moveToThread(self.engine_thread)
        self.load_engine.connect(self.engine_worker.load)
        self.generate_text.connect(self.engine_worker.generate)
        self.shutdown_engine.connect(self.engine_worker.shutdown)
        self.engine_worker.loaded.connect(self.on_loaded)
        self.engine_worker.piece.connect(self.window.append_result)
        self.engine_worker.finished.connect(self.on_generated)
        self.engine_worker.failed.connect(self.on_engine_error)
        self.engine_worker.stopped.connect(self.engine_thread.quit, Qt.DirectConnection)
        self.engine_thread.finished.connect(self.engine_worker.deleteLater)
        self.engine_thread.start()
        self.windows_thread = QThread(self)
        self.windows_thread.setObjectName("Redactor-accessibility")
        self.windows_worker = WindowsWorker()
        self.windows_worker.moveToThread(self.windows_thread)
        self.capture_target.connect(self.windows_worker.capture)
        self.read_selection.connect(self.windows_worker.selection)
        self.insert_text.connect(self.windows_worker.insert)
        self.shutdown_windows.connect(self.windows_worker.shutdown)
        self.windows_worker.captured.connect(self.on_captured)
        self.windows_worker.selection_ready.connect(self.on_selection)
        self.windows_worker.inserted.connect(self.on_inserted)
        self.windows_worker.failed.connect(self.on_windows_error)
        self.windows_worker.stopped.connect(self.windows_thread.quit, Qt.DirectConnection)
        self.windows_thread.finished.connect(self.windows_worker.deleteLater)
        self.windows_thread.start()
        self.window.generate_requested.connect(self.generate)
        self.window.regenerate_requested.connect(lambda: self.generate(regenerate=True))
        self.window.new_requested.connect(self.new_chat)
        self.window.cancel_requested.connect(self.cancel)
        self.window.capture_requested.connect(self.capture_selection)
        self.window.destination_requested.connect(self.choose_destination)
        self.window.copy_requested.connect(self.copy)
        self.window.insert_requested.connect(self.insert)
        self.window.settings_requested.connect(self.settings)
        self.orb.activated.connect(self.open)
        self.orb.moved.connect(self.orb_moved)
        self.orb.context_requested.connect(self.orb_menu)
        self.hotkey = GlobalHotkey(self.open)
        app.installNativeEventFilter(self.hotkey)
        try:
            self.hotkey.configure(self.config.hotkey)
        except ValueError as exc:
            notice = str(exc)
        self.menu = QMenu()
        self.menu.addAction("Ouvrir Redactor", self.open)
        self.menu.addAction("Réglages", self.settings)
        self.menu.addAction("Replacer au-dessus de la suite", self.follow_suite)
        self.menu.addSeparator()
        self.menu.addAction("Quitter Redactor", self.quit)
        self.tray = QSystemTrayIcon(theme.app_icon(), self)
        self.tray.setToolTip("Redactor · Rédaction locale")
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(lambda reason: self.open() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.hide()
        self.orb.show()
        self.placement = QTimer(self)
        self.placement.setInterval(120)
        self.placement.timeout.connect(lambda: position_orb(self.orb, self.config))
        self.placement.start()
        position_orb(self.orb, self.config)
        self.external_slots = threading.BoundedSemaphore(8)
        self.external_command.connect(self.handle_external)
        self.ipc = PipeServer(self.queue_external, lambda: self.public_state)
        self.ipc.start()
        # The supervisor may keep its connection open for heartbeats. A second
        # authenticated pipe lets local draft clients coexist with Fortinator.
        self.draft_ipc = PipeServer(self.queue_external, lambda: self.public_state, prefix="Redactor.v1")
        self.draft_ipc.start()
        app.aboutToQuit.connect(self.cleanup)
        if notice:
            self.window.message(notice)
        if not minimized:
            self.window.show()
            area = self.window.screen().availableGeometry()
            self.window.move(area.center() - self.window.rect().center())
        self.deferred_engine=bool(minimized and os.environ.get('ERGONATUS_BACKGROUND_START')=='1' and not no_model)
        if not no_model and not self.deferred_engine:
            QTimer.singleShot(50, self.reload_engine)
        else:
            self.window.set_engine(False, "Moteur non chargé")

    def show(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()
        if getattr(self,'deferred_engine',False):
            self.deferred_engine=False;self.reload_engine()

    @Slot()
    def open(self):
        if getattr(self,'deferred_engine',False):
            self.show();return
        if self.capture_pending or self.inserting or self.closing:
            return
        import win32gui
        import win32process
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == os.getpid():
            self.show()
            return
        self.capture_pending = True
        self.window.message("Identification du champ actif…")
        self.capture_target.emit(hwnd)

    @Slot(object)
    def on_captured(self, target):
        self.capture_pending = False
        self.target = target
        if not self.selecting:
            self.source_target = target
        self.selecting = False
        self.orb.setToolTip("Redactor · Ouvrir l’assistant de rédaction")
        self.window.target_label.setText(target.caption)
        self.window.target_label.setToolTip(target.caption)
        if target.selected:
            self.window.message("Sélection disponible. « Récupérer la sélection » la charge dans Redactor sans modifier l’application.")
        elif target.writable:
            self.window.message("Décrivez votre besoin. Vous pourrez copier la réponse après relecture.")
        else:
            self.window.message("Champ mémorisé. Cet éditeur pourra nécessiter Copier puis un collage manuel.")
        self.show()

    def choose_destination(self):
        if self.window.busy or self.inserting:
            return
        self.selecting = True
        self.target = None
        self.window.target_label.setText("Destination à choisir")
        self.orb.setToolTip("Choisissez votre champ de destination, puis cliquez sur cette orbe rouge.")
        self.window.hide()
        if self.tray.supportsMessages():
            self.tray.showMessage("Redactor · Choisir la destination", "Cliquez dans le champ où écrire, puis sur l’orbe rouge. Aucun délai imposé.", QSystemTrayIcon.Information, 8000)

    def capture_selection(self):
        if self.target is None:
            self.window.message("Sélectionnez du texte dans l’application, puis cliquez sur l’orbe Redactor.")
            return
        if self.window.editor.toPlainText().strip() and not self.confirm("Remplacer le texte source ?", "Le texte actuel de Redactor sera remplacé par la sélection. L’application source ne sera pas modifiée."):
            return
        self.source_target = self.target
        self.read_selection.emit(self.target)

    @Slot(str)
    def on_selection(self, text):
        self.window.editor.setPlainText(text)
        self.window.message("Sélection récupérée. Choisissez une action puis Générez.")

    def reload_engine(self):
        if self.window.busy or self.loading or self.closing:
            return
        self.loading = True
        self.public_state = "busy"
        self.window.set_engine(False, "Chargement local…")
        self.set_state("analyzing")
        self.load_engine.emit(replace(self.config))

    @Slot(object)
    def on_loaded(self, payload):
        self.loading = False
        name, metrics = payload
        self.public_state = "ready"
        self.window.set_engine(True, "IA locale prête")
        self.window.status.setToolTip(f"{name}\nChargé en {metrics.load_seconds:.2f} s · CPU uniquement")
        self.set_state("idle")
        self.window.message("Moteur prêt · Écrivez une demande ou récupérez une sélection.")

    def generate(self, regenerate=False):
        if self.window.busy or self.loading or self.inserting:
            return
        request = self.last_request if regenerate and self.last_request else self.window.request()
        try:
            request.messages()
        except ValueError as exc:
            self.window.message(str(exc))
            return
        if regenerate and self.window.result.toPlainText().strip() and not self.confirm("Remplacer la proposition ?", "La nouvelle génération remplacera cette proposition, y compris vos modifications manuelles."):
            return
        if request.action == "reply" and self.target == self.source_target:
            self.target = None
            self.window.target_label.setText("Choisir le champ de réponse")
        self.last_request = request
        self.window.begin_turn(request, regenerate=regenerate)
        self.window.metrics.clear()
        self.window.set_busy(True)
        self.public_state = "busy"
        self.set_state("generating")
        self.window.message("Génération locale en cours · Annuler permet de l’arrêter.")
        self.engine.stop.clear()
        self.generate_text.emit((request, self.config.max_tokens))

    @Slot(object)
    def on_generated(self, metrics):
        self.window.complete_turn(cancelled=metrics.finish_reason == "cancelled")
        self.window.set_busy(False)
        self.public_state = "ready"
        self.set_state("ready")
        self.window.metrics.setText(f"{metrics.total_seconds:.1f} s · {metrics.output_tokens} tokens")
        if metrics.finish_reason == "cancelled":
            self.window.message("Génération arrêtée. Le texte partiel reste modifiable ; rien n’a été inséré.")
        elif metrics.finish_reason == "length":
            self.window.message("Limite de longueur atteinte : la fin peut être coupée. Relisez, raccourcissez la demande ou augmentez les tokens.")
        elif not self.window.result.toPlainText().strip():
            self.window.message("Le modèle n’a pas fourni de texte visible. Essayez une consigne plus courte ou un autre modèle.")
        else:
            self.window.message("Relisez, modifiez ou demandez un ajustement, puis cliquez Copier la réponse.")

    def new_chat(self):
        if self.window.busy or self.inserting: return
        if (self.window.chat_history or self.window.editor.toPlainText().strip() or self.window.result.toPlainText().strip()) and not self.confirm("Nouvelle conversation", "Effacer cet échange de Redactor ? Vos documents ne seront pas modifiés."):
            return
        self.window.reset_chat()
        self.last_request = None
        self.target = self.source_target = None
        self.window.target_label.setText("Aucun champ choisi")
        self.window.message("Nouvel échange · historique conservé en mémoire uniquement.")

    def cancel(self):
        if self.window.busy:
            self.engine.cancel()
            self.window.message("Arrêt demandé au moteur…")
        elif self.window.result.toPlainText() and self.confirm("Effacer la proposition ?", "Le résultat et vos modifications seront effacés de Redactor."):
            self.window.result.clear()
            self.window.metrics.clear()
            self.set_state("idle")

    def copy(self):
        if self.window.busy or self.inserting:
            return
        text = self.window.result.toPlainText()
        if text.strip():
            self.app.clipboard().setText(text)
            if self.app.clipboard().text() != text:
                self.window.message("La copie a échoué. Réessayez lorsque le presse-papiers est disponible.")
                return
            self.window.message("Réponse copiée. Collez-la dans votre application avec Ctrl+V ou le menu Coller.")

    def insert(self):
        if self.window.busy or self.inserting:
            return
        if self.target is None:
            self.window.message("Choisissez d’abord la destination : cliquez Destination, puis le champ de saisie, puis l’orbe.")
            return
        text = self.window.result.toPlainText()
        if not text.strip():
            return
        if not self.target.writable:
            self.window.message("Cet éditeur ne permet pas une insertion UI Automation fiable. Cliquez Copier, puis collez dans le champ choisi.")
            return
        action = "remplacer la sélection" if self.target.selected else "insérer au point mémorisé"
        preview = text[:500] + ("…" if len(text) > 500 else "")
        if not self.confirm("Valider l’insertion", f"Destination : {self.target.caption}\n\nAction : {action}.\n\n{preview}\n\nConfirmez après relecture. Aucun envoi ne sera déclenché.", "Insérer"):
            return
        self.inserting = True
        self.window.insert.setEnabled(False)
        self.window.message("Vérification de la destination et insertion…")
        self.insert_text.emit((self.target, text))

    @Slot()
    def on_inserted(self):
        self.inserting = False
        self.target = None
        self.window.target_label.setText("Insertion effectuée · cible libérée")
        self.window.refresh_actions()
        self.window.message("Texte inséré dans le champ validé. Aucun envoi effectué.")
        self.window.hide()

    @Slot(str)
    def on_windows_error(self, text):
        self.capture_pending = False
        if self.inserting:
            self.target = None
            self.window.target_label.setText("Destination à vérifier")
        self.inserting = False
        self.window.refresh_actions()
        self.window.message(text)
        self.set_state("error")
        self.show()

    @Slot(str)
    def on_engine_error(self, text):
        was_loading = self.loading
        was_generating = self.window.busy
        self.loading = False
        self.window.set_busy(False)
        if was_generating and self.last_request and not self.window.editor.toPlainText():
            self.window.editor.setPlainText(self.last_request.text)
        if self.window.chat_history and self.window.chat_history[-1][0] == "user":
            self.window.chat_history.pop()
        self.public_state = "error"
        if was_loading:
            self.window.set_engine(False, "Modèle indisponible")
        self.window.message(text)
        self.set_state("error")

    def confirm(self, title, text, accept="Confirmer"):
        box = QMessageBox(self.window)
        box.setWindowTitle(title)
        box.setTextFormat(Qt.PlainText)
        box.setText(text)
        box.setIcon(QMessageBox.Question)
        yes = box.addButton(accept, QMessageBox.AcceptRole)
        no = box.addButton("Annuler", QMessageBox.RejectRole)
        box.setDefaultButton(no)
        box.setEscapeButton(no)
        box.exec()
        return box.clickedButton() == yes

    def settings(self):
        if self.window.busy or self.loading or self.inserting:
            self.show()
            self.window.message("Arrêtez la génération ou attendez la fin du chargement avant de modifier le moteur.")
            return
        self.show()
        dialog = SettingsDialog(self.config, self.window)
        if dialog.exec() != dialog.Accepted:
            return
        previous = self.config
        self.config = dialog.config
        try:
            self.config.save()
            self.hotkey.configure(self.config.hotkey)
        except (ValueError, OSError) as exc:
            self.window.message(str(exc))
        self.window.apply_config(self.config)
        self.orb.configure(self.config.animation, self.config.orb_color)
        position_orb(self.orb, self.config)
        if (previous.model_path, previous.threads, previous.context) != (self.config.model_path, self.config.threads, self.config.context) or not self.window.engine_ready:
            self.reload_engine()

    def set_state(self, state):
        self.orb.set_state(state)
        self.window.set_state(state)

    def follow_suite(self):
        self.config.follow_suite = True
        self.save_preferences()
        position_orb(self.orb, self.config)

    def orb_moved(self):
        if self.config.follow_suite:
            from app.windows.linked_orbs import move_companions
            try:
                move_companions(self.orb)
            except (ImportError, OSError):
                position_orb(self.orb, self.config)
        self.config.orb_x, self.config.orb_y = self.orb.x(), self.orb.y()
        self.save_preferences()

    def save_preferences(self):
        try:
            self.config.save()
        except OSError:
            self.window.message("Les réglages ne peuvent pas être enregistrés. L’application reste utilisable.")

    def orb_menu(self, position):
        self.menu.popup(position)

    def queue_external(self, payload):
        if not self.external_slots.acquire(blocking=False):
            raise ValueError("File de demandes locales pleine.")
        self.external_command.emit(payload)

    @Slot(object)
    def handle_external(self, payload):
        try:
            self.apply_external(payload)
        finally:
            self.external_slots.release()

    def apply_external(self, payload):
        from app.security.validation import validate_command
        try:
            validate_command(payload)
        except ValueError:
            return
        command = payload["command"]
        if command == "cancel":
            if self.window.busy:
                self.engine.cancel()
            return
        if command == "status":
            return
        if command == "open":
            self.show()
            return
        if self.window.busy or self.inserting:
            return
        self.show()
        if (self.window.editor.toPlainText().strip() or self.window.chat_history) and not self.confirm("Demande externe", "Une application locale propose une nouvelle demande. Remplacer l’échange actuel de Redactor ?"):
            return
        self.window.reset_chat()
        self.last_request = None
        self.target = None  # External text can never reuse a previously authorised target.
        self.source_target = None
        self.window.target_label.setText("Choisir une destination locale")
        self.window.select_action(command)
        self.window.editor.setPlainText(payload.get("text", ""))
        self.window.style.setCurrentText(payload.get("style", "Naturel"))
        self.window.message("Demande externe préparée. Vérifiez-la, cliquez Générer, puis copiez la réponse après relecture.")

    def quit(self):
        if self.inserting:
            self.window.message("Attendez la confirmation de l’insertion avant de quitter.")
            return
        self.closing = True
        self.engine.cancel()
        self.window.hide()
        self.orb.hide()
        self.shutdown_engine.emit()
        self.shutdown_windows.emit()
        # Keep the event loop alive until workers release native resources.
        self.shutdown_poll = QTimer(self)
        self.shutdown_poll.timeout.connect(self.finish_quit)
        self.shutdown_poll.start(100)

    def finish_quit(self):
        if not self.engine_thread.isRunning() and not self.windows_thread.isRunning():
            self.shutdown_poll.stop()
            self.app.quit()

    def cleanup(self):
        self.placement.stop()
        self.hotkey.close()
        self.ipc.close()
        self.draft_ipc.close()
        self.tray.hide()
        self.engine.cancel()
        if self.engine_thread.isRunning():
            self.shutdown_engine.emit()
            self.engine_thread.wait(5000)
        if self.windows_thread.isRunning():
            self.shutdown_windows.emit()
            self.windows_thread.wait(3000)
