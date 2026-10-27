"""Record the actual installed builds; old audit reports are never a version source."""
from pathlib import Path
import sys,json,hashlib,re
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from shared.ui.theme import APP_THEMES
OUT=ROOT/'output/audit/current';OUT.mkdir(parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
rows=[]
for key,item in APP_THEMES.items():
    exe=ROOT/'Hub/Ergonatus.exe' if key=='ergonatus' else ROOT/item['folder']/'runtime'/(item['folder']+'.exe')
    if not exe.exists():exe=next(exe.parent.glob('*.exe'),exe)
    source_version=None;cargo=ROOT/item['folder']/'Cargo.toml'
    if cargo.exists():source_version=re.search(r'^version\s*=\s*"([^"]+)"',cargo.read_text(),re.M)[1]
    rows.append(dict(app=key,name=item['name'],executable=str(exe.relative_to(ROOT)),exists=exe.exists(),sha256=sha(exe) if exe.exists() else None,source_version=source_version,modified_utc=datetime.fromtimestamp(exe.stat().st_mtime,timezone.utc).isoformat() if exe.exists() else None))
sources={}
for folder in ['Hub','shared','orb_manager','ergoai']:
    for p in (ROOT/folder).rglob('*.py'):
        if not {'_internal','vendor','__pycache__','.venv'} & set(p.parts):sources[str(p.relative_to(ROOT))]=sha(p)
sources['suite_design.py']=sha(ROOT/'suite_design.py')
engines=[]
for folder in ('runtime','proofreading/runtime','translation/runtime','voice/runtime','translation_voice/runtime'):
    for p in (ROOT/'ergoai'/folder).glob('*.exe'):
        engines.append(dict(executable=str(p.relative_to(ROOT)),sha256=sha(p)))
record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),apps=rows,engines=engines,sources=sources,policy='Audit results must identify these exact executable hashes. Historical screenshots and tests are not current validation.')
(OUT/'versions.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=True,indent=2))
