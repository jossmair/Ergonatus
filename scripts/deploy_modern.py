"""Install the verified modern builds without changing Rust applications or user data."""
from pathlib import Path
import hashlib,json,shutil,os
import psutil
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
jobs=[]
for key,version in [('claviernator','1.3.10'),('precisionator','1.0.7'),('transcrinator','1.3.17'),('redactor','0.4.1')]:
    name=APP_THEMES[key]['folder']
    jobs.append((key,ROOT/'.modern-package'/key/(name+'-'+version),ROOT/name/'runtime',name+'.exe'))
for key,item in APP_THEMES.items():
    if key in ('ergonatus','claviernator','precisionator','transcrinator','redactor','ecrinator','pdfinator'):continue
    jobs.append((key,ROOT/'.modern-package/satellites/ErgonatusSatellites',ROOT/item['folder']/'runtime',item['folder']+'.exe'))
jobs.append(('ergonatus',ROOT/'.modern-package/hub/Ergonatus',ROOT/'Hub','Ergonatus.exe'))
for key,source,target,exe in jobs:
    assert (source/exe).is_file() and (source/'_internal').is_dir(),key
    assert target.resolve().is_relative_to(ROOT)
targets={os.path.normcase(str(target/exe)) for _,_,target,exe in jobs}
for p in psutil.process_iter(['exe']):
    if p.info['exe'] and os.path.normcase(p.info['exe']) in targets:raise SystemExit('Application encore ouverte: '+p.info['exe'])
records=[]
for key,source,target,exe in jobs:
    target.mkdir(exist_ok=True)
    shutil.copytree(source/'_internal',target/'_internal',dirs_exist_ok=True)
    shutil.copy2(source/exe,target/exe)
    records.append(dict(app=key,executable=str((target/exe).relative_to(ROOT)),sha256=hashlib.sha256((target/exe).read_bytes()).hexdigest()))
    print('Installed '+key,flush=True)
(ROOT/'docs/maintenance/modern-installed-2026-10-24.json').write_text(json.dumps(records,indent=2))
manifest=ROOT/'docs/SATELLITES_ASSEMBLY.json'
old=json.loads(manifest.read_text())
updated={r['app']:r for r in records if r['app'] not in ('ergonatus','claviernator','precisionator','transcrinator','redactor')}
manifest.write_text(json.dumps([updated.pop(r['app'],r) for r in old]+list(updated.values()),indent=2))
