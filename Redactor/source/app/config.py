"""Preferences only: no text, clipboard or conversation is persisted."""
from dataclasses import asdict, dataclass, fields
import json
import os
from pathlib import Path
import sys


def project_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def assets_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", project_root())) / "assets"


def data_root() -> Path:
    override = os.environ.get("REDACTOR_DATA_DIR")
    return Path(override) if override else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Redactor"


@dataclass
class Config:
    model_path: str = ""
    threads: int = 0
    max_tokens: int = 384
    context: int = 2048
    animation: str = "reduced"
    orb_color: str = "red"
    text_size: int = 11
    hotkey: str = "Ctrl+Alt+R"
    orb_x: int | None = None
    orb_y: int | None = None
    follow_suite: bool = True

    def validate(self):
        if self.animation not in ("normal", "reduced", "none"):
            raise ValueError("Animation inconnue.")
        if self.orb_color not in ("red", "violet"):
            raise ValueError("Couleur d’orbe inconnue.")
        for name, low, high in (("threads", 0, 64), ("max_tokens", 32, 1024), ("context", 512, 8192), ("text_size", 10, 20)):
            v = getattr(self, name)
            if type(v) is not int or not low <= v <= high:
                raise ValueError(f"Réglage invalide : {name}.")
        if not isinstance(self.model_path, str) or not isinstance(self.hotkey, str):
            raise ValueError("Chemin ou raccourci invalide.")
        if type(self.follow_suite) is not bool:
            raise ValueError("Placement invalide.")
        for value in (self.orb_x, self.orb_y):
            if value is not None and (type(value) is not int or abs(value) > 100000):
                raise ValueError("Position invalide.")
        return self

    @classmethod
    def load(cls):
        path = data_root() / "settings.json"
        if not path.exists():
            return cls(), ""
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
            known = {f.name for f in fields(cls)}
            return cls(**{k: v for k, v in values.items() if k in known}).validate(), ""
        except (OSError, ValueError, TypeError, AttributeError):
            return cls(), "Réglages illisibles : valeurs par défaut utilisées. Le fichier original est conservé."

    def save(self):
        self.validate()
        path = data_root() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def model(self) -> Path | None:
        if self.model_path:
            return Path(self.model_path)
        candidates = ("LFM2-700M-Q4_K_M.gguf", "Luth-1.7B-Instruct-Q8_0.gguf", "Luciole-1B-Instruct-1.1-Q4_K_M.gguf", "qwen2.5-0.5b-instruct-q4_k_m.gguf")
        roots = [project_root() / "models"]
        if getattr(sys, "frozen", False):
            roots.append(project_root().parent.parent / "models")
        return next((root / n for root in roots for n in candidates if (root / n).is_file()), None)
