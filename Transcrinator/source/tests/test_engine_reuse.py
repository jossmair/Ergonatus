from dataclasses import replace
from types import SimpleNamespace
import psutil

import pytest

from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.services.engine_manager import EngineManager


@pytest.mark.parametrize("backend", ["cpu", "cuda"])
async def test_actual_load_is_attempted_despite_low_free_memory_estimate(monkeypatch, tmp_path, backend):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model fixture")
    monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(available=1))
    monkeypatch.setattr("app.services.engine_manager.choose_backend", lambda *args: backend)
    monkeypatch.setattr("app.services.engine_manager.runtime_file", lambda *args: tmp_path / "runtime.dll")
    monkeypatch.setattr("app.services.engine_manager.ModelManager", lambda: SimpleNamespace(
        installed=lambda key: True, path=lambda key: model
    ))
    loaded = []

    class Engine:
        def __init__(self, dll, model, device, vad, settings):
            self.backend, self.ready = device, False

        async def load(self):
            loaded.append(self.backend)
            self.ready = True

        async def close(self):
            self.ready = False

    monkeypatch.setattr("app.services.engine_manager.ParakeetUltraEngine", Engine)
    manager = EngineManager(Hardware("test", 4, 16 * 2**30, 1, [{"free_mb": 1}]))
    engine = await manager.prepare(Settings(acceleration="auto"))
    assert loaded == ["CUDA0" if backend == "cuda" else "cpu"] and engine.ready
    await manager.close()


@pytest.mark.parametrize("acceleration", ["auto", "gpu"])
async def test_gpu_load_failure_falls_back_only_in_auto(monkeypatch, tmp_path, acceleration):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"unit test fixture only")
    monkeypatch.setattr("app.services.engine_manager.choose_backend", lambda *args: "cuda")
    monkeypatch.setattr("app.services.engine_manager.runtime_file", lambda *args: tmp_path / "runtime.dll")
    monkeypatch.setattr("app.services.engine_manager.ModelManager", lambda: SimpleNamespace(
        installed=lambda key: True, path=lambda key: model
    ))
    engines = []

    class Engine:
        def __init__(self, dll, model, backend, vad, settings):
            self.backend, self.ready = backend, False
            self.closed = False
            engines.append(self)

        async def load(self):
            if self.backend == "CUDA0":
                raise RuntimeError("GPU incompatible")
            self.ready = True

        async def close(self):
            self.closed = True

    monkeypatch.setattr("app.services.engine_manager.ParakeetUltraEngine", Engine)
    manager = EngineManager(Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    settings = Settings(acceleration=acceleration)
    if acceleration == "gpu":
        with pytest.raises(RuntimeError, match="GPU incompatible"):
            await manager.prepare(settings)
        assert manager.active is None and len(engines) == 1
    else:
        engine = await manager.prepare(settings)
        assert engine.backend == "cpu" and engines[0].closed
        assert manager.fallback_reason and manager.is_prepared(settings)
        assert await manager.prepare(settings) is engine
        assert len(engines) == 2  # no GPU retry at every dictated sentence
        assert not manager.is_prepared(replace(settings, silence_ms=600))
    await manager.close()


async def test_warm_preparation_preserves_ready_state_and_original_load_time():
    settings = Settings()
    result = Controller(settings, Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    engine = object()
    result.manager = SimpleNamespace(is_prepared=lambda value: True, active=engine)
    result.diagnostic.load_seconds = 3.4
    ready = []
    result.ready_changed.connect(ready.append)
    assert await result._prepare() is engine
    assert ready == [] and result.diagnostic.load_seconds == 3.4
