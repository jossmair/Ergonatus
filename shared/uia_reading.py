"""Read selection from document providers, independently of insertion permissions."""
import os

def selection_from_candidates(candidates,pattern_id,interface,belongs):
    """Only return an explicit nonempty selection from the expected window."""
    for element in candidates:
        try:
            if element.CurrentIsPassword or not belongs(element):continue
            pattern=element.GetCurrentPattern(pattern_id).QueryInterface(interface)
            ranges=pattern.GetSelection()
            if not 1<=ranges.Length<=16:continue
            parts=[ranges.GetElement(index).GetText(24001) for index in range(ranges.Length)]
            text='\n'.join(part for part in parts if part.strip())
            if len(text)>24000:raise ValueError('Sélection trop longue : choisissez un passage plus court.')
            if text.strip():return text
        except ValueError:raise
        except Exception:continue
    raise ValueError('Cette application ne fournit pas de texte sélectionné accessible. Essayez un autre passage ou collez-le dans Lector.')

def read_document_selection(expected,point=None):
    import win32gui,win32process
    import comtypes,comtypes.client
    if not expected or win32gui.GetForegroundWindow()!=expected:raise ValueError('La fenêtre active a changé. Sélectionnez à nouveau le passage.')
    if win32process.GetWindowThreadProcessId(expected)[1]==os.getpid():raise ValueError('Sélectionnez le texte dans une autre application.')
    comtypes.CoInitialize()
    try:
        comtypes.client.GetModule('UIAutomationCore.dll')
        from comtypes.gen import UIAutomationClient as api
        client=comtypes.client.CreateObject('{E22AD333-B25F-460C-83D0-0581107395C9}',interface=api.IUIAutomation2)
        client.ConnectionTimeout=2000;client.TransactionTimeout=1500
        walker=client.RawViewWalker
        root=client.ElementFromHandle(expected)
        focused=client.GetFocusedElement()
        if focused.CurrentIsPassword:raise ValueError('Les champs confidentiels ne sont pas lus.')
        def belongs(element):
            for _ in range(40):
                if not element:return False
                if element.CurrentIsPassword:return False
                handle=element.CurrentNativeWindowHandle
                if handle:return win32gui.GetAncestor(handle,2)==expected
                element=walker.GetParentElement(element)
            return False
        def candidates():
            seeds=[]
            try:
                x,y=point if point is not None else win32gui.GetCursorPos();seeds.append(client.ElementFromPoint(api.tagPOINT(x,y)))
            except Exception:pass
            seeds.append(focused)
            visited=set()
            for element in seeds:
                for _ in range(40):
                    if not element:break
                    try:
                        identity=tuple(element.GetRuntimeId())
                        if identity in visited:break
                        visited.add(identity)
                        if not belongs(element):break
                        yield element
                        element=walker.GetParentElement(element)
                    except Exception:break
            # A browser can keep focus on a container while its document owns
            # the selection. Query document providers within this window only.
            yield root
            condition=client.CreatePropertyCondition(api.UIA_IsTextPatternAvailablePropertyId,True)
            documents=root.FindAll(api.TreeScope_Descendants,condition)
            for index in range(min(documents.Length,128)):
                element=documents.GetElement(index)
                if belongs(element):yield element
        text=selection_from_candidates(candidates(),api.UIA_TextPatternId,api.IUIAutomationTextPattern,belongs)
        if win32gui.GetForegroundWindow()!=expected:raise ValueError('La fenêtre a changé pendant la lecture de la sélection.')
        return text
    finally:comtypes.CoUninitialize()
