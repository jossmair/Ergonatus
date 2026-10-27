"""Package the existing frozen build, notices, source and a shareable ZIP."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fortinatus import __version__

root = Path(__file__).resolve().parents[1]
release = root / "dist" / f"Claviernator-{__version__}"
executable = release / "Claviernator.exe"
if not executable.is_file():
    raise SystemExit("Construisez d’abord Claviernator.spec avec PyInstaller.")

licenses = root / "docs" / "licenses"
required = ["LGPL-3.0.txt", "GPL-3.0.txt", "Python-LICENSE.txt", "NOTICE.txt"]
for name in required:
    if not (licenses / name).is_file():
        raise SystemExit("Licence manquante : " + name)
distribution = importlib.metadata.distribution("pyinstaller")
for item in distribution.files:
    if str(item).endswith("COPYING.txt"):
        shutil.copy2(distribution.locate_file(item), licenses / "PyInstaller-COPYING.txt")
        break
shutil.copytree(licenses, release / "Licences", dirs_exist_ok=True)
shutil.copy2(root / "README.md", release / "Guide-Claviernator.md")
shutil.copy2(root / "LICENSE", release / "LICENSE")
quickstart = f"""CLAVIERNATOR {__version__} — PREMIERS PAS

1. Ouvrir Claviernator.exe. Conserver le dossier _internal à côté.
2. Ajouter une touche : choisir une touche, puis son action.
3. Poubelle : supprimer seulement la ligne concernée.
4. Activer Inverser chiffres et caractères ou Démarrer avec Windows si besoin.

Clavier virtuel : activer l’interrupteur sur la fenêtre principale.
L’orbe turquoise apparaît au-dessus de celle de Transcrinator, en bas à droite.
Elle mesure 36 × 36 pixels et suit le pointeur sur vos écrans.
Clic droit sur l’orbe : même menu que l’icône près de l’horloge, pour ouvrir, mettre en pause ou quitter.
Cliquer d’abord dans votre document, puis sur l’orbe. Préparer le texte et cliquer Insérer.
Vous pouvez sélectionner un autre champ après l’ouverture : Insérer suit le dernier champ choisi.
Si le champ est caché, cliquer Choisir où écrire : le clavier disparaît.
Cliquer dans le champ souhaité ; au relâchement de la souris, le clavier revient avec votre texte intact.
Cliquer ensuite Insérer. L’orbe permet aussi de revenir sans choisir un autre champ.
Effacer, en bas du clavier : supprimer le caractère avant le curseur dans le champ choisi.
Ce bouton reste présent sur toutes les pages et conserve le texte préparé.
Vider, en haut : effacer le texte préparé dans le clavier.
Faire glisser la barre du haut pour déplacer le clavier, y compris sur un autre écran.
Le clavier garde son format compact de 900 × 320 pixels logiques.
Caractères donne accès aux accents, signes, emojis et codes Unicode.
Touches donne accès aux raccourcis, fonctions F1 à F24, pavé numérique et commandes média.
Démarrer avec Windows se trouve dans Options > Au démarrage.
Flèches de défilement : cliquer dans la zone à faire défiler, puis rester sur une flèche courbe autour de l’orbe.
Les croissants turquoise offrent une zone de survol de 54 × 28 pixels logiques.
La dernière zone cliquée reste la cible, même si le pointeur passe sur une autre zone.
Quitter la flèche arrête le défilement. L’option se désactive sur l’accueil et reste mémorisée.

La poubelle supprime la ligne concernée, sans toucher aux autres réglages.
Les adaptations sont actives au lancement ; vos réglages sont conservés.
Ctrl + V colle aussi si Ctrl gauche ou droit sert au clic souris : le collage prend la priorité.

Interrupteur Actif : désactiver pour retrouver le clavier d’origine sans effacer les réglages.
Tout réinitialiser : retrouver les réglages initiaux, après confirmation.
Options : aides de frappe et sauvegardes.
Claviers enregistrés : garder plusieurs réglages et choisir celui à utiliser.
Dépannage : relancer les commandes souris ou remettre des réglages à zéro.

METTRE EN PAUSE · F12 = PAUSE ET LIBÉRATION DES TOUCHES / CLICS.
Réactiver l’interrupteur en haut de la fenêtre permet de reprendre.

La croix masque la fenêtre près de l’horloge. « Quitter Claviernator » arrête le logiciel.
Un deuxième lancement rouvre la fenêtre existante.
Vos réglages sont sauvegardés dans %APPDATA%/Fortinatus/settings.json.

Consulter Guide-Claviernator.md pour le guide complet.
"""
(release / "LIRE-MOI.txt").write_text(quickstart, encoding="utf-8-sig")

with zipfile.ZipFile(release / "sources.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    candidates = [root / name for name in ["LICENSE", "README.md", "pyproject.toml", "Claviernator.spec", "Fortinatus.spec", "run_claviernator.py", "run_fortinatus.py", "Lancer Claviernator.cmd", "Lancer Fortinatus.cmd"]]
    for directory in ("fortinatus", "scripts", "tests", "assets", "docs/licenses"):
        candidates.extend(path for path in (root / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    for path in sorted(set(candidates)):
        archive.write(path, "Claviernator/" + path.relative_to(root).as_posix())

report = root / "docs" / "validation" / "windows-native.json"
if report.exists():
    shutil.copy2(report, release / "Validation-Windows.json")
click_report = root / "docs" / "validation" / "click-regression.json"
if click_report.exists():
    shutil.copy2(click_report, release / "Validation-clic.json")
instance_report = root / "docs" / "validation" / "single-instance.json"
if instance_report.exists():
    shutil.copy2(instance_report, release / "Validation-instance-unique.json")
sequence_report = root / "docs" / "validation" / "sequence-release.json"
if sequence_report.exists():
    shutil.copy2(sequence_report, release / "Validation-suite-et-redemarrage.json")
ui_report = root / "docs" / "validation" / "ui-release.json"
if ui_report.exists():
    shutil.copy2(ui_report, release / "Validation-interface.json")
keyboard_report = root / "docs" / "validation" / "virtual-keyboard-native.json"
if keyboard_report.exists():
    shutil.copy2(keyboard_report, release / "Validation-clavier-virtuel.json")
frozen_report = root / "docs" / "validation" / "frozen-keyboard.json"
if frozen_report.exists():
    shutil.copy2(frozen_report, release / "Validation-clavier-executable.json")
hover_report = root / "docs" / "validation" / "hover-scroll-native.json"
if hover_report.exists():
    shutil.copy2(hover_report, release / "Validation-defilement-survol.json")
shutil.copy2(root / "docs" / "VALIDATION.md", release / "Validation.md")

archive_path = root / "dist" / f"Claviernator-{__version__}-Windows-x64.zip"
with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(release.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(release.parent))
digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
(archive_path.with_suffix(".sha256")).write_text(f"{digest}  {archive_path.name}\n", encoding="ascii")
print(json.dumps({"executable": str(executable), "archive": str(archive_path),
                  "archive_mb": round(archive_path.stat().st_size / 1_000_000, 1), "sha256": digest}, indent=2))

