"""Explicit, verified downloads; no network access during normal application use."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import time
import urllib.request

MAX_MODEL_BYTES = 2_000_000_000


@dataclass(frozen=True)
class ModelInfo:
    id: str
    repository: str
    revision: str
    filename: str
    size: int
    sha256: str
    license: str

    @property
    def url(self):
        return f"https://huggingface.co/{self.repository}/resolve/{self.revision}/{self.filename}"


CATALOG = (
    ModelInfo("luciole", "OpenLLM-France/Luciole-1B-Instruct-1.1-GGUF", "d781024544a6c4165d6fd0a5cd127e9ed1d96539",
              "Luciole-1B-Instruct-1.1-Q4_K_M.gguf", 1016226464,
              "8614c1e4c1c1fec6df12312be91f32d7231f8c1c8056fdc44c6739c19ad7c6be", "Apache-2.0"),
    ModelInfo("qwen", "Qwen/Qwen2.5-0.5B-Instruct-GGUF", "9217f5db79a29953eb74d5343926648285ec7e67",
              "qwen2.5-0.5b-instruct-q4_k_m.gguf", 491400032,
              "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db", "Apache-2.0"),
    ModelInfo("luth700", "kurakurai/Luth-LFM2-700M-GGUF", "a3ce71ba1dd188d2e84f31938280ab71774cbbb9",
              "LFM2-700M-Q4_K_M.gguf", 468625856,
              "babe3c3e926a571aae2506f27cbd8c974a58cf2a12392a91c743c5c376384cc8", "LFM Open License v1.0"),
    ModelInfo("luth17", "kurakurai/Luth-1.7B-Instruct-GGUF", "9c0491062e197f8f68654584978bc05210edeb3a",
              "Luth-1.7B-Instruct-Q8_0.gguf", 1834425984,
              "eac2cf4226524f3cc479b2e9774fc26cf6e7aac26f961f0892f824ab2f69a96f", "Apache-2.0"),
)


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_model(path: Path, *, check_hash=False, available_ram=None):
    path = Path(path)
    if not path.is_file():
        raise ValueError("Modèle absent. Ouvrez les réglages pour choisir un fichier GGUF local.")
    size = path.stat().st_size
    if not 1024 <= size < MAX_MODEL_BYTES:
        raise ValueError("Le modèle doit être un GGUF complet de moins de 2 Go.")
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:4] != b"GGUF" or struct.unpack_from("<I", header, 4)[0] not in (2, 3):
        raise ValueError("Ce fichier n’est pas un GGUF valide (version 2 ou 3 attendue).")
    known = next((m for m in CATALOG if m.filename == path.name), None)
    if known and size != known.size:
        raise ValueError("Taille incorrecte : le modèle est incomplet ou a été modifié.")
    if check_hash and known and sha256(path) != known.sha256:
        raise ValueError("Empreinte SHA-256 incorrecte. Le modèle ne sera pas chargé.")
    # Conservative preflight, not a claim about actual peak use.
    if available_ram is not None and available_ram < size + 768 * 1024**2:
        raise ValueError("RAM disponible insuffisante. Fermez des applications ou choisissez un modèle plus petit.")
    return known


def download_model(info: ModelInfo, directory: Path, *, consent: bool, progress=None):
    if consent is not True:
        raise PermissionError("Le téléchargement du modèle nécessite votre accord explicite.")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / info.filename
    if target.exists():
        validate_model(target, check_hash=True)
        return target
    temp = target.with_suffix(".part")
    total = temp.stat().st_size if temp.exists() else 0
    for attempt in range(5):
        if total == info.size:
            break
        if total > info.size:
            raise ValueError("Le fichier incomplet dépasse la taille officielle. Déplacez-le avant de réessayer.")
        headers = {"User-Agent": "Redactor-model-installer/0.1"}
        if total:
            headers["Range"] = f"bytes={total}-"
        request = urllib.request.Request(info.url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                resumed = total > 0 and response.status == 206
                if resumed and not response.headers.get("Content-Range", "").startswith(f"bytes {total}-"):
                    raise ValueError("Le serveur n’a pas confirmé le point de reprise.")
                if not resumed:
                    total = 0
                with temp.open("ab" if resumed else "wb") as output:
                    for chunk in iter(lambda: response.read(4 * 1024 * 1024), b""):
                        total += len(chunk)
                        if total > info.size or total >= MAX_MODEL_BYTES:
                            raise ValueError("Le téléchargement dépasse la taille officielle.")
                        output.write(chunk)
                        if progress:
                            progress(total, info.size)
        except (TimeoutError, ConnectionError, urllib.error.URLError):
            total = temp.stat().st_size if temp.exists() else 0
        if total < info.size:
            time.sleep(min(4, attempt + 1))
    if total != info.size or sha256(temp) != info.sha256:
        raise ValueError("Téléchargement incomplet ou empreinte incorrecte. Le fichier .part n’est pas utilisé.")
    temp.replace(target)
    receipt = {"repository": info.repository, "revision": info.revision, "filename": info.filename,
               "size": total, "sha256": info.sha256, "license": info.license, "verified": True}
    target.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return target
