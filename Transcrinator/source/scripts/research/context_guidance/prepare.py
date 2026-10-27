"""Rebuild the isolated experiment from pinned public sources; never install it."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

import httpx


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=ROOT / "build/context-guidance-rebuilt-source")
    args = parser.parse_args()
    manifest = json.loads((HERE / "source-manifest.json").read_text(encoding="utf-8"))
    target = args.target.resolve()
    if not target.is_relative_to((ROOT / "build").resolve()):
        raise RuntimeError("The experiment must stay inside the project build directory")
    if target.exists() and any(target.iterdir()):
        raise RuntimeError(f"Refusing to overwrite an existing experiment: {target}")
    target.mkdir(parents=True, exist_ok=True)
    cache = ROOT / "vendor/downloads"
    cache.mkdir(parents=True, exist_ok=True)
    for component in ("parakeet", "ggml"):
        expected = manifest[component]
        archive = cache / f"context-guidance-{expected['sha256']}.zip"
        if not archive.exists():
            response = httpx.get(expected["url"], follow_redirects=True, timeout=90)
            response.raise_for_status()
            archive.write_bytes(response.content)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected["sha256"]:
            raise RuntimeError(f"Source checksum mismatch: {component}")
        destination = target if component == "parakeet" else target / "third_party/ggml"
        prefix = expected["directory"] + "/"
        with zipfile.ZipFile(archive) as source:
            for entry in source.infolist():
                if not entry.filename.startswith(prefix):
                    raise RuntimeError("Unexpected source archive prefix")
                relative = entry.filename[len(prefix):]
                if not relative or entry.is_dir():
                    continue
                path = (destination / relative).resolve()
                if not path.is_relative_to(destination.resolve()):
                    raise RuntimeError("Source archive path escapes the build directory")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(source.read(entry))
    for name, expected in manifest["normalized_base_files_sha256"].items():
        normalized = (target / name).read_text(encoding="utf-8").replace("\r\n", "\n")
        if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != expected:
            raise RuntimeError(f"Unexpected upstream source: {name}")
    for folder in ("src", "tests"):
        for path in (HERE / folder).iterdir():
            shutil.copyfile(path, target / folder / path.name)
    patch = str(HERE / "context.patch")
    subprocess.run(["git", "apply", "--check", patch], cwd=target, check=True)
    subprocess.run(["git", "apply", patch], cwd=target, check=True)
    print(json.dumps({"source": str(target), "experimental_only": True, "installed": False}))


if __name__ == "__main__":
    main()
