"""Explicit packaged runtime validation; never part of normal dictation."""

import asyncio
import json
import time
import wave
from pathlib import Path

import numpy as np
import soxr

from app.core.device_detector import detect
from app.core.settings import Settings
from app.services.engine_manager import EngineManager


async def validate(engine_id, acceleration, audio_path, output):
    manager = EngineManager(detect())
    report = {"engine": engine_id, "acceleration": acceleration, "success": False}
    try:
        engine = await manager.prepare(Settings(engine=engine_id, acceleration=acceleration))
        events = []
        await engine.begin(events.append)
        with wave.open(str(audio_path), "rb") as stream:
            if stream.getsampwidth() != 2:
                raise RuntimeError("PCM16 requis.")
            audio = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32)
            audio = audio.reshape(-1, stream.getnchannels()).mean(axis=1) / 32768
            audio = soxr.resample(audio, stream.getframerate(), 16000).astype(np.float32)
        started = time.monotonic()
        for offset in range(0, len(audio), 512):
            await engine.feed(audio[offset : offset + 512])
            await asyncio.sleep(max(0, started + (offset + 512) / 16000 - time.monotonic()))
        await engine.finish()
        finals = [e for e in events if e.final]
        report.update(
            backend=engine.backend,
            final_events=len(finals),
            success=any(e.text for e in finals),
            elapsed_seconds=time.monotonic() - started,
        )
    except Exception as error:
        report["error_type"] = type(error).__name__
        if getattr(error, "winerror", None) is not None:
            report["windows_error"] = error.winerror
    finally:
        await manager.close()
        Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["success"] else 1
