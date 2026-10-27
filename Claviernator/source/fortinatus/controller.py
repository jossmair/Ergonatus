from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
from PySide6.QtCore import QObject, Signal

from .config import Mapping, Profile, Settings
from .keys import EMERGENCY, KEYS, MODIFIERS, SYMBOLS, key_name
from .windows import HookService, set_startup, startup_enabled


class Controller(QObject):
    state = Signal(bool)
    notice = Signal(str)
    changed = Signal()
    _native_state = Signal(bool)
    _native_notice = Signal(str)

    def __init__(self, settings, path, no_hooks=False):
        super().__init__()
        self.settings, self.path = settings, path
        self.saved = deepcopy(settings)
        self.active = settings.start_active and not no_hooks
        self.suspended = False
        self.service = None
        self._native_state.connect(self.native_state)
        self._native_notice.connect(self.native_notice)
        if not no_hooks:
            self.service = HookService(self._native_state.emit, self._native_notice.emit)
            try:
                self.service.start(settings.profile, self.active)
            except Exception:
                self.service.stop()
                self.service = None
                self.active = False
                raise

    def native_state(self, active):
        if not self.suspended:
            self.active = active
            self.state.emit(active)

    def native_notice(self, text):
        if text.startswith("Pause d’urgence"):
            self.active = False
            self.state.emit(False)
        self.notice.emit(text)

    def commit(self):
        try:
            self.settings.save(self.path)
            if self.service:
                self.service.configure(self.settings.profile, self.active and not self.suspended)
            self.saved = deepcopy(self.settings)
        except Exception as exc:
            self.settings = deepcopy(self.saved)
            try:
                self.settings.save(self.path)
            except OSError:
                pass
            self.notice.emit(str(exc))
            self.changed.emit()
            return False
        self.changed.emit()
        return True

    def toggle(self):
        if self.service is None:
            self.notice.emit("Le service clavier est désactivé dans cet aperçu.")
            return
        requested = not self.active
        try:
            self.service.configure(self.settings.profile, requested)
            self.active = requested
            self.state.emit(requested)
        except Exception as exc:
            self.active = False
            self.state.emit(False)
            self.notice.emit(str(exc))

    def pause_runtime(self):
        self.active = False
        if self.service:
            try:
                self.service.configure(self.settings.profile, False)
            except Exception:
                self.service.stop()
                self.service = None
        self.state.emit(False)

    def restore_keyboard(self):
        self.pause_runtime()
        if self.commit():
            self.notice.emit("Clavier normal. Vos réglages sont conservés.")
            return True
        return False

    def repair_service(self):
        self.pause_runtime()
        if self.service:
            self.service.stop()
        self.service = None
        try:
            service = HookService(self._native_state.emit, self._native_notice.emit)
            self.service = service
            service.start(self.settings.profile, True)
            self.active = True
            self.state.emit(True)
            self.notice.emit("Commandes souris relancées.")
            return True
        except Exception as exc:
            if self.service:
                self.service.stop()
            self.service = None
            self.active = False
            self.state.emit(False)
            self.notice.emit(str(exc))
            return False

    def backup(self):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-UTC")
        path = self.path.parent / "sauvegardes" / f"avant-reinitialisation-{timestamp}-{uuid4().hex[:6]}.json"
        self.settings.save(path)
        return path

    def reset_mouse(self):
        self.pause_runtime()
        try:
            backup = self.backup()
            profile = self.settings.profile
            mouse = {"mouse_click", "mouse_hold", "mouse_toggle", "double_click", "wheel", "move"}
            profile.mappings = [m for m in profile.mappings if m.kind not in mouse]
            profile.pointer_speed = Profile().pointer_speed
            if self.commit():
                self.notice.emit("Souris réinitialisée. Sauvegarde : " + str(backup))
                return True
        except (OSError, ValueError) as exc:
            self.notice.emit(str(exc))
        return False

    def restore_key(self, source):
        if type(source) is not int or source not in KEYS or source == EMERGENCY:
            self.notice.emit("Cette touche ne peut pas être modifiée.")
            return False
        profile = self.settings.profile
        current = next((m for m in profile.mappings if m.source == source), None)
        exception = (profile.sticky_modifiers or profile.suppress_repeat
                     or (profile.debounce_ms > 0 and source not in MODIFIERS)
                     or (profile.invert_numbers and source in SYMBOLS))
        if (current is None and not exception) or (current and current.enabled and current.kind == "original" and exception):
            self.notice.emit(key_name(source) + " fonctionne déjà normalement.")
            return True
        try:
            self.backup()
            profile.mappings = [m for m in profile.mappings if m.source != source]
            if exception:
                profile.mappings.append(Mapping(source, "original"))
            if self.commit():
                self.notice.emit(key_name(source) + " : fonction d’origine rétablie.")
                return True
        except (OSError, ValueError) as exc:
            self.notice.emit(str(exc))
        return False

    def delete_mapping(self, source):
        if type(source) is not int or source not in KEYS or source == EMERGENCY:
            self.notice.emit("Cette touche ne peut pas être modifiée.")
            return False
        profile = self.settings.profile
        if not any(mapping.source == source for mapping in profile.mappings):
            return True
        try:
            self.backup()
            profile.mappings = [mapping for mapping in profile.mappings if mapping.source != source]
            if self.commit():
                self.notice.emit(key_name(source) + " : ligne supprimée.")
                return True
        except (OSError, ValueError) as exc:
            self.notice.emit(str(exc))
        return False

    def reset_profile(self):
        self.pause_runtime()
        try:
            backup = self.backup()
            current = self.settings.profile
            index = self.settings.profiles.index(current)
            self.settings.profiles[index] = Profile(name=current.name)
            if self.commit():
                self.notice.emit("Profil réinitialisé. Sauvegarde : " + str(backup))
                return True
        except (OSError, ValueError) as exc:
            self.notice.emit(str(exc))
        return False

    def reset_all(self):
        self.pause_runtime()
        startup_was_enabled = False
        try:
            backup = self.backup()
            startup_was_enabled = startup_enabled()
            if startup_was_enabled:
                set_startup(False)
            self.settings = Settings()
            if self.commit():
                self.notice.emit("Réinitialisation terminée. Sauvegarde : " + str(backup))
                return True
            if startup_was_enabled:
                set_startup(True, self.path.parent)
        except (OSError, ValueError) as exc:
            self.notice.emit(str(exc))
        return False

    @contextmanager
    def editing(self):
        self.suspended = True
        try:
            if self.service:
                self.service.configure(self.settings.profile, False)
            yield
        finally:
            self.suspended = False
            if self.service:
                try:
                    self.service.configure(self.settings.profile, self.active)
                except Exception as exc:
                    self.active = False
                    self.state.emit(False)
                    self.notice.emit(str(exc))

    def stop(self):
        if self.service:
            self.service.stop()

