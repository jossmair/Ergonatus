"""Package the authored assets, never source checkouts, caches or user data."""
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
version = sys.argv[1]
icons = sorted((root / 'assets/school-icons').glob('*.svg'))
assert len(icons) == 92
illustrations = sorted((root / 'assets/subjects').glob('*.png'))
assert len(illustrations) == 13
destination = root / f'dist/Ecrinator-{version}-icones-et-illustration.zip'
destination.parent.mkdir(parents=True, exist_ok=True)
files = [(p, 'icones/' + p.name) for p in icons]
files += [(root / 'assets' / name, name) for name in ['icon-catalog.svg', 'ecrinator.svg', 'ecrinator.png', 'ecrinator.ico', 'ATTRIBUTION.md']]
files += [(p, 'bandeaux/' + p.name) for p in illustrations]
files += [(root / 'assets/subjects/PROMPTS.json', 'bandeaux/PROMPTS.json')]
files += [(p, 'fonds-matieres/' + p.name) for p in sorted((root / 'assets/subject-backgrounds').glob('*.png'))]
files += [(root / 'assets/subject-backgrounds/PROMPTS.json', 'fonds-matieres/PROMPTS.json')]

files += [(root / 'assets' / name, 'fond/' + name) for name in ['workspace-banner-v1.png', 'workspace-banner-v1.PROMPT.json', 'workspace-banner-v2.png', 'workspace-banner-v2.PROMPT.json', 'workspace-banner-v3.png', 'workspace-banner-v3.PROMPT.json']]
files += [(root / 'test-output/icon-catalog.png', 'icon-catalog.png'),
          (root / 'assets/fonts/NotoSerif-OFL.txt', 'NotoSerif-OFL.txt'),
          (root / 'licenses/LICENSE-MIT', 'LICENSE-MIT.txt'),
          (root / 'scripts/generate_icons.py', 'sources/generate_icons.py'),
          (root / 'scripts/generate_app_icon.py', 'sources/generate_app_icon.py')]
with ZipFile(destination, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
    for path, name in files:
        assert path.is_file(), path
        archive.write(path, name)
    archive.writestr('LIRE-MOI.txt', 'ÉCRINATOR — ressources graphiques Ergonatus\n\n92 pictogrammes SVG, planche SVG/PNG, icône Windows et 13 illustrations distinctes pour les matières, plus le fond panoramique IA et sa consigne dans fond/.\nLes noms de fichiers correspondent aux actions du logiciel.\nLes symboles sont convertis en tracés : aucune police n’est requise pour afficher les SVG.\nLes images ont été générées avec ImageGen ; leurs consignes sont dans bandeaux/PROMPTS.json.\nPour les SVG : scripts dans le dossier sources du projet Écrinator, fontTools et Noto Serif.\nLes ressources originales suivent la licence du projet ; les contours de police gardent la SIL OFL jointe.\nLes attributions détaillées sont dans ATTRIBUTION.md.\n')
print(destination)

backgrounds = sorted((root / 'assets/subject-backgrounds').glob('*.png'))
assert len(backgrounds) == 13
background_zip = root / f'dist/Ecrinator-{version}-fonds-matieres.zip'
with ZipFile(background_zip, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
    for path in backgrounds:
        archive.write(path, path.name)
    archive.write(root / 'assets/subject-backgrounds/PROMPTS.json', 'PROMPTS.json')
    archive.write(root / 'assets/ATTRIBUTION.md', 'ATTRIBUTION.md')
    archive.writestr('LIRE-MOI.txt', 'Écrinator — 13 fonds de matière originaux ImageGen.\nPNG sources conservés sans modification. Le logiciel adapte leur affichage sans modifier ces fichiers.\nConsignes exactes et origine dans PROMPTS.json.\n')
print(background_zip)

library_zip=root/f'dist/Ecrinator-{version}-bibliotheque-scolaire.zip'
with ZipFile(library_zip,'w',ZIP_DEFLATED,compresslevel=9) as archive:
    with ZipFile(root/'assets/library/library.eclib') as pack:
        for name in pack.namelist():
            archive.writestr(name, pack.read(name))
print(library_zip)
