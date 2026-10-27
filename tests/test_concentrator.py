import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPoint,QRect
from PySide6.QtTest import QTest

@pytest.fixture
def window(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.tools import ToolsApplication
    w=ToolsApplication('concentrator')
    yield w
    w.closing=True;w.cleanup();w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()

def test_orb_selects_then_hole_passes_input_and_dark_click_exits(window):
    window.orb.activated.emit('concentrator')
    # The selector is deliberately delayed; wait for readiness instead of
    # assuming the GUI queue always finishes within a 50 ms scheduling margin.
    for _ in range(150):
        if window.focus_selector is not None and window.focus_selector.isVisible():break
        QTest.qWait(10)
    selector=window.focus_selector
    assert selector is not None and selector.isVisible() and not window.isVisible()
    QTest.mousePress(selector,Qt.LeftButton,pos=QPoint(100,100))
    QTest.mouseRelease(selector,Qt.LeftButton,pos=QPoint(350,280))
    assert window.focus_overlays and window.focus_escape.isActive()
    overlay=next(o for o in window.focus_overlays if not o.hole.isEmpty())
    assert not overlay.mask().contains(QPoint(150,150))
    assert overlay.mask().contains(QPoint(20,20))
    assert not overlay.windowFlags() & Qt.WindowTransparentForInput
    QTest.mouseClick(overlay,Qt.LeftButton,pos=QPoint(20,20))
    assert not window.focus_overlays and not window.focus_escape.isActive()

def test_escape_and_tiny_region_cancel_selection(window):
    window.show_focus();QTest.qWait(220);QTest.keyClick(window.focus_selector,Qt.Key_Escape)
    assert window.focus_selector is None and not window.focus_overlays
    window.show_focus();QTest.qWait(220);selector=window.focus_selector
    QTest.mousePress(selector,Qt.LeftButton,pos=QPoint(40,40));QTest.mouseRelease(selector,Qt.LeftButton,pos=QPoint(42,42))
    assert not window.focus_overlays

def test_darkness_updates_all_screens_and_is_saved(window):
    app=QApplication.instance();window.apply_focus(app.primaryScreen(),QRect(100,100,200,160))
    assert len(window.focus_overlays)==len(app.screens())
    window.dim_slider.setValue(100)
    assert window.preferences['focus_darkness']==100 and all(o.opacity==100 for o in window.focus_overlays)
    QTest.keyClick(window.focus_overlays[0],Qt.Key_Escape)
    assert not window.focus_overlays

def test_global_escape_while_work_area_has_focus(window,monkeypatch):
    import ctypes
    window.apply_focus(QApplication.primaryScreen(),QRect(100,100,200,160))
    monkeypatch.setattr(ctypes.windll.user32,'GetAsyncKeyState',lambda key:0x8000)
    window.check_focus_escape();assert not window.focus_overlays
