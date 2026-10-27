import pytest

from app.core import win32


def test_paste_uses_real_right_control_and_the_target_keyboard_layout(monkeypatch):
    monkeypatch.setattr(win32.user, "GetWindowThreadProcessId", lambda hwnd, pid: 123)
    monkeypatch.setattr(win32.user, "GetKeyboardLayout", lambda tid: 456 if tid == 123 else 0)
    mappings = []
    def mapping(key, kind, layout):
        mappings.append((key, kind, layout))
        return {0xA3: 0x1D, 0x56: 0x2F}[key]
    monkeypatch.setattr(win32.user, "MapVirtualKeyExW", mapping)
    keys = win32.paste_inputs(10)
    assert mappings == [(0xA3, 0, 456), (0x56, 0, 456)]
    assert [(item.value.keyboard.vk, item.value.keyboard.scan, item.value.keyboard.flags) for item in keys] == [
        (0, 0x1D, 9), (0, 0x2F, 8), (0, 0x2F, 10), (0, 0x1D, 11)]


def test_intercepted_control_never_sends_a_bare_v_and_is_always_released(monkeypatch):
    sent = []
    monkeypatch.setattr(win32, "send", lambda inputs: sent.append(inputs))
    monkeypatch.setattr(win32.time, "sleep", lambda delay: None)
    monkeypatch.setattr(win32.user, "GetAsyncKeyState", lambda key: 0)
    assert win32.send_paste(["control_down", "v_down", "v_up", "control_up"]) is False
    assert sent == [["control_down"], ["control_up"]]


def test_one_paste_releases_control_even_when_the_paste_key_batch_fails(monkeypatch):
    sent = []
    def send(inputs):
        sent.append(inputs)
        if inputs == ["v_down", "v_up"]:
            raise RuntimeError("interrupted input")
    monkeypatch.setattr(win32, "send", send)
    monkeypatch.setattr(win32.time, "sleep", lambda delay: None)
    monkeypatch.setattr(win32.user, "GetAsyncKeyState", lambda key: 0x8000)
    with pytest.raises(RuntimeError, match="interrupted input"):
        win32.send_paste(["control_down", "v_down", "v_up", "control_up"])
    assert sent == [["control_down"], ["v_down", "v_up"], ["control_up"]]
