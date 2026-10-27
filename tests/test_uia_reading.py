from types import SimpleNamespace as NS
import pytest
from shared.uia_reading import selection_from_candidates

class Element:
    def __init__(self,texts=(),password=False,window=10):
        self.texts=texts;self.CurrentIsPassword=password;self.window=window
    def GetCurrentPattern(self,identifier):return self
    def QueryInterface(self,interface):return self
    def GetSelection(self):return NS(Length=len(self.texts),GetElement=lambda index:NS(GetText=lambda limit:self.texts[index][:limit]))

def read(elements):return selection_from_candidates(elements,10014,object,lambda element:element.window==10)

def test_read_document_after_focus_container_has_no_selection():
    assert read([Element(),Element(['Un passage dans un navigateur.'])])=='Un passage dans un navigateur.'

def test_read_only_document_does_not_require_insertion_permission():
    assert read([Element(['Un PDF sélectionné.'])])=='Un PDF sélectionné.'

def test_selection_in_another_window_is_ignored():
    assert read([Element(['Fenêtre étrangère'],window=20),Element(['Bonne fenêtre'])])=='Bonne fenêtre'

def test_password_and_empty_selection_are_not_read():
    with pytest.raises(ValueError):read([Element(['secret'],password=True),Element(['   '])])

def test_multiple_selection_ranges_are_joined_and_bounded():
    assert read([Element(['Premier passage.','Second passage.'])])=='Premier passage.\nSecond passage.'
    with pytest.raises(ValueError,match='trop longue'):read([Element(['a'*24001])])

def test_stale_control_does_not_prevent_document_selection():
    class Stale(Element):
        def GetCurrentPattern(self,identifier):raise OSError('Element no longer available')
    assert read([Stale(),Element(['Texte toujours sélectionné.'])])=='Texte toujours sélectionné.'

def test_reader_fallback_uses_document_and_original_release_point(monkeypatch):
    import win32gui,shared.text_target,shared.uia_reading,shared.selection_validation
    from shared.reading_selection import read_selection
    monkeypatch.setattr(win32gui,'GetForegroundWindow',lambda:123)
    def cannot_capture():raise ValueError('Not a plain EDIT')
    monkeypatch.setattr(shared.text_target,'TextTarget',lambda:NS(capture=cannot_capture))
    monkeypatch.setattr(shared.selection_validation,'read_uia_selection',lambda expected:cannot_capture())
    calls=[]
    def document(expected,point=None):calls.append((expected,point));return 'Message Codex.'
    monkeypatch.setattr(shared.uia_reading,'read_document_selection',document)
    assert read_selection(123,point=(700,500))=='Message Codex.'
    assert calls==[(123,(700,500))]

def test_working_firefox_reader_is_kept_before_document_fallback(monkeypatch):
    import win32gui,shared.text_target,shared.uia_reading,shared.selection_validation
    from shared.reading_selection import read_selection
    monkeypatch.setattr(win32gui,'GetForegroundWindow',lambda:123)
    def cannot_capture():raise ValueError('Not a plain EDIT')
    monkeypatch.setattr(shared.text_target,'TextTarget',lambda:NS(capture=cannot_capture))
    calls=[]
    def previous_reader(expected):calls.append(expected);return 'Sélection Firefox conservée.'
    monkeypatch.setattr(shared.selection_validation,'read_uia_selection',previous_reader)
    monkeypatch.setattr(shared.uia_reading,'read_document_selection',lambda *args,**kwargs:pytest.fail('Must preserve the working reader'))
    assert read_selection(123,point=(700,500))=='Sélection Firefox conservée.'
    assert calls==[123]

def test_native_edit_reader_is_kept_before_uia(monkeypatch):
    import win32gui,shared.text_target,shared.selection_validation
    from shared.reading_selection import read_selection
    monkeypatch.setattr(win32gui,'GetForegroundWindow',lambda:123)
    monkeypatch.setattr(shared.text_target,'TextTarget',lambda:NS(capture=lambda:NS(selected='Sélection Windows.')))
    monkeypatch.setattr(shared.selection_validation,'read_uia_selection',lambda expected:pytest.fail('Native reader already succeeded'))
    assert read_selection(123)=='Sélection Windows.'

def test_focus_change_refuses_document_read(monkeypatch):
    import win32gui,shared.uia_reading
    from shared.reading_selection import read_selection
    monkeypatch.setattr(win32gui,'GetForegroundWindow',lambda:456)
    monkeypatch.setattr(shared.uia_reading,'read_document_selection',lambda *args,**kwargs:pytest.fail('Should not read a changed window'))
    with pytest.raises(ValueError,match='fenêtre a changé'):read_selection(123)
