"""Disposable native EDIT control for UI Automation integration tests only."""
import json
import os
import sys
import win32api
import win32con
import win32gui

NAME = "RedactorNativeFixture"
HWND, EDIT = 0, 0


def handler(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_APP + 2:
        win32gui.SetWindowText(EDIT, "Modifié dans l’application")
        return 0
    if msg == win32con.WM_APP + 1:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.SetFocus(EDIT)
        win32gui.SendMessage(EDIT, 0x00B1, 7, 13)  # EM_SETSEL, a user/test fixture selection, no click.
        return 0
    if msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
        return 0
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


if __name__ == "__main__":
    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = handler
    wc.lpszClassName = NAME
    wc.hInstance = win32api.GetModuleHandle(None)
    win32gui.RegisterClass(wc)
    HWND = win32gui.CreateWindow(NAME, "Redactor · Test UIA jetable", win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
        150, 150, 560, 240, 0, 0, wc.hInstance, None)
    EDIT = win32gui.CreateWindowEx(win32con.WS_EX_CLIENTEDGE, "EDIT", "Avant. fautes Après.",
        win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP | win32con.ES_MULTILINE,
        20, 20, 490, 140, HWND, 100, wc.hInstance, None)
    print(json.dumps({"hwnd": HWND, "edit": EDIT, "pid": os.getpid()}), flush=True)
    win32gui.PostMessage(HWND, win32con.WM_APP + 1, 0, 0)
    win32gui.PumpMessages()
