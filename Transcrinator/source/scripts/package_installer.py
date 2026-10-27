import hashlib
import json
import shutil
import subprocess
import sys
import os
import zipfile
from pathlib import Path
from app import __version__

root = Path(__file__).resolve().parent.parent
payload_dir = root / "dist" / f"Installation-Transcrinator-{__version__}"
payload_dir.mkdir(parents=True, exist_ok=True)
source = root / "dist" / f"Transcrinator-{__version__}"
for name in ("README.md", "LICENSE"):
    src = root / name
    dest = source / name
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    elif src.exists():
        shutil.copy2(src, dest)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


files = {}
with zipfile.ZipFile(payload_dir / "payload.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for file in source.rglob("*"):
        if file.is_file():
            name = file.relative_to(source).as_posix()
            archive.write(file, name, compress_type=zipfile.ZIP_STORED if file.suffix == ".gguf" else zipfile.ZIP_DEFLATED)
            files[name] = sha(file)
manifest = {"sha256": sha(payload_dir / "payload.zip"), "files": files}
(payload_dir / "payload.json").write_text(json.dumps(manifest), encoding="utf-8")
task_env = os.environ.copy()
task_env["PATH"] = os.pathsep.join(
    [
        str(Path(sys.executable).parent),
        str(Path(os.environ["SystemRoot"]) / "System32"),
        os.environ["SystemRoot"],
    ]
)
subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "Uninstall-Transcrinator",
        "--icon",
        "assets/transcri.ico",
        "installer/setup.py",
    ],
    cwd=root,
    check=True,
    env=task_env,
)
shutil.copy2(root / "dist" / "Uninstall-Transcrinator.exe", payload_dir / "uninstaller.exe")
subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        f"Installer-Transcrinator-{__version__}",
        "--icon",
        "assets/transcri.ico",
        "installer/setup.py",
    ],
    cwd=root,
    check=True,
    env=task_env,
)
portable_archive = root / "dist" / f"Transcrinator-{__version__}-Complet.zip"
if portable_archive.exists():
    portable_archive.unlink()
try:
    os.link(payload_dir / "payload.zip", portable_archive)
except OSError:
    shutil.copy2(payload_dir / "payload.zip", portable_archive)
shutil.copy2(root / "dist" / f"Installer-Transcrinator-{__version__}.exe", payload_dir / "Installer-Transcrinator.exe")
print("Dossier complet et installateur hors ligne produits.")
