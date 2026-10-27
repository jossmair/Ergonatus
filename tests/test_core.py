import json
from pathlib import Path
import pytest
from shared.catalog import Catalog, valid_executable, suite_root
from shared.profiles import ProfileStore, default_profile, validate
from shared.ui.theme import APP_THEMES

def test_catalog_and_stable_legacy_colors():
    assert len(APP_THEMES)==19
    assert len({t['accent'].lower() for t in APP_THEMES.values()})==19
    assert len({t['icon'] for t in APP_THEMES.values()})==19
    assert APP_THEMES['precisionator']['accent']=='#9164E8'
    assert APP_THEMES['claviernator']['accent']=='#81E2C6'
    assert APP_THEMES['transcrinator']['accent']=='#D5914E'
    assert not {'gestinator','copinator'} & APP_THEMES.keys()


def test_retired_app_removed_without_resetting_profile(tmp_path):
    old=default_profile('Mon profil')
    old.update(active=['gestinator','copinator','lector'],favorites=['gestinator','copinator','redactor'],hidden=['gestinator','copinator'],positions={'gestinator':[40,80],'copinator':[80,100],'lector':[120,240]},large=True,autolaunch=True)
    old['order'][0:0]=['gestinator','copinator']
    path=tmp_path/'profiles.json';path.write_text(json.dumps({'version':1,'active':'Mon profil','profiles':[old]}),encoding='utf-8')
    store=ProfileStore(path);profile=store.load()[0]
    assert not store.notice and store.active_name=='Mon profil'
    assert profile['active']==['lector'] and profile['favorites']==['redactor'] and profile['hidden']==[]
    assert profile['positions']=={'lector':[120,240]} and profile['large'] and profile['autolaunch']
    assert 'gestinator' not in profile['order'] and old['active'][0]=='gestinator'

def test_real_assembly_detects_only_delivered_apps():
    catalog=Catalog()
    delivered={key for key in APP_THEMES if catalog.detect(key)}
    assert {'claviernator','precisionator','transcrinator','redactor'}<=delivered
    if (suite_root()/'docs/SATELLITES_ASSEMBLY.json').exists():
        satellites=json.loads((suite_root()/'docs/SATELLITES_ASSEMBLY.json').read_text())
        assert delivered=={'claviernator','precisionator','transcrinator','redactor'}|{item['app'] for item in satellites}
        assert {'ecrinator','pdfinator'} <= delivered
    manifest=json.loads((suite_root()/'docs/ASSEMBLY.json').read_text())
    import hashlib
    for item in manifest:
        assert hashlib.sha256((suite_root()/item['executable']).read_bytes()).hexdigest()==item['sha256']

@pytest.mark.parametrize('path',['relative.exe',r'\\server\tool.exe','C:/missing.exe','C:/Windows/System32/cmd.bat'])
def test_unsafe_or_missing_executable(path):
    assert not valid_executable(path)

def test_unbuilt_app_never_launches(tmp_path):
    with pytest.raises(ValueError): Catalog(tmp_path).launch('corrector')

def test_no_force_stop():
    with pytest.raises(ValueError,match='arrêt distant'): Catalog().stop('claviernator')

def test_profile_roundtrip_and_backup(tmp_path):
    store=ProfileStore(tmp_path/'profiles.json')
    profile=default_profile('Élève'); profile['active']=['claviernator'];profile['positions']={'redactor':[-100,200]}
    store.save([profile]);store.save([profile])
    assert store.load()==[profile]
    assert store.path.with_suffix('.bak').exists()
    store.path.write_text('{invalid')
    assert store.load()==[profile]
    assert store.notice
    store.export_profile(tmp_path/'export.json',profile)
    assert store.import_profile(tmp_path/'export.json')==profile

@pytest.mark.parametrize('change',[
    {'active':['unknown']},{'active':['redactor','redactor']},{'orb_limit':0},
    {'orb_limit':True},{'animations':'yes'},{'theme':'invalid'},
    {'positions':{'redactor':[float('nan'),0]}},{'name':''},{'command':'cmd.exe'},
    {'active':[{}]}, {'positions':{'redactor':[True,0]}}
])
def test_profile_rejects_malformed_import(change):
    with pytest.raises(ValueError): validate(default_profile()|change)

def test_no_private_text_in_profiles():
    assert not {'text','clipboard','audio','commands','model_prompt'} & default_profile().keys()

def test_active_generated_assets_are_transparent():
    from PySide6.QtGui import QImage
    for app_id in APP_THEMES:
        image=QImage(str(suite_root()/'assets/orbs'/f'{app_id}.png'))
        assert not image.isNull()
        assert image.hasAlphaChannel()
        assert image.pixelColor(0,0).alpha()==0

def test_native_art_replacement_is_reversible():
    import hashlib
    root=suite_root()
    records=json.loads((root/'docs/ORB_ASSETS.json').read_text())
    assert len(records)==13
    for item in records:
        assert hashlib.sha256((root/'assets/originals'/item['path']).read_bytes()).hexdigest()==item['original_sha256']
        assert hashlib.sha256((root/item['path']).read_bytes()).hexdigest()==item['generated_sha256']
