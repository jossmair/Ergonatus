from pathlib import Path
import shutil
import sys
import json
import hashlib
import os
import psutil
import argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shared.ui.theme import APP_THEMES
root=Path(__file__).resolve().parents[1]
source=root/'.package-satellites/ErgonatusSatellites'
parser=argparse.ArgumentParser();parser.add_argument('--app',action='append');args=parser.parse_args()
selected={key for key in APP_THEMES if key not in ('ergonatus','claviernator','precisionator','transcrinator','redactor','ecrinator','pdfinator')}
if args.app:
    if not set(args.app)<=selected:parser.error('Application inconnue ou originale non remplaçable.')
    selected=set(args.app)
targets={os.path.normcase(str((root/item['folder']/'runtime'/(item['folder']+'.exe')).resolve())):item['name'] for key,item in APP_THEMES.items() if key in selected}
for process in psutil.process_iter(['exe']):
    try:
        executable=process.info.get('exe')
        if executable and os.path.normcase(str(Path(executable).resolve())) in targets:
            raise SystemExit('Fermez '+targets[os.path.normcase(str(Path(executable).resolve()))]+' avant le conditionnement. Aucun fichier remplacé.')
    except (psutil.AccessDenied,psutil.NoSuchProcess):pass
manifest_path=root/'docs/SATELLITES_ASSEMBLY.json'
manifest=[item for item in json.loads(manifest_path.read_text()) if item['app'] not in selected] if manifest_path.exists() else []
for key,item in APP_THEMES.items():
    if key not in selected:continue
    folder=root/item['folder'];runtime=folder/'runtime';runtime.mkdir(exist_ok=True)
    shutil.copytree(source/'_internal',runtime/'_internal',dirs_exist_ok=True)
    exe=runtime/(item['folder']+'.exe');shutil.copy2(source/(item['folder']+'.exe'),exe)
    (folder/'main.py').write_text('from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]))\nfrom run_satellite import main\nif __name__=="__main__":\n    sys.argv[1:1]=["--app","'+key+'"]\n    raise SystemExit(main())\n',encoding='utf-8')
    (folder/('Lancer '+item['folder']+'.cmd')).write_text('@echo off\nstart "" "%~dp0runtime\\'+item['folder']+'.exe"\n',encoding='utf-8')
    manifest.append(dict(app=key,executable=str(exe.relative_to(root)),sha256=hashlib.sha256(exe.read_bytes()).hexdigest()))
(root/'docs/SATELLITES_ASSEMBLY.json').write_text(json.dumps(manifest,indent=2))
print(str(len(selected))+' satellite(s) conditionné(s) avec un runtime indépendant chacun.')
