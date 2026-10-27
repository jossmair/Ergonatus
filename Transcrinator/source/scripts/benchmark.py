"""Explicit local corpus evaluation; never logs text from normal dictation."""

import argparse
import asyncio
import json
import re
import time
import wave
from pathlib import Path

import numpy as np
import psutil
import soxr

from app.core.device_detector import detect
from app.core.settings import Settings
from app.services.engine_manager import EngineManager


def wer(reference, hypothesis):
    def tokens(text):
        return re.findall(r"\w+", text.casefold())

    a, b = tokens(reference), tokens(hypothesis)
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(current[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = current
    return row[-1] / max(1, len(a))


def make_corpus(destination):
    import win32com.client

    destination.mkdir(parents=True, exist_ok=True)
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    voices = [v for v in voice.GetVoices() if "40c" in v.GetAttribute("Language").lower()]
    if not voices:
        raise RuntimeError("Aucune voix SAPI française installée. Fournissez vos WAV français.")
    voice.Voice = voices[0]
    corpus = json.loads(Path("tests/corpus_fr.json").read_text(encoding="utf-8"))
    for item in corpus:
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Format.Type = 22  # 22.05 kHz, 16-bit mono
        stream.Open(str((destination / (item["id"] + ".wav")).resolve()), 3)
        voice.AudioOutputStream = stream
        voice.Speak(item["text"])
        stream.Close()
    (destination / "provenance.json").write_text(
        json.dumps({"source": "synthetic SAPI French", "voice": voice.Voice.GetDescription()}),
        encoding="utf-8",
    )
    return corpus


async def evaluate(args):
    manager = EngineManager(detect())
    settings = Settings(engine=args.engine, acceleration=args.acceleration)
    results = {
        "engine": args.engine,
        "acceleration": args.acceleration,
        "corpus": "synthetic SAPI French" if args.synthesize else "user supplied WAV",
        "validated": False,
        "cases": [],
    }
    corpus = (
        make_corpus(args.audio)
        if args.synthesize
        else json.loads(Path("tests/corpus_fr.json").read_text(encoding="utf-8"))
    )
    provenance = args.audio / "provenance.json"
    if provenance.exists():
        results["corpus"] = json.loads(provenance.read_text())["source"]
    try:
        started = time.monotonic()
        engine = await manager.prepare(settings)
        results["load_seconds"] = time.monotonic() - started
        results["backend"] = engine.backend
        if hasattr(engine, "readiness"):
            results["runtime_readiness"] = engine.readiness
        for case in corpus:
            with wave.open(str(args.audio / (case["id"] + ".wav")), "rb") as stream:
                rate = stream.getframerate()
                if stream.getsampwidth() != 2:
                    raise ValueError("WAV PCM16 requis")
                audio = (
                    np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32)
                    / 32768
                )
                audio = audio.reshape(-1, stream.getnchannels()).mean(axis=1)
                audio = soxr.resample(audio, rate, 16000).astype(np.float32)
            events = []
            started = time.monotonic()
            await engine.begin(events.append)
            peak_ram = psutil.Process().memory_info().rss
            for offset in range(0, len(audio), 512):
                await engine.feed(audio[offset : offset + 512])
                rss = sum(
                    p.memory_info().rss
                    for p in [psutil.Process(), *psutil.Process().children()]
                    if p.is_running()
                )
                peak_ram = max(peak_ram, rss)
                if args.realtime:
                    await asyncio.sleep(max(0, started + (offset + 512) / 16000 - time.monotonic()))
            stop_time = time.monotonic()
            await engine.finish()
            text = " ".join(e.text for e in events if e.final)
            finals = [e for e in events if e.final]
            results["cases"].append(
                {
                    "id": case["id"],
                    "wer": wer(case["text"], text),
                    "hypothesis": text,
                    "audio_seconds": len(audio) / 16000,
                    "elapsed_seconds": time.monotonic() - started,
                    "flush_seconds": time.monotonic() - stop_time,
                    "first_partial_seconds": next(
                        (e.received_at - started for e in events if not e.final), None
                    ),
                    "final_events": len(finals),
                    "peak_process_tree_ram_mb": peak_ram / 2**20,
                }
            )
        results["validated"] = all(c["hypothesis"] for c in results["cases"])
    except Exception as error:
        results["error"] = str(error)
        raise
    finally:
        await manager.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=("parakeet",), required=True)
    parser.add_argument("--acceleration", choices=("auto", "cpu", "gpu"), default="cpu")
    parser.add_argument("--audio", type=Path, default=Path("vendor/corpus"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--synthesize", action="store_true")
    parser.add_argument("--realtime", action="store_true")
    asyncio.run(evaluate(parser.parse_args()))
