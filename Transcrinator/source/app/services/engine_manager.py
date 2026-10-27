import asyncio
from functools import lru_cache
import sys
import json,time,hashlib

from app.core.settings import bundle_root, directory
from app.core.device_detector import run
from app.engines.parakeet_ultra import ParakeetUltraEngine
from app.engines.native_library import missing_cuda_libraries
from app.services.model_manager import ModelManager


def runtime_file(engine, backend):
    if engine != "parakeet":
        return None
    name = "parakeet.dll"
    for base in (bundle_root() / "runtimes", directory("runtimes")):
        root = base / engine / backend
        if root.exists():
            result = next(root.rglob(name), None)
            if result:
                return result
    return None


def probe_runtime(binary):
    command = (
        [sys.executable, "--probe-parakeet-runtime", str(binary)]
        if getattr(sys, "frozen", False)
        else [sys.executable, "-m", "app.services.runtime_probe", str(binary)]
    )
    result = run(command, timeout=15)
    return result is not None and result.returncode == 0


@lru_cache(maxsize=16)
def _guidance_runtime_available(path, modified, size):
    # A failed extension must leave the existing CUDA runtime available. Cache
    # only this cheap ABI check, keyed by the actual binary revision.
    return probe_runtime(path)


def recognition_runtime(binary, backend, hardware):
    if binary is None or backend != "cuda":
        return binary
    first_cuda = next((gpu for gpu in hardware.gpus if "cuda_capability" in gpu), {})
    if first_cuda.get("cuda_capability") != 7.5:
        return binary
    candidate = binary.with_name("parakeet-context-sm75.dll")
    try:
        info = candidate.stat()
        if candidate.is_file() and _guidance_runtime_available(str(candidate), info.st_mtime_ns, info.st_size):
            return candidate
    except OSError:
        pass
    return binary


def choose_backend(engine, acceleration, hw, probe=True):
    if engine != "parakeet":
        raise RuntimeError("Cette édition utilise uniquement Parakeet Ultra.")
    if acceleration == "cpu":
        if not runtime_file(engine, "cpu"):
            raise RuntimeError("Runtime CPU absent. Restaurez le dossier runtimes fourni avec Transcrinator.")
        return "cpu"
    if acceleration=='auto' and runtime_file(engine,'cpu'):
        try:
            cached=json.loads((directory('cache')/'backend-fallback.json').read_text())
            if time.time()-cached['time']<600 and cached['fingerprint']==backend_fingerprint(hw):return 'cpu'
        except (OSError,ValueError,KeyError,TypeError):pass
    for backend in ("cuda", "vulkan"):
        binary = runtime_file(engine, backend)
        if not binary:
            continue
        if backend == "cuda" and not any(g.get("cuda_capability", 0) >= 7.5 for g in hw.gpus):
            continue
        if backend == "vulkan" and not hw.vulkan_loader:
            continue
        if engine == "parakeet":
            if backend == "cuda" and missing_cuda_libraries(binary):
                continue
            if probe and not probe_runtime(binary):
                continue
        return backend
    if acceleration == "gpu":
        raise RuntimeError(
            "Aucun backend GPU installé et compatible. Installez CUDA/Vulkan ou choisissez CPU."
        )
    if runtime_file(engine, "cpu"):
        return "cpu"
    label = "Parakeet Ultra"
    raise RuntimeError(
        f"Aucun runtime utilisable pour {label}. Restaurez son runtime CPU "
        f"ou un backend GPU compatible. Dossier vérifié : {directory('runtimes') / engine}"
    )

def backend_fingerprint(hw):
    runtimes=[]
    for backend in ('cuda','vulkan'):
        path=runtime_file('parakeet',backend)
        if path:
            info=path.stat();runtimes.append((str(path),info.st_size,info.st_mtime_ns))
    hardware=[{key:gpu.get(key) for key in ('name','vendor','cuda_capability','vram_mb')} for gpu in hw.gpus]
    return hashlib.sha256(json.dumps([hardware,runtimes],sort_keys=True).encode()).hexdigest()


class EngineManager:
    def __init__(self, hardware):
        self.hardware = hardware
        self.active = None
        self.signature = None
        self.fallback_reason = ""

    @staticmethod
    def settings_signature(settings):
        return (
            settings.engine,
            settings.acceleration,
            settings.silence_ms,
            settings.vad_threshold,
            settings.segment_seconds,
            settings.progressive,
        )

    def is_prepared(self, settings):
        return bool(self.active and self.active.ready and self.settings_signature(settings) == self.signature)

    async def prepare(self, settings):
        signature = self.settings_signature(settings)
        if self.is_prepared(settings):
            return self.active
        await self.close()
        backend = await asyncio.to_thread(
            choose_backend, settings.engine, settings.acceleration, self.hardware
        )
        manager = ModelManager()
        if settings.engine != "parakeet":
            raise RuntimeError("Cette édition utilise uniquement Parakeet Ultra.")
        for key in ("parakeet", "silero"):
            if not manager.installed(key):
                if manager.path(key).is_file():
                    await asyncio.to_thread(manager.verify, key)
                else:
                    raise RuntimeError("Modèle absent. Restaurez le dossier models livré avec Transcrinator.")
        model = manager.path("parakeet")
        # File size and momentary free RAM/VRAM do not establish whether Windows
        # can commit the model. Attempt the real allocation; auto mode already
        # retries on CPU if accelerated loading actually fails.
        device = {"cpu": "cpu", "cuda": "CUDA0", "vulkan": "Vulkan0"}[backend]
        def create(binary, selected_device):
            return ParakeetUltraEngine(
                binary, model, selected_device,
                manager.path("silero"), settings
            )

        async def load_backend(selected_backend, selected_device):
            original = runtime_file("parakeet", selected_backend)
            binary = await asyncio.to_thread(recognition_runtime, original, selected_backend, self.hardware)
            self.active = create(binary, selected_device)
            try:
                await self.active.load()
            except Exception:
                if binary == original:
                    raise
                # An optional extension failing at model load must first retry
                # the shipped runtime on the same GPU, preserving acceleration.
                await self.close()
                self.active = create(original, selected_device)
                await self.active.load()

        self.fallback_reason = ""
        try:
            await load_backend(backend, device)
        except Exception:
            await self.close()
            if settings.acceleration != "auto" or backend == "cpu" or not runtime_file("parakeet", "cpu"):
                raise
            try:
                await load_backend("cpu", "cpu")
            except BaseException:
                await self.close()
                raise
            self.fallback_reason = "GPU indisponible au chargement : CPU actif."
            try:(directory('cache')/'backend-fallback.json').write_text(json.dumps(dict(time=time.time(),fingerprint=backend_fingerprint(self.hardware))))
            except OSError:pass
        except BaseException:
            await self.close()
            raise
        self.signature = signature
        return self.active

    async def close(self):
        active,self.active=self.active,None
        self.signature = None
        if active:
            try:await active.close()
            except (OSError,ValueError,RuntimeError):
                # A failed native worker may already have closed its handles.
                # Keep the controller usable so auto fallback/retry can proceed.
                pass
