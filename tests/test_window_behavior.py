import json
import pytest
from PySide6.QtCore import QRect,QPoint,QPointF,QEvent,Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication,QWidget,QLineEdit
from PySide6.QtTest import QTest
from shared.ui.components import ErgoWindow
from shared.ui.window_behavior import fit_window

@pytest.fixture(scope='session')
def app():return QApplication.instance() or QApplication([])

@pytest.mark.parametrize('rect',[QRect(4000,3000,680,550),QRect(-4000,-3000,680,550),QRect(20,20,4000,3000)])
def test_window_recovered_after_screen_removed(rect):
    area=QRect(0,0,1280,720)
    assert area.contains(fit_window(rect,[area]))

def test_window_keeps_negative_monitor_coordinates():
    rect=QRect(-1200,70,680,550)
    assert fit_window(rect,[QRect(0,0,1280,720),QRect(-1280,0,1280,720)])==rect

def test_header_drag_has_manual_fallback_without_affecting_inputs(app,monkeypatch):
    window=ErgoWindow();header=QWidget(window);header.setGeometry(0,0,600,50);window.drag_area(header)
    window.move(100,100);window.show();app.processEvents();origin=window.pos()
    monkeypatch.setattr(window.behavior,'start_native_move',lambda:False)
    start=header.mapToGlobal(QPoint(10,10));end=start+QPoint(40,30)
    for kind,local,glob,button,buttons in [(QEvent.MouseButtonPress,QPoint(10,10),start,Qt.LeftButton,Qt.LeftButton),(QEvent.MouseMove,QPoint(50,40),end,Qt.NoButton,Qt.LeftButton),(QEvent.MouseButtonRelease,QPoint(50,40),end,Qt.LeftButton,Qt.NoButton)]:
        QApplication.sendEvent(header,QMouseEvent(kind,QPointF(local),QPointF(glob),button,buttons,Qt.NoModifier))
    assert window.pos()==origin+QPoint(40,30)
    assert header.cursor().shape()==Qt.SizeAllCursor
    window.close()

def test_keyboard_move_can_cancel_and_does_not_capture_other_windows(app):
    window=ErgoWindow();window.move(100,100);field=QLineEdit(window);field.setText('Texte conservé');window.show();app.processEvents();origin=window.pos()
    window.behavior.begin_keyboard_move();QTest.keyClick(field,Qt.Key_Right)
    assert window.pos()==origin+QPoint(10,0)
    other=QLineEdit();other.show();QTest.keyClick(other,Qt.Key_Right)
    assert window.pos()==origin+QPoint(10,0)
    QTest.keyClick(field,Qt.Key_Escape)
    assert window.pos()==origin and field.text()=='Texte conservé'
    other.close();window.close()

def test_position_restored_and_corruption_ignored(app,tmp_path):
    path=tmp_path/'window.json'
    first=ErgoWindow();first.behavior.configure(path);first.show();app.processEvents();first.move(100,100);first.behavior.save();first.close()
    assert json.loads(path.read_text())['geometry'][:2]==[100,100]
    second=ErgoWindow();second.behavior.configure(path);second.show();app.processEvents()
    assert second.pos()==QPoint(100,100)
    second.close();path.write_text('{broken')
    third=ErgoWindow();third.behavior.configure(path);third.show();app.processEvents()
    assert third.behavior.ready
    third.close()
