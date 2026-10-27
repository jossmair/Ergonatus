import pytest
from types import SimpleNamespace
from app.core.device_detector import detect
from app.services.engine_manager import EngineManager

def test_quick_detection_never_runs_system_subprocesses(monkeypatch):
    monkeypatch.setattr('app.core.device_detector.run',lambda *a,**kw:pytest.fail('Blocking system probe'))
    assert detect(quick=True).pending_detection

async def test_failed_native_cleanup_does_not_disable_controller_retry():
    class Broken:
        async def close(self):raise RuntimeError('Native handle already closed')
    manager=EngineManager(SimpleNamespace());manager.active=Broken();manager.signature=('old',)
    await manager.close()
    assert manager.active is None and manager.signature is None
