"""Local, manifest-verified package operations. No remote URLs or silent deletion."""
from pathlib import Path,PurePosixPath
import hashlib
import json
import shutil
import time
import zipfile
import uuid
from shared.ui.theme import APP_THEMES
from shared.catalog import valid_executable

def validate_package(path,app_id):
    if app_id not in APP_THEMES or app_id=='ergonatus':raise ValueError('Application invalide.')
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist()
        if len(infos)>20000 or sum(i.file_size for i in infos)>4*1024**3:raise ValueError('Paquet trop volumineux.')
        names=[i.filename for i in infos]
        if len(set(n.casefold() for n in names))!=len(names):raise ValueError('Fichiers dupliqués.')
        for info in infos:
            name=PurePosixPath(info.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in info.filename or ':' in info.filename or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Chemin dangereux dans le paquet.')
        if archive.getinfo('package.json').file_size>1024**2:raise ValueError('Manifeste trop volumineux.')
        manifest=json.loads(archive.read('package.json'))
        if manifest.get('app')!=app_id or manifest.get('schema')!=1 or not isinstance(manifest.get('files'),dict):raise ValueError('Paquet incompatible.')
        if set(names)!={'package.json',*manifest['files']}:raise ValueError('Le manifeste ne décrit pas tous les fichiers.')
        for name,digest in manifest['files'].items():
            if not name.startswith('runtime/') or not isinstance(digest,str) or len(digest)!=64:raise ValueError('Manifeste invalide.')
            sha=hashlib.sha256()
            with archive.open(name) as stream:
                for chunk in iter(lambda:stream.read(4*1024**2),b''):sha.update(chunk)
            if sha.hexdigest()!=digest:raise ValueError('Empreinte incorrecte : '+name)
    return manifest

def install_package(root,path,app_id):
    manifest=validate_package(path,app_id);base=Path(root)/APP_THEMES[app_id]['folder'];base.mkdir(exist_ok=True)
    if base.is_symlink() or base.resolve().parent!=Path(root).resolve():raise ValueError('Destination hors du dossier de la suite.')
    stage=base/('stage-'+uuid.uuid4().hex);stage.mkdir()
    try:
        with zipfile.ZipFile(path) as archive:
            for name in manifest['files']:
                target=stage/name;target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(name) as source,target.open('wb') as output:shutil.copyfileobj(source,output)
        executable=stage/'runtime'/(APP_THEMES[app_id]['folder']+'.exe')
        if not valid_executable(executable) or not (stage/'runtime/_internal').is_dir():raise ValueError('Exécutable Windows ou runtime absent/invalide.')
        runtime=base/'runtime'
        if runtime.exists():runtime.rename(base/('runtime-backup-'+uuid.uuid4().hex))
        (stage/'runtime').rename(runtime)
    finally:
        if stage.is_dir():
            if stage.resolve().parent!=base.resolve() or not stage.name.startswith('stage-') or stage.is_symlink():raise ValueError('Nettoyage refusé : dossier temporaire inattendu.')
            shutil.rmtree(stage)
    return manifest

def uninstall(root,app_id):
    if app_id not in APP_THEMES or app_id=='ergonatus':raise ValueError('Application invalide.')
    base=Path(root)/APP_THEMES[app_id]['folder'];source=base/'runtime'
    if not source.is_dir():raise ValueError('Application non installée.')
    destination=base/('runtime-retired-'+uuid.uuid4().hex)
    source.rename(destination)
    return destination
