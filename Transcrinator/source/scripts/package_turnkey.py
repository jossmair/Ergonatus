"""Assemble installed, verified weights and runtimes beside the executable. No download."""

import argparse
import json
import shutil
import os
from pathlib import Path
from app import __version__

from app.core.settings import directory, bundle_root
from app.services.model_manager import MODELS, ModelManager, sha256


def include_recognition_runtime(source, runtime_dir, manifest_path):
    """Bundle only the exact native binary that passed the release comparison."""
    metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not metadata.get("production_enabled") or metadata.get("filename") != "parakeet-context-sm75.dll":
        raise RuntimeError("Runtime de reconnaissance non validé pour la distribution.")
    if sha256(source) != metadata["sha256"]:
        raise RuntimeError("Le runtime de reconnaissance diffère du binaire validé.")
    library = next(runtime_dir.rglob("parakeet.dll"))
    shutil.copy2(source, library.with_name(metadata["filename"]))
    shutil.copy2(manifest_path, library.with_name("context-guidance.json"))
    shutil.copy2(manifest_path.with_name("LICENSE.parakeet"), library.with_name("LICENSE.context-guidance"))
    shutil.copy2(manifest_path.with_name("LICENSE.ggml"), library.with_name("LICENSE.ggml-context-guidance"))
    return {"backend": "cuda", "compute_capability": 7.5, "sha256": metadata["sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recognition-runtime", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / "dist" / f"Transcrinator-{__version__}"
    models = destination / "models"
    models.mkdir(exist_ok=True)
    manifest = {"version": __version__, "default_engine": "parakeet", "default_backend": "auto", "models": {}}
    manager = ModelManager()
    for engine, artifact in MODELS.items():
        source = manager.path(engine)
        if not source.is_file() or sha256(source) != artifact.sha256:
            raise RuntimeError(f"Poids réels absents ou corrompus : {engine}. Aucun téléchargement automatique.")
        target = models / artifact.name
        if not target.exists() or sha256(target) != artifact.sha256:
            shutil.copy2(source, target)
        target.with_suffix(target.suffix + ".sha256").write_text(
            f"{artifact.sha256}  {artifact.name}\n", encoding="ascii"
        )
        manifest["models"][engine] = {"file": artifact.name, "sha256": artifact.sha256,
                                      "bytes": artifact.size, "license": artifact.license}
        print(f"Modèle inclus et vérifié : {engine}", flush=True)
    for engine, backends in (("parakeet", ("cpu", "vulkan", "cuda")),):
        for backend in backends:
            source = bundle_root() / "runtimes" / engine / backend
            if not (source / "runtime.json").is_file():
                source = directory("runtimes") / engine / backend
            if not (source / "runtime.json").is_file():
                raise RuntimeError(f"Runtime manquant : {engine}/{backend}")
            shutil.copytree(source, destination / "runtimes" / engine / backend, dirs_exist_ok=True)
            if engine == "parakeet":
                omp = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/vcomp140.dll"
                if not omp.is_file():
                    raise RuntimeError("Runtime Microsoft OpenMP x64 absent sur le poste de compilation.")
                library = next((destination / "runtimes" / engine / backend).rglob("parakeet.dll"))
                shutil.copy2(omp, library.parent / "vcomp140.dll")
            print(f"Runtime inclus : {engine}/{backend}", flush=True)
    if args.recognition_runtime:
        manifest["recognition_guidance"] = include_recognition_runtime(
            args.recognition_runtime, destination / "runtimes/parakeet/cuda",
            root / "scripts/research/context_guidance/validated-runtime.json",
        )
        print("Guidage natif du dictionnaire inclus et vérifié.", flush=True)
    license_source = root / "assets/licenses"
    (models / "licences").mkdir(exist_ok=True)
    for name in ("CC-BY-4.0.txt", "SILERO-MIT.txt", "NVIDIA-CUDA-EULA.txt"):
        shutil.copy2(license_source / name, models / "licences" / name)
    (models / "licences/ATTRIBUTION.txt").write_text(
        "Parakeet Ultra : Moondream et NVIDIA (Parakeet TDT v3) — CC BY 4.0.\n"
        "Poids Ultra convertis et quantifiés en GGUF Q8 par mudler ; pas de réentraînement.\n"
        "https://huggingface.co/moondream/parakeet-ultra\n"
        "https://huggingface.co/mudler/parakeet-cpp-gguf\n"
        "https://creativecommons.org/licenses/by/4.0/\n"
        "Silero VAD : Silero Team — MIT.\n", encoding="utf-8"
    )
    (destination / "bundle.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Dossier Transcrinator prêt à utiliser, avec ses modèles et runtimes.", flush=True)


if __name__ == "__main__":
    main()
