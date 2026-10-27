import datetime as dt
from fractions import Fraction
from pathlib import Path
import json
import zipfile
import pytest
from shared.domain import calculate,Records,next_review,folder_plan,create_folders,atomic_text
from shared.text_target import validate_span
from shared.installation import validate_package

@pytest.mark.parametrize('text,expected',[('0.1+0.2',Fraction(3,10)),('(12,5 + 3) / 4',Fraction(31,8)),('1/3+1/6',Fraction(1,2)),('2**10',Fraction(1024)),('-5*3',Fraction(-15))])
def test_exact_calculations(text,expected):assert calculate(text)==expected

@pytest.mark.parametrize('text',["__import__('os')",'1/0','2**1000000','[1,2]','float(3)','(1).__class__'])
def test_calculator_rejects_unsafe_inputs(text):
    with pytest.raises((ValueError,ZeroDivisionError,SyntaxError)):calculate(text)

def test_records_and_spaced_repetition(tmp_path):
    store=Records('memorinator',tmp_path);key=store.add('card',dict(question='Q',answer='R',successes=0,due='2026-10-17'))
    updated=next_review(store.all('card')[0][1],True,dt.date(2026,10,17));store.update(key,'card',updated)
    assert store.all('card')[0][1]['due']=='2026-10-19'
    assert next_review(updated,False,dt.date(2026,10,17))['due']=='2026-10-18'
    store.close();other=Records('memorinator',tmp_path);assert other.all('card')[0][1]['answer']=='R';other.close()

def test_organizer_only_creates_missing_folders(tmp_path):
    original=tmp_path/'important.txt';original.write_text('keep')
    assert len(folder_plan(tmp_path,'École'))==6
    assert len(create_folders(tmp_path,'École'))==6
    assert not create_folders(tmp_path,'École')
    assert original.read_text()=='keep'
    with pytest.raises(ValueError):folder_plan('','École')

def test_atomic_text_keeps_backup(tmp_path):
    path=tmp_path/'work.txt';atomic_text(path,'first');atomic_text(path,'second')
    assert path.read_text()=='second';assert path.with_name('work.txt.bak').read_text()=='first'

def test_utf16_selection_safety():
    validate_span('A😀B',1,3,'😀')
    with pytest.raises(ValueError):validate_span('abc',1,1,'')
    with pytest.raises(ValueError):validate_span('abc',0,2,'bc')

@pytest.mark.parametrize('name',['../outside.exe','runtime/../../oops','/absolute.exe','runtime\\escape.exe'])
def test_package_rejects_path_traversal(tmp_path,name):
    path=tmp_path/'bad.zip'
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('package.json',json.dumps(dict(schema=1,app='corrector',files={})))
        archive.writestr(name,'bad')
    with pytest.raises(ValueError):validate_package(path,'corrector')

def test_docx_roundtrip_and_pdf_extract(tmp_path):
    from shared.documents import save_docx,read_text
    path=tmp_path/'work.docx';save_docx(path,'Bonjour\nDeuxième ligne','Arial','Français')
    assert read_text(path)=='Bonjour\nDeuxième ligne'
    import pymupdf
    pdf=tmp_path/'work.pdf'
    with pymupdf.open() as document:
        page=document.new_page();page.insert_text((40,40),'Hello PDF');document.save(pdf)
    assert 'Hello PDF' in read_text(pdf)
