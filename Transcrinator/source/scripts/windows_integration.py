"""Real Windows tests against a disposable native editor in a separate process."""

import json
import multiprocessing as mp
import time
from pathlib import Path

import win32api
import win32con
import win32gui
import ctypes
import win32process

from app.core.audio_capture import AudioCapture
from app.core.focus_manager import FocusManager
from app.core.hotkeys import GlobalHotkey
from app.core.text_injector import TextInjector


def activate_fixture(hwnd):
    """Test harness only: temporarily join input queues to activate its own editor."""
    if win32gui.GetForegroundWindow() == hwnd:
        return
    user = ctypes.windll.user32
    # MTA validation threads have no message loop; create their input queue first.
    from ctypes import wintypes
    message = wintypes.MSG()
    user.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
    foreground = win32gui.GetForegroundWindow()
    tid = win32api.GetCurrentThreadId()
    other = win32process.GetWindowThreadProcessId(foreground)[0] if foreground else tid
    attached = tid != other and bool(user.AttachThreadInput(tid, other, True))
    try:
        try:
            win32gui.SetForegroundWindow(hwnd)
        except win32gui.error:
            if win32gui.GetForegroundWindow() != hwnd:
                raise
    finally:
        if attached:
            user.AttachThreadInput(tid, other, False)


def native_editor(pipe):
    handles = {}

    def procedure(hwnd, message, wparam, lparam):
        if message == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        if message == win32con.WM_APP + 1:
            name = {1: "edit", 2: "password", 3: "readonly", 4: "button"}.get(wparam)
            if name:
                win32gui.SetFocus(handles[name])
        return win32gui.DefWindowProc(hwnd, message, wparam, lparam)

    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = procedure
    wc.lpszClassName = "TranscriValidationEditor"
    wc.hInstance = win32api.GetModuleHandle(None)
    win32gui.RegisterClass(wc)
    hwnd = win32gui.CreateWindow(
        wc.lpszClassName,
        "Transcri — éditeur de validation Windows",
        win32con.WS_OVERLAPPEDWINDOW,
        100,
        100,
        650,
        400,
        0,
        0,
        wc.hInstance,
        None,
    )
    base = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP | win32con.WS_BORDER
    for index, name in enumerate(("edit", "password", "readonly", "button")):
        kind = "BUTTON" if name == "button" else "EDIT"
        style = base | (
            win32con.ES_PASSWORD
            if name == "password"
            else win32con.ES_READONLY
            if name == "readonly"
            else win32con.ES_MULTILINE
            | win32con.ES_AUTOVSCROLL
            | win32con.ES_WANTRETURN
            | win32con.WS_VSCROLL
        )
        handles[name] = win32gui.CreateWindow(
            kind, "", style, 20, 20 + index * 70, 550, 55, hwnd, 100 + index, wc.hInstance, None
        )
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    activate_fixture(hwnd)
    win32gui.SetFocus(handles["edit"])
    pipe.send({"hwnd": hwnd, **handles})
    win32gui.PumpMessages()
    pipe.close()


def text_of(hwnd):
    import ctypes

    buffer = ctypes.create_unicode_buffer(4096)
    ctypes.windll.user32.SendMessageW(hwnd, win32con.WM_GETTEXT, len(buffer), buffer)
    return buffer.value


def main():
    context = mp.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(target=native_editor, args=(child,), daemon=True)
    process.start()
    child.close()
    results = {}
    handles = None
    try:
        if not parent.poll(10):
            raise RuntimeError("Éditeur de test indisponible.")
        handles = parent.recv()
        time.sleep(0.3)
        focus = FocusManager()
        target = focus.locate()
        results["native_edit_detected"] = target.pid == process.pid
        injector = TextInjector(focus, "unicode")
        assert injector.insert("Bonjour é😀")
        time.sleep(0.1)
        results["unicode_insert"] = text_of(handles["edit"]) == "Bonjour é😀 "
        win32gui.SendMessage(handles["edit"], win32con.EM_SETSEL, 8, 9)
        focus.locate()  # must preserve the focused editor selection
        injector.insert("à")
        time.sleep(0.1)
        results["selection_preserved"] = text_of(handles["edit"]) == "Bonjour à 😀 "
        native = TextInjector(focus, "native")
        end = win32gui.SendMessage(handles["edit"], win32con.WM_GETTEXTLENGTH, 0, 0)
        win32gui.SendMessage(handles["edit"], win32con.EM_SETSEL, end, end)
        assert native.insert("\nDeuxième ligne.")
        results["native_control_unicode_and_newline"] = (
            text_of(handles["edit"]) == "Bonjour à 😀 \r\nDeuxième ligne. "
        )
        automatic = TextInjector(focus)
        assert automatic.insert(" Automatique.")
        results["automatic_native_insertion"] = text_of(handles["edit"]).endswith(" Automatique. ")
        for index, name in ((2, "password"), (3, "readonly"), (4, "button")):
            win32gui.PostMessage(handles["hwnd"], win32con.WM_APP + 1, index, 0)
            time.sleep(0.1)
            results[name + "_rejected"] = not focus._safe(focus.uia.GetFocusedElement())
            results[name + "_focus_change_blocks_injection"] = not focus.valid()
        original_pointer = win32api.GetCursorPos()
        try:
            rect = win32gui.GetWindowRect(handles["edit"])
            win32api.SetCursorPos((rect[0] + 25, rect[1] + 15))
            try:
                focus.locate()
                results["pointer_does_not_steal_focus"] = False
            except RuntimeError:
                results["pointer_does_not_steal_focus"] = (
                    focus.uia.GetFocusedElement().CurrentNativeWindowHandle == handles["button"]
                )
        finally:
            win32api.SetCursorPos(original_pointer)
        hook = GlobalHotkey(lambda: None)
        hook.start()
        results["native_low_level_hook_installed"] = hook.error is None
        hook.stop()
        capture = AudioCapture()
        try:
            capture.start()
            blocks = 0
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                if capture.read():
                    blocks += 1
                time.sleep(0.01)
            results["real_microphone_blocks_received"] = blocks
        finally:
            capture.stop()
            results["microphone_closed"] = capture.stream is None
        win32gui.PostMessage(handles["hwnd"], win32con.WM_CLOSE, 0, 0)
        process.join(3)
        results["closed_window_blocks_injection"] = not focus.valid()
        path = Path("docs/validation/windows-native.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps(results))
        assert all(v for v in results.values())
    finally:
        if process.is_alive():
            if handles:
                win32gui.PostMessage(handles["hwnd"], win32con.WM_CLOSE, 0, 0)
            process.join(1)
            if process.is_alive():
                process.terminate()
        parent.close()


if __name__ == "__main__":
    mp.freeze_support()
    main()
