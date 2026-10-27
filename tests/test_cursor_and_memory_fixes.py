import pytest
from PySide6.QtWidgets import QApplication,QPlainTextEdit,QTextEdit,QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from suite_design import install,INK

@pytest.fixture(scope='module')
def app():
    a=QApplication.instance() or QApplication([]);a.setApplicationName('Corrector');install(a);return a

@pytest.mark.parametrize('cls',[QPlainTextEdit,QTextEdit,QLineEdit])
def test_editors_keep_a_visible_text_cursor_and_receive_typing(app,cls):
    from PySide6.QtGui import QPalette
    w=cls();w.resize(300,100);w.show();w.setFocus();app.processEvents()
    try:
        assert w.cursor().shape()==Qt.IBeamCursor
        assert w.palette().color(QPalette.Text).name().lower()==INK.lower()
        assert w.graphicsEffect() is None
        QTest.keyClicks(w,'Bonjour');app.processEvents()
        assert (w.text() if isinstance(w,QLineEdit) else w.toPlainText())=='Bonjour'
        if not isinstance(w,QLineEdit):assert w.cursorWidth()>=2 and w.viewport().cursor().shape()==Qt.IBeamCursor
    finally:w.close();app.processEvents()

def test_low_memory_still_returns_local_grammar_and_explicit_warning(monkeypatch):
    from ergoai.correction import correct
    def unavailable(*args,**kw):raise ValueError('RAM disponible insuffisante.')
    monkeypatch.setattr('ergoai.proofreading_client.correct',unavailable)
    result=correct('Les enfant mange des pomme.')
    assert result['text']=='Les enfants mangent des pommes.'
    assert result['degraded'] and 'IA indisponible' in result['warning']

def test_integrity_failures_and_cancel_are_not_silenced(monkeypatch):
    from ergoai.correction import correct
    def invalid(*args,**kw):raise ValueError('Le moteur a modifié des nombres.')
    monkeypatch.setattr('ergoai.proofreading_client.correct',invalid)
    with pytest.raises(ValueError,match='nombres'):correct('Marie a trois livres.')

def test_translation_and_correction_use_one_model_host(monkeypatch):
    from ergoai.proofreading_service import endpoint
    from ergoai.translation_service import endpoint as translation_endpoint
    assert endpoint()==translation_endpoint()

def test_simultaneous_service_start_does_not_load_a_second_model(monkeypatch):
    from ergoai.proofreading_service import serve
    monkeypatch.setattr('ergoai.host_instance.claim_host',lambda endpoint:False)
    serve(host_factory=lambda:pytest.fail('Duplicate host allocated a model'))

def test_scroll_background_and_message_bubble_do_not_shadow_colour_helper(app):
    from PySide6.QtWidgets import QWidget,QVBoxLayout,QScrollArea,QFrame
    root=QWidget();root.resize(400,260);layout=QVBoxLayout(root);scroll=QScrollArea();layout.addWidget(scroll)
    panel=QWidget();contents=QVBoxLayout(panel);bubble=QFrame();bubble.setObjectName('UserBubble');contents.addWidget(bubble)
    edit=QPlainTextEdit();contents.addWidget(edit);scroll.setWidget(panel);root.show();app.processEvents();edit.setFocus();app.processEvents()
    try:
        assert not panel.testAttribute(Qt.WA_TranslucentBackground)
        assert edit.cursorWidth()==2 and 'border-radius:16px' in bubble.styleSheet()
    finally:root.close();app.processEvents()
