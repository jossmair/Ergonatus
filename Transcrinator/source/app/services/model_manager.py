from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from app.core.settings import bundle_root, directory


@dataclass(frozen=True)
class Artifact:
    name: str
    url: str
    size: int
    sha256: str
    license: str


MODELS = {
    "parakeet": Artifact(
        "ultra-q8_0.gguf",
        "https://huggingface.co/mudler/parakeet-cpp-gguf/resolve/main/ultra-q8_0.gguf",
        941517728,
        "c2fb452a9df468a141012b01c8c168a25ce93f710897c7de6e353c6cc250986a",
        "CC BY 4.0 — Moondream / NVIDIA ; conversion Q8 par mudler",
    ),
    "silero": Artifact(
        "silero_vad.onnx",
        "https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx",
        2327524,
        "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3",
        "MIT — Silero Team",
    ),
}

PARAKEET_CUDA = Artifact(
    "cudart-parakeet-bin-win-cuda-x64.zip",
    "https://github.com/mudler/parakeet.cpp/releases/download/v0.6.1/cudart-parakeet-bin-win-cuda-x64.zip",
    580185113,
    "cc2b5fb99951720130e4a701e0978419d0a878e25c88bebc1416152616bd1d94",
    "NVIDIA CUDA EULA — bibliothèques redistribuables CUDA 12",
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ModelManager:
    def path(self, engine):
        supplied = bundle_root() / "models" / MODELS[engine].name
        if supplied.is_file():
            return supplied
        return directory("models") / MODELS[engine].name

    def receipt(self, engine):
        path = self.path(engine)
        if path.is_relative_to(bundle_root() / "models"):
            name = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()
            return directory("cache") / (name + ".model.json")
        return path.with_suffix(path.suffix + ".receipt.json")

    def installed(self, engine):
        if engine not in MODELS:
            return False
        path = self.path(engine)
        receipt = self.receipt(engine)
        try:
            record = json.loads(receipt.read_text())
            return (
                path.stat().st_size == MODELS[engine].size
                and record["sha256"] == MODELS[engine].sha256
                and record["mtime_ns"] == path.stat().st_mtime_ns
            )
        except (OSError, ValueError, KeyError):
            return False

    def verify(self, engine):
        path, artifact = self.path(engine), MODELS[engine]
        if not path.exists() or path.stat().st_size != artifact.size or sha256(path) != artifact.sha256:
            raise RuntimeError("Fichier modèle absent, incomplet ou corrompu.")
        record = {**asdict(artifact), "mtime_ns": path.stat().st_mtime_ns}
        self.receipt(engine).write_text(json.dumps(record), encoding="utf-8")

    def install(self, engine, progress=lambda done, total: None, cancel=None):
        artifact = MODELS[engine]
        if not self.installed(engine):
            self.download(artifact, self.path(engine), progress, cancel)
        self.verify(engine)
        if engine == "parakeet" and not self.installed("silero"):
            self.install("silero", progress, cancel)

    def remove(self, engine):
        path = self.path(engine)
        for file in (
            path,
            self.receipt(engine),
            path.with_suffix(path.suffix + ".part"),
        ):
            file.unlink(missing_ok=True)

    @staticmethod
    def download(artifact, path, progress=lambda done, total: None, cancel=None):
        """No automatic call: invoked only from an explicit Install action / CLI consent."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(path.suffix + ".part")
        offset = part.stat().st_size if part.exists() else 0
        if offset > artifact.size:
            part.unlink()
            offset = 0
        if shutil.disk_usage(path.parent).free < artifact.size - offset + 64 * 1024 * 1024:
            raise RuntimeError("Espace disque insuffisant pour le téléchargement.")
        if offset != artifact.size:
            with httpx.Client(follow_redirects=True, timeout=60, trust_env=False) as client:
                with client.stream(
                    "GET", artifact.url, headers={"Range": f"bytes={offset}-"} if offset else {}
                ) as response:
                    response.raise_for_status()
                    if offset and response.status_code == 206:
                        if not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                            raise RuntimeError("Réponse de reprise invalide.")
                    else:
                        offset = 0
                    with part.open("ab" if offset else "wb") as stream:
                        for chunk in response.iter_bytes(1024 * 1024):
                            if cancel and cancel.is_set():
                                raise RuntimeError("Téléchargement interrompu ; reprise possible.")
                            offset += len(chunk)
                            if offset > artifact.size:
                                raise RuntimeError("Taille du téléchargement incohérente.")
                            stream.write(chunk)
                            progress(offset, artifact.size)
        if part.stat().st_size != artifact.size or sha256(part) != artifact.sha256:
            part.unlink(missing_ok=True)
            raise RuntimeError("Intégrité SHA-256 invalide ; fichier refusé.")
        part.replace(path)


class RuntimeInstaller:
    def install(self, engine, backend="cpu", progress=lambda done, total: None, cancel=None):
        if backend not in ("cpu", "cuda", "vulkan") or engine != "parakeet":
            raise ValueError("Runtime non pris en charge.")
        version = "0.6.1"
        name = f"parakeet-v{version}-lib-win-{backend}-x64.zip"
        url = f"https://github.com/mudler/parakeet.cpp/releases/download/v{version}/{name}"
        with httpx.Client(follow_redirects=True, timeout=60, trust_env=False) as client:
            head = client.head(url)
            head.raise_for_status()
            size = int(head.headers["Content-Length"])
            release = client.get(f"https://api.github.com/repos/mudler/parakeet.cpp/releases/tags/v{version}")
            release.raise_for_status()
            asset = next(a for a in release.json()["assets"] if a["name"] == name)
            digest = (asset.get("digest") or "").removeprefix("sha256:")
            if len(digest) != 64:
                raise RuntimeError("Pas de SHA-256 publié pour ce runtime : installation refusée.")
        archive = directory("cache") / name
        if not archive.exists() or archive.stat().st_size != size or sha256(archive) != digest:
            ModelManager.download(
                Artifact(name, url, size, digest, "MIT"),
                archive,
                progress,
                cancel,
            )
        target = directory("runtimes") / engine / backend
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zip_file:
            for entry in zip_file.infolist():
                resolved = (target / entry.filename).resolve()
                if not resolved.is_relative_to(target.resolve()):
                    raise RuntimeError("Archive runtime invalide.")
            zip_file.extractall(target)
        if engine == "parakeet" and backend == "cuda":
            binary = next(target.rglob("parakeet.dll"))
            self.install_parakeet_cuda(binary.parent, progress, cancel)
        (target / "runtime.json").write_text(
            json.dumps({"version": version, "backend": backend, "sha256": digest}), encoding="utf-8"
        )

    def install_parakeet_cuda(self, target, progress=lambda done, total: None, cancel=None):
        """Install the runtime companion published with the pinned upstream release."""
        artifact = PARAKEET_CUDA
        archive = directory("cache") / artifact.name
        if not archive.exists() or archive.stat().st_size != artifact.size or sha256(archive) != artifact.sha256:
            ModelManager.download(artifact, archive, progress, cancel)
        with zipfile.ZipFile(archive) as bundle:
            if shutil.disk_usage(target).free < sum(info.file_size for info in bundle.infolist()):
                raise RuntimeError("Espace disque insuffisant pour décompresser les dépendances CUDA.")
            for info in bundle.infolist():
                if cancel and cancel.is_set():
                    raise RuntimeError("Installation CUDA interrompue ; reprise possible.")
                if info.is_dir():
                    continue
                relative = Path(info.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError("Archive CUDA invalide.")
                destination = target / (
                    relative.name if relative.suffix.lower() == ".dll" else Path("cuda-notices") / relative
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix(destination.suffix + ".part")
                with bundle.open(info) as source, temporary.open("wb") as output:
                    shutil.copyfileobj(source, output)
                temporary.replace(destination)
        (target / "cuda-dependencies.json").write_text(
            json.dumps({"release": "v0.6.1", "sha256": artifact.sha256}), encoding="utf-8"
        )
        license_source = (
            Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
            / "assets/licenses/NVIDIA-CUDA-EULA.txt"
        )
        notices = target / "cuda-notices"
        notices.mkdir(exist_ok=True)
        shutil.copy2(license_source, notices / license_source.name)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("engine", choices=("parakeet",))
    parser.add_argument("--backend", choices=("cpu", "cuda", "vulkan"), default="cpu")
    parser.add_argument("--accept-download", action="store_true", required=True)
    args = parser.parse_args()
    RuntimeInstaller().install(args.engine, args.backend)
    ModelManager().install(args.engine)
    print("Installation et intégrité vérifiées. Test de transcription encore nécessaire.")
