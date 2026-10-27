import time,threading
from pathlib import Path
import pytest
from PySide6.QtCore import Qt,QThreadPool
from PySide6.QtWidgets import QApplication,QMainWindow,QMenu
from PySide6.QtTest import QTest
from shared.ui.theme import APP_THEMES

@pytest.fixture(scope='module')
def app():
    app=QApplication.instance() or QApplication([])
    from suite_design import install
    install(app);return app

@pytest.fixture
def make(app,tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1');monkeypatch.setenv('ERGONATUS_TEST_MODE','1')
    from shared.apps.base import ApplicationWindow
    windows=[]
    def make(key):
        w=ApplicationWindow(key);windows.append(w);w.show();QTest.qWait(150);return w
    yield make
    for w in windows:
        w.closing=True;QThreadPool.globalInstance().waitForDone(10000);app.processEvents();w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close()
    app._suite_interactions.poll();app.processEvents()

@pytest.mark.parametrize('key',[k for k in APP_THEMES if k not in ('ergonatus','claviernator','precisionator','transcrinator','redactor','ecrinator','pdfinator')])
def test_common_orb_menus_explain_every_satellite(make,key):
    w=make(key);menu=w.create_orb_menu();labels=[a.text() for a in menu.actions()]
    assert ('Régler le minuteur' if key=='temporator' else 'Ouvrir '+APP_THEMES[key]['name']) in labels
    assert 'Réglages' in labels and 'Affichage' not in labels
    assert len([a for a in menu.actions() if not a.isSeparator()])<=6
    assert any(a.menu() and any(v.text()=='Masquer la fenêtre' for v in a.menu().actions()) for a in menu.actions())
    assert 'Aide et lecture vocale' in labels
    assert labels[-1]=='Quitter '+APP_THEMES[key]['name']
    assert APP_THEMES[key]['name'] in w.orb.toolTip();menu.deleteLater()

def test_hourglass_tracks_success_error_and_overlapping_jobs(make,app):
    w=make('dictionnator');focus=w.focusWidget();manager=app._suite_interactions
    from shared.jobs import background
    background(w,lambda:(time.sleep(.9),'done')[1],lambda result:None)
    QTest.qWait(550);assert manager.hourglass.isVisible();assert manager.hourglass.testAttribute(Qt.WA_ShowWithoutActivating);assert manager.hourglass.windowFlags() & Qt.WindowTransparentForInput
    QTest.qWait(700);assert not manager.hourglass.isVisible()
    def failed():time.sleep(.5);raise ValueError('Essai')
    background(w,failed,lambda result:None);QTest.qWait(1000);assert not manager.hourglass.isVisible()
    background(w,lambda:time.sleep(.9),lambda result:None);background(w,lambda:time.sleep(.4),lambda result:None);QTest.qWait(600);assert manager.hourglass.isVisible();QTest.qWait(500);assert not manager.hourglass.isVisible()

def test_fast_tasks_do_not_flash_an_hourglass(make,app):
    w=make('dictionnator')
    from shared.jobs import background
    background(w,lambda:'fast',lambda result:None);QTest.qWait(400);assert not app._suite_interactions.hourglass.isVisible()

def test_redactor_and_transcription_busy_states(app):
    from types import SimpleNamespace
    w=QMainWindow();w.busy=True;manager=app._suite_interactions;manager.poll();QTest.qWait(400);assert manager.hourglass.isVisible()
    w.busy=False;manager.poll();assert not manager.hourglass.isVisible();w.controller=SimpleNamespace(machine=SimpleNamespace(state=SimpleNamespace(value='Traitement…')));manager.poll();QTest.qWait(400);assert manager.hourglass.isVisible()
    w.controller.machine.state.value='Écoute…';manager.poll();assert not manager.hourglass.isVisible();w.close();w.deleteLater()

def test_legacy_dark_menu_keeps_actions_and_readable_surface(app):
    class LegacyMenu(QMenu):
        def paintEvent(self,event):raise AssertionError('Old black paint must be replaced')
    menu=LegacyMenu();menu.addAction('Ouvrir Transcrinator');menu.addAction('Quitter Transcrinator');menu.popup(app.primaryScreen().availableGeometry().center());QTest.qWait(150);assert menu.isVisible();assert '#FFFFFF' in menu.styleSheet();assert len(menu.actions())>=3;menu.close();menu.deleteLater()

def test_hub_and_native_orbs_get_clear_menus(app):
    from types import SimpleNamespace
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QWidget
    calls=[];captured=[]
    hub=QMainWindow();hub.hub_orb=QWidget();hub.hub_orb.setContextMenuPolicy(Qt.CustomContextMenu);hub.hub_orb.customContextMenuRequested.connect(lambda *_:None);hub.external_orbs={'pdfinator':QWidget()};hub.reveal=lambda:calls.append('hub');hub.toggle_launcher=lambda:calls.append('launcher');hub.launch=lambda key:calls.append('open '+key);hub.catalog=SimpleNamespace(stop=lambda key:calls.append('quit '+key))
    app._suite_interactions.hook_hub(hub)
    def inspect_and_close(action=None):
        menu=app.activePopupWidget();assert isinstance(menu,QMenu)
        captured.append([a.text() for a in menu.actions()])
        if action and 'PDFinator' in action:assert '#5D49DF' in menu.styleSheet()
        if action:next(a for a in menu.actions() if a.text()==action).trigger()
        menu.close()
    QTimer.singleShot(40,inspect_and_close);hub.hub_orb.customContextMenuRequested.emit(hub.hub_orb.rect().topLeft());assert 'Quitter toute la suite' in captured[-1]
    QTimer.singleShot(40,lambda:inspect_and_close('Ouvrir PDFinator'));hub.external_orb_menu('pdfinator');assert 'Aide et lecture vocale' in captured[-1]
    QTimer.singleShot(40,lambda:inspect_and_close('Quitter PDFinator'));hub.external_orb_menu('pdfinator');assert calls==['open pdfinator','quit pdfinator']
    hub.hub_orb.close();hub.external_orbs['pdfinator'].close();hub.close();hub.deleteLater();app.processEvents()


def test_existing_reading_and_correction_hourglass_uses_common_surface(app):
    from shared.ui.reading_busy import ReadingBusy
    widget=ReadingBusy();widget.app_id='corrector';widget.begin(animated=False);QTest.qWait(100)
    assert widget.width()==136 and widget.height()==160;assert widget.name=='Corrector';assert widget.color.name()=='#159b64';assert not widget.grab().isNull();widget.finish();widget.close();widget.deleteLater()
