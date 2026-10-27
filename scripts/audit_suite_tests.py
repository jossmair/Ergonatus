"""Run each test file in a separate process: reliable Qt lifetime and bounded tests."""
from pathlib import Path
import subprocess,sys,time,json,os
import argparse
parser=argparse.ArgumentParser(description='Only explicitly reviewed current tests may be run by the audit.')
parser.add_argument('--reviewed-tests',nargs='+',required=True)
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/audit/2026-10-25';OUT.mkdir(parents=True,exist_ok=True)
rows=[]
for filename in args.reviewed_tests:
    path=ROOT/'tests'/filename
    if path.parent!=ROOT/'tests' or not path.is_file() or not path.name.startswith('test_'):raise ValueError('Test invalide: '+filename)
    start=time.monotonic();env=os.environ.copy();env['PYTHONUNBUFFERED']='1'
    try:
        r=subprocess.run([sys.executable,'-u','-m','pytest','-p','no:cacheprovider',str(path),'-q','--tb=short'],cwd=ROOT,env=env,capture_output=True,timeout=100)
        output=(r.stdout+r.stderr).decode(errors='replace');status=r.returncode
    except subprocess.TimeoutExpired as error:
        output=((error.stdout or b'')+(error.stderr or b'')).decode(errors='replace');status='timeout'
    (OUT/(path.stem+'.log')).write_text(output,encoding='utf-8')
    row=dict(file=path.name,exit=status,seconds=round(time.monotonic()-start,2),summary=output[-1600:]);rows.append(row)
    (OUT/'tests.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row,ensure_ascii=True),flush=True)
