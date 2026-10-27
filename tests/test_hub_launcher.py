import json
from types import SimpleNamespace
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from shared.ui.theme import APP_THEMES
from orb_manager.manager import selected_stack

@pytest.fixture(scope='module')
def hub_application():
    app=QApplication.instance() or QApplication([])
    from suite_design import install
    app.setApplicationName('Ergonatus');install(app)
    return app

@pytest.fixture
def hub(hub_application,tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_TEST_MODE','1');monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1');monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path/'appdata'))
    app=hub_application
    from Hub.fort_hub import HubWindow
    w=HubWindow(tmp_path/'hub');w.show();app.processEvents();yield w
    w.close();app.processEvents()

def test_hub_orb_opens_all_suite_tiles_on_one_click(hub):
    QTest.mouseClick(hub.hub_orb,Qt.LeftButton)
    assert hub.launcher.isVisible() and not hub.isVisible()
    assert set(hub.launcher.tiles)==set(APP_THEMES)-{'ergonatus'} and len(hub.launcher.tiles)==len(APP_THEMES)-1
    QTest.mouseClick(hub.hub_orb,Qt.LeftButton);assert not hub.launcher.isVisible()
    assert not hub.manager.preview

def test_launcher_tiles_show_name_and_function(hub):
    from PySide6.QtWidgets import QLabel
    hub.toggle_launcher()
    for key,tile in hub.launcher.tiles.items():
        assert tile.findChild(QLabel,'TileName').text()==APP_THEMES[key]['name']
        description=tile.findChild(QLabel,'TileDescription')
        assert description.text()==APP_THEMES[key]['description'] and description.wordWrap()

def test_launch_tile_calls_only_chosen_app(hub,monkeypatch):
    calls=[];monkeypatch.setattr(hub.catalog,'launch',lambda key,minimized=False:calls.append((key,minimized)) or True)
    hub.toggle_launcher();QTest.mouseClick(hub.launcher.tiles['applinator'],Qt.LeftButton)
    for _ in range(40):
        if calls:break
        QTest.qWait(50)
    assert calls==[('applinator',False)] and not hub.launcher.isVisible()
    assert 'applinator' in hub.profile['active']

def test_base_orb_and_launch_order_with_constant_gap(hub,monkeypatch):
    monkeypatch.setattr(hub.catalog,'running',lambda key:[SimpleNamespace(pid=999999)] if key in ('lector','corrector') else [])
    hub.launched_order=['corrector','lector'];hub.arrange_orbs()
    data=json.loads(hub.catalog.layout_path.read_text())['apps'];base=data['ergonatus']['position'];above=data['corrector']['position'];next_pos=data['lector']['position']
    area=QApplication.primaryScreen().availableGeometry()
    assert base==selected_stack(area,['ergonatus'])[0]
    assert base[0]==above[0]==next_pos[0] and base[1]-above[1]==46 and above[1]-next_pos[1]==46
    assert hub.hub_orb.isVisible()

def test_windows_check_is_persistent_and_explicit(hub,monkeypatch):
    calls=[];monkeypatch.setattr('shared.startup.set_enabled',lambda value:calls.append(value))
    hub.compact_cards['lector']['startup'].setChecked(True)
    assert hub.startup_apps==['lector'] and calls==[True]
    saved=json.loads((hub.store.path.parent/'hub-launcher.json').read_text());assert saved['windows_apps']==['lector']

def test_compact_fortinator_layout_and_options(hub):
    assert hub.size().width()==600 and hub.size().height()==480
    assert len(hub.compact_cards)==len(APP_THEMES)-1 and not hub.cards
    assert hub.advanced_page is None and not hub.orb_widgets
    hub.show_options();assert hub.pages.currentIndex()==1 and len(hub.cards)==len(APP_THEMES)
    hub.show_home();assert hub.pages.currentIndex()==0
    hub.hide();assert hub.hub_orb.isVisible()

def test_launcher_opacity_changes_only_background_and_persists(hub):
    from PySide6.QtWidgets import QPushButton
    assert not any(button.text()=='Options' for button in hub.surface.findChildren(QPushButton))
    hub.toggle_launcher();hub.launcher.opacity_slider.setValue(35)
    assert hub.launcher.isVisible() and hub.launcher_opacity==35
    assert hub.launcher.windowOpacity()==1.0
    saved=json.loads((hub.store.path.parent/'hub-launcher.json').read_text())
    assert saved['launcher_opacity']==35
    from PySide6.QtCore import QPoint
    image=hub.launcher.grab().toImage()
    assert 85<=image.pixelColor(QPoint(2,2)).alpha()<=94

def test_only_hub_sources_show_tray():
    root=Path(__file__).resolve().parents[1]
    for file in ['shared/apps/base.py','Claviernator/source/fortinatus/main.py','Precisionator/source/application.py','Transcrinator/source/app/main.py','Redactor/source/app/controller.py']:
        content=(root/file).read_text(encoding='utf-8')
        assert 'tray.show()' not in content

def test_help_buttons_explain_without_launching(hub,monkeypatch):
    calls=[];monkeypatch.setattr(hub,'launch',lambda *args,**kwargs:calls.append(args))
    assert all('help' in row for row in hub.compact_cards.values())
    QTest.mouseClick(hub.compact_cards['lector']['help'],Qt.LeftButton)
    assert hub.help_popup.isVisible() and not calls
    hub.help_popup.close();hub.toggle_launcher()
    from PySide6.QtWidgets import QToolButton
    helpers=hub.launcher.findChildren(QToolButton,'HelpIcon')
    assert len(helpers)==len(APP_THEMES)-1
    QTest.mouseClick(helpers[0],Qt.LeftButton)
    assert hub.help_popup.isVisible() and hub.launcher.isVisible() and not calls
    hub.help_popup.close()

def test_header_is_draggable_and_orb_is_spherical_asset(hub,monkeypatch):
    from PySide6.QtCore import QPoint,QEvent
    from PySide6.QtGui import QMouseEvent,QPixmap
    from shared.catalog import suite_root
    monkeypatch.setattr(hub.behavior,'start_native_move',lambda:False)
    hub.move(100,100);origin=hub.pos();point=QPoint(230,15)
    QTest.mousePress(hub.header_bar,Qt.LeftButton,pos=point)
    event=QMouseEvent(QEvent.MouseMove,point+QPoint(35,20),hub.header_bar.mapToGlobal(point)+QPoint(35,20),Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
    QApplication.sendEvent(hub.header_bar,event)
    QTest.mouseRelease(hub.header_bar,Qt.LeftButton,pos=point+QPoint(35,20))
    assert hub.pos()==origin+QPoint(35,20)
    assert hub.header_bar.cursor().shape()==Qt.ArrowCursor
    expected=QPixmap(str(suite_root()/'assets/orbs/ergonatus-orb.png')).scaled(128,128,Qt.KeepAspectRatio,Qt.SmoothTransformation)
    assert not expected.isNull() and hub.hub_orb.image.toImage()==expected.toImage()


def test_preset_prepares_choices_then_explicit_load(hub,monkeypatch):
    from Hub.fort_hub import PRESETS
    calls=[];monkeypatch.setattr(hub,'launch',lambda key,minimized=False:calls.append(key))
    hub.preset_box.setCurrentText('Élève DYS')
    assert hub.profile['active']==PRESETS['Élève DYS'] and not calls
    hub.load_chosen_profile()
    for _ in range(80):
        if len(calls)==len(PRESETS['Élève DYS']):break
        QTest.qWait(50)
    assert calls==PRESETS['Élève DYS']
    hub.profile['active'].remove('temporator');hub.prepare_profile('Personnalisé');hub.prepare_profile('Élève DYS')
    assert 'temporator' not in hub.profile['active']


def test_new_learning_apps_are_available_and_searchable(hub):
    for key in ('dictionnator','explicator','tablinator'):assert key in hub.compact_cards
    hub.hub_search.setText('diction');assert not hub.compact_cards['dictionnator']['card'].isHidden();assert hub.compact_cards['tablinator']['card'].isHidden()
    hub.hub_search.clear();hub.toggle_launcher();QApplication.processEvents();assert len(hub.launcher.tiles)==21
    for key in ('dictionnator','explicator','tablinator'):assert hub.launcher.tiles[key].isEnabled() and hub.launcher.tiles[key].isVisible()
    assert hub.launcher.scroll.verticalScrollBar().maximum()==0


def test_hub_corners_are_transparent_and_antialiased(hub):
    from suite_design import install
    app=QApplication.instance();app.setApplicationName('Ergonatus');install(app);hub.update();QTest.qWait(100)
    assert hub.testAttribute(Qt.WA_TranslucentBackground);assert hub.mask().isEmpty();assert not hasattr(hub,'_identity_edge')
    image=hub.grab().toImage();assert image.pixelColor(0,0).alpha()==0
    assert any(0<image.pixelColor(x,y).alpha()<255 for x in range(30) for y in range(30))


def test_launcher_buttons_have_hover_press_feedback_and_work(hub):
    hub.toggle_launcher();QTest.qWait(60);button=hub.launcher.open_hub_button
    QTest.mouseMove(hub.launcher,hub.launcher.rect().bottomLeft());QTest.qWait(30);normal=button.grab().toImage()
    QTest.mouseMove(button,button.rect().center());QTest.qWait(40);hover=button.grab().toImage();assert hover!=normal
    QTest.mousePress(button,Qt.LeftButton);pressed=button.grab().toImage();assert pressed!=hover;QTest.mouseRelease(button,Qt.LeftButton);assert hub.isVisible() and not hub.launcher.isVisible()
    hub.toggle_launcher();QTest.mouseClick(hub.launcher.close_button,Qt.LeftButton);assert not hub.launcher.isVisible();assert hub.launcher.close_button.toolTip()=='Fermer le panneau des logiciels'
