"""Real Ultra inference -> controller -> disposable Windows editor; synthetic French only."""
import asyncio
import json
import multiprocessing as mp
import re
import time
from pathlib import Path

import numpy as np
import win32com.client
import win32con
import win32gui

from app.core.controller import Controller
from app.core.device_detector import detect
from app.core.focus_manager import FocusManager
from app.core.settings import Settings
from app.core.text import TextFormatter, TextLedger
from app.core.text_injector import TextInjector
from app.services.engine_manager import EngineManager
from scripts.engine_integration import load_wav
from scripts.windows_integration import activate_fixture, native_editor, text_of


def corpus():
    folder = Path("vendor/corpus-acceptance")
    folder.mkdir(exist_ok=True)
    texts = ["Bonjour.", "Oui.", "Non.", "Premier mot, je termine avec le dernier.",
             "Test pour voir si ça marche. Bien. D'accord. Non."]
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    voice.Voice = next(v for v in voice.GetVoices() if "40c" in v.GetAttribute("Language").lower())
    cases = []
    for i, text in enumerate(texts):
        path = (folder / f"edge-{i}.wav").resolve()
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Format.Type = 22
        stream.Open(str(path), 3)
        voice.AudioOutputStream = stream
        voice.Speak(text)
        stream.Close()
        audio = load_wav(path)
        active = np.flatnonzero(np.abs(audio) > .002)
        # Remove SAPI's leading/trailing silence; keep 10 ms at each speech edge.
        audio = audio[max(0, active[0]-160):min(len(audio), active[-1]+160)].copy()
        cases.append((f"edge-{i}", text, audio))
    cases.append(("pauses", "Bonjour. Oui. Non.", np.concatenate([
        cases[0][2], np.zeros(32000, np.float32), cases[1][2],
        np.zeros(32000, np.float32), cases[2][2]])))
    cases.append(("silence", "", np.zeros(48000, np.float32)))
    return cases


async def main():
    cases = corpus()
    context = mp.get_context("spawn")
    parent, child = context.Pipe()
    editor = context.Process(target=native_editor, args=(child,), daemon=True)
    editor.start()
    child.close()
    assert parent.poll(10)
    handles = parent.recv()
    hw = detect()
    manager = EngineManager(hw)
    results = []
    try:
        for acceleration in ("cpu", "gpu"):
            settings = Settings(engine="parakeet", acceleration=acceleration)
            loaded = time.monotonic()
            engine = await manager.prepare(settings)
            load_seconds = time.monotonic()-loaded
            for identity, reference, audio in cases:
                activate_fixture(handles["hwnd"])
                win32gui.PostMessage(handles["hwnd"], win32con.WM_APP+1, 1, 0)
                await asyncio.sleep(.1)
                win32gui.SendMessage(handles["edit"], win32con.WM_SETTEXT, 0, "")
                focus = FocusManager()
                focus.locate()
                controller = Controller(settings, hw)
                controller.focus, controller.injector = focus, TextInjector(focus)
                controller.ledger, controller.formatter = TextLedger(), TextFormatter(settings)
                controller.blocked, controller.last_audio = False, time.monotonic()
                await engine.begin(controller._transcript)
                started = time.monotonic()
                for offset in range(0, len(audio), 512):
                    controller.last_audio = time.monotonic()
                    await engine.feed(audio[offset:offset+512])
                    await asyncio.sleep(max(0, started+(offset+512)/16000-time.monotonic()))
                stopped = time.monotonic()
                await engine.finish()
                await controller._finish_insertion()
                flush = time.monotonic()-stopped
                await asyncio.sleep(.1)
                text = "".join(controller.ledger.confirmed)
                ref = re.findall(r"\w+", reference.casefold())
                hyp = re.findall(r"\w+", text.casefold())
                result = {"case": identity, "backend": engine.backend,
                          "load_seconds": round(load_seconds, 3),
                          "flush_seconds": round(flush, 3),
                          "first_word": not ref or bool(hyp) and hyp[0] == ref[0],
                          "last_word": not ref or bool(hyp) and hyp[-1] == ref[-1],
                          "inserted_exactly_once": text_of(handles["edit"]) == (text.rstrip(" ") + " " if text else "") and not controller.ledger.pending,
                          "not_blocked": not controller.blocked,
                          "no_punctuation_run": not re.search(r"[.,;:!?…](?:\s*[.,;:!?…]){2,}", text),
                          "silence_empty": bool(ref) or not text,
                          "hypothesis_synthetic_corpus_only": text,
                          "model_reused": await manager.prepare(settings) is engine}
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        await manager.close()
        win32gui.PostMessage(handles["hwnd"], win32con.WM_CLOSE, 0, 0)
        editor.join(3)
        if editor.is_alive():
            editor.terminate()
        parent.close()
        Path("docs/validation/parakeet-1.1.1-acceptance.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    assert len(results) == 14
    assert all(all(r[k] for k in ("first_word", "last_word", "inserted_exactly_once", "not_blocked", "no_punctuation_run", "silence_empty", "model_reused")) for r in results)


if __name__ == "__main__":
    mp.freeze_support()
    asyncio.run(main())
