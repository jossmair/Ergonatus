import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication,QToolButton
from PySide6.QtCore import Qt,QPoint,QThreadPool
from PySide6.QtTest import QTest
from shared.apps.app_launcher import ApplinatorWindow,shortcut,discover_apps

@pytest.fixture
def window(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([]);monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path/'data'));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    w=ApplinatorWindow(preload=False);w.show();app.processEvents();yield w
    w.closing=True;w.cleanup();QThreadPool.globalInstance().waitForDone(10000);w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()

def test_shortcuts_add_deduplicate_remove_persist(window,tmp_path):
    path=tmp_path/'Mon logiciel.exe';path.write_bytes(b'test');w=window;w.add_shortcut(path);w.add_shortcut(path)
    assert len(w.shortcuts)==1 and w.list.count()==1
    assert w.records.all('settings')[0][1]['launcher_shortcuts'][0]['path']==str(path)
    w.list.setCurrentRow(0);w.remove_selected();assert not w.shortcuts and path.read_bytes()==b'test'

def test_invalid_target(tmp_path):
    path=tmp_path/'texte.txt';path.write_text('test')
    with pytest.raises(ValueError):shortcut(path)
    with pytest.raises(ValueError):shortcut(tmp_path/'absent.exe')

def test_overlay_orb_background_and_escape(window):
    w=window;w.activate();assert w.overlay.isVisible() and not w.isVisible()
    QTest.mouseClick(w.overlay,Qt.LeftButton,pos=QPoint(4,4));assert not w.overlay.isVisible()
    w.activate();QTest.keyClick(w.overlay,Qt.Key_Escape);assert not w.overlay.isVisible()
    w.activate();w.activate();assert not w.overlay.isVisible()
    w.open_settings();assert w.isVisible()

def test_launch_hides_before_windows_open(window,tmp_path,monkeypatch):
    import shared.apps.app_launcher as module
    path=tmp_path/'Application.lnk';path.write_text('shortcut');w=window;w.add_shortcut(path);calls=[]
    monkeypatch.setattr(module.QDesktopServices,'openUrl',lambda url:calls.append((url.toLocalFile(),w.overlay.isVisible())) or True)
    w.activate();tile=w.overlay.findChild(QToolButton,'AppTile');assert tile
    QTest.mouseClick(tile,Qt.LeftButton);QTest.qWait(30)
    assert len(calls)==1 and Path(calls[0][0])==path and calls[0][1] is False

def test_opacity_and_reorder(window,tmp_path):
    w=window
    for name in ['A.exe','B.exe']:
        path=tmp_path/name;path.write_text('test');w.add_shortcut(path)
    item=w.list.takeItem(0);w.list.addItem(item);w.save_order();assert [a['name'] for a in w.shortcuts]==['B','A']
    w.opacity.setValue(0);assert w.preferences['launcher_opacity']==0
    w.activate();assert w.overlay.isVisible();w.opacity.setValue(100);assert w.preferences['launcher_opacity']==100

def test_discover_start_menu(tmp_path,monkeypatch):
    import shared.apps.app_launcher as module
    from types import SimpleNamespace
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=b'[]'))
    monkeypatch.setenv('APPDATA',str(tmp_path));monkeypatch.setenv('PROGRAMDATA',str(tmp_path/'other'))
    root=tmp_path/'Microsoft/Windows/Start Menu/Programs';root.mkdir(parents=True);(root/'Application.lnk').write_text('test')
    assert any(item['name']=='Application' for item in discover_apps())

def test_profile_rename_preserves_user_choices():
    from shared.profiles import default_profile,validate
    profile=default_profile();profile['active']=['dictator'];profile['favorites']=['dictator'];profile['order']=['dictator','applinator'];profile['positions']={'dictator':[50,60]}
    migrated=validate(profile)
    assert migrated['active']==['applinator'] and migrated['favorites']==['applinator'] and migrated['positions']=={'applinator':[50,60]}
    assert migrated['order']==['applinator'] and profile['active']==['dictator']


def test_preload_pc_apps_only_one_suite_entry(window,tmp_path):
    from shared.apps.app_launcher import preload_entries
    entries=[dict(name='Firefox',path='firefox.exe'),dict(name='Firefox',path='duplicate.lnk'),dict(name='Lector',path='Lector.exe'),dict(name='Lancer Calculinator',path='Calculinator.exe'),dict(name='Ergonatus',path='old.lnk'),dict(name='Désinstaller Firefox',path='uninstall.exe')]
    w=window;w.apply_preload(entries)
    assert [e['name'] for e in w.catalog].count('Ergonatus')==1
    assert [e['name'] for e in w.catalog].count('Firefox')==1
    assert not any(e['name'] in ['Lector','Lancer Calculinator','Désinstaller Firefox'] for e in w.catalog)
    assert w.preferences['launcher_preloaded_version']==1
    w.apply_preload(entries);assert len(w.catalog)==2 and not w.shortcuts


def test_store_apps_discovered_and_launched(window,monkeypatch,tmp_path):
    import shared.apps.app_launcher as module
    from types import SimpleNamespace
    monkeypatch.setenv('APPDATA',str(tmp_path));monkeypatch.setenv('PROGRAMDATA',str(tmp_path/'other'))
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=b'[{"Name":"Calculatrice","AppID":"Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"}]'))
    entries=module.discover_apps();entry=next(e for e in entries if e['name']=='Calculatrice');assert module.shortcut(entry['path'])
    calls=[];monkeypatch.setattr(module.os,'startfile',lambda path:calls.append(path))
    window.launch_shortcut(entry);QTest.qWait(30);assert calls==[entry['path']]


def test_widget_search_and_readable_orb_menu(window,tmp_path):
    w=window
    for name in ['Firefox.exe','Bloc-notes.exe']:
        path=tmp_path/name;path.write_text('test');w.add_shortcut(path)
    w.activate();w.overlay.search.setText('firefox');QTest.qWait(30)
    tiles=w.overlay.scroll.widget().findChildren(QToolButton,'AppTile')
    assert len(tiles)==1 and tiles[0].text()=='Firefox' and tiles[0].height()>=92
    menu=w.create_orb_menu();texts=[a.text() for a in menu.actions() if not a.isSeparator()]
    assert texts==['Afficher / masquer les applications','Configurer mes raccourcis','Quitter Applinator']
    assert 'QMenu::item:selected' in menu.styleSheet();menu.close()


def test_only_checked_catalog_entries_appear_in_widget(window):
    w=window;w.apply_preload([dict(name='Firefox',path='firefox.exe'),dict(name='Word',path='word.exe'),dict(name='7-Zip Help',path='help.lnk'),dict(name='Administrative Tools',path='admin.lnk')])
    assert not w.shortcuts and not any(a['name'] in ('7-Zip Help','Administrative Tools') for a in w.catalog)
    index=next(i for i in range(w.list.count()) if w.list.item(i).data(Qt.UserRole)['name']=='Firefox')
    w.list.setCurrentRow(index);QTest.keyClick(w.list,Qt.Key_Space)
    assert [a['name'] for a in w.shortcuts]==['Firefox']
    w.app_search.setText('Word');assert [a['name'] for a in w.shortcuts]==['Firefox']
    w.activate();tiles=w.overlay.scroll.widget().findChildren(QToolButton,'AppTile');assert [t.text() for t in tiles]==['Firefox']
    assert [a['name'] for a in w.records.all('settings')[0][1]['launcher_shortcuts']]==['Firefox']
    w.clear_selection();assert not w.shortcuts


def test_technical_noise_and_category_sort():
    from shared.apps.app_launcher import preload_entries,app_category
    junk=['7-Zip Help','Python 3.12 Module Docs (64-bit)','Developer PowerShell for VS','Visual Studio Installer','VLC media player - reset preferences and cache files','Application Verifier (X64)','Task Manager','FAQ']
    entries=preload_entries([dict(name=name,path=name+'.lnk') for name in junk+['Visual Studio Code','Word','Firefox','VLC media player']])
    names=[a['name'] for a in entries]
    assert not set(junk)&set(names)
    assert {'Visual Studio Code','Word','Firefox','VLC media player'}<=set(names)
    assert app_category('Firefox')=='Internet' and app_category('Word')=='Bureautique'
