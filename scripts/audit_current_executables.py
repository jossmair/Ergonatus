"""Fresh installed-executable observations, tied to the exact baseline hashes."""
from pathlib import Path
import json,os,subprocess,tempfile,uuid,time,hashlib,psutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/audit/current';CAP=OUT/'captures';CAP.mkdir(exist_ok=True)
baseline=json.loads((OUT/'versions.json').read_text(encoding='utf-8'));rows=[]
for item in baseline['apps']:
    key=item['app']
    if key in ('claviernator','precisionator','redactor','transcrinator','ecrinator','pdfinator'):continue
    exe=ROOT/item['executable'];assert hashlib.sha256(exe.read_bytes()).hexdigest()==item['sha256'],'Version changée depuis inventaire: '+key
    env=os.environ.copy();env.update(USERDOMAIN='CurrentAudit'+uuid.uuid4().hex,ERGONATUS_DATA=tempfile.mkdtemp(prefix='current-audit-'),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1',ERGONATUS_BACKGROUND_START='1')
    start=time.monotonic();args=[str(exe),'--smoke-test','--snapshot',str(CAP/(key+'.png'))]
    try:
        r=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,timeout=110);status=r.returncode;output=(r.stdout+r.stderr).decode(errors='replace')[-2000:]
    except subprocess.TimeoutExpired:status='timeout';output='Délai de vérification dépassé.'
    row=dict(app=key,sha256=item['sha256'],exit=status,seconds=round(time.monotonic()-start,2),capture_exists=(CAP/(key+'.png')).exists(),output=output,unchanged_after=hashlib.sha256(exe.read_bytes()).hexdigest()==item['sha256'])
    rows.append(row);(OUT/'executables.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row,ensure_ascii=True),flush=True)
    # A test owns a private identity. Its model must not remain resident and
    # distort the memory available to the following, unrelated test identity.
    for process in psutil.process_iter(['exe']):
        try:
            if process.info['exe'] and Path(process.info['exe']).is_relative_to(ROOT/'ergoai') and process.environ().get('USERDOMAIN')==env['USERDOMAIN']:
                process.terminate();process.wait(timeout=5)
        except (psutil.Error,ValueError):pass
