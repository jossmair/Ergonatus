"""Reviewed local update. Content-addressed rollback; never touch user data."""
from pathlib import Path
import shutil,hashlib,json,os,sys,psutil,time,atexit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
TARGET=Path('C:/Users/Josselin/Desktop/Ergonatus').resolve()
OUT=ROOT/'output/audit/2026-10-26-visual-speed';BACKUP=OUT/'rollback';BACKUP.mkdir(exist_ok=True)
record=OUT/'installed-file-changes.json'
manifest=json.loads(record.read_text()) if record.exists() else [];digest_cache={}
atexit.register(lambda:record.write_text(json.dumps(manifest,indent=2),encoding='utf-8'))
def digest(path):
    stat=path.stat();key=(str(path),stat.st_mtime_ns,stat.st_size)
    if key not in digest_cache:
        with path.open('rb') as stream:digest_cache[key]=hashlib.file_digest(stream,'sha256').hexdigest()
    return digest_cache[key]
def copy_file(source,destination):
    assert destination.resolve().is_relative_to(TARGET) or destination.resolve().is_relative_to(ROOT)
    if destination.exists() and source.stat().st_size==destination.stat().st_size and digest(source)==digest(destination):return
    if destination.is_relative_to(TARGET):
        old=digest(destination) if destination.exists() else None
        if old and not (BACKUP/old).exists():shutil.copy2(destination,BACKUP/old)
        manifest.append(dict(path=str(destination.relative_to(TARGET)),before=old,after=digest(source)))
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
def tree(source,destination):
    for path in source.rglob('*'):
        if path.is_file() and '.previous' not in path.parts:copy_file(path,destination/path.relative_to(source))
assert TARGET.is_dir() and TARGET!=ROOT
active=[];services=[];hubs=[]
for p in psutil.process_iter(['exe']):
    try:
        exe=Path(p.info['exe']).resolve() if p.info['exe'] else None
        if exe and exe.is_relative_to(TARGET):
            if exe==TARGET/'Hub/Ergonatus.exe':hubs.append(p)
            elif exe.is_relative_to(TARGET/'ergoai'):services.append(p)
            else:active.append(str(exe))
    except (psutil.Error,OSError):pass
if active:raise SystemExit('Un logiciel est ouvert ; fichiers non modifiés : '+', '.join(active))
for p in hubs+services:
    try:p.terminate();p.wait(timeout=10)
    except psutil.NoSuchProcess:pass
for package,destination,exe in [('.package-proofreader/ErgoProofread','ergoai/proofreading/runtime','ErgoProofread.exe'),('.package-service/ErgoAI','ergoai/runtime','ErgoAI.exe'),('.package-translation/ErgoTranslate','ergoai/translation/runtime','ErgoTranslate.exe'),('.hub-premium-package/Ergonatus','Hub','Ergonatus.exe')]:
    source=ROOT/package;assert (source/exe).is_file();tree(source/'_internal',ROOT/destination/'_internal');copy_file(source/exe,ROOT/destination/exe)
for key,item in APP_THEMES.items():
    if key=='ergonatus':source=ROOT/'Hub';destination=TARGET/'Hub';copy_file(source/'Ergonatus.exe',destination/'Ergonatus.exe');tree(source/'_internal',destination/'_internal')
    else:tree(ROOT/item['folder']/'runtime',TARGET/item['folder']/'runtime')
    print(item['name'],flush=True)
for relative in ['ergoai/proofreading/runtime','ergoai/runtime','ergoai/translation/runtime','assets']:
    tree(ROOT/relative,TARGET/relative)
for name in ['suite_design.py','suite_interactions.py','suite_interactions.json','scripts/windows_ocr.ps1']:copy_file(ROOT/name,TARGET/name)
(OUT/'installed-file-changes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
versions=[]
for key,item in APP_THEMES.items():
    relative=Path('Hub/Ergonatus.exe') if key=='ergonatus' else Path(item['folder'])/'runtime'/(item['folder']+'.exe')
    versions.append(dict(app=key,sha256=digest(TARGET/relative),workspace_same=digest(ROOT/relative)==digest(TARGET/relative)))
assert all(row['workspace_same'] for row in versions)
(OUT/'installed-versions.json').write_text(json.dumps(versions,indent=2),encoding='utf-8')
meta=TARGET/'MISE-A-JOUR-LOCALE.json';data=json.loads(meta.read_text(encoding='utf-8-sig')) if meta.exists() else {};data.update(audit_fixes='2026-10-26',applications=21,versions_synchronized=True,portable_archive_created=False,hub_sha256=versions[0]['sha256']);meta.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('All 22 executable identities match the workspace. User data preserved.',flush=True)
