"""Install reviewed local build files without producing a distribution archive."""
from pathlib import Path
import shutil,psutil,os,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
jobs=[(ROOT/'.fix-package/proofreader/ErgoProofread',ROOT/'ergoai/proofreading/runtime','ErgoProofread.exe'),(ROOT/'.fix-package/translation/ErgoTranslate',ROOT/'ergoai/translation/runtime','ErgoTranslate.exe'),(ROOT/'.fix-package/hub/Ergonatus',ROOT/'Hub','Ergonatus.exe')]
if '--engines-only' not in sys.argv:
    for key,item in APP_THEMES.items():
        if key not in ('ergonatus','claviernator','precisionator','transcrinator','redactor','ecrinator','pdfinator'):
            jobs.append((ROOT/'.fix-package/satellites/ErgonatusSatellites',ROOT/item['folder']/'runtime',item['folder']+'.exe'))
for source,target,exe in jobs:
    assert (source/exe).is_file() and (source/'_internal').is_dir()
    assert target.resolve().is_relative_to(ROOT)
paths={os.path.normcase(str(t/e)) for _,t,e in jobs}
for p in psutil.process_iter(['exe']):
    if p.info['exe'] and os.path.normcase(p.info['exe']) in paths:raise SystemExit('Fermer avant remplacement : '+p.info['exe'])
records=[]
for source,target,exe in jobs:
    target.mkdir(parents=True,exist_ok=True);shutil.copytree(source/'_internal',target/'_internal',dirs_exist_ok=True);shutil.copy2(source/exe,target/exe)
    records.append(dict(executable=str((target/exe).relative_to(ROOT)),sha256=hashlib.sha256((target/exe).read_bytes()).hexdigest()));print(exe,flush=True)
manifest=ROOT/'output/audit/current/local-fixes-installed.json'
previous=json.loads(manifest.read_text()) if manifest.exists() else []
merged={item['executable']:item for item in previous}
merged.update({item['executable']:item for item in records})
manifest.write_text(json.dumps(list(merged.values()),indent=2))
