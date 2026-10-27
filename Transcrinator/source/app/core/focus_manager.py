from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass

import comtypes.client
import win32api
import win32con
import win32security
import win32gui

from app.core.win32 import user


class TargetError(RuntimeError):
    """An unavailable editor does not invalidate the loaded speech model."""


@dataclass
class Target:
    hwnd: int
    pid: int
    runtime_id: tuple[int, ...]
    element: object
    rect: tuple[int, int, int, int]
    native_hwnd: int = 0


class GUIInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
               ("active", wintypes.HWND), ("focus", wintypes.HWND),
               ("capture", wintypes.HWND), ("menu", wintypes.HWND),
               ("move", wintypes.HWND), ("caret", wintypes.HWND), ("rect", wintypes.RECT)]


def gui_info(hwnd):
    info = GUIInfo()
    info.cbSize = ctypes.sizeof(info)
    tid = user.GetWindowThreadProcessId(hwnd, None)
    return info if user.GetGUIThreadInfo(tid, ctypes.byref(info)) else None


class FocusManager:
    """COM must be constructed and used on the same worker thread."""

    def __init__(self):
        self.lib = self.uia = None
        try:
            lib = comtypes.client.GetModule("UIAutomationCore.dll")
            self.lib = lib
            self.uia = comtypes.client.CreateObject(lib.CUIAutomation, interface=lib.IUIAutomation)
        except (OSError, comtypes.COMError):
            pass  # The Windows keyboard focus does not require an accessibility provider.
        self.target = None

    def _focused(self):
        try:
            return self.uia.GetFocusedElement() if self.uia else None
        except (OSError, comtypes.COMError):
            return None

    def _blocked(self, element):
        """Reject positive protection signals, never a missing editor pattern."""
        if not element:
            return False
        try:
            current = element
            for _ in range(20):
                if not current:
                    break
                if current.CurrentIsPassword:
                    return True
                current = self.uia.ControlViewWalker.GetParentElement(current)
            if (element.CurrentControlType == 50004 and element.GetCurrentPropertyValue(30043)
                    and element.GetCurrentPropertyValue(30046)):
                return True
        except (OSError, comtypes.COMError, AttributeError):
            pass
        return False

    def _safe(self, element):
        try:
            if not element.CurrentIsEnabled or element.CurrentIsOffscreen:
                return False
            if element.CurrentProcessId == os.getpid():
                return False
            # Password property is checked on ancestors as well (embedded browser controls).
            current = element
            for _ in range(20):
                if not current:
                    break
                if current.CurrentIsPassword:
                    return False
                current = self.uia.ControlViewWalker.GetParentElement(current)
            control = element.CurrentControlType
            if control not in (50004, 50030):  # Edit / Document only
                # Some browser/custom widgets expose an editable MSAA role
                # through UIA instead of an Edit/TextPattern.
                legacy = element.GetCurrentPattern(10018).QueryInterface(self.lib.IUIAutomationLegacyIAccessiblePattern)
                return legacy.CurrentRole == 42 and not legacy.CurrentState & (0x40 | 0x20000000)
            if element.GetCurrentPropertyValue(30043):  # IsValuePatternAvailable
                return not bool(element.GetCurrentPropertyValue(30046))  # ValueIsReadOnly
            if element.GetCurrentPropertyValue(30040):  # IsTextPatternAvailable
                pattern = element.GetCurrentPattern(10014).QueryInterface(self.lib.IUIAutomationTextPattern)
                value = pattern.DocumentRange.GetAttributeValue(40015)  # IsReadOnly
                return value is False or value == 0
            # Native edit controls: still reject ES_PASSWORD and ES_READONLY.
            native = element.CurrentNativeWindowHandle
            if native:
                style = user.GetWindowLongPtrW(native, -16)
                return control == 50004 and not style & (0x20 | 0x800)
            return False
        except (OSError, comtypes.COMError, AttributeError):
            return False

    def _privileges(self, pid):
        process = win32api.OpenProcess(0x1000, False, pid)
        try:
            token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
            try:
                sid = win32security.GetTokenInformation(token, win32security.TokenIntegrityLevel)[0]
                level = sid.GetSubAuthority(sid.GetSubAuthorityCount() - 1)
            finally:
                token.Close()
        finally:
            process.Close()
        mine = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        try:
            own_sid = win32security.GetTokenInformation(mine, win32security.TokenIntegrityLevel)[0]
            own = own_sid.GetSubAuthority(own_sid.GetSubAuthorityCount() - 1)
        finally:
            mine.Close()
        return level <= own

    def locate(self):
        self.target = None
        focused = self._focused()
        native = self._native_target(focused)
        if native:
            self.target = native
            return native
        if focused and self._safe(focused):
            return self._capture(focused)
        raise TargetError("Aucun éditeur détecté ; la dictée sera conservée.")

    def _native_target(self, element):
        """Route a normal paste to Windows' actual focus, without an app whitelist."""
        hwnd = int(user.GetForegroundWindow() or 0)
        info = gui_info(hwnd) if hwnd else None
        if not info or user.GetAncestor(info.focus or hwnd, 2) != hwnd:
            return None
        native = int(info.focus or hwnd)
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(native, ctypes.byref(pid))
        if pid.value == os.getpid() or not win32gui.IsWindowEnabled(native):
            return None
        try:
            kind = win32gui.GetClassName(native).lower()
            if self._blocked(element):
                return None
            native_edit = kind == "edit" or kind.startswith("richedit")
            if native_edit and user.GetWindowLongPtrW(native, -16) & (0x20 | 0x800):
                return None
            if not self._privileges(pid.value):
                return None
            return Target(hwnd, pid.value, (), None, win32gui.GetWindowRect(native), native)
        except (OSError, comtypes.COMError, AttributeError):
            return None

    def _capture(self, element):
        hwnd = int(user.GetForegroundWindow())
        pid = element.CurrentProcessId
        native = element.CurrentNativeWindowHandle
        if native and user.GetAncestor(native, 2) != hwnd:
            raise TargetError("La cible ne correspond pas à la fenêtre active.")
        if not self._privileges(pid):
            raise TargetError("Fenêtre protégée : Windows empêche Transcrinator d’y écrire.")
        r = element.CurrentBoundingRectangle
        self.target = Target(
            hwnd, pid, tuple(element.GetRuntimeId()), element, (r.left, r.top, r.right, r.bottom), native
        )
        return self.target

    def valid(self):
        target = self.target
        if not target or not user.IsWindow(target.hwnd) or user.GetForegroundWindow() != target.hwnd:
            return False
        try:
            element = self._focused()
            if target.element is None:
                info = gui_info(target.hwnd)
                native = int(info.focus or target.hwnd) if info else 0
                pid = wintypes.DWORD()
                if native:
                    user.GetWindowThreadProcessId(native, ctypes.byref(pid))
                return (native == target.native_hwnd and win32gui.IsWindowEnabled(native)
                        and pid.value == target.pid
                        and not self._blocked(element))
            return bool(element) and (
                element.CurrentProcessId == target.pid
                and self._safe(element)
                and tuple(element.GetRuntimeId()) == target.runtime_id
            )
        except (OSError, comtypes.COMError):
            return False

    def previous_character(self):
        """Read at most one character before the selection, without changing it."""
        if not self.target or self.target.element is None:
            return None
        try:
            pattern = self.target.element.GetCurrentPattern(10014).QueryInterface(self.lib.IUIAutomationTextPattern)
            selection = pattern.GetSelection()
            if not selection.Length:
                return None
            before = selection.GetElement(0).Clone()
            before.MoveEndpointByRange(1, before, 0)  # collapse to selection start
            before.MoveEndpointByUnit(0, 0, -1)  # expand one character backwards
            return before.GetText(1)[-1:]
        except (OSError, comtypes.COMError, AttributeError):
            return None

    def anchor(self):
        if not self.target:
            return None

        # Native GUI caret when available; otherwise use the editor rectangle.
        info = gui_info(self.target.hwnd)
        if info and info.caret:
            point = wintypes.POINT(info.rect.left, info.rect.bottom)
            user.ClientToScreen(info.caret, ctypes.byref(point))
            return (point.x, point.y)
        left, top, right, bottom = self.target.rect
        return (left, bottom)
