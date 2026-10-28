"""Restore the reviewed GitHub presentation from its maintained template."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
(ROOT / "README.md").write_text((ROOT / "docs/github-readme.md").read_text(encoding="utf-8"), encoding="utf-8")
