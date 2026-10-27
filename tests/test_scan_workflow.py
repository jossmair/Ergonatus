import pytest
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication,QWidget,QPushButton
from PySide6.QtTest import QTest
from shared.ocr import format_text,clipboard_html

@pytest.fixture(scope='session')
def app():return QApplication.instance() or QApplication([])

@pytest.fixture
def scan(app,tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.text import TextApplication
    window=TextApplication('scanator');window.show();app.processEvents()
    yield window
    window.closing=True;window.layout_timer.stop();window.orb.close();window.tray.hide();window.server.close();window.records.close();window.close()

def test_paragraphs_preserve_content_lists_and_separations():
    assert format_text('Une phrase\nsur deux lignes.\n\nUne autre.','paragraphs')=='Une phrase sur deux lignes.\n\nUne autre.'
    assert format_text('Titre\n- Premier\ncomplément\n- Second')=='Titre\n\n- Premier complément\n\n- Second'
    assert format_text('Nom\tNote\nAlice\t18','columns')=='Nom\tNote\nAlice\t18'

def test_clipboard_html_is_clean_and_escaped():
    html=clipboard_html('<texte> & exemple\n\nSuite','paragraphs')
    assert '<p>&lt;texte&gt; &amp; exemple</p>' in html and '<p>Suite</p>' in html
    assert '<img' not in html and 'background' not in html
    assert '<td>Alice</td><td>18</td>' in clipboard_html('Nom\tNote\nAlice\t18','columns')

def test_scanator_has_compact_actions_and_reversible_layout(scan,app):
    assert not scan.image_label.isVisible()
    assert all(button.height()<=36 for button in (scan.scan_open,scan.scan_capture,scan.scan_copy))
    assert not any('Enregistrer l’image' in button.text() for button in scan.findChildren(QPushButton))
    scan.scan_recognized('Une phrase\nsur deux lignes.')
    assert scan.input.toPlainText()=='Une phrase sur deux lignes.'
    scan.scan_layout.setCurrentIndex(1)
    assert scan.input.toPlainText()=='Une phrase\nsur deux lignes.'
    scan.input.insertPlainText('Ajout ');edited=scan.input.toPlainText()
    scan.scan_layout.setCurrentIndex(0)
    assert 'Ajout' in scan.input.toPlainText()
    scan.input.undo();assert scan.input.toPlainText()==edited

class FakeCapture(QWidget):
    captured=Signal(object);cancelled=Signal()

def test_orb_capture_copies_without_opening_the_window(scan,app,monkeypatch):
    import shared.apps.overlays
    monkeypatch.setattr(shared.apps.overlays,'CaptureOverlay',FakeCapture)
    copied=[];monkeypatch.setattr(scan,'write_scan_clipboard',lambda text,html:copied.append((text,html)))
    monkeypatch.setattr(scan,'ocr',lambda:scan.scan_recognized('Texte reconnu\nen deux lignes.'))
    scan.hide();scan.activate();assert scan.capture_pending
    scan.activate();QTest.qWait(300)
    scan.capture_overlay.captured.emit(QPixmap(40,30));app.processEvents()
    assert copied[0][0]=='Texte reconnu en deux lignes.' and '<p>' in copied[0][1]
    assert not scan.isVisible() and not scan.capture_pending
    menu=scan.create_orb_menu();next(action for action in menu.actions() if action.text()=='Ouvrir Scanator').trigger()
    assert scan.isVisible() and not scan.capture_pending
    menu.close()

def test_cancel_and_empty_ocr_preserve_clipboard(scan,app,monkeypatch):
    import shared.apps.overlays
    monkeypatch.setattr(shared.apps.overlays,'CaptureOverlay',FakeCapture)
    copied=[];monkeypatch.setattr(scan,'write_scan_clipboard',lambda *values:copied.append(values))
    scan.hide();scan.activate();QTest.qWait(300);scan.capture_overlay.cancelled.emit();app.processEvents()
    assert not copied and not scan.isVisible()
    scan.scan_auto_copy=True;scan.scan_recognized('   ')
    assert not copied and scan.orb.state=='Attention'
