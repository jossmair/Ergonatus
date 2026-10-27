"""Explicit, private-data-free source and Windows payload staging."""
from pathlib import Path
import sys,os,json,shutil,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
OUT=ROOT/'output/releases/2026.10.27';PAYLOAD=OUT/'payload/Ergonatus';SOURCE=OUT/'source';ASSETS=OUT/'assets'
for d in (PAYLOAD,SOURCE,ASSETS):d.mkdir(parents=True,exist_ok=True)
EXCLUDED={'.git','.venv','__pycache__','.pytest_cache','.previous','cache','logs','data','output','build','dist','target','target-release','test-output','release','.tools','originals','reference','examples','audit','fortinator_reference'}
def copytree(relative,destination,source=False):
    start=ROOT/relative
    if not start.exists():return
    for base,dirs,names in os.walk(start):
        dirs[:]=[d for d in dirs if d.lower() not in EXCLUDED and not d.startswith(('.backup','.test')) and not (source and d.lower() in ('runtime','runtimes','_internal','models','voices','.package','.build'))]
        for name in names:
            p=Path(base)/name
            if source and 'docs' in p.relative_to(start).parts and not any(part in p.relative_to(start).parts for part in ('third-party','licenses','sources')):continue
            if source and p.suffix.lower() in ('.png','.jpg','.jpeg','.webp') and 'assets' not in p.parts:continue
            if name in ('live-layout.json','window.json','.env') or p.suffix.lower() in ('.log','.pyc','.pyo','.sqlite','.sqlite3','.db','.pem','.key','.pfx'):continue
            if source and (p.suffix.lower() in ('.exe','.dll','.pyd','.so','.a','.pdb','.lib','.gguf','.onnx','.bin','.zip','.7z','.pdf','.docx','.odt') or p.stat().st_size>90*1024**2):continue
            dest=destination/p.relative_to(start);dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists():continue
            if source or p.suffix.lower()=='.exe':shutil.copy2(p,dest)
            else:
                try:os.link(p,dest)
                except OSError:shutil.copy2(p,dest)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
# Runtime directories only: never distribute workspaces or personal stores.
copytree('Hub/_internal',PAYLOAD/'Hub/_internal');shutil.copy2(ROOT/'Hub/Ergonatus.exe',PAYLOAD/'Hub/Ergonatus.exe')
for key,item in APP_THEMES.items():
    if key!='ergonatus':copytree(item['folder']+'/runtime',PAYLOAD/item['folder']/'runtime')
for name in ('assets','models','ergoai','shared','orb_manager'):copytree(name,PAYLOAD/name)
dictionary=PAYLOAD/'Dictionnator/data';dictionary.mkdir(parents=True,exist_ok=True)
for p in (ROOT/'Dictionnator/data').iterdir():
    if p.is_file() and not (dictionary/p.name).exists():os.link(p,dictionary/p.name)
for name in ('suite_design.py','suite_interactions.py','suite_interactions.json','run_ergoai.py','run_ergovoice.py','run_proofreader.py','run_translation.py','run_translation_voice.py'):
    shutil.copy2(ROOT/name,PAYLOAD/name)
for key in ('Claviernator','Precisionator','Transcrinator','Redactor'):
    # Preserve the historical redistribution notices without their test captures.
    for name in ('LICENSE','LICENSE.txt','LICENCE.md'):
        p=ROOT/key/'source'/name
        if p.exists():dest=PAYLOAD/'licenses'/key/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    for relative in ('assets/licenses','docs/third-party'):copytree(key+'/source/'+relative,PAYLOAD/'licenses'/key/relative)
for key in ('Ecrinator','PDFinator'):copytree(key+'/licenses',PAYLOAD/'licenses'/key)
launcher='@echo off\r\ncd /d "%~dp0"\r\nset "ERGONATUS_DATA=%~dp0Data"\r\nset "TRANSCRI_DATA=%~dp0Data\\Transcrinator"\r\nset "REDACTOR_DATA_DIR=%~dp0Data\\Redactor"\r\nstart "" "%~dp0Hub\\Ergonatus.exe" --data-dir "%~dp0Data\\hub"\r\n'
(PAYLOAD/'Lancer Ergonatus.cmd').write_text(launcher,encoding='utf-8')
readme='''# Ergonatus — 27 octobre 2026

Suite Windows x64 : hub et 21 logiciels. Extraire tous les volumes de la version portable, puis ouvrir « Lancer Ergonatus.cmd ». Conserver le dossier complet : il contient les moteurs, voix et dictionnaire hors ligne. Aucun Python installé nécessaire.

Un clic sur l’orb du hub affiche les outils ; double-clic ouvre le hub ; clic droit ouvre le menu. Quitter le hub arrête la suite. Les aides et leurs actions dépendent de chaque application.

Corrector et Explicator : conversation SMS, texte envoyé à gauche, réponse à droite et icône Copier dans chaque réponse. Traductor : langues et discussion bilingue. Les propositions linguistiques restent à relire ; aucune garantie « zéro faute ».

Windows 10/11 x64, espace libre conseillé 15 Go, 8 Go de RAM minimum (16 Go conseillés pour l’IA). Accélération Vulkan si compatible, repli CPU. OCR selon les langues Windows installées. Applications non signées : Windows peut afficher un avertissement de réputation.

Les données des outils récents sont dans Data pour le lanceur portable. Certaines préférences des quatre applications historiques restent dans leur emplacement Windows habituel. Rien n’est configuré pour démarrer avec Windows par défaut.

Applications : Claviernator, Precisionator, Transcrinator, Redactor, Scanator, Écrinator, Organisator, Lector, Applinator, Temporator, Concentrator, PDFinator, Calculinator, Communicator, Memorinator, Planinator, Traductor, Corrector, Dictionnator, Explicator, Tablinator.

Sources : https://github.com/jossmair/Ergonatus
Les composants tiers, modèles et ressources conservent leurs licences respectives, fournies dans leurs dossiers et licenses/. Le dictionnaire dérive du Wiktionnaire via Kaikki (Dictionnator/data/LICENCE.md). Pas de licence globale nouvelle appliquée aux composants préexistants.
'''
(PAYLOAD/'LIRE-MOI.md').write_text(readme,encoding='utf-8')
# Clean source tree, including build resources but excluding compiled products.
for name in ('shared','orb_manager','Hub','assets','ergoai','scripts','tests'):
    copytree(name,SOURCE/name,True)
for item in APP_THEMES.values():
    folder=item['folder']
    if folder=='Hub':continue
    if folder in ('Claviernator','Precisionator','Transcrinator','Redactor'):copytree(folder+'/source',SOURCE/folder/'source',True)
    elif folder in ('Ecrinator','PDFinator'):
        for name in ('src','assets','licenses','scripts','tests','.cargo'):copytree(folder+'/'+name,SOURCE/folder/name,True)
        for name in ('Cargo.toml','Cargo.lock','build.rs','README.md','LICENSE','LICENSE-MIT','LICENSE-APACHE'):
            p=ROOT/folder/name
            if p.exists():(SOURCE/folder).mkdir(exist_ok=True);shutil.copy2(p,SOURCE/folder/name)
    else:
        for name in ('main.py','README.md'):
            p=ROOT/folder/name
            if p.exists():(SOURCE/folder).mkdir(exist_ok=True);shutil.copy2(p,SOURCE/folder/name)
for p in ROOT.iterdir():
    if p.is_file() and (p.suffix in ('.py','.ps1') or p.name.startswith('requirements')):shutil.copy2(p,SOURCE/p.name)
shutil.copy2(ROOT/'suite_interactions.json',SOURCE/'suite_interactions.json')
(SOURCE/'README.md').write_text(readme+'\n## Développement\n\nVoir BUILDING.md. Les moteurs compilés et modèles volumineux sont dans les téléchargements de release, séparés du dépôt Git.\n',encoding='utf-8')
(SOURCE/'BUILDING.md').write_text('''# Construire la suite

Python 3.12 x64 : créer un environnement virtuel puis installer requirements-dev.txt. Les tests Qt requièrent Windows. Les spécifications PyInstaller sont dans scripts/ ; satellites.spec produit les quinze satellites, deploy_satellites.py les place dans leurs dossiers. Le hub démarre via run_ergonatus.py.

Les quatre applications historiques conservent leurs sources et leurs instructions dans <application>/source/. Écrinator et PDFinator sont natifs Rust : installer Rust stable MSVC et le compilateur C++ Windows, puis cargo build --release dans chaque dossier. Cargo télécharge les dépendances du lockfile ; les dossiers target/ et vendor/ ne sont pas publiés.

Les données volumineuses ne sont pas dans Git : récupérer les volumes portables de cette release pour les modèles et runtimes ; les reçus de provenance sont inclus. Dictionnator/data contient le dictionnaire et sa licence dans la distribution.

Les scripts de publication ont des chemins de développement locaux à adapter ; ils ne sont pas des services de mise à jour. Aucune clé n’est incluse. Les binaires ne sont pas signés.
''',encoding='utf-8')
(SOURCE/'.gitignore').write_text('''__pycache__/
.venv/
.pytest_cache/
target/
target-release/
runtime/
_internal/
dist/
output/
.tools/
Data/
*.log
*.exe
*.dll
*.pdb
*.gguf
*.onnx
*.sqlite3
.env
''')
manifest={p.relative_to(PAYLOAD).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in PAYLOAD.rglob('*') if p.is_file()}
(PAYLOAD/'MANIFEST.json').write_text(json.dumps(dict(version='2026.10.27',files=manifest),indent=2))
(OUT/'staging.json').write_text(json.dumps(dict(files=len(manifest),bytes=sum(i['bytes'] for i in manifest.values()),executables={k:sha(PAYLOAD/(('Hub/Ergonatus.exe') if k=='ergonatus' else item['folder']+'/runtime/'+item['folder']+'.exe')) for k,item in APP_THEMES.items()}),indent=2))
print((OUT/'staging.json').read_text(),flush=True)
