from copy import deepcopy
from pathlib import Path
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout
from .config import Profile, Settings
from .dialog import MappingDialog
from .theme import BackdropDialog, label


class ProfileActions:
    def edit_mapping(self, checked=False, mapping=None, source=None, kind=None):
        if source is not None:
            mapping = next((m for m in self.profile.mappings if m.source == source), None)
        try:
            with self.controller.editing():
                dialog = MappingDialog(self, mapping, source, kind)
                if dialog.exec() != QDialog.Accepted:
                    return
                if dialog.reset_requested:
                    self.controller.restore_key(dialog.source.currentData())
                    return
                chosen = dialog.mapping
                duplicate = next((m for m in self.profile.mappings if m.source == chosen.source and m is not mapping), None)
                if duplicate:
                    self.show_notice("Cette touche possède déjà une affectation. Modifiez celle-ci ou choisissez une autre touche.")
                    return
                if mapping:
                    self.profile.mappings[self.profile.mappings.index(mapping)] = chosen
                else:
                    self.profile.mappings.append(chosen)
                self.controller.commit()
        except Exception as exc:
            self.show_notice(str(exc))

    def switch_profile(self, name):
        if name and name != self.controller.settings.active_profile:
            self.controller.settings.active_profile = name
            self.controller.commit()

    def ask_name(self, title, initial):
        dialog = BackdropDialog(self)
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        layout.addWidget(dialog.header(title))
        layout.addWidget(label("Nom du clavier"))
        entry = QLineEdit(initial)
        entry.setMaxLength(60)
        entry.setAccessibleName("Nom du clavier")
        entry.selectAll()
        layout.addWidget(entry)
        row = QHBoxLayout()
        cancel, save = QPushButton("Annuler"), QPushButton("Enregistrer")
        save.setObjectName("Primary")
        save.setDefault(True)
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)
        row.addWidget(cancel)
        row.addWidget(save)
        layout.addLayout(row)
        entry.setFocus()
        accepted = dialog.exec() == QDialog.Accepted
        name = entry.text().strip()
        dialog.deleteLater()
        if not accepted:
            return None
        if not name or len(name) > 60:
            self.show_notice("Choisissez un nom entre 1 et 60 caractères.")
            return None
        return name

    def new_profile(self, original=None):
        if len(self.controller.settings.profiles) >= 30:
            self.show_notice("La limite de 30 claviers enregistrés est atteinte.")
            return
        source = original if isinstance(original, Profile) else None
        name = self.ask_name("Copier ce clavier" if source else "Créer un clavier", (source.name[:50] + " · copie") if source else "Nouveau clavier")
        if not name:
            return
        if any(p.name == name for p in self.controller.settings.profiles):
            self.show_notice("Ce nom de clavier existe déjà.")
            return
        profile = deepcopy(source) if source else Profile()
        profile.name = name
        self.controller.settings.profiles.append(profile)
        self.controller.settings.active_profile = name
        self.controller.commit()

    def rename_profile(self, profile):
        name = self.ask_name("Changer le nom du clavier", profile.name)
        if not name or name == profile.name:
            return
        if any(p.name == name for p in self.controller.settings.profiles):
            self.show_notice("Ce nom de clavier existe déjà.")
            return
        if profile is self.profile:
            self.controller.settings.active_profile = name
        profile.name = name
        self.controller.commit()

    def export_settings(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder mes réglages", "Claviernator-reglages.json", "Réglages Claviernator (*.json)")
        if path:
            try:
                if Path(path).resolve() == self.controller.path.resolve():
                    raise ValueError("Choisissez un autre fichier que la configuration en cours.")
                self.controller.settings.save(path)
                self.show_notice("Profils exportés.")
            except (ValueError, OSError) as exc:
                self.show_notice(str(exc))

    def import_settings(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger une sauvegarde", "", "Réglages Claviernator (*.json)")
        if not path:
            return
        try:
            if not Path(path).is_file():
                raise ValueError("Fichier introuvable.")
            imported = Settings.load(path)
            selected = imported.profile
            existing = self.controller.settings
            if len(existing.profiles) + len(imported.profiles) > 30:
                raise ValueError("Cet import dépasserait la limite de 30 profils.")
            names = {p.name for p in existing.profiles}
            self.controller.backup()
            for profile in imported.profiles:
                base = profile.name[:45]
                index = 1
                while profile.name in names:
                    profile.name = f"{base} · import {index}"
                    index += 1
                names.add(profile.name)
            existing.profiles.extend(imported.profiles)
            existing.active_profile = selected.name
            if self.controller.commit():
                self.show_notice("Profils importés. Choisissez celui que vous souhaitez utiliser.")
        except (ValueError, OSError) as exc:
            self.show_notice(str(exc))
