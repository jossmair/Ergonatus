"""Active pinned models. Network is used only after explicit UI consent."""
from pathlib import Path
import hashlib
import json
import urllib.request
MODELS=[
    dict(filename='LFM2-700M-Q4_K_M.gguf',repository='kurakurai/Luth-LFM2-700M-GGUF',revision='a3ce71ba1dd188d2e84f31938280ab71774cbbb9',size=468625856,sha256='babe3c3e926a571aae2506f27cbd8c974a58cf2a12392a91c743c5c376384cc8',license='LFM Open License v1.0'),
    dict(filename='Luth-1.7B-Instruct-Q8_0.gguf',repository='kurakurai/Luth-1.7B-Instruct-GGUF',revision='9c0491062e197f8f68654584978bc05210edeb3a',size=1834425984,sha256='eac2cf4226524f3cc479b2e9774fc26cf6e7aac26f961f0892f824ab2f69a96f',license='Apache-2.0'),
]

def download_missing(root,cancel):
    from ergoai.inventory import digest
    root=Path(root);root.mkdir(parents=True,exist_ok=True);results=[]
    for model in MODELS:
        target=root/model['filename']
        if target.is_file() and target.stat().st_size==model['size'] and digest(target)==model['sha256']:results.append(target.name+' : déjà vérifié');continue
        part=target.with_suffix('.gguf.part')
        if part.exists() and part.stat().st_size>model['size']:raise ValueError('Un téléchargement partiel dépasse la taille prévue.')
        offset=part.stat().st_size if part.exists() else 0
        request=urllib.request.Request('https://huggingface.co/'+model['repository']+'/resolve/'+model['revision']+'/'+model['filename'],headers={'Range':f'bytes={offset}-'} if offset else {})
        if offset<model['size']:
            with urllib.request.urlopen(request,timeout=30) as response:
                resumed=offset>0 and response.status==206
                if resumed and not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):raise ValueError('Point de reprise non confirmé.')
                if not resumed:offset=0
                with part.open('ab' if resumed else 'wb') as output:
                    for chunk in iter(lambda:response.read(1024**2),b''):
                        if cancel.is_set():raise ValueError('Téléchargement annulé. Le fichier partiel est conservé pour une reprise.')
                        offset+=len(chunk)
                        if offset>model['size']:raise ValueError('Le modèle dépasse la taille annoncée.')
                        output.write(chunk)
        if part.stat().st_size!=model['size'] or digest(part)!=model['sha256']:raise ValueError('Modèle incomplet ou empreinte incorrecte. Le fichier partiel ne sera pas utilisé.')
        part.replace(target);target.with_suffix('.receipt.json').write_text(json.dumps(dict(model,verified=True)),encoding='utf-8');results.append(target.name+' : téléchargé et vérifié')
    return results
