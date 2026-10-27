"""UIA reads and verified plain-text writes, all on one dedicated COM thread.

There is no SendInput, click, automatic paste or send operation here.
Rich editors unsupported by ValuePattern use an explicit manual clipboard fallback.
"""
from dataclasses import dataclass
import os
import time
import uuid
from app.security.validation import fingerprint, splice_text


@dataclass(frozen=True)
class Target:
    token: str
    hwnd: int
    window_pid: int
    pid: int
    created: float
    runtime_id: tuple
    title: str
    control_name: str
    selected: str
    original: str | None
    start: int | None
    end: int | None
    writable: bool
    native_edit: int = 0

    @property
    def caption(self):
        return (self.title[:65] or "Fenêtre sans titre") + (" · " + self.control_name[:45] if self.control_name else "")


class Accessibility:
    """Instantiate and call only from the Windows worker thread."""
    def __init__(self):
        import comtypes
        import comtypes.client
        comtypes.CoInitialize()
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen import UIAutomationClient as UIA
        self.api = UIA
        self.client = comtypes.client.CreateObject("{E22AD333-B25F-460C-83D0-0581107395C9}", interface=UIA.IUIAutomation2)
        self.client.ConnectionTimeout = 2000
        self.client.TransactionTimeout = 1500
        self.elements = {}

    @staticmethod
    def native_span(hwnd, original):
        """EM_GETSEL on a verified standard EDIT; offsets are UTF-16 code units."""
        import ctypes
        from ctypes import wintypes
        native = ctypes.WinDLL("user32", use_last_error=True)
        native.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
            wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
        native.SendMessageTimeoutW.restype = wintypes.LPARAM
        result = ctypes.c_size_t()
        if not native.SendMessageTimeoutW(hwnd, 0x00B0, 0, 0, 2, 300, ctypes.byref(result)):
            raise ValueError("Le champ ne répond pas. Aucun texte inséré.")
        first, last = result.value & 0xffff, (result.value >> 16) & 0xffff
        encoded = original.encode("utf-16-le")
        if not 0 <= first <= last <= len(encoded) // 2 < 65535:
            raise ValueError("Position de sélection non fiable.")
        start = len(encoded[:first * 2].decode("utf-16-le"))
        end = len(encoded[:last * 2].decode("utf-16-le"))
        return start, end

    def capture(self, expected_hwnd=0):
        import psutil
        import win32gui
        import win32process
        foreground = win32gui.GetForegroundWindow()
        if expected_hwnd and foreground != expected_hwnd:
            raise ValueError("Le focus a changé pendant la capture. Cliquez dans le champ, puis sur l’orbe.")
        _, window_pid = win32process.GetWindowThreadProcessId(foreground)
        if window_pid == os.getpid():
            raise ValueError("Choisissez le champ d’une autre application, puis cliquez sur l’orbe Redactor.")
        element = self.client.GetFocusedElement()
        pid = element.CurrentProcessId
        if pid == os.getpid() or element.CurrentIsPassword:
            raise ValueError("Ce champ est privé ou appartient à Redactor. Aucune capture n’a été effectuée.")
        # Bind the focused UIA element to the actual foreground root window.
        root = element
        walker = self.client.RawViewWalker
        linked = False
        for _ in range(64):
            handle = root.CurrentNativeWindowHandle
            if handle and win32gui.GetAncestor(handle, 2) == foreground:
                linked = True
                break
            root = walker.GetParentElement(root)
            if not root:
                break
        if not linked:
            raise ValueError("Le contrôle actif ne peut pas être rattaché à la fenêtre. Choisissez une destination explicite.")
        selected, original, start, end, writable, native_edit = "", None, None, None, False, 0
        value_writable = False
        try:
            value_pattern = element.GetCurrentPattern(self.api.UIA_ValuePatternId).QueryInterface(self.api.IUIAutomationValuePattern)
            original = value_pattern.CurrentValue
            value_writable = not value_pattern.CurrentIsReadOnly
            writable = value_writable and element.CurrentControlType == self.api.UIA_EditControlTypeId
        except Exception:
            pass
        try:
            text = element.GetCurrentPattern(self.api.UIA_TextPatternId).QueryInterface(self.api.IUIAutomationTextPattern)
            selection = text.GetSelection()
            if selection.Length == 1:
                selected_range = selection.GetElement(0)
                selected = selected_range.GetText(24001)
                if len(selected) > 24000:
                    raise ValueError("Sélection trop longue. Sélectionnez un passage de moins de 24 000 caractères.")
                full_range = text.DocumentRange
                document = full_range.GetText(24001)
                prefix = full_range.Clone()
                prefix.MoveEndpointByRange(self.api.TextPatternRangeEndpoint_End, selected_range, self.api.TextPatternRangeEndpoint_Start)
                prefix_text = prefix.GetText(24001)
                if original is not None and document == original and len(document) <= 24000:
                    start, end = len(prefix_text), len(prefix_text) + len(selected)
                    if original[start:end] != selected or not 0 <= start <= end <= len(original):
                        start = end = None
        except Exception:
            pass
        if len(selected) > 24000:
            raise ValueError("Sélection trop longue. Sélectionnez un passage de moins de 24 000 caractères.")
        # Standard Win32 EDIT controls expose ValuePattern but often no TextPattern.
        # Their native selection is still unambiguous; do not extend to RichEdit.
        native_handle = element.CurrentNativeWindowHandle
        if original is not None and len(original) <= 24000 and native_handle:
            try:
                _, native_pid = win32process.GetWindowThreadProcessId(native_handle)
                if (win32gui.GetClassName(native_handle).casefold() == "edit" and native_pid == pid
                        and win32gui.GetAncestor(native_handle, 2) == foreground):
                    start, end = self.native_span(native_handle, original)
                    selected = original[start:end]
                    native_edit = int(native_handle)
                    # UIA8 exposes multiline Win32 EDIT as Document (50030).
                    # The verified native class, PID, root and selection prove
                    # this is still a plain EDIT, not a rich document editor.
                    writable = value_writable
            except Exception:
                start = end = None
        if win32gui.GetForegroundWindow() != foreground:
            raise ValueError("La fenêtre active a changé pendant la capture. Veuillez réessayer.")
        target = Target(uuid.uuid4().hex, foreground, window_pid, pid, psutil.Process(pid).create_time(),
                        tuple(element.GetRuntimeId()), win32gui.GetWindowText(foreground), element.CurrentName or "",
                        selected, original, start, end, bool(writable and start is not None and end is not None), native_edit)
        self.elements[target.token] = element
        while len(self.elements) > 8:
            self.elements.pop(next(iter(self.elements)))
        return target

    def validate(self, target):
        import psutil
        import win32gui
        import win32process
        if not win32gui.IsWindow(target.hwnd) or not win32gui.IsWindowVisible(target.hwnd):
            raise ValueError("La fenêtre cible n’existe plus ou n’est plus visible. Choisissez à nouveau la destination.")
        _, pid = win32process.GetWindowThreadProcessId(target.hwnd)
        if pid != target.window_pid or psutil.Process(target.pid).create_time() != target.created:
            raise ValueError("L’identité de la fenêtre cible a changé. Choisissez à nouveau la destination.")
        if win32gui.GetWindowText(target.hwnd) != target.title:
            raise ValueError("Le document ou le titre de la fenêtre a changé. Choisissez à nouveau la destination.")
        element = self.elements.get(target.token)
        if element is None or tuple(element.GetRuntimeId()) != target.runtime_id or element.CurrentProcessId != target.pid:
            raise ValueError("Le contrôle cible a changé. Choisissez à nouveau la destination.")
        if element.CurrentIsPassword or not element.CurrentIsEnabled or element.CurrentIsOffscreen:
            raise ValueError("Le champ cible n’est pas disponible pour l’insertion.")
        if (element.CurrentName or "") != target.control_name:
            raise ValueError("L’identité du champ a changé. Choisissez à nouveau la destination.")
        return element

    def selection(self, target):
        self.validate(target)
        # Return the captured selection, never an implicit clipboard operation.
        if not target.selected:
            raise ValueError("Aucun texte sélectionné dans la cible mémorisée. Sélectionnez du texte puis cliquez sur l’orbe.")
        return target.selected

    def insert(self, target, replacement):
        import win32gui
        element = self.validate(target)
        if not target.writable or target.original is None:
            raise ValueError("Cet éditeur ne permet pas une insertion UI Automation fiable. Utilisez Copier, puis collez vous-même dans le champ choisi.")
        value = element.GetCurrentPattern(self.api.UIA_ValuePatternId).QueryInterface(self.api.IUIAutomationValuePattern)
        if value.CurrentIsReadOnly or value.CurrentValue != target.original:
            raise ValueError("Le texte du champ a changé depuis sa sélection. Choisissez à nouveau la destination.")
        if target.native_edit and self.native_span(target.native_edit, target.original) != (target.start, target.end):
            raise ValueError("Le point d’insertion ou la sélection a changé. Choisissez à nouveau le champ.")
        if not target.native_edit:
            try:
                pattern = element.GetCurrentPattern(self.api.UIA_TextPatternId).QueryInterface(self.api.IUIAutomationTextPattern)
                selections = pattern.GetSelection()
                if selections.Length != 1: raise ValueError()
                current = selections.GetElement(0)
                prefix = pattern.DocumentRange.Clone()
                prefix.MoveEndpointByRange(self.api.TextPatternRangeEndpoint_End, current, self.api.TextPatternRangeEndpoint_Start)
                start = len(prefix.GetText(24001))
                selected = current.GetText(24001)
                if (start, start + len(selected), selected) != (target.start, target.end, target.selected):
                    raise ValueError()
            except Exception:
                raise ValueError("La sélection n’est plus identique. Choisissez à nouveau la destination.") from None
        wanted = splice_text(target.original, target.start, target.end, target.selected, replacement)
        win32gui.SetForegroundWindow(target.hwnd)
        element.SetFocus()
        focused = self.client.GetFocusedElement()
        if win32gui.GetForegroundWindow() != target.hwnd or tuple(focused.GetRuntimeId()) != target.runtime_id:
            raise ValueError("Windows n’a pas confirmé le focus sur le champ choisi. Aucun texte inséré.")
        # Check again immediately before the only write in this module.
        self.validate(target)
        if value.CurrentValue != target.original:
            raise ValueError("Le champ vient de changer. Aucun texte inséré.")
        value.SetValue(wanted)
        if value.CurrentValue != wanted:
            raise ValueError("L’application n’a pas confirmé le texte attendu. Vérifiez le champ ; ne relancez pas l’insertion automatiquement.")
        self.elements.pop(target.token, None)  # One-shot target; no accidental second insertion.

    def close(self):
        self.elements.clear()
        self.client = None
        import comtypes
        comtypes.CoUninitialize()
