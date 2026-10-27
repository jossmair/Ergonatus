import json
from PySide6.QtCore import QRect
from shared.orb_layout import read_layout,move_stack
from orb_manager.manager import selected_stack
from shared.ui.theme import APP_THEMES

def test_stack_only_selected_small_orbs():
    area=QRect(0,0,1920,1040);order=['corrector','lector','traductor']
    points=selected_stack(area,order)
    assert len(points)==3
    assert len({point[0] for point in points})==1
    assert points[0][1]-points[1][1]==46
    assert points[1][1]-points[2][1]==46
    assert all(area.contains(QRect(*point,36,36)) for point in points)

def test_clavier_scroll_controls_have_space():
    points=selected_stack(QRect(0,0,1920,1040),['corrector','claviernator','lector'])
    assert points[0][1]-points[1][1]>=64
    assert points[1][1]-points[2][1]>=64

def test_shared_group_drag_moves_only_visible_apps(tmp_path,monkeypatch):
    path=tmp_path/'layout.json';data=dict(version=1,apps={'corrector':dict(visible=True,position=[100,200]),'lector':dict(visible=True,position=[100,154]),'traductor':dict(visible=False,position=[100,108])})
    path.write_text(json.dumps(data));monkeypatch.setenv('ERGONATUS_ORB_LAYOUT',str(path))
    assert move_stack('corrector',[130,180])
    assert read_layout('lector')['position']==[130,134]
    assert read_layout('traductor')['position']==[100,108]

def test_orb_size_matches_original_apps(app=None):
    from PySide6.QtWidgets import QApplication
    from shared.ui.components import ErgoOrb
    app=QApplication.instance() or QApplication([])
    orb=ErgoOrb('corrector',floating=True,preview=False)
    assert (orb.width(),orb.height())==(36,36)
    assert 'aperçu' not in orb.accessibleName()
    orb.close()
