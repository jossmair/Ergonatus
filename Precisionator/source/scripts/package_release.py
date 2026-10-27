"""Bundle documents, dependency licences, hashes and a portable ZIP."""
from importlib import metadata
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist/Precisionator-1.0.7"
if not (DIST / "Precisionator.exe").exists():
    raise SystemExit("Compiler Precisionator.spec d’abord.")
for filename in ("README.md", "docs/VALIDATION.md", "docs/DESIGN.md", "requirements.txt"):
    shutil.copy2(ROOT / filename, DIST / Path(filename).name)
shutil.copytree(ROOT / "docs/validation", DIST / "docs/validation", dirs_exist_ok=True)
licenses = DIST / "licenses"
licenses.mkdir(exist_ok=True)
shutil.copytree(ROOT / "assets/licenses", licenses / "family", dirs_exist_ok=True)
for package in ("PySide6-Essentials", "shiboken6", "numpy", "dxcam", "opencv-python", "comtypes", "pyinstaller"):
    dist = metadata.distribution(package)
    target = licenses / package
    target.mkdir(exist_ok=True)
    (target / "VERSION.txt").write_text(f"{package} {dist.version}\n", encoding="utf-8")
    for file in dist.files or []:
        if any(word in str(file).lower() for word in ("license", "copying", "notice")):
            path = Path(dist.locate_file(file))
            if path.is_file():
                name = str(file).replace("/", "_").replace("\\", "_")
                shutil.copy2(path, target / name)
archive = ROOT / "dist/Precisionator-1.0.7-Windows-x64.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as output:
    for file in sorted(DIST.rglob("*")):
        if file.is_file():
            output.write(file, file.relative_to(DIST.parent))
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix(".zip.sha256").write_text(digest + "  " + archive.name + "\n", encoding="ascii")
print(str(archive))
sources = ROOT / "dist/Precisionator-1.0.7-Sources.zip"
with zipfile.ZipFile(sources, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as output:
    folders = {"core", "ui", "services", "assets", "tests", "scripts", "docs"}
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in ("__pycache__", "test-settings", ".venv", ".tools", "dist", "build", ".test-tmp", ".pytest_cache") for part in relative.parts):
            continue
        if len(relative.parts) == 1 or relative.parts[0] in folders:
            output.write(path, Path("Precisionator") / relative)
print(str(sources))
sources.with_suffix(".zip.sha256").write_text(hashlib.sha256(sources.read_bytes()).hexdigest() + "  " + sources.name + "\n", encoding="ascii")
