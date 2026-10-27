"""Install generated PNGs only in copied distributions, preserving original artwork.

Native existing animation, hit targets, input handling and timers stay unchanged.
No network, no rebuilt satellite executable, no modification of upstream projects.
"""
from pathlib import Path
import shutil
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]

def install():
    mappings={
        'claviernator':[f'Claviernator/runtime/_internal/assets/keyboard/frames/core-{i:02}.png' for i in range(4)],
        'precisionator':[f'Precisionator/runtime/_internal/assets/frames/core-{i:02}.png' for i in range(4)],
        'transcrinator':[f'Transcrinator/runtime/_internal/assets/hud-orange/frames/core-{i:02}.png' for i in range(4)],
        'redactor':['Redactor/runtime/_internal/assets/orbs/ruby-v2.png'],
    }
    records=[]
    for app_id,targets in mappings.items():
        source=ROOT/'assets/orbs'/f'{app_id}.png'
        if not source.is_file(): raise RuntimeError(f'Image absente : {app_id}')
        for relative in targets:
            target=ROOT/relative
            if not target.is_file(): raise RuntimeError(f'Ressource native absente : {relative}')
            backup=ROOT/'assets/originals'/relative
            backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists(): shutil.copy2(target,backup)
            shutil.copy2(source,target)
            records.append(dict(path=relative,original_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
                                generated_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    (ROOT/'docs/ORB_ASSETS.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(f'{len(records)} ressources installées, originaux conservés.')

if __name__=='__main__': install()
