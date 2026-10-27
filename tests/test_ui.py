import os
import json
import pytest
from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtNetwork import QLocalSocket
from shared.ui.components import ErgoOrb
from shared.profiles import default_profile
from orb_manager.manager import stack_positions, clamp_position

@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or QApplication([])

@pytest.mark.parametrize('rect',[QRect(0,0,1920,1080),QRect(-1920,0,1920,1080),QRect(0,0,800,600),QRect(0,-1200,1600,1200)])
def test_stack_multimonitor(rect):
    positions=stack_positions(rect,20)
    assert len({tuple(p) for p in positions})==20
    for x,y in positions:
        assert rect.contains(QRect(x,y,36,36))

def test_orb_click_drag_and_keyboard(app):
    orb=ErgoOrb('corrector'); calls=[];orb.activated.connect(calls.append);orb.show();app.processEvents()
    QTest.mouseClick(orb,Qt.LeftButton)
    assert calls==['corrector']
    QTest.keyClick(orb,Qt.Key_Space)
    assert len(calls)==2
    orb.set_animations(False)
    assert not orb.timer.isActive()
    for state in orb.STATES:
        orb.update_state(state)
        assert state in orb.accessibleName()
    orb.close()

def test_animation_changes_rendering_without_moving_target(app):
    orb=ErgoOrb('corrector');orb.show();app.processEvents()
    before=orb.grab().toImage();geometry=orb.geometry()
    for _ in range(10): orb.tick()
    after=orb.grab().toImage()
    assert before!=after
    assert orb.geometry()==geometry
    orb.set_animations(False)
    assert not orb.timer.isActive()
    orb.close()

def test_hub_profile_loading_does_not_launch(app,tmp_path,monkeypatch):
    from Hub.window import HubWindow
    window=HubWindow(tmp_path)
    monkeypatch.setattr(window.catalog,'launch',lambda key:pytest.fail('Chargement de profil ne doit pas lancer'))
    assert len(window.cards)==19
    window.profiles[1]['active']=['claviernator']
    window.profile_box.setCurrentIndex(1)
    window.save()
    assert window.store.load()[1]['active']==['claviernator']
    window.close()

def test_ipc_state_only_and_oversize(app,tmp_path):
    from shared.catalog import Catalog
    from orb_manager.manager import OrbManager
    manager=OrbManager(Catalog())
    if not manager.listening:
        pytest.fail('IPC Windows indisponible : exécuter ce test hors restriction des pipes')
    def send(payload):
        socket=QLocalSocket(); socket.connectToServer(manager.server_name)
        assert socket.waitForConnected(1000)
        socket.write(payload);socket.flush()
        for _ in range(20): app.processEvents(); QTest.qWait(5)
        reply=bytes(socket.readAll());socket.abort();return reply
    assert b'true' in send(json.dumps(dict(version=1,app='corrector',state='Attention')).encode()+b'\n')
    assert manager.states['corrector']=='Attention'
    assert b'false' in send(b'{"command":"launch"}\n')
    assert not send(b'x'*5000)
    manager.close()
