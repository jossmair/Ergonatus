from pathlib import Path
from dataclasses import replace
import json,os,time,threading,zipfile
import pytest
from shared.organizer import (PROFILES,INBOX,create_space,load_space,folder_specs,analyze,apply_moves,undo_last,inside,read_text)


@pytest.fixture
def space(tmp_path):
    return create_space(tmp_path,'Mes fichiers','Particulier')[0]


@pytest.mark.parametrize('profile',list(PROFILES))
def test_profiles_create_all_folders_and_preserve_desktop_files(tmp_path,profile):
    original=tmp_path/'Important.txt';original.write_text('Ne pas toucher')
    root,config=create_space(tmp_path,'Mon espace',profile)
    assert all((root/spec['path']).is_dir() for spec in folder_specs(profile))
    assert original.read_text()=='Ne pas toucher'
    with pytest.raises(FileExistsError):create_space(tmp_path,'Mon espace',profile)
    assert original.read_text()=='Ne pas toucher' and load_space(root)[1]['profile']==profile


@pytest.mark.parametrize('name',['..','../ailleurs','C:\\temp','NUL','AUX.txt','nom.','/absolu','nom?'])
def test_invalid_space_names_are_refused(tmp_path,name):
    with pytest.raises(ValueError):create_space(tmp_path,name,'Collège')


def test_names_and_content_classify_and_ambiguity_stays(space):
    (space/INBOX/'facture eau.txt').write_text('Montant de votre facture',encoding='utf-8')
    (space/INBOX/'scan.txt').write_text('Ordonnance de mon médecin : suivi médical',encoding='utf-8')
    (space/INBOX/'note.txt').write_text('Sans indice particulier',encoding='utf-8')
    proposals,warnings=analyze(space);rows={Path(p.source).name:p for p in proposals}
    assert rows['facture eau.txt'].destination=='Factures' and rows['facture eau.txt'].confidence>=.92
    assert rows['scan.txt'].destination=='Santé' and rows['note.txt'].destination==INBOX
    assert not warnings


def test_school_subfolders_and_english_not_ambiguous(tmp_path):
    root,_=create_space(tmp_path,'Collège','Collège')
    (root/INBOX/'exercices maths.txt').write_text('Fractions',encoding='utf-8')
    (root/INBOX/'anglais.txt').write_text('English vocabulary',encoding='utf-8')
    result,_=analyze(root);dest={Path(p.source).name:p.destination for p in result}
    assert dest=={'anglais.txt':'Anglais/Cours','exercices maths.txt':'Mathématiques/Exercices'}


def test_move_collision_and_undo_never_overwrite(space):
    source=space/INBOX/'facture.txt';source.write_text('NOUVELLE FACTURE')
    existing=space/'Factures/facture.txt';existing.write_text('FACTURE EXISTANTE')
    plans,_=analyze(space);moved,errors=apply_moves(space,plans)
    assert len(moved)==1 and not errors and existing.read_text()=='FACTURE EXISTANTE'
    destination=space/moved[0]['destination'];assert destination.name=='facture (1).txt' and destination.read_text()=='NOUVELLE FACTURE'
    restored,errors=undo_last(space);assert len(restored)==1 and not errors
    assert source.read_text()=='NOUVELLE FACTURE' and existing.read_text()=='FACTURE EXISTANTE'
    assert undo_last(space)==([],[])


def test_changed_source_not_moved_and_changed_destination_not_undone(space):
    source=space/INBOX/'facture.txt';source.write_text('Ancienne version');plans,_=analyze(space)
    source.write_text('Version modifiée plus longue');assert not apply_moves(space,plans)[0] and source.exists()
    plans,_=analyze(space);moved,_=apply_moves(space,plans);destination=space/moved[0]['destination'];destination.write_text('MODIFIÉ APRÈS TRI')
    restored,errors=undo_last(space);assert not restored and errors and destination.read_text()=='MODIFIÉ APRÈS TRI'


def test_undo_keeps_new_file_at_original_location(space):
    source=space/INBOX/'facture.txt';source.write_text('ORIGINAL');plans,_=analyze(space);moved,_=apply_moves(space,plans)
    source.write_text('NOUVEAU');restored,errors=undo_last(space)
    assert not restored and errors and source.read_text()=='NOUVEAU' and (space/moved[0]['destination']).read_text()=='ORIGINAL'


def test_no_escape_or_unselected_file_moves(space,tmp_path):
    source=space/INBOX/'facture.txt';source.write_text('À classer');outside=tmp_path/'extérieur.txt';outside.write_text('HORS ESPACE')
    plans,_=analyze(space)
    assert not apply_moves(space,[replace(plans[0],destination='../ailleurs')])[0]
    assert not apply_moves(space,[replace(plans[0],source='../extérieur.txt')])[0]
    assert source.read_text()=='À classer' and outside.read_text()=='HORS ESPACE'
    with pytest.raises(ValueError):inside(space,space/'../absent.txt')


def test_link_like_destination_is_rejected(space,monkeypatch):
    import shared.organizer as organizer
    source=space/INBOX/'facture.txt';source.write_text('ORIGINAL');plans,_=analyze(space)
    original=organizer._link;monkeypatch.setattr(organizer,'_link',lambda p:p==space/'Factures' or original(p))
    assert not apply_moves(space,plans)[0] and source.read_text()=='ORIGINAL'


def test_cancel_leaves_files_in_place(space):
    file=space/INBOX/'facture.txt';file.write_text('ORIGINAL');plans,_=analyze(space);cancel=threading.Event();cancel.set()
    assert apply_moves(space,plans,cancel)==([],[]) and file.exists()


def test_office_text_and_no_external_program_needed(tmp_path):
    path=tmp_path/'devoir.docx'
    with zipfile.ZipFile(path,'w') as archive:archive.writestr('word/document.xml','<document><p>Exercice de mathématiques</p></document>')
    assert 'mathématiques' in read_text(path)[0]


def test_planned_crash_can_be_undone(space,monkeypatch):
    import shared.organizer as organizer
    source=space/INBOX/'facture.txt';source.write_text('ORIGINAL');plans,_=analyze(space);real=organizer._journal
    def journal(root,item):
        if item['state']=='moved':raise OSError('Panne simulée après déplacement')
        real(root,item)
    monkeypatch.setattr(organizer,'_journal',journal);moved,errors=apply_moves(space,plans)
    assert moved and errors;monkeypatch.setattr(organizer,'_journal',real)
    assert undo_last(space)[0] and source.read_text()=='ORIGINAL'


@pytest.fixture
def window(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QThreadPool
    app=QApplication.instance() or QApplication([]);monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path/'data'));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.organizer_workspace import OrganisatorWindow
    desktop=tmp_path/'Bureau';desktop.mkdir();w=OrganisatorWindow(desktop);w.show();app.processEvents();yield w
    w.closing=True;w.cleanup();QThreadPool.globalInstance().waitForDone(10000);app.processEvents();w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()


def wait_for(predicate,timeout=10):
    from PySide6.QtTest import QTest
    deadline=time.monotonic()+timeout
    while not predicate():
        assert time.monotonic()<deadline,'Traitement trop long'
        QTest.qWait(30)


def test_gui_create_preview_move_undo_with_mouse(window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w=window;w.profile.setCurrentText('Collège');QTest.mouseClick(w.create_button,Qt.LeftButton);wait_for(lambda:w.root is not None and not w.busy)
    source=w.root/INBOX/'exercices maths.txt';source.write_text('Exercices de mathématiques : fractions.',encoding='utf-8');w.scan();wait_for(lambda:not w.busy and len(w.proposals)==1)
    wait_for(lambda:'fractions' in w.preview_text.toPlainText())
    QTest.mouseClick(w.sort_button,Qt.LeftButton);wait_for(lambda:not w.busy)
    assert (w.root/'Mathématiques/Exercices'/source.name).is_file()
    QTest.mouseClick(w.undo_button,Qt.LeftButton);wait_for(lambda:not w.busy)
    assert source.read_text(encoding='utf-8').startswith('Exercices') and not w.auto.isChecked()


def test_auto_sort_only_high_confidence_and_stable_files(window):
    w=window;w.profile.setCurrentText('Professionnel');w.create();wait_for(lambda:w.root is not None and not w.busy)
    source=w.root/INBOX/'facture client.txt';source.write_text('facture facture facture',encoding='utf-8')
    # An unambiguous name; Client alone in the filename is deliberately ambiguous.
    source.rename(w.root/INBOX/'facture.txt');source=w.root/INBOX/'facture.txt'
    uncertain=w.root/INBOX/'inconnu.txt';uncertain.write_text('Sans thème évident',encoding='utf-8');past=time.time()-10;os.utime(source,(past,past))
    w.auto.setChecked(True);wait_for(lambda:(w.root/'Factures/facture.txt').exists() and not w.busy)
    assert uncertain.exists();w.undo();wait_for(lambda:not w.busy);assert source.exists() and not w.auto.isChecked()


def test_auto_sort_waits_for_new_file_to_settle(window):
    w=window;w.profile.setCurrentText('Professionnel');w.create();wait_for(lambda:w.root is not None and not w.busy)
    source=w.root/INBOX/'facture récente.txt';source.write_text('Facture du jour',encoding='utf-8')
    w.auto.setChecked(True)
    wait_for(lambda:(w.root/'Factures'/source.name).exists() and not w.busy,12)


def test_icons_and_visual_previews(window,tmp_path):
    from shared.organizer import Proposal
    from PySide6.QtGui import QImage,QColor
    from shared.apps.organizer_workspace import preview_file
    import pymupdf
    w=window;w.create();wait_for(lambda:w.root is not None and not w.busy)
    assert (w.root/'Français/desktop.ini').is_file()
    assert list((w.root/'.organisator/icons').glob('*.ico'))
    image=QImage(80,60,QImage.Format_RGB32);image.fill(QColor('red'));path=w.root/INBOX/'image.png';image.save(str(path))
    info=path.stat();proposal=Proposal(str(path.relative_to(w.root)),INBOX,0,'',info.st_size,info.st_mtime_ns)
    assert not preview_file(w.root,proposal)[0].isNull()
    path=w.root/INBOX/'lecture.pdf'
    with pymupdf.open() as pdf:
        page=pdf.new_page();page.insert_text((60,60),'Document de lecture');pdf.save(path)
    info=path.stat();proposal=Proposal(str(path.relative_to(w.root)),INBOX,0,'',info.st_size,info.st_mtime_ns)
    result=preview_file(w.root,proposal)
    assert not result[0].isNull() and 'lecture' in result[1]


def test_spaces_remembered_and_reopened_from_window(window):
    from PySide6.QtWidgets import QListWidget
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w=window;w.create();wait_for(lambda:w.root is not None and not w.busy);first=w.root
    w.new_space();w.profile.setCurrentText('Particulier');w.create();wait_for(lambda:w.root is not None and not w.busy);second=w.root
    assert first!=second
    w.show_spaces();listing=w.spaces_window.findChild(QListWidget)
    assert listing.count()==2
    item=next(listing.item(i) for i in range(2) if listing.item(i).data(Qt.UserRole)==str(first))
    QTest.mouseClick(listing.viewport(),Qt.LeftButton,pos=listing.visualItemRect(item).center())
    assert w.root==first and not w.spaces_window.isVisible()
    assert len(w.preferences['organizer_spaces'])==2
    saved=w.records.all('settings')[0][1]['organizer_spaces']
    assert saved[0]['path']==str(first) and len(saved)==2


def test_missing_space_stays_in_list_without_switching(window):
    from PySide6.QtWidgets import QListWidget
    from PySide6.QtCore import Qt
    w=window;missing=w.desktop/'Absent';w.remember('organizer_spaces',[dict(path=str(missing),name='Absent',profile='Collège')]);w.show_spaces()
    listing=w.spaces_window.findChild(QListWidget)
    assert 'introuvable' in listing.item(0).text()
    listing.itemClicked.emit(listing.item(0))
    assert w.root is None and w.spaces_window.isVisible()
    w.spaces_window.close()
