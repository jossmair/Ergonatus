"""Create a local update package; never downloads or publishes anything."""
from pathlib import Path
import argparse,hashlib,json,sys,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shared.ui.theme import APP_THEMES
parser=argparse.ArgumentParser();parser.add_argument('app',choices=[k for k in APP_THEMES if k!='ergonatus']);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
root=Path(__file__).resolve().parents[1];runtime=root/APP_THEMES[args.app]['folder']/'runtime'
if not runtime.is_dir():raise SystemExit('Logiciel non installé.')
files={}
paths=sorted(path for path in runtime.rglob('*') if path.is_file())
for path in paths:
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024**2),b''):digest.update(chunk)
    files['runtime/'+path.relative_to(runtime).as_posix()]=digest.hexdigest()
args.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
    archive.writestr('package.json',json.dumps(dict(schema=1,app=args.app,files=files)))
    for path in paths:archive.write(path,'runtime/'+path.relative_to(runtime).as_posix())
print(str(args.output.resolve()))
