"""Create a self-contained Windows portable ZIP from explicit runtime directories."""
from pathlib import Path
import sys,os,json,hashlib,zipfile,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
out=ROOT/'output/releases';out.mkdir(parents=True,exist_ok=True)
target=out/'Ergonatus-portable-2026-10-25.zip'
assert not target.exists(),target
files={}
excluded={'.venv','__pycache__','.previous','.git','cache','logs','.pytest_cache','originals','data'}
def add_tree(folder):
    for base,dirs,names in os.walk(ROOT/folder):
        dirs[:]=[d for d in dirs if d.lower() not in excluded and not d.startswith('.backup')]
        for name in names:
            p=Path(base)/name
            if p.suffix.lower() in ('.pyc','.pyo','.log','.sqlite','.sqlite3','.db') or p.name in ('live-layout.json','window.json'):continue
            files[p.relative_to(ROOT).as_posix()]=p
add_tree('Hub/_internal');files['Hub/Ergonatus.exe']=ROOT/'Hub/Ergonatus.exe'
for key,item in APP_THEMES.items():
    if key!='ergonatus':add_tree(item['folder']+'/runtime')
for name in ('assets','models','ergoai','shared','orb_manager'):add_tree(name)
for name in ('suite_design.py','run_ergoai.py','run_ergovoice.py','run_proofreader.py','run_translation.py','run_translation_voice.py'):
    files[name]=ROOT/name
# Package fresh builds directly, even when the installed suite is open.
for source,destination in [(ROOT/'.portable-package/Ergonatus','Hub'),(ROOT/'.portable-planinator/ErgonatusSatellites','Planinator/runtime')]:
    assert source.is_dir(),source
    for p in source.rglob('*'):
        if p.is_file():files[destination+'/'+p.relative_to(source).as_posix()]=p
total=sum(p.stat().st_size for p in files.values());print(json.dumps(dict(files=len(files),uncompressed_bytes=total)),flush=True)
launcher='@echo off\r\ncd /d "%~dp0"\r\nset "ERGONATUS_DATA=%~dp0Data"\r\nset "TRANSCRI_DATA=%~dp0Data\\Transcrinator"\r\nset "REDACTOR_DATA_DIR=%~dp0Data\\Redactor"\r\nstart "" "%~dp0Hub\\Ergonatus.exe" --data-dir "%~dp0Data\\hub"\r\n'
readme='ERGONATUS — VERSION PORTABLE — 25 octobre 2026\n\n1. Extraire TOUT le ZIP dans un dossier accessible en écriture.\n2. Ouvrir « Lancer Ergonatus.cmd ». Aucun Python ni installation nécessaire.\n3. Cocher les applications souhaitées dans le hub.\n\nConserver tous les sous-dossiers : ils contiennent les moteurs, modèles et voix locales. Le lancement principal conserve les données des nouveaux outils dans Data. Certains logiciels historiques conservent leurs préférences Windows habituelles.\n\nUn clic sur l’Orb du hub affiche les 18 logiciels avec leurs noms et fonctions. Double-clic : ouvrir le hub. Quitter Ergonatus arrête la suite.\n\nCette archive contient les logiciels et ressources de fonctionnement, sans les historiques, profils et notes personnels du poste de développement.\n'
manifest={};written=0;last=time.monotonic()
with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=2,allowZip64=True) as z:
    z.writestr('Ergonatus/Lancer Ergonatus.cmd',launcher);z.writestr('Ergonatus/LIRE-MOI.txt',readme)
    for name,p in sorted(files.items()):
        z.write(p,'Ergonatus/'+name)
        digest=hashlib.sha256()
        with p.open('rb') as stream:
            for block in iter(lambda:stream.read(8*1024**2),b''):digest.update(block)
        manifest[name]=dict(bytes=p.stat().st_size,sha256=digest.hexdigest());written+=p.stat().st_size
        if time.monotonic()-last>25:print(str(round(written/total*100))+' %',flush=True);last=time.monotonic()
    z.writestr('Ergonatus/PORTABLE-MANIFEST.json',json.dumps(dict(version='2026.10.25',files=manifest),ensure_ascii=False,indent=2))
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    for key,item in APP_THEMES.items():
        if key=='ergonatus':continue
        expected=('Ergonatus/'+item['folder']+'/runtime/'+item['folder']+'.exe').casefold()
        assert expected in {n.casefold() for n in z.namelist()},key
report=dict(archive=str(target),files=len(files),uncompressed_bytes=total,zip_bytes=target.stat().st_size,crc_verified=True)
(out/'Ergonatus-portable-2026-10-25.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
