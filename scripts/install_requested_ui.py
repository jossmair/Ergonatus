"""Install reviewed satellite UI binaries, preserving documents and native apps."""
from pathlib import Path
import sys,json,hashlib,shutil,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
TARGET=Path('C:/Users/Josselin/Desktop/Ergonatus').resolve()
OUT=ROOT/'output/ui-revision-2026-10-27';BACKUP=OUT/'rollback';BACKUP.mkdir(exist_ok=True)
selected={key:item for key,item in APP_THEMES.items() if key not in ('ergonatus','claviernator','precisionator','transcrinator','redactor','ecrinator','pdfinator')}
targets={str((TARGET/item['folder']/'runtime'/(item['folder']+'.exe')).resolve()).casefold() for item in selected.values()}
active=[]
for p in psutil.process_iter(['exe']):
    try:
        if (p.info['exe'] or '').casefold() in targets:active.append(p.info['exe'])
    except psutil.Error:pass
if active:raise SystemExit('Logiciels ouverts : '+', '.join(active))
def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
changes=[];versions=[]
def copy(source,destination):
    assert destination.resolve().is_relative_to(TARGET)
    new=digest(source);old=digest(destination) if destination.exists() else None
    if old==new:return
    if old and not (BACKUP/old).exists():shutil.copy2(destination,BACKUP/old)
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
    assert digest(destination)==new
    changes.append(dict(path=str(destination.relative_to(TARGET)),before=old,after=new))
for key,item in selected.items():
    relative=Path(item['folder'])/'runtime';source=ROOT/relative
    assert (source/(item['folder']+'.exe')).is_file()
    for path in source.rglob('*'):
        if path.is_file() and '.previous' not in path.parts:copy(path,TARGET/relative/path.relative_to(source))
    versions.append(dict(app=key,sha256=digest(TARGET/relative/(item['folder']+'.exe'))))
    print(key,flush=True)
for name in ('suite_design.py','suite_interactions.py','suite_interactions.json'):copy(ROOT/name,TARGET/name)
(OUT/'installed-ui.json').write_text(json.dumps(dict(changes=changes,versions=versions),indent=2),encoding='utf-8')
print('15 satellites synchronisés ; logiciels natifs, moteurs et documents préservés.',flush=True)
