import json,time
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QThreadPool
from PySide6.QtTest import QTest
from shared.organizer import create_space,INBOX
from shared.apps.organizer_binder import list_documents,preview_document,BinderDocument,text_pages

def wait(predicate,seconds=8):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        QApplication.processEvents();QTest.qWait(20)
        if predicate():return
    assert predicate()

@pytest.fixture(scope='session')
def binder_app():return QApplication.instance() or QApplication([])

@pytest.fixture
def book(binder_app,tmp_path,monkeypatch):
    app=binder_app
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path/'data'));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from suite_design import install
    app.setApplicationName('Organisator');install(app)
    from shared.apps.organizer_workspace import OrganisatorWindow
    desktop=tmp_path/'Bureau';desktop.mkdir();root,config=create_space(desktop,'Mon classeur','Collège')
    (root/'Mathématiques/Cours/01 Fractions.txt').write_text('Comprendre les fractions.\n'+('Une fraction représente une partie du tout. '*70),encoding='utf-8')
    import pymupdf
    with pymupdf.open() as pdf:
        for text in ('Première feuille','Deuxième feuille'):
            page=pdf.new_page();page.insert_text((40,60),text)
        pdf.save(root/'Mathématiques/Cours/02 Exercices.pdf')
    w=OrganisatorWindow(desktop);w.use_space(root,config);wait(lambda:not w.busy)
    yield w,root
    w.closing=True;w.cleanup();QThreadPool.globalInstance().waitForDone(10000);app.processEvents();w.layout_timer.stop();w.orb.close();w.server.close();w.records.close();w.close();app.processEvents()

def test_single_click_opens_binder_double_click_opens_manager(book):
    w,root=book;w.hide();QTest.mouseClick(w.orb,Qt.LeftButton)
    wait(lambda:w.binder is not None and w.binder.isVisible())
    assert not w.isVisible()
    QTest.mouseDClick(w.orb,Qt.LeftButton);QApplication.processEvents()
    assert w.isVisible() and not w.binder.isVisible()
    w.toggle_binder();assert w.binder.isVisible();w.toggle_binder();assert not w.binder.isVisible()

def test_nested_documents_and_pdf_pages_are_real_and_read_only(book,monkeypatch):
    w,root=book;before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    w.toggle_binder();b=w.binder;wait(lambda:len(b.documents)==2)
    b.set_section('Mathématiques');wait(lambda:b.current is not None and b.open_button.isEnabled())
    assert b.list.count()==2
    b.list.setCurrentRow(1);wait(lambda:b.kind.text()=='PDF' and b.open_button.isEnabled())
    assert b.pages==2 and b.page==0
    b.step(1);wait(lambda:b.page==1 and b.open_button.isEnabled());assert not b.next.isEnabled()
    b.step(-1);wait(lambda:b.page==0 and b.open_button.isEnabled())
    opened=[];monkeypatch.setattr('shared.apps.organizer_binder.QDesktopServices.openUrl',lambda url:opened.append(url.toLocalFile()) or True)
    b.open_button.click();assert Path(opened[0])==root/'Mathématiques/Cours/02 Exercices.pdf'
    assert all((root/name).read_bytes()==content for name,content in before.items())

def test_search_and_folder_context_keep_original_paths(book):
    w,root=book;w.toggle_binder();b=w.binder;wait(lambda:len(b.documents)==2);b.set_section('Mathématiques')
    b.search.setText('exercices');wait(lambda:b.list.count()==1)
    assert b.visible_documents[0].relative.endswith('02 Exercices.pdf')
    assert 'Cours' in [b.folder.itemText(i) for i in range(b.folder.count())]
    b.set_section('Français');assert b.list.count()==0 and not b.open_button.isEnabled()

def test_text_pagination_and_ecr_preview(book):
    w,root=book;rows,_=list_documents(root);doc=next(d for d in rows if d.relative.endswith('.txt'))
    first=preview_document(root,doc);last=preview_document(root,doc,-1)
    assert first['pages']>1 and last['page']==last['pages']-1
    assert len(''.join(text_pages('Un texte. '*900)))>5000
    file=root/INBOX/'Texte.ecr';file.write_text(json.dumps(dict(document=dict(body=[dict(text='Bonjour le classeur')]))),encoding='utf-8')
    info=file.stat();result=preview_document(root,BinderDocument(file.relative_to(root).as_posix(),info.st_size,info.st_mtime_ns))
    assert 'Bonjour le classeur' in result['text']

def test_index_refuses_redirected_paths(book,monkeypatch):
    w,root=book
    import shared.organizer as organizer
    original=organizer._link;monkeypatch.setattr(organizer,'_link',lambda p:p==root/'Mathématiques' or original(p))
    assert not list_documents(root)[0]

def test_widget_is_fullscreen_and_opacity_only_changes_backdrop(book):
    w,root=book;w.toggle_binder();b=w.binder;wait(lambda:b.isFullScreen() and len(b.documents)==2)
    assert b.geometry()==b.screen().geometry()
    b.opacity_slider.setValue(0);QApplication.processEvents();clear=b.grab().toImage().pixelColor(0,0).alpha()
    b.opacity_slider.setValue(100);QApplication.processEvents();opaque=b.grab().toImage().pixelColor(0,0).alpha()
    assert clear<10 and opaque>245 and b.windowOpacity()==1
    assert w.preferences['organizer_binder_opacity']==100
