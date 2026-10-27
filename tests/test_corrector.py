import threading
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from ergoai.correction import correct_rules as correct

def test_real_grammar_corrects_reported_sentence_and_agreements():
    assert correct('teste pour voir si sa marchent biens ici')['text']=='Teste pour voir si ça marche bien ici.'
    assert correct('Les enfant mange des pomme.')['text']=='Les enfants mangent des pommes.'
    assert correct('Bonjour, je voudrais un verre d’eau.')['changes']==0

def test_real_grammar_keeps_paragraphs_and_cancel():
    assert correct('Les enfant.\n\nDes pomme.')['text']=='Les enfants.\n\nDes pommes.'
    cancelled=threading.Event();cancelled.set()
    with pytest.raises(ValueError,match='annul'):correct('Un texte.',cancelled)

@pytest.fixture
def window(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    import ergoai.correction
    monkeypatch.setattr(ergoai.correction,'correct',ergoai.correction.correct_rules)
    from shared.apps.corrector import CorrectorWindow
    w=CorrectorWindow();monkeypatch.setattr(w.picker,'probe',lambda:(__import__('PySide6.QtCore',fromlist=['QPoint']).QPoint(100,100),False,False,123,False,123))
    yield w
    w.closing=True;w.cleanup();w.behavior.detach();w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()

def wait(window):
    for _ in range(200):
        if not window.busy:return
        QTest.qWait(10)
    assert not window.busy

def test_single_click_arms_double_click_opens_without_arming(window):
    window.orb.activated.emit('corrector');assert window.picker.armed and not window.isVisible()
    QTest.mouseDClick(window.orb,Qt.LeftButton)
    assert window.isVisible() and not window.picker.armed

def test_manual_correction_is_real_and_has_no_target_write(window):
    window.input.setPlainText('Les enfant mange des pomme.');window.correct_manual();wait(window)
    assert window.output.toPlainText()=='Les enfants mangent des pommes.'
    assert not window.restore_button.isEnabled()


@pytest.mark.parametrize('outcome',['success','error','cancel'])
def test_processing_hourglass_lifecycle(window,outcome):
    from PySide6.QtCore import Qt
    release=threading.Event()
    def operation(cancel):
        release.wait(2)
        if outcome=='error':raise ValueError('Erreur de test')
        return dict(original='Un texte.',text='Un texte.',changes=0,target=None,wanted=None,reason='')
    try:
        window.start_correction(operation)
        indicator=window.busy_indicator
        assert indicator.isVisible() and indicator.timer.isActive()
        assert indicator.windowFlags() & Qt.WindowDoesNotAcceptFocus
        assert indicator.windowFlags() & Qt.WindowTransparentForInput
        indicator.phase=.4;first=indicator.grab().toImage()
        indicator.phase=2.5;second=indicator.grab().toImage()
        assert first!=second
        if outcome=='cancel':
            window.cancel_correction();assert not indicator.isVisible()
    finally:release.set()
    wait(window)
    assert not indicator.isVisible() and not indicator.timer.isActive()

def test_selection_corrects_before_replacing_and_can_restore(window,monkeypatch):
    import shared.corrector_target
    from types import SimpleNamespace as NS
    target=NS(selected='Les enfant mange des pomme.');calls=[]
    class API:
        def capture(self,expected):assert expected==123;return target
        def replace(self,captured,replacement):calls.append(replacement);return 'Avant '+replacement+' Après'
        def restore(self,captured,wanted):calls.append('restore')
        def close(self):pass
    monkeypatch.setattr(shared.corrector_target,'CorrectionTarget',API)
    window.activate();window.selected_text(123);wait(window)
    assert calls==['Les enfants mangent des pommes.']
    assert window.restore_button.isEnabled() and not window.isVisible()
    window.restore_original();QTest.qWait(80);assert calls[-1]=='restore'

def test_changed_selection_shows_proposal_without_retry(window,monkeypatch):
    import shared.corrector_target
    from types import SimpleNamespace as NS
    calls=[]
    class API:
        def capture(self,expected):return NS(selected='Des pomme.')
        def replace(self,*args):calls.append('attempt');raise ValueError('La sélection a changé.')
        def close(self):pass
    monkeypatch.setattr(shared.corrector_target,'CorrectionTarget',API)
    window.activate();window.selected_text(123);wait(window)
    assert calls==['attempt'] and window.output.toPlainText()=='Des pommes.'
    assert window.isVisible() and not window.restore_button.isEnabled()


def test_changed_uia_snapshot_never_pastes(monkeypatch):
    from shared.corrector_target import CorrectionTarget,WebSelection
    target=WebSelection(123,(1,2),55,1.0,'Avant faute Après',6,11,'faute')
    changed=WebSelection(123,(1,2),55,1.0,'Avant autre Après',6,11,'autre')
    api=CorrectionTarget();monkeypatch.setattr(api,'web_capture',lambda _:changed)
    monkeypatch.setattr(api,'paste',lambda *_:pytest.fail('Changed selection must never paste'))
    with pytest.raises(ValueError,match='changé'):api.replace(target,'correction')


def test_cancel_after_capture_never_replaces(window,monkeypatch):
    import shared.corrector_target,ergoai.correction
    from types import SimpleNamespace as NS
    ready=threading.Event();release=threading.Event();writes=[]
    class API:
        def capture(self,_):return NS(selected='Des pomme.')
        def replace(self,*_):writes.append(True)
        def close(self):pass
    def slow(text,cancel,**kwargs):ready.set();release.wait(1);return dict(text='Des pommes.',changes=1)
    monkeypatch.setattr(shared.corrector_target,'CorrectionTarget',API);monkeypatch.setattr(ergoai.correction,'correct',slow)
    window.activate();window.selected_text(123);assert ready.wait(1)
    window.cancel_correction();release.set();wait(window);assert writes==[]


def test_punctuation_only_after_five_words_and_no_duplicate():
    from ergoai.correction import punctuate
    assert punctuate('un deux trois quatre cinq')=='un deux trois quatre cinq'
    assert punctuate('un deux trois quatre cinq six')=='Un deux trois quatre cinq six.'
    assert punctuate('Un deux trois quatre cinq six ?')=='Un deux trois quatre cinq six ?'
    assert punctuate('Un deux trois quatre cinq six…')=='Un deux trois quatre cinq six…'
    assert punctuate('« un deux trois quatre cinq six »')=='« un deux trois quatre cinq six. »'
    assert punctuate('  un deux trois quatre cinq six  \n\nPetit titre')=='  Un deux trois quatre cinq six.  \n\nPetit titre'


def test_clipboard_snapshot_materializes_text_and_html(monkeypatch):
    import win32clipboard as clip
    from shared.corrector_target import clipboard_snapshot
    formats={13:'Texte précédent',49152:'<p>Texte précédent</p>'.encode('utf-8')}
    monkeypatch.setattr(clip,'OpenClipboard',lambda:None);monkeypatch.setattr(clip,'CloseClipboard',lambda:None)
    monkeypatch.setattr(clip,'EnumClipboardFormats',lambda previous:next((fmt for fmt in formats if fmt>previous),0))
    monkeypatch.setattr(clip,'GetClipboardData',lambda fmt:formats[fmt])
    assert dict(clipboard_snapshot())==formats


def test_clipboard_unknown_handle_refuses_before_any_write(monkeypatch):
    import win32clipboard as clip
    from shared.corrector_target import clipboard_snapshot
    monkeypatch.setattr(clip,'OpenClipboard',lambda:None);monkeypatch.setattr(clip,'CloseClipboard',lambda:None)
    monkeypatch.setattr(clip,'EnumClipboardFormats',lambda previous:2 if previous==0 else 0)
    monkeypatch.setattr(clip,'GetClipboardData',lambda fmt:12345)
    with pytest.raises(ValueError,match='préservé'):clipboard_snapshot()


def test_clipboard_restore_never_overwrites_new_copy(monkeypatch):
    import win32clipboard as clip,shared.corrector_target as module
    monkeypatch.setattr(clip,'OpenClipboard',lambda:None);monkeypatch.setattr(clip,'CloseClipboard',lambda:None)
    monkeypatch.setattr(module,'win32clipboard_sequence',lambda:999)
    monkeypatch.setattr(clip,'EmptyClipboard',lambda:pytest.fail('New clipboard must stay intact'))
    module.restore_clipboard([(13,'Ancien texte')],123)


def test_existing_stop_after_selected_text_is_not_duplicated():
    from ergoai.correction import punctuate
    assert punctuate('un deux trois quatre cinq six',following='. Suite')=='Un deux trois quatre cinq six'
    assert punctuate('un deux trois quatre cinq six',following=' ?')=='Un deux trois quatre cinq six'


def test_spelling_and_agreement_in_reported_sentence():
    assert correct('testes pour voir si sa marchent ici la corection gramaticales')['text']=='Teste pour voir si ça marche ici la correction grammaticale.'


def test_spelling_rank_is_general_and_ties_are_not_random():
    from ergoai.correction import spelling_choice
    assert spelling_choice('corection',['correction','corrections','porrection'])=='correction'
    assert spelling_choice('gramaticales',['grammaticales','agrammaticales','grammaticale'])=='grammaticales'
    assert spelling_choice('chatx',['chats','chat']) is None
    assert spelling_choice('xyz',['bonjour']) is None


def test_final_review_does_not_silently_hide_unresolved_agreement():
    result=correct('Je suis aller au marché hier.')
    assert any(issue['text']=='aller' and 'allé' in issue['suggestions'] for issue in result['remaining'])
    assert correct('testes pour voir si sa marchent ici la corection gramaticales')['remaining']==[]


def test_remaining_issues_are_visible_in_window(window,monkeypatch):
    import ergoai.correction
    monkeypatch.setattr(ergoai.correction,'correct',lambda *args,**kwargs:dict(text='Un mot.',changes=1,remaining=[dict(start=3,end=6,text='mot',suggestions=['autre'])]))
    window.input.setPlainText('Un mot.');window.correct_manual();wait(window)
    assert window.review_label.text()=='À vérifier : mot'
    assert len(window.output.extraSelections())==1
    assert 'vérifier' in window.status.text()


def test_future_control_preserves_hypothesis_and_politeness():
    assert correct('Demain, je retournerais le chercher si j’ai le temps.')['text']=='Demain, je retournerai le chercher si j’ai le temps.'
    assert correct('Demain, je partirais si j’avais le temps.')['text']=='Demain, je partirais si j’avais le temps.'
    assert correct('Demain, je voudrais un café, si possible.')['text']=='Demain, je voudrais un café, si possible.'


def test_main_corrector_uses_neural_host_before_grammar(monkeypatch):
    import ergoai.proofreading_client,ergoai.correction
    calls=[]
    def neural(text,cancel):
        calls.append(text);return dict(text='Les enfant jouent.',model='Luth-1.7B-Instruct-Q8_0.gguf',seconds=1)
    monkeypatch.setattr(ergoai.proofreading_client,'correct',neural)
    result=ergoai.correction.correct('Les enfant joue.')
    assert calls==['Les enfants jouent.'] and result['text']=='Les enfants jouent.'


def test_neural_guard_rejects_changed_facts_and_explanations():
    from ergoai.proofreading_service import validate_output
    with pytest.raises(ValueError,match='nombres'):validate_output('Marie a 3 livres.','Marie a 4 livres.')
    with pytest.raises(ValueError,match='négation'):validate_output('Je ne veux pas venir demain.','Je veux venir demain.')
    with pytest.raises(ValueError,match='présentation'):validate_output('Un texte.','Voici le texte corrigé : Un texte.')


def test_neural_prompt_and_independent_sentence_boundary():
    from ergoai.proofreading_service import messages,EXAMPLES
    request=messages('La phrase à corriger.')
    assert len(request)==8 and request[-1]['content']=='La phrase à corriger.'
    assert all('magasin' not in source for source,_ in EXAMPLES)


def test_neural_stop_is_not_duplicated_outside_selection(monkeypatch):
    import ergoai.correction,ergoai.proofreading_client
    monkeypatch.setattr(ergoai.proofreading_client,'correct',lambda *args:dict(text='Les réunions sont terminées.',model='Luth',seconds=1))
    assert ergoai.correction.correct('Les réunion sont terminé',following='. Après')['text']=='Les réunions sont terminées'
