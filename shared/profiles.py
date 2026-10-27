"""Strict, portable preferences; imports never launch processes."""
import json
import os
import shutil
import time
from pathlib import Path
from shared.ui.theme import APP_THEMES

PROFILE_NAMES = ['Personnalisé', 'Handicap moteur', 'Élève DYS', 'Fatigabilité', 'Élève allophone', 'Communication']
RETIRED_APPS = {'gestinator','copinator'}

def default_profile(name='Personnalisé'):
    return dict(name=name, active=[], favorites=[], hidden=[], order=list(APP_THEMES)[1:],
                orb_limit=4, animations=True, large=False, theme='system', positions={},autolaunch=False)

def validate(value):
    if not isinstance(value, dict):
        raise ValueError('Profil invalide.')
    value = dict(value)
    for field in ('active','favorites','hidden','order'):
        if isinstance(value.get(field),list):
            value[field] = [item for item in value[field] if not isinstance(item,str) or item not in RETIRED_APPS]
    if isinstance(value.get('positions'),dict):
        value['positions'] = {key:pos for key,pos in value['positions'].items() if key not in RETIRED_APPS}
    for field in ('active','favorites','hidden','order'):
        if isinstance(value.get(field),list):
            items=value[field]
            value[field]=['applinator' if item=='dictator' else item for item in items if item!='dictator' or 'applinator' not in items]
    if isinstance(value.get('positions'),dict) and 'dictator' in value['positions']:
        value['positions']=dict(value['positions']);old=value['positions'].pop('dictator');value['positions'].setdefault('applinator',old)
    if set(value) - set(default_profile()):
        raise ValueError('Champs inconnus dans le profil.')
    result = default_profile()
    result.update(value)
    if not isinstance(result['name'], str) or not 1 <= len(result['name'].strip()) <= 80:
        raise ValueError('Nom de profil invalide.')
    for key in ('active', 'favorites', 'hidden', 'order'):
        items = result[key]
        if not isinstance(items, list) or len(items) > len(APP_THEMES)-1 or len(set(str(x) for x in items)) != len(items) or any(not isinstance(x,str) or x not in APP_THEMES or x == 'ergonatus' for x in items):
            raise ValueError('Liste d’applications invalide.')
    if type(result['orb_limit']) is not int or not 1 <= result['orb_limit'] <= len(APP_THEMES)-1:
        raise ValueError('Limite d’Orbs invalide.')
    if any(type(result[key]) is not bool for key in ('animations', 'large','autolaunch')) or result['theme'] not in ('system', 'light', 'dark'):
        raise ValueError('Préférences visuelles invalides.')
    if not isinstance(result['positions'], dict) or len(result['positions']) > len(APP_THEMES):
        raise ValueError('Positions invalides.')
    for app_id, pos in result['positions'].items():
        if app_id not in APP_THEMES or not isinstance(pos, list) or len(pos) != 2 or any(type(v) is not int or abs(v) > 100000 for v in pos):
            raise ValueError('Position invalide.')
    return result

class ProfileStore:
    def __init__(self, path=None):
        self.path = Path(path or Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Ergonatus' / 'profiles.json')
        self.notice = ''
        self.active_name=None

    def load(self):
        for path in (self.path, self.path.with_suffix('.bak')):
            if not path.is_file():
                continue
            try:
                if path.stat().st_size > 256000:
                    raise ValueError('Fichier trop volumineux.')
                document = json.loads(path.read_text(encoding='utf-8'))
                if document.get('version') != 1 or not isinstance(document.get('profiles'), list) or not 1 <= len(document['profiles']) <= 50:
                    raise ValueError('Format incompatible.')
                profiles = [validate(p) for p in document['profiles']]
                if len({p['name'] for p in profiles}) != len(profiles):
                    raise ValueError('Noms de profils dupliqués.')
                self.active_name=document.get('active') if document.get('active') in {p['name'] for p in profiles} else profiles[0]['name']
                return profiles
            except (ValueError, OSError, TypeError, AttributeError):
                self.notice = 'Préférences illisibles : récupération sans lancement automatique.'
        return [default_profile(name) for name in PROFILE_NAMES]

    def save(self, profiles, active_name=None):
        profiles = [validate(p) for p in profiles]
        if not 1 <= len(profiles) <= 50 or len({p['name'] for p in profiles}) != len(profiles):
            raise ValueError('Liste de profils invalide.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            shutil.copy2(self.path, self.path.with_suffix('.bak'))
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(dict(version=1, profiles=profiles,active=active_name or profiles[0]['name']), ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.path)

    def import_profile(self, path):
        path = Path(path)
        if path.stat().st_size > 64000:
            raise ValueError('Profil trop volumineux.')
        return validate(json.loads(path.read_text(encoding='utf-8')))

    def export_profile(self, path, profile):
        Path(path).write_text(json.dumps(validate(profile), ensure_ascii=False, indent=2), encoding='utf-8')
