import pytest
from PySide6.QtWidgets import QApplication,QMenu
from PySide6.QtCore import Qt,QTimer,QEvent,QPointF
from PySide6.QtGui import QContextMenuEvent,QMouseEvent
from PySide6.QtTest import QTest,QSignalSpy

@pytest.fixture(scope='module')
def app():
    app=QApplication.instance() or QApplication([])
    from suite_design import install
    app.setApplicationName('Lector');install(app);return app
@pytest.fixture
def lector(app,tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1');monkeypatch.setenv('ERGONATUS_BACKGROUND_START','1')
    from shared.apps.text import TextApplication
    from shared.reading_capture import ReadingCapture
    calls=[];monkeypatch.setattr(TextApplication,'warm_lector_voice',lambda self:None);monkeypatch.setattr(ReadingCapture,'start',lambda self,*args:calls.append('capture'))
    w=TextApplication('lector')
    w.orb.customContextMenuRequested.disconnect();w.orb.customContextMenuRequested.connect(lambda *_:calls.append('legacy-right-special'))
    w.orb.doubleActivated.disconnect();w.orb.doubleActivated.connect(lambda *_:calls.append('legacy-double-window'))
    monkeypatch.setattr(w,'activate',lambda *args:calls.append('single'));QTest.qWait(220);assert w.orb in app._suite_interactions.orb_owners
    yield w,calls
    w.closing=True;w._suite_orb_single_timer.stop();w.selection_picker.stop();w.selection_picker.cursor.close();w.lector_capture.cancel();w.busy_indicator.finish();w.busy_indicator.close();w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()

def test_single_click_reads_selection_once(lector):
    w,calls=lector;QTest.mouseClick(w.orb,Qt.LeftButton);QTest.qWait(QApplication.doubleClickInterval()+80);assert calls==['single']

def test_full_double_click_captures_without_single_action(lector):
    w,calls=lector;QTest.mouseClick(w.orb,Qt.LeftButton);QTest.qWait(30);QTest.mouseDClick(w.orb,Qt.LeftButton);QTest.mouseRelease(w.orb,Qt.LeftButton);QTest.qWait(QApplication.doubleClickInterval()+80);assert calls==['capture']

def test_right_click_only_opens_menu(lector,app):
    w,calls=lector;labels=[]
    def close():
        menu=app.activePopupWidget();assert isinstance(menu,QMenu);labels.extend(a.text() for a in menu.actions());menu.close()
    QTimer.singleShot(60,close);point=w.orb.rect().center();QApplication.sendEvent(w.orb,QContextMenuEvent(QContextMenuEvent.Mouse,point,w.orb.mapToGlobal(point)));QTest.qWait(QApplication.doubleClickInterval()+80)
    assert 'Ouvrir Lector' in labels and 'Lire une zone de l’écran' in labels;assert calls==[]

def test_drag_keeps_moving_orb_without_triggering_actions(lector):
    w,calls=lector;orb=w.orb;point=orb.rect().center();spy=QSignalSpy(orb.moved);QTest.mousePress(orb,Qt.LeftButton,pos=point)
    moved=QPointF(point.x()+18,point.y()+12);global_point=QPointF(orb.mapToGlobal(point))+QPointF(18,12);QApplication.sendEvent(orb,QMouseEvent(QEvent.MouseMove,moved,global_point,Qt.NoButton,Qt.LeftButton,Qt.NoModifier));QTest.mouseRelease(orb,Qt.LeftButton,pos=point);QTest.qWait(QApplication.doubleClickInterval()+80)
    assert spy.count()==1 and calls==[]


def test_legacy_retry_hint_uses_double_click(lector):
    w,calls=lector;w.orb.setToolTip('Lector · aucun texte · clic droit pour réessayer.');assert 'double-clic pour réessayer' in w.orb.toolTip()
