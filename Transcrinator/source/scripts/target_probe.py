"""Explicit insertion check in a caller-selected, empty test document.

Never moves focus. The caller must observe and select its disposable document,
then supply the exact window id. Only the fixed synthetic fixture is inserted.
"""
import argparse
import json
import queue
import threading
import time
from pathlib import Path

import comtypes
import win32gui

from app.core.focus_manager import FocusManager
from app.core.text_injector import TextInjector

FIXTURE = "Test Transcri : une phrase entière, avec des accents éàç et une ponctuation normale."


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-window-id", type=int, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--wait-focus", type=float, default=0,
                        help="Wait for the observed disposable document without activating any window")
    args = parser.parse_args()
    comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
    focus = None
    report = {"success": False}
    try:
        deadline = time.monotonic() + min(max(args.wait_focus, 0), 120)
        while win32gui.GetForegroundWindow() != args.expected_window_id and time.monotonic() < deadline:
            time.sleep(0.05)
        focus = FocusManager()
        target = focus.locate()
        assert target.hwnd == args.expected_window_id, "The observed test document lost focus"
        injector = TextInjector(focus)
        report.update(native_class=win32gui.GetClassName(target.native_hwnd) if target.native_hwnd else "",
                      native_fallback=target.element is None, native_insert=injector.native_available())
        report["success"] = injector.insert(FIXTURE)
    except Exception as error:
        report.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if focus:
            focus.target, focus.uia = None, None
        focus = None
        comtypes.CoUninitialize()
        print(json.dumps(report), flush=True)


def main():
    errors = queue.Queue()

    def work():
        try:
            run()
        except BaseException as error:
            errors.put(error)

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    if not errors.empty():
        raise errors.get()


if __name__ == "__main__":
    main()
