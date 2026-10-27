"""Offline asset verification. Never downloads, never infers backend performance."""
import hashlib
import json
from pathlib import Path

def digest(path):
    sha=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''): sha.update(chunk)
    return sha.hexdigest()

def verify(root):
    root=Path(root)
    manifest=json.loads((root/'ergoai/transcription/bundle.json').read_text(encoding='utf-8'))
    result=[]
    for key,item in manifest['models'].items():
        path=root/'ergoai/transcription/models'/item['file']
        result.append(dict(model=key,valid=path.is_file() and path.stat().st_size==item['bytes'] and digest(path)==item['sha256']))
    from ergoai.models import MODELS
    for model in MODELS:
        path=root/'models'/model['filename']
        result.append(dict(model=model['filename'],valid=path.is_file() and path.stat().st_size==model['size'] and digest(path)==model['sha256']))
    return result

if __name__=='__main__':
    result=verify(Path(__file__).resolve().parents[1]);print(json.dumps(result,indent=2))
    raise SystemExit(0 if all(item['valid'] for item in result) else 1)
