"""Exercise the full dictation controller with synthetic audio and a disposable editor."""
import asyncio
import json
import multiprocessing as mp
import queue
import threading
import time
from pathlib import Path
from app import __version__

import win32con
import win32gui
import comtypes

import app.core.controller as controller_module
from app.core.controller import Controller
from app.core.device_detector import detect
from app.core.focus_manager import FocusManager
from app.core.settings import Settings
from app.core.state_machine import State
from app.core.text_injector import TextInjector
from app.services.engine_manager import EngineManager
from scripts.engine_integration import load_wav
from scripts.windows_integration import activate_fixture, native_editor, text_of


async def main():
    audio = load_wav(Path("vendor/corpus/fr03.wav"))
    context = mp.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(target=native_editor, args=(child,), daemon=True)
    process.start()
    child.close()
    handles = None
    hardware = detect()
    manager = EngineManager(hardware)
    reports = []
    original_capture = controller_module.AudioCapture
    try:
        assert parent.poll(10)
        handles = parent.recv()
        for progressive in (True, False):
            settings = Settings(acceleration="auto", progressive=progressive)
            controller = Controller(settings, hardware)
            controller.manager = manager
            engine = await controller._prepare()
            controller.focus = FocusManager()
            controller.injector = TextInjector(controller.focus)
            interrupted = []
            valid = controller.focus.valid

            def check_focus():
                result = valid()
                if not result and controller.focus.target and not interrupted:
                    target = controller.focus.target
                    focused = controller.focus.uia.GetFocusedElement()
                    interrupted.append({
                        "foreground_matches": win32gui.GetForegroundWindow() == target.hwnd,
                        "focused_process_matches": focused.CurrentProcessId == target.pid,
                        "focused_control_type": focused.CurrentControlType,
                        "target_offscreen": bool(target.element.CurrentIsOffscreen),
                    })
                return result

            controller.focus.valid = check_focus
            activate_fixture(handles["hwnd"])
            win32gui.PostMessage(handles["hwnd"], win32con.WM_APP + 1, 1, 0)
            await asyncio.sleep(0.1)
            win32gui.SendMessage(handles["edit"], win32con.WM_SETTEXT, 0, "")

            class FileCapture:
                def __init__(self, device):
                    self.offset = 0

                def start(self):
                    self.started = time.monotonic()

                def read(self):
                    if self.offset >= len(audio):
                        controller.stop_requested.set()
                        return None
                    if time.monotonic() - self.started < self.offset / 16000:
                        return None
                    block = audio[self.offset:self.offset + 512]
                    self.offset += len(block)
                    return block, time.monotonic()

                def request_stop(self):
                    controller.stop_requested.set()

                def stop(self):
                    remaining = audio[self.offset:]
                    self.offset = len(audio)
                    return [(remaining, time.monotonic())] if len(remaining) else []

            controller_module.AudioCapture = FileCapture
            started = time.monotonic()
            await controller._dictate()
            text = "".join(controller.ledger.confirmed)
            report = {
                "progressive": progressive,
                "com_apartment": "MTA",
                "backend": engine.backend,
                "audio_seconds": round(len(audio) / 16000, 3),
                "session_seconds": round(time.monotonic() - started, 3),
                "inserted_exactly_once": text_of(handles["edit"]) == text.rstrip(" ") + " " and bool(text),
                "no_pending_or_retained": not controller.ledger.pending and not controller.retained,
                "microphone_closed": controller.capture is None,
                "ready_again": controller.machine.state == State.IDLE,
                "model_reused": manager.active is engine and manager.is_prepared(settings),
                "focus_interruptions": interrupted,
            }
            reports.append(report)
            print(json.dumps(report), flush=True)
    finally:
        controller_module.AudioCapture = original_capture
        await manager.close()
        if handles:
            win32gui.PostMessage(handles["hwnd"], win32con.WM_CLOSE, 0, 0)
        process.join(3)
        if process.is_alive():
            process.terminate()
        parent.close()
        Path(f"docs/validation/controller-{__version__}.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    assert len(reports) == 2 and all(all(r[k] for k in (
        "inserted_exactly_once", "no_pending_or_retained", "microphone_closed", "ready_again", "model_reused"
    )) for r in reports)


if __name__ == "__main__":
    mp.freeze_support()
    errors = queue.Queue()

    def run():
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        try:
            asyncio.run(main())
        except BaseException as error:
            errors.put(error)
        finally:
            comtypes.CoUninitialize()

    thread = threading.Thread(target=run, name="validation-uia-mta")
    thread.start()
    thread.join()
    if not errors.empty():
        raise errors.get()
