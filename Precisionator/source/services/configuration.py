"""Validated preferences, atomically saved in the current user's profile."""
from dataclasses import asdict, dataclass, field
import json
import math
import os
from pathlib import Path
import tempfile

from core.motion_analyzer import MotionThresholds

TUNING_LIMITS = {
    "lens_diameter": (120, 600),
    "minimum_speed": (5, 200),
    "trigger_speed": (20, 1200),
    "exit_speed": (40, 2400),
    "activation_delay_ms": (50, 1000),
    "idle_delay_ms": (100, 5000),
}


@dataclass
class Preferences:
    enabled: bool = True
    magnification: float = 2.5
    startup: bool = False
    orb_position: tuple[int, int] | None = None
    orb_screen: str = ""
    lens_diameter: int = 300
    minimum_speed: int = 10
    trigger_speed: int = 650
    exit_speed: int = 1100
    activation_delay_ms: int = 50
    idle_delay_ms: int = 2000
    orb_positions: dict[str, tuple[int, int]] = field(default_factory=dict)

    def thresholds(self):
        return MotionThresholds(self.minimum_speed, self.trigger_speed, self.exit_speed,
                                self.activation_delay_ms, self.idle_delay_ms)

    def normalize_tuning(self):
        for key, (low, high) in TUNING_LIMITS.items():
            value = getattr(self, key)
            if type(value) is not int:
                value = getattr(Preferences(), key)
            setattr(self, key, max(low, min(value, high)))
        self.trigger_speed = max(self.trigger_speed, self.minimum_speed + 5)
        self.exit_speed = max(self.exit_speed, self.trigger_speed + 20)
        self.lens_diameter += self.lens_diameter % 2


def valid_position(value):
    return isinstance(value, (list, tuple)) and len(value) == 2 and all(type(n) is int and abs(n) < 1000000 for n in value)


def config_path():
    return Path(os.environ.get("APPDATA", Path.home())) / "Precisionator" / "settings.json"


class Configuration:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else config_path()

    def load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return Preferences()
            p = Preferences()
            for key in ("enabled", "startup"):
                if type(raw.get(key)) is bool:
                    setattr(p, key, raw[key])
            if type(raw.get("magnification")) in (int, float) and raw["magnification"] in (1.8, 2.5, 3.0):
                p.magnification = float(raw["magnification"])
            pos = raw.get("orb_position")
            if valid_position(pos):
                p.orb_position = tuple(pos)
            if isinstance(raw.get("orb_screen"), str):
                p.orb_screen = raw["orb_screen"][:200]
            positions = raw.get("orb_positions")
            if isinstance(positions, dict):
                p.orb_positions = {name[:200]: tuple(pos) for name, pos in list(positions.items())[:32]
                                   if isinstance(name, str) and valid_position(pos)}
            for key in TUNING_LIMITS:
                if type(raw.get(key)) is int:
                    setattr(p, key, raw[key])
            p.normalize_tuning()
            return p
        except (OSError, ValueError, TypeError):
            return Preferences()

    def save(self, prefs):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix="settings-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(asdict(prefs), stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
