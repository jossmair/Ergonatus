import asyncio
import multiprocessing as mp
import time
import re

from app.core.vad import Segmenter, SileroVAD
from app.engines.base import Engine, Transcript
from app.engines.parakeet_worker import worker
from app.engines.recognition_vocabulary import recognition_phrases


def sanitize_transcript(text):
    """Clean decoder punctuation without removing spoken words or repetitions."""
    if not any(c.isalnum() for c in text):
        return ""
    def punctuation(match):
        marks = re.sub(r"\s", "", match.group())
        if marks in ("?!", "!?"):
            return marks
        if "." in marks or "…" in marks:
            return "."
        return marks[0]
    text = re.sub(r"[.,;:!?…](?:[ \t]*[.,;:!?…])+", punctuation, text)
    # Sentence boundaries glued by the decoder; preserve decimals, URLs and U.S.A.
    text = re.sub(r"([^\W\d_]{2,}[.!?])(?=[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ])", r"\1 ", text)
    return text.strip()


class ParakeetUltraEngine(Engine):
    def __init__(self, dll, model, backend, vad, settings):
        self.dll, self.model, self.backend, self.vad, self.settings = dll, model, backend, vad, settings
        self.process = None
        self.task = None
        self.vocabulary_status = {"supported": False, "enabled": False, "phrases": 0}
        self._vocabulary_phrases = None

    async def _receive(self, timeout):
        if not await asyncio.to_thread(self.pipe.poll, timeout):
            raise RuntimeError("Parakeet ne répond plus. Délai dépassé.")
        try:
            result = self.pipe.recv()
        except (EOFError, OSError):
            raise RuntimeError("Le processus Parakeet s’est interrompu.") from None
        if "error" in result:
            error = RuntimeError(result["error"])
            error.winerror = result.get("winerror")
            raise error
        return result

    async def load(self):
        context = mp.get_context("spawn")
        self.pipe, child = context.Pipe()
        phrases = recognition_phrases(self.settings.vocabulary)
        self.process = context.Process(
            target=worker, args=(child, str(self.dll), str(self.model), self.backend, phrases), daemon=True
        )
        self.process.start()
        child.close()
        result = await self._receive(120)
        self.backend = result["backend"]
        self.vocabulary_status = result.get("vocabulary", self.vocabulary_status)
        self._vocabulary_phrases = phrases
        self.detector = SileroVAD(self.vad)
        self.ready = True

    async def update_vocabulary(self, entries):
        phrases = recognition_phrases(entries)
        if phrases == self._vocabulary_phrases:
            return
        if self.task is not None:
            raise RuntimeError("Le dictionnaire sera mis à jour après la dictée.")
        if not self.vocabulary_status["supported"]:
            self._vocabulary_phrases = phrases
            return
        try:
            await asyncio.to_thread(self.pipe.send, {"kind": "vocabulary", "phrases": phrases})
            result = await self._receive(30)
            self.vocabulary_status = result["vocabulary"]
            self._vocabulary_phrases = phrases
        except (OSError, RuntimeError, KeyError):
            await self.close()
            raise

    async def begin(self, emit):
        self.emit, self.sequence = emit, 0
        self.rejected_artifacts = 0
        self.detector.reset()
        self.segmenter = Segmenter(
            self.detector,
            self.settings.vad_threshold,
            self.settings.silence_ms,
            self.settings.segment_seconds,
            # Automatic dictation keeps internal breathing pauses in context.
            # Only the stop command or the bounded 30 s window finalizes it.
            end_on_silence=self.settings.progressive,
        )
        self.segments = asyncio.Queue(maxsize=8)
        self.task = asyncio.create_task(self._transcribe())

    async def _transcribe(self):
        while True:
            segment = await self.segments.get()
            if segment is None:
                return
            await asyncio.to_thread(self.pipe.send, segment)
            result = await self._receive(60)
            self.sequence += 1
            text = sanitize_transcript(result["text"])
            if text:
                self.emit(Transcript(f"segment-{self.sequence}", text, True, time.monotonic()))
            elif result["text"].strip():
                self.rejected_artifacts += 1

    async def _queue(self, segments):
        if self.task.done():
            await self.task
            raise RuntimeError("Session Parakeet interrompue.")
        for segment in segments:
            try:
                self.segments.put_nowait(segment)
            except asyncio.QueueFull:
                raise RuntimeError(
                    "Parakeet est trop lent pour cette configuration. Dictée arrêtée."
                ) from None

    async def feed(self, audio):
        await self._queue(self.segmenter.feed(audio))

    async def finish(self):
        await self._queue(self.segmenter.flush())
        await asyncio.wait_for(self.segments.put(None), 60)
        await asyncio.wait_for(self.task, 90)
        self.task = None

    async def close(self):
        self.ready = False
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None
        if self.process:
            if self.process.is_alive():
                try:
                    self.pipe.send(None)
                except (OSError, BrokenPipeError):
                    pass
                await asyncio.to_thread(self.process.join, 2)
                if self.process.is_alive():
                    self.process.terminate()
                    await asyncio.to_thread(self.process.join, 3)
            self.pipe.close()
            self.process.close()
            self.process = None
