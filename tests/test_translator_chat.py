import threading,time
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from shared.translation import matches_voice,translate


@pytest.fixture
def chat(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.translator_chat import TraductorWindow
    w=TraductorWindow();w.show();app.processEvents()
    yield w
    w.cleanup();w.closing=True;w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()


def wait(chat):
    for _ in range(500):
        QApplication.processEvents();time.sleep(.01)
        if not chat.job_id and not chat.pending:return
    assert not chat.pending


def test_sms_send_and_two_actions_per_bubble(chat,monkeypatch):
    import shared.translation
    calls=[]
    def translation(text,source,target,*args):calls.append((text,source,target));return 'Hello!'
    monkeypatch.setattr(shared.translation,'translate',translation)
    QTest.keyClicks(chat.input,'Bonjour !');QTest.keyClick(chat.input,Qt.Key_Return);wait(chat)
    assert calls==[('Bonjour !','fr','en')]
    assert [bubble.text for bubble in chat.bubbles]==['Bonjour !','Hello!']
    assert all(b.copy_button.isEnabled() and b.listen_button.isEnabled() for b in chat.bubbles)
    QTest.mouseClick(chat.bubbles[1].copy_button,Qt.LeftButton)
    assert QApplication.clipboard().text()=='Hello!'
    assert not chat.input.toPlainText()


def test_language_snapshot_for_translation_and_playback(chat,monkeypatch):
    import shared.translation
    monkeypatch.setattr(shared.translation,'translate',lambda *args:'Hola')
    chat.destination.setCurrentIndex(chat.destination.findData('es'));chat.input.setPlainText('Bonjour');chat.send_message();wait(chat)
    bubble=chat.bubbles[-1];chat.destination.setCurrentIndex(chat.destination.findData('de'))
    spoken=[]
    monkeypatch.setattr(shared.translation,'speak_language',lambda speaker,text,language:spoken.append((text,language)) or True)
    QTest.mouseClick(bubble.listen_button,Qt.LeftButton);wait(chat)
    assert spoken==[('Hola','es')]
    assert chat.preferences['target_language']=='de'


def test_swap_and_shift_enter(chat):
    QTest.mouseClick(chat.swap,Qt.LeftButton)
    assert chat.source.currentData()=='en' and chat.destination.currentData()=='fr'
    QTest.keyClicks(chat.input,'One');QTest.keyClick(chat.input,Qt.Key_Return,Qt.ShiftModifier);QTest.keyClicks(chat.input,'Two')
    assert chat.input.toPlainText()=='One\nTwo' and not chat.bubbles


def test_cancellation_ignores_late_answer_and_keeps_next_draft(chat,monkeypatch):
    import shared.translation
    release=threading.Event()
    def slow(*args):release.wait(2);return 'Stale answer'
    monkeypatch.setattr(shared.translation,'translate',slow)
    chat.input.setPlainText('Bonjour');chat.send_message();chat.input.setPlainText('Prochain message');chat.cancel_translation();release.set();wait(chat)
    assert chat.input.toPlainText()=='Prochain message' and chat.bubbles[-1].pending
    assert chat.bubbles[-1].text=='Traduction annulée.'


def test_errors_are_visible_without_copying_placeholder(chat,monkeypatch):
    import shared.translation
    def failure(*args):raise ValueError('Moteur indisponible')
    monkeypatch.setattr(shared.translation,'translate',failure);chat.input.setPlainText('Bonjour');chat.send_message();wait(chat)
    assert chat.bubbles[-1].pending and not chat.bubbles[-1].copy_button.isEnabled()
    assert chat.status.text()=='Moteur indisponible'


def test_voice_language_matching_rejects_wrong_language():
    assert matches_voice('409;809','en') and matches_voice('40c','fr')
    assert matches_voice('c0a','es') and matches_voice('422','uk')
    assert not matches_voice('40c','en') and not matches_voice('invalid','fr')


def test_translation_routes_explicit_source_and_target(monkeypatch):
    import ergoai.translation_client
    calls=[]
    monkeypatch.setattr(ergoai.translation_client,'translate',lambda text,source,target,cancel:calls.append((text,source,target)) or dict(text='Hello'))
    result=translate('Bonjour','fr','en','test',threading.Event(),{})
    assert result=='Hello' and calls==[('Bonjour','fr','en')]
    assert translate('Identique','fr','fr','test',threading.Event(),{})=='Identique'


def test_cancelled_request_never_calls_engine(monkeypatch):
    import ergoai.translation_client
    stop=threading.Event();stop.set()
    monkeypatch.setattr(ergoai.translation_client,'translate',lambda *args,**kwargs:pytest.fail('Cancelled request reached engine'))
    with pytest.raises(ValueError,match='annulée'):translate('Bonjour','fr','en','cancelled',stop,{})


def test_translation_worker_closes_stream_on_cancel():
    from ergoai.translation_service import Translator
    stop=threading.Event();closed=[]
    class Stream:
        def __iter__(self):
            yield {'choices':[{'delta':{'content':'First'}}]}
            stop.set()
            yield {'choices':[{'delta':{'content':'Late'}}]}
        def close(self):closed.append(True)
    class Engine:
        def __init__(self):self.stop=threading.Event();self.llm=self
        def create_chat_completion(self,**kwargs):return Stream()
    host=Translator();host.engine=Engine()
    with pytest.raises(ValueError,match='annulée'):host.translate('Bonjour','fr','en',stop)
    assert closed==[True]


def test_translation_worker_rejects_truncated_output():
    from ergoai.translation_service import Translator
    class Engine:
        def __init__(self):self.stop=threading.Event();self.llm=self
        def create_chat_completion(self,**kwargs):return iter([{'choices':[{'delta':{'content':'Hello'},'finish_reason':'length'}]}])
    host=Translator();host.engine=Engine()
    with pytest.raises(ValueError,match='incomplète'):host.translate('Bonjour','fr','en',threading.Event())


def test_source_left_and_translation_right(chat,monkeypatch):
    import shared.translation
    monkeypatch.setattr(shared.translation,'translate',lambda *args:'Hello')
    chat.input.setPlainText('Bonjour');chat.send_message();wait(chat)
    source,reply=chat.bubbles
    assert source.mapTo(chat,source.rect().topLeft()).x()<reply.mapTo(chat,reply.rect().topLeft()).x()


def test_all_languages_route_to_bundled_speech(monkeypatch):
    from shared.translation import LANGUAGES,speak_language
    from ergoai.translation_voices import VOICES
    import shared.translation_speech
    calls=[]
    monkeypatch.setattr(shared.translation_speech,'speak',lambda speaker,text,language:calls.append(language) or True)
    assert set(VOICES)==set(LANGUAGES)
    for language in LANGUAGES:assert speak_language(object(),'message',language)
    assert calls==list(LANGUAGES)


def test_bundled_voice_hashes_and_language_configs():
    import hashlib,json
    from shared.catalog import suite_root
    from ergoai.translation_voices import VOICES
    for language,(filename,expected) in VOICES.items():
        path=suite_root()/'ergoai/voices'/filename
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
        config=json.loads(path.with_suffix('.onnx.json').read_text(encoding='utf-8'))
        assert config['language']['code'].split('_')[0]==language
        assert config.get('phoneme_type','espeak')=='espeak'


def test_stopped_voice_does_not_start_playback():
    from shared.translation_speech import speak
    from shared.speech import Speaker
    speaker=Speaker();speaker.cancel()
    assert speak(speaker,'Bonjour','fr') is False and speaker.audio is None
