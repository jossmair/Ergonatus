"""Validated, atomic local settings. Imported profiles never change Windows startup."""
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path

from .keys import EMERGENCY, KEYS

ACTION_NAMES = {
    "key": "Touche ou combinaison", "sequence": "Suite de touches", "text": "Écrire un texte",
    "mouse_click": "Clic simple",
    "mouse_hold": "Clic maintenu pendant l’appui", "mouse_toggle": "Clic verrouillé (appui / appui)",
    "double_click": "Double-clic gauche", "wheel": "Faire défiler",
    "move": "Déplacer le pointeur", "disabled": "Désactiver la touche",
    "original": "Fonction normale",
}


@dataclass
class Mapping:
    source: int
    kind: str = "key"
    keys: list[int] = field(default_factory=list)
    text: str = ""
    button: str = "left"
    amount: int = 120
    direction: str = "right"
    enabled: bool = True
    sequence: list[list[int]] = field(default_factory=list)
    interval_ms: int = 80

    def validate(self):
        if type(self.source) is not int or self.source not in KEYS or self.source == EMERGENCY:
            raise ValueError("Touche source invalide. F12 est réservé à l’arrêt d’urgence.")
        if self.kind not in ACTION_NAMES or type(self.enabled) is not bool:
            raise ValueError("Action invalide.")
        if not isinstance(self.keys, list) or len(self.keys) > 8:
            raise ValueError("Une combinaison peut contenir jusqu’à 8 touches.")
        if any(type(k) is not int or k not in KEYS or k == EMERGENCY for k in self.keys):
            raise ValueError("La combinaison contient une touche invalide ou F12.")
        if len(set(self.keys)) != len(self.keys) or (self.kind == "key" and not self.keys):
            raise ValueError("Choisissez une touche ou une combinaison sans doublon.")
        if not isinstance(self.sequence, list) or len(self.sequence) > 50 or (self.kind == "sequence" and not self.sequence):
            raise ValueError("Ajoutez entre 1 et 50 étapes à la suite.")
        for step in self.sequence:
            if (not isinstance(step, list) or not 1 <= len(step) <= 8
                    or any(type(key) is not int or key not in KEYS or key == EMERGENCY for key in step)
                    or len(set(step)) != len(step)):
                raise ValueError("Une étape doit contenir une touche ou un raccourci valide, sans F12 ni doublon.")
        if type(self.interval_ms) is not int or not 20 <= self.interval_ms <= 2000:
            raise ValueError("Choisissez un délai entre 20 et 2 000 ms.")
        if not isinstance(self.text, str) or len(self.text) > 500 or (self.kind == "text" and not self.text):
            raise ValueError("Le texte doit contenir entre 1 et 500 caractères.")
        if self.button not in ("left", "right", "middle"):
            raise ValueError("Bouton de souris invalide.")
        if type(self.amount) is not int or self.amount not in (-360, -240, -120, 120, 240, 360):
            raise ValueError("Défilement invalide.")
        if self.direction not in ("left", "right", "up", "down"):
            raise ValueError("Direction invalide.")


@dataclass
class Profile:
    name: str = "Mon clavier"
    mappings: list[Mapping] = field(default_factory=list)
    invert_numbers: bool = False
    sticky_modifiers: bool = False
    debounce_ms: int = 0
    suppress_repeat: bool = False
    pointer_speed: int = 8

    def validate(self):
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 60:
            raise ValueError("Le nom du profil doit contenir entre 1 et 60 caractères.")
        for value in (self.invert_numbers, self.sticky_modifiers, self.suppress_repeat):
            if type(value) is not bool:
                raise ValueError("Option de profil invalide.")
        if type(self.debounce_ms) is not int or not 0 <= self.debounce_ms <= 1000:
            raise ValueError("Le délai anti-rebond doit être compris entre 0 et 1 000 ms.")
        if type(self.pointer_speed) is not int or not 1 <= self.pointer_speed <= 40:
            raise ValueError("La vitesse doit être comprise entre 1 et 40.")
        if not isinstance(self.mappings, list) or len(self.mappings) > 200:
            raise ValueError("Un profil peut contenir jusqu’à 200 affectations.")
        seen = set()
        for mapping in self.mappings:
            mapping.validate()
            if mapping.source in seen:
                raise ValueError("Une touche source ne peut avoir qu’une affectation par profil.")
            seen.add(mapping.source)


@dataclass
class Settings:
    version: int = 1
    active_profile: str = "Mon clavier"
    profiles: list[Profile] = field(default_factory=lambda: [Profile()])
    start_minimized: bool = False
    start_active: bool = True
    virtual_keyboard: bool = True
    hover_scroll: bool = True

    @property
    def profile(self):
        return next(p for p in self.profiles if p.name == self.active_profile)

    def validate(self):
        if type(self.version) is not int or self.version != 1:
            raise ValueError("Version de configuration non prise en charge.")
        if any(type(value) is not bool for value in (self.start_minimized, self.start_active, self.virtual_keyboard, self.hover_scroll)):
            raise ValueError("Option de démarrage invalide.")
        if not isinstance(self.profiles, list) or not 1 <= len(self.profiles) <= 30:
            raise ValueError("La configuration doit contenir entre 1 et 30 profils.")
        for profile in self.profiles:
            profile.validate()
        names = [p.name for p in self.profiles]
        if len(set(names)) != len(names) or self.active_profile not in names:
            raise ValueError("Noms de profils en double ou profil actif introuvable.")

    @classmethod
    def from_dict(cls, data):
        try:
            if not isinstance(data, dict):
                raise ValueError("Le fichier doit contenir une configuration JSON.")
            raw = dict(data)
            profiles = []
            for item in raw.get("profiles", []):
                item = dict(item)
                item["mappings"] = [Mapping(**m) for m in item.get("mappings", [])]
                profiles.append(Profile(**item))
            raw["profiles"] = profiles
            result = cls(**raw)
            result.validate()
            return result
        except (TypeError, KeyError, AttributeError) as exc:
            raise ValueError("La structure du fichier de configuration est invalide.") from exc

    @classmethod
    def load(cls, path):
        path = Path(path)
        if not path.exists():
            return cls()
        if path.stat().st_size > 1_000_000:
            raise ValueError("Le fichier de configuration est trop volumineux.")
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("Le fichier de configuration n’est pas un JSON valide.") from exc

    def save(self, path):
        self.validate()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(asdict(self), stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

