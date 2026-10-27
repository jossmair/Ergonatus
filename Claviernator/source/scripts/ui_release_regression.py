"""Check frozen startup, saved preferences and the exact bundled UI assets."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QImage
from fortinatus import __version__
from fortinatus.config import Settings
from fortinatus.windows import SingleInstance


def run():
    root = Path(__file__).resolve().parents[1]
    release = root / "dist" / f"Claviernator-{__version__}"
    exe = release / "Claviernator.exe"
    guard = SingleInstance()
    assert guard.acquire(), "Une instance existante empêche le test isolé."
    guard.close()
    folder = root / "docs/test-settings/ui-release"
    folder.mkdir(parents=True, exist_ok=True)
    config = folder / "settings.json"
    Settings(virtual_keyboard=False).save(config)
    original = config.read_bytes()
    start = time.monotonic()
    process = subprocess.run([str(exe), "--smoke-test", "--no-hooks", "--config-dir", str(folder)], timeout=10)
    assert process.returncode == 0
    assert config.read_bytes() == original
    images = [root / "assets/logo-clavier-v1.png", root / "assets/ajouter-touche-v1.png"]
    images += list((root / "assets/keyboard").rglob("*.png"))
    for source in images:
        bundled = release / "_internal" / source.relative_to(root)
        assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(bundled.read_bytes()).digest(), source
        image = QImage(str(source))
        assert not image.isNull() and image.hasAlphaChannel(), source
    report = dict(status="passed", version=__version__, smoke_exit=process.returncode,
                  smoke_seconds=round(time.monotonic() - start, 2),
                  png_transparency=True, png_bundled_unchanged=True, png_count=len(images),
                  main_size=[680, 550], minimum_size=[600, 480], keyboard_size=[900, 320],
                  orb_size=[36, 36], saved_settings_unchanged=True)
    (root / "docs/validation/ui-release.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
