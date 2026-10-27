"""Real inference -> verified Windows field, plus pauses, silence and reuse."""

import asyncio
import json
import multiprocessing as mp
import time
import wave
from pathlib import Path

import numpy as np
import soxr
import win32con
import win32gui

from app.core.device_detector import detect
from app.core.focus_manager import FocusManager
from app.core.settings import Settings
from app.core.text import TextFormatter, TextLedger
from app.core.text_injector import TextInjector
from app.services.engine_manager import EngineManager
from scripts.windows_integration import activate_fixture, native_editor, text_of


def load_wav(path):
    with wave.open(str(path), "rb") as stream:
        audio = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32)
        audio = audio.reshape(-1, stream.getnchannels()).mean(axis=1) / 32768
        return soxr.resample(audio, stream.getframerate(), 16000).astype(np.float32)


async def evaluate():
    context = mp.get_context("spawn")
    parent, child = context.Pipe()
    editor = context.Process(target=native_editor, args=(child,), daemon=True)
    editor.start()
    child.close()
    if not parent.poll(10):
        raise RuntimeError("Éditeur indisponible.")
    handles = parent.recv()
    results = []
    manager = EngineManager(detect())
    try:
        for engine_id in ("parakeet",):
            settings = Settings(engine=engine_id, acceleration="cpu")
            engine = await manager.prepare(settings)
            reused = await manager.prepare(settings)
            result = {"engine": engine_id, "same_loaded_model_reused": reused is engine}
            activate_fixture(handles["hwnd"])
            win32gui.PostMessage(handles["hwnd"], win32con.WM_APP + 1, 1, 0)
            await asyncio.sleep(0.1)
            focus = FocusManager()
            focus.locate()
            injector = TextInjector(focus)
            ledger = TextLedger()
            formatter = TextFormatter(settings)
            seen_finals = []
            preview_updates = []

            def emit(event):
                if event.final:
                    seen_finals.append(event)
                    if event.identity not in ledger.seen and ledger.confirm(event.identity, formatter.format(event.text)):
                        while ledger.pending:
                            text = ledger.pending[0]
                            if injector.insert(text):
                                ledger.acknowledge(text)
                            else:
                                break
            win32gui.SendMessage(handles["edit"], win32con.WM_SETTEXT, 0, "")
            win32gui.SendMessage(handles["edit"], win32con.EM_SETSEL, 0, 0)
            audio = np.concatenate(
                [
                    load_wav("vendor/corpus/fr01.wav"),
                    np.zeros(24000, np.float32),
                    load_wav("vendor/corpus/fr03.wav"),
                ]
            )
            await engine.begin(emit)
            started = time.monotonic()
            for offset in range(0, len(audio), 512):
                await engine.feed(audio[offset : offset + 512])
                await asyncio.sleep(max(0, started + (offset + 512) / 16000 - time.monotonic()))
            await engine.finish()
            await asyncio.sleep(0.1)
            result["multiple_sentences_with_pause"] = len(seen_finals) >= 2
            result["provisional_updates_in_real_field"] = len(preview_updates)
            result["final_event_count"] = len(seen_finals)
            expected = "".join(part.rstrip(" ") + " " for part in ledger.inserted)
            result["unicode_insertion_matches_confirmed_text"] = text_of(handles["edit"]) == expected
            if not result["unicode_insertion_matches_confirmed_text"]:
                result["fixture_expected"] = expected
                result["fixture_actual"] = text_of(handles["edit"])
            if hasattr(engine, "readiness"):
                result["runtime_readiness"] = engine.readiness
            result["no_pending_text_after_stop"] = not ledger.pending
            silence_events = []
            await engine.begin(silence_events.append)
            for _ in range(32):
                await engine.feed(np.zeros(512, np.float32))
            await engine.finish()
            result["silence_no_text"] = not any(e.text.strip() for e in silence_events if e.final)
            results.append(result)
    finally:
        await manager.close()
        if editor.is_alive():
            win32gui.PostMessage(handles["hwnd"], win32con.WM_CLOSE, 0, 0)
            editor.join(2)
            if editor.is_alive():
                editor.terminate()
        parent.close()
        Path("docs/validation/engine-windows-integration.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )
        print(json.dumps(results))
        assert len(results) == 1
        assert all(r["unicode_insertion_matches_confirmed_text"] and r["silence_no_text"] and r["no_pending_text_after_stop"] for r in results)



if __name__ == "__main__":
    mp.freeze_support()
    asyncio.run(evaluate())
