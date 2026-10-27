from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import replace

import comtypes
import numpy as np
from PySide6.QtCore import QObject, Signal

from app.core.audio_capture import AudioCapture
from app.core.focus_manager import FocusManager, TargetError
from app.core.hotkeys import trigger_spec
from app.core.state_machine import State, StateMachine
from app.core.text import TextFormatter, TextLedger
from app.core.text_options import TextPostprocessor, normalize_vocabulary
from app.core.text_injector import TextInjector
from app.services.engine_manager import EngineManager
from app.services.diagnostics import Diagnostics


class Controller(QObject):
    status = Signal(str)
    error = Signal(str)
    partial = Signal(str)
    level = Signal(float)
    backend_changed = Signal(str)
    anchor_changed = Signal(object)
    ready_changed = Signal(bool)
    retained_changed = Signal(str)
    diagnostics_changed = Signal(object)
    test_result_changed = Signal(str)

    def __init__(self, settings, hardware):
        super().__init__()
        self.settings, self.hardware = replace(settings), hardware
        self.text_processor = TextPostprocessor(settings.vocabulary, settings.number_style, settings.abbreviate_units)
        self.commands = queue.Queue(maxsize=16)
        self.stop_requested = threading.Event()
        self.shutdown = threading.Event()
        self.machine = StateMachine()
        self.diagnostic = Diagnostics()
        self.retained = []
        self.capture = None
        self.session_pending = False
        self.blocked = False
        self.thread = threading.Thread(target=self._thread, name="transcri-controller", daemon=True)

    def start(self):
        self.thread.start()

    def request(self, kind, value=None):
        if kind == "manual_input":
            # Clicking or typing can choose the eventual insertion point. Only
            # the dictation shortcut ends capture; no editor is pinned at start.
            return
        # Stop capture promptly even while the worker waits for an inference/network operation.
        if kind == "toggle" and self.machine.state == State.LISTENING:
            self.stop_requested.set()
            if self.capture:
                self.capture.request_stop()
            return
        if kind == "toggle" and self.session_pending:
            # A second press during preparation cancels this dictation instead of queuing another.
            self.stop_requested.set()
            if self.capture:
                self.capture.request_stop()
            return
        if kind == "toggle" and self.machine.state == State.PREPARING:
            return  # configuration load: dictation is enabled only after readiness
        if kind == "quit":
            self.shutdown.set()
            self.stop_requested.set()
            if self.capture:
                self.capture.request_stop()
        if kind == "toggle":
            self.session_pending = True
            self.stop_requested.clear()
        try:
            self.commands.put_nowait((kind, value))
        except queue.Full:
            if kind == "toggle":
                self.session_pending = False
            self.error.emit("Trop de commandes en attente.")

    def _thread(self):
        # UI Automation runs outside Qt's message loop and requires an MTA.
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        try:
            asyncio.run(self._run())
        except Exception as error:
            self.diagnostic.error("worker", error)
            self.error.emit(f"Service Windows indisponible ({type(error).__name__}). Redémarrez Transcrinator.")
        finally:
            # Release UI Automation proxies before uninitializing their owning COM apartment.
            self.injector = None
            if getattr(self, "focus", None):
                self.focus.target = None
                self.focus.uia = None
                self.focus = None
            comtypes.CoUninitialize()

    def _state(self, state):
        self.machine.transition(state)
        self.status.emit(state.value)

    async def _prepare(self):
        if self.manager.is_prepared(self.settings):
            return self.manager.active
        self.ready_changed.emit(False)
        self._state(State.PREPARING)
        started = time.monotonic()
        engine = await self.manager.prepare(self.settings)
        self.diagnostic.load_seconds = round(time.monotonic() - started, 3)
        self.diagnostic.backend, self.diagnostic.model = engine.backend, self.settings.engine
        self.backend_changed.emit(engine.backend)
        self.diagnostic.fallback_reason = self.manager.fallback_reason
        self.ready_changed.emit(True)
        self._state(State.IDLE)
        return engine

    async def _run(self):
        if getattr(self.hardware,'pending_detection',False):
            from app.core.device_detector import detect
            self.status.emit('Préparation de la dictée…')
            try:self.hardware=await asyncio.to_thread(detect)
            except Exception:self.hardware.pending_detection=False
        self.manager = EngineManager(self.hardware)
        try:
            self.focus = (None if self.settings.insertion_strategy in ("auto", "clipboard")
                          else FocusManager())
            self.injector = TextInjector(self.focus, self.settings.insertion_strategy)
            await self._process_commands()
        finally:
            try:
                await self.manager.close()
            finally:
                self._state(State.CLOSED)

    async def _update_recognition_vocabulary(self):
        active = getattr(getattr(self, "manager", None), "active", None)
        update = getattr(active, "update_vocabulary", None)
        if update and active.ready:
            await update(self.settings.vocabulary)

    async def _process_commands(self):
        while not self.shutdown.is_set():
            try:
                kind, value = self.commands.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.03)
                continue
            try:
                if kind == "quit":
                    break
                if kind == "configure":
                    self.settings = replace(value)
                    await self._prepare()
                    await self._update_recognition_vocabulary()
                elif kind == "load":
                    await self._prepare()
                elif kind == "text_options":
                    self.settings.vocabulary = normalize_vocabulary(value.get("vocabulary", []))
                    self.settings.number_style = value.get("number_style", "digits")
                    self.settings.abbreviate_units = value.get("abbreviate_units", self.settings.abbreviate_units)
                    self.text_processor = TextPostprocessor(self.settings.vocabulary, self.settings.number_style,
                                                            self.settings.abbreviate_units)
                    await self._update_recognition_vocabulary()
                elif kind in ("toggle", "transcription_test"):
                    if kind == "transcription_test":
                        self.stop_requested.clear()
                    self.session_pending = True
                    try:
                        if kind == "toggle":
                            await self._dictate()
                        else:
                            await self._transcription_test()
                    finally:
                        self.session_pending = False
                elif kind == "mic_test":
                    await self._microphone_test()
                elif kind == "clear_retained":
                    self.retained.clear()
                    self.retained_changed.emit("")
                elif kind == "remove_model":
                    from app.services.model_manager import ModelManager

                    await self.manager.close()
                    self.ready_changed.emit(False)
                    ModelManager().remove(value)
                    self.status.emit("Modèle supprimé — non chargé")
            except TargetError as error:
                self.diagnostic.error("target", error)
                # An unavailable insertion point does not invalidate the model.
                if self.machine.state != State.IDLE:
                    self._state(State.IDLE)
            except Exception as error:
                self.diagnostic.error(kind, error)
                if self.machine.state != State.ERROR:
                    self._state(State.ERROR)
                self.error.emit(
                    str(error)
                    if isinstance(error, RuntimeError)
                    else f"La dictée a été interrompue. Réessayez avec {trigger_spec(self.settings.trigger_key)[1]}."
                )
                self.ready_changed.emit(False)
                await self.manager.close()
            self.diagnostics_changed.emit(self.diagnostic.snapshot())

    async def _dictate(self):
        if self.machine.state not in (State.IDLE, State.ERROR):
            return
        if self.stop_requested.is_set():
            return
        self.injector.strategy = self.settings.insertion_strategy
        if self.injector.strategy not in ("auto", "clipboard") and self.focus is None:
            self.focus = FocusManager()
            self.injector.focus = self.focus
        # The destination is chosen only when the final text is ready to insert.
        self.anchor_changed.emit(None)
        engine = await self._prepare()
        if self.stop_requested.is_set() or self.shutdown.is_set():
            return
        self.ledger, self.formatter = TextLedger(), TextFormatter(self.settings)
        self.blocked = False
        self.preview_text = ""
        self.last_audio = time.monotonic()
        self.capture = AudioCapture(self.settings.microphone)
        capture_failed = False
        engine_started = finish_started = False
        try:
            self._state(State.PREPARING)
            await engine.begin(self._transcript)
            engine_started = True
            if self.stop_requested.is_set() or self.shutdown.is_set():
                finish_started = True
                await engine.finish()
                self._state(State.IDLE)
                return
            try:
                self.capture.start()
            except Exception:
                capture_failed = True
                raise
            if self.stop_requested.is_set() or self.shutdown.is_set():
                self.capture.stop()
                finish_started = True
                await engine.finish()
                self._state(State.IDLE)
                return
            self.diagnostic.microphone = str(self.settings.microphone or "par défaut")
            self._state(State.LISTENING)
            while not self.stop_requested.is_set() and not self.shutdown.is_set():
                try:
                    block = self.capture.read()
                except Exception:
                    capture_failed = True
                    raise
                if block:
                    audio, self.last_audio = block
                    self.level.emit(float(np.sqrt(np.mean(audio * audio))) if len(audio) else 0)
                    if len(audio):
                        await engine.feed(audio)
                await asyncio.sleep(0.005)
            remaining = self.capture.stop()
            self.diagnostic.microphone = "inactif"
            self.level.emit(0)
            self._state(State.FLUSHING)
            for audio, timestamp in remaining:
                if len(audio):
                    self.last_audio = timestamp
                    await engine.feed(audio)
            finish_started = True
            await engine.finish()
            self._finalize_text()
            await self._finish_insertion()
            if self.ledger.pending:
                self._retain_pending()
            self.partial.emit("")
            self._state(State.IDLE)
        except BaseException as error:
            try:
                remaining = self.capture.stop()
            except Exception as stop_error:
                self.diagnostic.error("capture_cleanup", stop_error)
                remaining = []
            if engine_started and not finish_started and (capture_failed or isinstance(error, TargetError)):
                # Recover capture failures only. Never replay audio after an engine/delivery failure.
                self.diagnostic.microphone = "inactif"
                self.level.emit(0)
                if self.machine.state == State.LISTENING:
                    self._state(State.FLUSHING)
                try:
                    for audio, timestamp in remaining:
                        if len(audio):
                            self.last_audio = timestamp
                            await engine.feed(audio)
                    await asyncio.wait_for(engine.finish(), 90)
                except Exception as recovery_error:
                    self.diagnostic.error("capture_recovery", recovery_error)
            if self.ledger.pending:
                self._finalize_text()
                self._retain_pending()
            raise
        finally:
            self.diagnostic.microphone = "inactif"
            self.level.emit(0)
            self.capture = None
            # Drop stale toggles queued during PREPARING/FLUSHING.
            keep = []
            while not self.commands.empty():
                command = self.commands.get_nowait()
                if command[0] != "toggle":
                    keep.append(command)
            for command in keep:
                self.commands.put_nowait(command)

    def _retain_pending(self):
        text = "".join(self.ledger.pending)
        if self.retained and text and not text[0].isspace() and text[0] not in ".,;:!?":
            if self.retained[-1] and not self.retained[-1][-1].isspace():
                text = " " + text
        self.retained.append(text)
        self.retained_changed.emit("".join(self.retained))

    def _finalize_text(self):
        if self.ledger.finalized:
            return
        text = self.text_processor.apply("".join(self.ledger.pending))
        self.ledger.pending[:] = [text] if text else []
        self.ledger.confirmed[:] = [text] if text else []
        self.ledger.finalized = True

    def _transcript(self, event):
        if self.ledger.finalized:
            return  # late/replayed callbacks cannot reopen a completed delivery
        if event.final:
            # Parakeet emits confirmed segments; append each identity exactly once.
            if event.identity not in self.ledger.seen:
                text = self.formatter.format(event.text)
                self.ledger.confirm(event.identity, text)
                self.diagnostic.latencies.append(round(max(0, event.received_at - self.last_audio) * 1000, 1))
            self.partial.emit("".join(self.ledger.confirmed)[-180:])
        else:
            prefix = "" if self.settings.progressive else "".join(self.ledger.confirmed)[-300:]
            self.partial.emit((prefix + " " + event.text).strip() if prefix else event.text)

    def _block_insertion(self, error):
        self.blocked = True
        self.stop_requested.set()
        if self.capture:
            self.capture.request_stop()
        self.diagnostic.error("insertion", error)
        self.error.emit(str(error))

    def _insert_pending(self, force=False):
        if self.blocked or not force:
            return
        self.target_missing = False
        while self.ledger.pending:
            pending = list(self.ledger.pending)
            text = "".join(pending)
            # Ordinary paste belongs to Windows' current focus. Field detection
            # is reserved for the explicit legacy insertion strategies.
            if self.settings.insertion_strategy not in ("auto", "clipboard"):
                try:
                    self.focus.locate()
                except TargetError:
                    self.target_missing = True
                    return
                if not self.focus.valid():
                    return
            try:
                accepted = self.injector.insert(text)
                if not accepted:
                    return
            except RuntimeError as error:
                self._block_insertion(error)
                return
            self.preview_text = ""
            for part in pending:
                self.ledger.acknowledge(part)

    async def _finish_insertion(self, timeout=2.0):
        """Send one paste, retrying only while no paste key has been delivered."""
        deadline = time.monotonic() + timeout
        while self.ledger.pending and not self.blocked and not self.shutdown.is_set():
            self._insert_pending(force=True)
            if not self.ledger.pending or self.blocked or time.monotonic() >= deadline:
                break
            await asyncio.sleep(0.02)

    async def _microphone_test(self):
        capture = AudioCapture(self.settings.microphone)
        self._state(State.PREPARING)
        capture.start()
        self._state(State.LISTENING)
        try:
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline and not self.shutdown.is_set():
                block = capture.read()
                if block:
                    audio, _ = block
                    self.level.emit(float(np.sqrt(np.mean(audio * audio))))
                await asyncio.sleep(0.02)
        finally:
            capture.stop()
            self.level.emit(0)
        self._state(State.FLUSHING)
        self._state(State.IDLE)

    async def _transcription_test(self):
        """Real microphone and active model, with private preview and no target injection."""
        engine = await self._prepare()
        if self.shutdown.is_set() or self.stop_requested.is_set():
            return
        confirmed = []
        seen = set()

        def emit(event):
            if event.final:
                if event.identity not in seen and event.text.strip():
                    seen.add(event.identity)
                    confirmed.append(event.text.strip())
                self.partial.emit("")
            else:
                self.partial.emit(event.text)

        self.capture = AudioCapture(self.settings.microphone)
        try:
            self._state(State.PREPARING)
            await engine.begin(emit)
            if self.shutdown.is_set() or self.stop_requested.is_set():
                await engine.finish()
                self._state(State.IDLE)
                return
            self.capture.start()
            if self.shutdown.is_set() or self.stop_requested.is_set():
                await engine.finish()
                self._state(State.IDLE)
                return
            self.diagnostic.microphone = "test de transcription actif"
            self._state(State.LISTENING)
            deadline = time.monotonic() + 6
            while (
                time.monotonic() < deadline
                and not self.shutdown.is_set()
                and not self.stop_requested.is_set()
            ):
                block = self.capture.read()
                if block:
                    audio, _ = block
                    self.level.emit(float(np.sqrt(np.mean(audio * audio))) if len(audio) else 0)
                    if len(audio):
                        await engine.feed(audio)
                await asyncio.sleep(0.005)
            remaining = self.capture.stop()
            self._state(State.FLUSHING)
            for audio, _ in remaining:
                if len(audio):
                    await engine.feed(audio)
            await engine.finish()
            self.test_result_changed.emit(" ".join(confirmed) or "Aucune parole reconnue pendant le test.")
            self._state(State.IDLE)
        finally:
            self.capture.stop()
            self.capture = None
            self.diagnostic.microphone = "inactif"
            self.level.emit(0)
            self.partial.emit("")

