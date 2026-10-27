from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.settings import Settings
from app.engines.parakeet_ultra import ParakeetUltraEngine
from app.engines.recognition_vocabulary import NativeRecognitionVocabulary, recognition_phrases


class Function:
    def __init__(self, handler=lambda *args: 0):
        self.handler, self.calls = handler, []

    def __call__(self, *args):
        self.calls.append(args)
        return self.handler(*args)


def library(handler=lambda *args: 0):
    return SimpleNamespace(parakeet_capi_transcribe_pcm=Function(),
                           transcrinator_transcribe_guided=Function(),
                           transcrinator_context_set=Function(handler))


def test_guidance_keeps_canonical_names_and_cities_and_never_boosts_error_aliases():
    phrases = recognition_phrases([
        {"name": "Chantonnay", "category": "city"},
        {"name": "Josselin", "aliases": ["Jocelyn"], "category": "proper_name"},
        {"name": "outil", "category": "technical"},
        {"name": "Produit", "category": "product"},
    ])
    assert phrases == ("Josselin", "josselin", "Chantonnay", "chantonnay")
    assert "Jocelyn" not in phrases


def test_native_payload_is_bounded_and_cannot_inject_extra_phrases():
    phrases = recognition_phrases([
        {"name": "Nom\nIntrus", "category": "proper_name"},
        {"name": "Al", "category": "proper_name"},
        *({"name": f"Commune {i}", "category": "city"} for i in range(10000)),
    ])
    assert len(phrases) <= 768
    assert len("\n".join(phrases).encode()) <= 24000
    assert "Intrus" not in phrases and "Al" not in phrases


def test_unextended_runtime_retains_the_original_inference_function():
    original = Function()
    context = NativeRecognitionVocabulary(SimpleNamespace(parakeet_capi_transcribe_pcm=original), 1)
    assert context.configure(("Bérénice",)) == {"supported": False, "enabled": False, "phrases": 0}
    assert context.transcribe is original


def test_guidance_compiles_once_then_empty_vocabulary_restores_original_decoder():
    dll = library()
    context = NativeRecognitionVocabulary(dll, 1)
    assert context.configure(("Bérénice",))["enabled"]
    assert context.transcribe is dll.transcrinator_transcribe_guided
    context.configure(("Bérénice",))
    assert len(dll.transcrinator_context_set.calls) == 1
    assert dll.transcrinator_context_set.calls[0][1:] == ("Bérénice".encode(), 2.0, 3)
    assert not context.configure(())["enabled"]
    assert context.transcribe is dll.parakeet_capi_transcribe_pcm


def test_failed_native_compilation_clears_previous_guidance_instead_of_stale_names():
    dll = library(lambda ctx, payload, *args: int(payload == b"rejected"))
    context = NativeRecognitionVocabulary(dll, 1)
    context.configure(("Bérénice",))
    status = context.configure(("rejected",))
    assert not status["enabled"]
    assert dll.transcrinator_context_set.calls[-1][1] == b""
    assert context.transcribe is dll.parakeet_capi_transcribe_pcm


async def test_dictionary_changes_use_one_idle_control_message_without_model_reload():
    engine = ParakeetUltraEngine(None, None, "cpu", None, Settings())
    engine.vocabulary_status = {"supported": True}
    sent = []
    engine.pipe = SimpleNamespace(send=sent.append)
    engine._receive = AsyncMock(return_value={"vocabulary": {"supported": True, "enabled": True, "phrases": 2}})
    entries = [{"name": "Bérénice", "category": "proper_name"}]
    await engine.update_vocabulary(entries)
    await engine.update_vocabulary([{**entries[0], "aliases": ["Bérény"]}])
    assert sent == [{"kind": "vocabulary", "phrases": ("Bérénice", "bérénice")}]
    assert engine._receive.await_count == 1 and engine.process is None


async def test_updates_cannot_consume_a_transcription_reply_during_active_audio():
    engine = ParakeetUltraEngine(None, None, "cpu", None, Settings())
    engine.task = object()
    with pytest.raises(RuntimeError, match="après la dictée"):
        await engine.update_vocabulary([{"name": "Bérénice", "category": "proper_name"}])


async def test_failed_control_channel_closes_engine_for_clean_recovery():
    engine = ParakeetUltraEngine(None, None, "cpu", None, Settings())
    engine.vocabulary_status = {"supported": True}
    engine.pipe = SimpleNamespace(send=lambda message: None)
    engine._receive = AsyncMock(side_effect=RuntimeError("worker interrupted"))
    engine.close = AsyncMock()
    with pytest.raises(RuntimeError, match="worker interrupted"):
        await engine.update_vocabulary([{"name": "Bérénice", "category": "proper_name"}])
    engine.close.assert_awaited_once()
