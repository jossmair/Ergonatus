"""Bounded cleanup inventory. Deletion is performed separately with literal PowerShell paths."""
import os,json,hashlib,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/maintenance';REPORT.mkdir(exist_ok=True)
def files_under(path):
    if path.is_symlink() or path.is_junction():raise ValueError('Linked target: '+str(path))
    if path.is_file():yield path;return
    for base,dirs,files in os.walk(path,followlinks=False):
        for name in dirs:
            p=Path(base)/name
            if p.is_symlink() or p.is_junction():raise ValueError('Linked directory: '+str(p))
        for name in files:
            p=Path(base)/name
            if p.is_symlink():raise ValueError('Linked file: '+str(p))
            yield p
def stat_tree(path):
    logical=0;unique=0;count=0;seen=set()
    for p in files_under(path):
        s=p.stat();logical+=s.st_size;count+=1
        identity=(s.st_dev,s.st_ino)
        if identity not in seen:unique+=s.st_size;seen.add(identity)
    return dict(bytes=logical,unique_bytes=unique,files=count)
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def plan():
    before=stat_tree(ROOT);candidates={}
    def add(p,reason):
        p=p.resolve();p.relative_to(ROOT)
        if p==ROOT:raise ValueError('Root target')
        candidates[p]=reason
    for p in ROOT.iterdir():
        if p.is_dir() and (p.name.startswith(('.build','.package','.qa')) or p.name in ('.pytest_cache','.test-data','tmp','__pycache__')):add(p,'Build, test output or cache')
        if p.is_file() and p.name.startswith('.') and (p.suffix=='.log' or p.name=='.piper-voices-catalog.json'):add(p,'Historical build/test log or downloaded catalog')
    for name in ('Claviernator','Precisionator','Transcrinator','Redactor'):
        for p in (ROOT/name).iterdir():
            if p.is_dir() and (p.name in ('.build-orb','.rebuilt') or p.name.startswith('runtime-before-bridge-')):add(p,'Superseded deployment or build copy')
            if p.is_file() and p.name.startswith('.build') and p.suffix=='.log':add(p,'Historical build log')
    add(ROOT/'ergoai/voice/.venv','Build-only environment; both packaged voice engines are installed')
    for name in ('Ecrinator','PDFinator'):
        # The standalone Rust editions replace the old Python placeholders.
        if (ROOT/name/'runtime/_internal').is_dir():add(ROOT/name/'runtime','Superseded Python placeholder runtime; native editions are protected')
    for name in ('qwen2.5-0.5b-instruct-q4_k_m.gguf','qwen2.5-0.5b-instruct-q4_k_m.receipt.json'):add(ROOT/'models'/name,'Superseded translation model; current translator uses Luth')
    # Source bytecode is reproducible. Packaged runtime bytecode is deliberately preserved.
    for parent in ('shared','ergoai','tests','scripts','Hub','orb_manager','Claviernator/source','Precisionator/source','Transcrinator/source','Redactor/source'):
        for base,dirs,files in os.walk(ROOT/parent):
            dirs[:]=[d for d in dirs if d not in ('runtime','_internal','.venv','site-packages')]
            if Path(base).name=='__pycache__':add(Path(base),'Source bytecode cache');dirs.clear()
    selected=[]
    for p,reason in sorted(candidates.items(),key=lambda x:len(x[0].parts)):
        if not p.exists() or any(p.is_relative_to(parent) for parent,_,_ in selected):continue
        selected.append((p,reason,stat_tree(p)))
    # Keep tiny historical logs compressed for audit traceability.
    with zipfile.ZipFile(REPORT/'historique-journaux-2026-10-20.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p,reason,_ in selected:
            if p.is_file() and p.suffix=='.log':z.write(p,p.relative_to(ROOT))
    protected=[]
    exact={str(p) for p,_,_ in selected if p.is_file()}
    prefixes=tuple(str(p)+os.sep for p,_,_ in selected if p.is_dir())
    for p in files_under(ROOT):
        if str(p) in exact or str(p).startswith(prefixes):continue
        if p.suffix.lower() in ('.exe','.gguf','.onnx') and ('runtime' in p.parts or '_internal' in p.parts or 'models' in p.parts or 'voices' in p.parts or p.parent==ROOT/'Hub'):
            protected.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=digest(p)))
    document=dict(root=str(ROOT),before=before,candidates=[dict(path=str(p),relative=str(p.relative_to(ROOT)),reason=r,**s) for p,r,s in selected],protected=protected)
    (REPORT/'cleanup-plan-2026-10-20.json').write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(before_gb=round(before['bytes']/1e9,3),removable_gb=round(sum(s['bytes'] for _,_,s in selected)/1e9,3),targets=len(selected),protected_files=len(protected))))
if __name__=='__main__':plan()
