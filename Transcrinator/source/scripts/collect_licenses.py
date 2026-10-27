import importlib.metadata
import shutil
from pathlib import Path

root = Path("docs/third-party")
root.mkdir(parents=True, exist_ok=True)
packages = [
    "PySide6-Essentials",
    "shiboken6",
    "sounddevice",
    "numpy",
    "soxr",
    "pywin32",
    "comtypes",
    "httpx",
    "httpcore",
    "onnxruntime",
    "psutil",
    "cffi",
    "certifi",
    "anyio",
    "idna",
    "typing_extensions",
    "pycparser",
    "flatbuffers",
    "protobuf",
    "text2num",
    "num2words",
    "docopt",
]
for package in packages:
    dist = importlib.metadata.distribution(package)
    destination = root / package
    destination.mkdir(exist_ok=True)
    metadata = dist.metadata
    (destination / "NOTICE.txt").write_text(
        f"{metadata['Name']} {metadata['Version']}\n"
        f"{metadata.get('License', '')}\n{metadata.get('Home-page', '')}\n"
        + "\n".join(metadata.get_all("Project-URL") or []),
        encoding="utf-8",
    )
    for file in dist.files or []:
        if file.name.lower().startswith(("license", "copying", "notice")):
            source = Path(dist.locate_file(file))
            if source.is_file():
                shutil.copy2(source, destination / file.name)
print("Notices de dépendances copiées.")
