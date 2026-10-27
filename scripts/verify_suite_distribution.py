"""Extract, hash-check and execute disposable release installations."""
from pathlib import Path
import sys,os,json,hashlib,subprocess,shutil,uuid,sqlite3
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/releases/2026.10.27';ASSETS=OUT/'assets'
SEVEN=OUT/'tools/extra/x64/7za.exe';report={}
def run(args,log,timeout=600,env=None):
    with (OUT/log).open('wb') as f:r=subprocess.run([str(a) for a in args],stdout=f,stderr=subprocess.STDOUT,timeout=timeout,env=env)
    assert r.returncode==0,(log,r.returncode);return r
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def clean(path):
    assert path.resolve().parent==OUT.resolve() and path.name in ('check-portable','check-install')
    if path.exists():shutil.rmtree(path)
def verify_tree(path):
    manifest=json.loads((path/'MANIFEST.json').read_text())
    for name,data in manifest['files'].items():
        p=path/name;assert p.is_file() and p.stat().st_size==data['bytes'] and sha(p)==data['sha256'],name
    db=sqlite3.connect((path/'Dictionnator/data/dictionary.sqlite3').as_uri()+'?mode=ro',uri=True)
    assert db.execute('SELECT word FROM entries LIMIT 1').fetchone();db.close()
    assert (path/'ergoai/grammar/vendor').is_dir()
    return len(manifest['files'])
def smoke(path,prefix):
    env=dict(os.environ,USERDOMAIN='Release'+uuid.uuid4().hex,ERGONATUS_DATA=str(path/'Data-test'),ERGONATUS_TEST_MODE='1',ERGONATUS_NO_HOTKEYS='1')
    for app,exe in [('hub','Hub/Ergonatus.exe'),('dictionary','Dictionnator/runtime/Dictionnator.exe'),('tables','Tablinator/runtime/Tablinator.exe')]:
        run([path/exe,'--smoke-test'],prefix+'-'+app+'.log',90,env)
    run([path/'Ecrinator/runtime/Ecrinator.exe','--verify',path/'ecrinator-verification'],prefix+'-ecrinator.log',180,env)
portable=OUT/'check-portable';clean(portable)
run([SEVEN,'t',ASSETS/'Ergonatus-2026.10.27-portable.zip.001'],'portable-crc.log')
run([SEVEN,'x',ASSETS/'Ergonatus-2026.10.27-portable.zip.001','-o'+str(portable),'-y'],'portable-extraction.log')
report['portable_files_verified']=verify_tree(portable/'Ergonatus');smoke(portable/'Ergonatus','portable');report['portable_verified']=True
(OUT/'verification-progress.json').write_text(json.dumps(report,indent=2));clean(portable)
installed=OUT/'check-install';clean(installed)
run([ASSETS/'Ergonatus-2026.10.27-Setup.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/TESTINSTALL=1','/DIR='+str(installed),'/LOG='+str(OUT/'installer-test.log')],'installer-console.log',900)
report['installer_files_verified']=verify_tree(installed);smoke(installed,'installed');report['installer_verified']=True;clean(installed)
report['assets']={p.name:sha(p) for p in ASSETS.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt'}
sums=''.join(digest+'  '+name+'\n' for name,digest in sorted(report['assets'].items()));(ASSETS/'SHA256SUMS.txt').write_text(sums,encoding='utf-8');report['assets']['SHA256SUMS.txt']=sha(ASSETS/'SHA256SUMS.txt')
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
