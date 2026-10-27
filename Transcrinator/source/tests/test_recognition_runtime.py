import hashlib
import json
from types import SimpleNamespace

import pytest

from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.engines.native_library import shutdown_backend
from app.services import engine_manager as manager_module
from scripts.package_turnkey import include_recognition_runtime


def test_guidance_runtime_is_limited_to_first_cuda_device_and_probed_once(tmp_path, monkeypatch):
    original = tmp_path / "parakeet.dll"
    candidate = tmp_path / "parakeet-context-sm75.dll"
    original.write_bytes(b"stock fixture")
    candidate.write_bytes(b"guidance fixture")
    hw = Hardware("test", 4, 16, 8, [{"cuda_capability": 7.5}])
    probes = []
    monkeypatch.setattr(manager_module, "probe_runtime", lambda binary: probes.append(binary) or True)
    manager_module._guidance_runtime_available.cache_clear()
    assert manager_module.recognition_runtime(original, "cuda", hw) == candidate
    assert manager_module.recognition_runtime(original, "cuda", hw) == candidate
    assert len(probes) == 1
    hw.gpus = [{"cuda_capability": 8.6}, {"cuda_capability": 7.5}]
    assert manager_module.recognition_runtime(original, "cuda", hw) == original
    assert manager_module.recognition_runtime(original, "cpu", hw) == original
    assert len(probes) == 1
    hw.gpus = [{"cuda_capability": 7.5}]
    candidate.write_bytes(b"changed fixture with a new size")
    monkeypatch.setattr(manager_module, "probe_runtime", lambda binary: False)
    assert manager_module.recognition_runtime(original, "cuda", hw) == original


async def test_optional_guidance_failure_retries_original_gpu_before_cpu(tmp_path, monkeypatch):
    original, candidate = tmp_path / "parakeet.dll", tmp_path / "parakeet-context-sm75.dll"
    monkeypatch.setattr(manager_module, "choose_backend", lambda *args: "cuda")
    monkeypatch.setattr(manager_module, "runtime_file", lambda *args: original)
    monkeypatch.setattr(manager_module, "recognition_runtime", lambda *args: candidate)
    monkeypatch.setattr(manager_module, "ModelManager", lambda: SimpleNamespace(
        installed=lambda key: True, path=lambda key: tmp_path / key))
    engines = []

    class Engine:
        def __init__(self, dll, model, device, vad, settings):
            self.dll, self.backend, self.ready = dll, device, False
            self.closed = False
            engines.append(self)

        async def load(self):
            if self.dll == candidate:
                raise RuntimeError("optional extension unavailable")
            self.ready = True

        async def close(self):
            self.ready, self.closed = False, True

    monkeypatch.setattr(manager_module, "ParakeetUltraEngine", Engine)
    manager = manager_module.EngineManager(Hardware("test", 4, 16, 8))
    settings = Settings(acceleration="gpu")
    engine = await manager.prepare(settings)
    assert [(entry.dll, entry.backend) for entry in engines] == [(candidate, "CUDA0"), (original, "CUDA0")]
    assert engines[0].closed and engine.ready
    assert await manager.prepare(settings) is engine and len(engines) == 2
    assert not manager.fallback_reason
    await manager.close()


def test_backend_shutdown_uses_only_explicit_optional_c_extension():
    shutdown_backend(None)
    shutdown_backend(SimpleNamespace())

    class Function:
        called = False

        def __call__(self):
            self.called = True

    function = Function()
    shutdown_backend(SimpleNamespace(transcrinator_shutdown_backend=function))
    assert function.called and function.argtypes == [] and function.restype is None


def test_packaging_rejects_a_native_binary_that_was_not_validated(tmp_path):
    source = tmp_path / "candidate.dll"
    source.write_bytes(b"native test fixture")
    runtime = tmp_path / "runtime/release"
    runtime.mkdir(parents=True)
    original = runtime / "parakeet.dll"
    original.write_bytes(b"original runtime fixture")
    manifest = tmp_path / "validated-runtime.json"
    metadata = {"production_enabled": True, "filename": "parakeet-context-sm75.dll", "sha256": "0" * 64}
    manifest.write_text(json.dumps(metadata))
    with pytest.raises(RuntimeError, match="diffère"):
        include_recognition_runtime(source, runtime, manifest)
    assert not original.with_name(metadata["filename"]).exists()
    metadata["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(metadata))
    (tmp_path / "LICENSE.parakeet").write_text("license fixture")
    (tmp_path / "LICENSE.ggml").write_text("ggml license fixture")
    include_recognition_runtime(source, runtime, manifest)
    assert original.read_bytes() == b"original runtime fixture"
    assert original.with_name(metadata["filename"]).read_bytes() == source.read_bytes()
