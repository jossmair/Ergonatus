from app.core.controller import Controller
from app.core.device_detector import Hardware
from app.core.settings import Settings
from app.core.state_machine import State

from types import SimpleNamespace


def test_second_toggle_during_preparation_cancels_without_queued_session():
    controller = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    controller.session_pending = True
    controller.machine.transition(State.PREPARING)
    for _ in range(5):
        controller.request("toggle")
    assert controller.stop_requested.is_set()
    assert controller.commands.empty()


async def test_listening_is_announced_once_after_microphone_start(monkeypatch):
    controller = Controller(Settings(), Hardware("test", 4, 16 * 2**30, 8 * 2**30))
    states = []
    controller.status.connect(states.append)

    async def begin(emit):
        pass

    async def finish():
        pass

    class Capture:
        def __init__(self, device):
            pass

        def start(self):
            assert State.LISTENING.value not in states
            assert controller.machine.state == State.PREPARING

        def read(self):
            controller.stop_requested.set()
            return None

        def stop(self):
            return []

    controller.manager = SimpleNamespace(
        is_prepared=lambda settings: True, active=SimpleNamespace(begin=begin, finish=finish)
    )
    controller.focus = SimpleNamespace(locate=lambda: None, valid=lambda: True, anchor=lambda: None)
    controller.injector = SimpleNamespace()
    monkeypatch.setattr("app.core.controller.AudioCapture", Capture)
    await controller._dictate()
    assert states == [State.PREPARING.value, State.LISTENING.value, State.FLUSHING.value, State.IDLE.value]
    assert controller.capture is None
