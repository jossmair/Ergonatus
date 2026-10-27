"""Acceptance checks for the current glass interface, independent of old screenshots."""
import json
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication,QLabel
from PySide6.QtCore import Qt,QPoint
from suite_design import install
from shared.ui.theme import APP_THEMES

@pytest.fixture(scope='module')
def app():
    instance=QApplication.instance() or QApplication([]);instance.setApplicationName('Ergonatus');install(instance);return instance

def test_actual_build_inventory_is_complete_and_matches_files():
    import hashlib
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'output/audit/current/versions.json').read_text(encoding='utf-8'))
    assert len(manifest['apps'])==19
    for item in manifest['apps']:
        assert item['exists']
        assert hashlib.sha256((root/item['executable']).read_bytes()).hexdigest()==item['sha256']

def test_all_launcher_cards_have_current_name_and_function(app,tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_TEST_MODE','1');monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from Hub.fort_hub import HubWindow
    w=HubWindow(tmp_path/'hub')
    try:
        w.launcher.resize(1280,720);w.launcher.rebuild();w.launcher.show();app.processEvents()
        assert set(w.launcher.tiles)==set(APP_THEMES)-{'ergonatus'}
        for key,tile in w.launcher.tiles.items():
            assert tile.findChild(QLabel,'TileName').text()==APP_THEMES[key]['name']
            assert tile.findChild(QLabel,'TileDescription').text()==APP_THEMES[key]['description']
            assert tile.findChild(QLabel,'TileDescription').wordWrap()
    finally:w.close();app.processEvents()

def test_month_gaps_are_light_and_current_calendar_has_only_needed_weeks(app,tmp_path,monkeypatch):
    from datetime import date
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.planner_agenda import PlaninatorWindow
    w=PlaninatorWindow()
    try:
        w.selected=date(2026,10,25);w.set_view('Mois');w.show();app.processEvents()
        cell=w.grid.itemAtPosition(1,0).widget();p=cell.geometry().topRight()+QPoint(3,20)
        assert w.grid_root.grab().toImage().pixelColor(p).lightness()>180
        assert not w.grid_root.testAttribute(Qt.WA_TranslucentBackground)
        assert w.grid.itemAtPosition(6,0) is None
    finally:w.cleanup();w.closing=True;w.orb.close();w.server.close();w.records.close();w.close();app.processEvents()
