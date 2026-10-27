import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint,Qt
from PySide6.QtTest import QTest
from shared.jobs import background as real_background

@pytest.fixture
def lector(tmp_path,monkeypatch):
    application=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path))
    monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    import shared.speech,shared.jobs
    monkeypatch.setattr(shared.speech,'available_voices',lambda:['Femme · naturelle','Homme · naturelle'])
    from types import SimpleNamespace
    def synchronous(owner,function,done):
        done(function())
        return SimpleNamespace(signals=SimpleNamespace(error=SimpleNamespace(connect=lambda callback:None)))
    monkeypatch.setattr(shared.jobs,'background',synchronous)
    from shared.apps.text import TextApplication
    monkeypatch.setattr(TextApplication,'warm_lector_voice',lambda self:None)
    window=TextApplication('lector')
    monkeypatch.setattr(window.selection_picker,'probe',lambda:(QPoint(100,100),False,False,123,False,123))
    yield window
    window.closing=True;window.selection_picker.stop();window.selection_picker.cursor.close()
    window.lector_capture.cancel()
    window.busy_indicator.finish();window.busy_indicator.close()
    window.layout_timer.stop();window.orb.close();window.tray.hide();window.server.close();window.records.close();window.close()

def test_orb_arms_selection_then_stops(lector,monkeypatch):
    calls=[];monkeypatch.setattr(lector.speaker,'cancel',lambda:calls.append('stop'))
    lector.activate()
    assert lector.lector_active and lector.selection_picker.armed
    assert not lector.isVisible()
    lector.activate()
    assert not lector.lector_active and not lector.selection_picker.armed
    assert calls==['stop']

def test_selection_reads_only_while_armed(lector,monkeypatch):
    import shared.reading_selection
    monkeypatch.setattr(shared.reading_selection,'read_selection',lambda expected,**kwargs:'Le passage sélectionné.')
    spoken=[];monkeypatch.setattr(lector,'lector_speak',spoken.append)
    lector.read_lector_selection(123)
    assert spoken==[]
    lector.activate();lector.read_lector_selection(123)
    assert spoken==['Le passage sélectionné.']
    assert not lector.selection_picker.armed

def test_open_window_does_not_arm_selection(lector):
    from shared.apps.base import ApplicationWindow
    ApplicationWindow.activate(lector)
    assert lector.isVisible() and not lector.selection_picker.armed

def test_double_click_starts_capture_and_cancels_text_selection(lector,monkeypatch):
    prepare_capture(lector,monkeypatch)
    lector.activate();assert lector.lector_active
    QTest.mouseDClick(lector.orb,Qt.LeftButton)
    assert lector.capture_pending and not lector.isVisible() and not lector.selection_picker.armed


def test_wait_indicator_stops_on_first_speech_segment_or_cancel(lector):
    lector.busy_indicator.begin();assert lector.busy_indicator.isVisible()
    lector.speech_segment.emit('Le premier son arrive.')
    assert not lector.busy_indicator.isVisible()
    lector.busy_indicator.begin();lector.stop_lector();assert not lector.busy_indicator.isVisible()

def test_release_point_is_passed_to_document_reader(lector,monkeypatch):
    import shared.reading_selection
    captured=[]
    def read(expected,point=None):captured.append((expected,point));return 'Message sélectionné.'
    monkeypatch.setattr(shared.reading_selection,'read_selection',read)
    monkeypatch.setattr(lector,'lector_speak',lambda text:None)
    lector.activate();lector.selection_picker.release_point=(900,600)
    lector.read_lector_selection(123)
    assert captured==[(123,(900,600))]

def test_voice_options_are_named_and_saved(lector):
    assert lector.voice_name=='Femme · naturelle'
    lector.voice_choice.setCurrentText('Homme')
    assert lector.voice_name==lector.preferences['voice_name']=='Homme · naturelle'

def test_picker_requires_foreign_voluntary_selection(lector,monkeypatch):
    picker=lector.selection_picker;selected=[];picker.selected.connect(selected.append)
    picker.start();picker.timer.stop()
    for own in (True,False):
        monkeypatch.setattr(picker,'probe',lambda own=own:(QPoint(100,100),True,False,123,own,123));picker.poll()
        monkeypatch.setattr(picker,'probe',lambda:(QPoint(100,100),False,False,123,False,123));picker.poll()
        QTest.qWait(170)
        assert selected==([] if own else [123])

def test_escape_cancels_selection(lector,monkeypatch):
    lector.activate()
    monkeypatch.setattr(lector.selection_picker,'probe',lambda:(QPoint(100,100),False,True,123,False,123))
    lector.selection_picker.poll()
    assert not lector.lector_active and not lector.selection_picker.armed

def test_stop_ignores_selection_arriving_late(lector,monkeypatch):
    import shared.jobs
    from types import SimpleNamespace
    callbacks=[]
    def delayed(owner,function,done):
        callbacks.append(done)
        return SimpleNamespace(signals=SimpleNamespace(error=SimpleNamespace(connect=lambda callback:None)))
    monkeypatch.setattr(shared.jobs,'background',delayed)
    spoken=[];monkeypatch.setattr(lector,'lector_speak',spoken.append)
    lector.activate();lector.read_lector_selection(123);lector.stop_lector()
    callbacks[0]('Texte arrivé après annulation.')
    assert spoken==[]

def test_native_hit_testing_uses_physical_pixels(lector,monkeypatch):
    import win32gui,win32process
    from shared.reading_selection import SelectionPicker
    points=[]
    monkeypatch.setattr(win32gui,'GetCursorPos',lambda:(900,600))
    monkeypatch.setattr(win32gui,'WindowFromPoint',lambda point:points.append(point) or 123)
    monkeypatch.setattr(win32gui,'GetAncestor',lambda window,mode:123)
    monkeypatch.setattr(win32process,'GetWindowThreadProcessId',lambda window:(1,999999))
    monkeypatch.setattr(win32gui,'GetForegroundWindow',lambda:123)
    SelectionPicker.probe(lector.selection_picker)
    assert points==[(900,600)]

def test_paragraphs_join_wrapped_lines_without_losing_words():
    from ergoai.voice_service import phrases
    assert list(phrases('Une ligne\ncontinue.\n\nUn paragraphe.'))==['Une ligne continue.','Un paragraphe.']
    text='Bonjour tout le monde. '*100
    chunks=list(phrases(text))
    assert all(len(chunk)<=700 for chunk in chunks)
    assert ' '.join(chunks)==text.strip()

def prepare_capture(lector,monkeypatch):
    from PySide6.QtWidgets import QWidget
    from PySide6.QtCore import Signal
    import shared.apps.overlays,shared.jobs
    class FakeCapture(QWidget):
        captured=Signal(object);cancelled=Signal()
    monkeypatch.setattr(shared.apps.overlays,'CaptureOverlay',FakeCapture)
    monkeypatch.setattr(shared.jobs,'background',real_background)
    spoken=[];monkeypatch.setattr(lector,'lector_speak',spoken.append)
    return spoken

def emit_capture(lector):
    from PySide6.QtGui import QPixmap,QColor
    image=QPixmap(260,80);image.fill(QColor('white'))
    lector.lector_capture.overlay.captured.emit(image)

def wait_capture(lector):
    for _ in range(100):
        if not lector.lector_capture.busy:return
        QTest.qWait(20)
    pytest.fail('Capture worker did not finish')

def test_double_click_selects_zone_then_ocr_reads_automatically(lector,monkeypatch,tmp_path):
    import shared.reading_layout
    spoken=prepare_capture(lector,monkeypatch)
    monkeypatch.setattr(shared.reading_layout,'recognize_reading',lambda path,double_page=False:'Un passage sur deux lignes.')
    lector.hide();QTest.mouseDClick(lector.orb,Qt.LeftButton)
    assert lector.capture_pending and not lector.isVisible()
    QTest.qWait(300);emit_capture(lector);wait_capture(lector)
    assert spoken==['Un passage sur deux lignes.']
    assert lector.input.toPlainText()==spoken[0] and not lector.capture_pending
    assert not lector.isVisible() and not list(tmp_path.rglob('reading-*.png'))

def test_ocr_cancel_does_not_read_old_result(lector,monkeypatch,tmp_path):
    import shared.reading_layout,threading
    spoken=prepare_capture(lector,monkeypatch);release=threading.Event();started=threading.Event()
    def recognize(path,double_page=False):started.set();release.wait(2);return 'Résultat après annulation.'
    monkeypatch.setattr(shared.reading_layout,'recognize_reading',recognize)
    QTest.mouseDClick(lector.orb,Qt.LeftButton);QTest.qWait(300);emit_capture(lector)
    assert started.wait(1)
    lector.activate();release.set();wait_capture(lector)
    assert spoken==[] and not lector.lector_active
    assert not list(tmp_path.rglob('reading-*.png'))

def test_empty_ocr_does_not_read_and_allows_retry(lector,monkeypatch):
    import shared.reading_layout
    spoken=prepare_capture(lector,monkeypatch)
    monkeypatch.setattr(shared.reading_layout,'recognize_reading',lambda path,double_page=False:'   ')
    QTest.mouseDClick(lector.orb,Qt.LeftButton);QTest.qWait(300);emit_capture(lector);wait_capture(lector)
    assert spoken==[] and not lector.lector_active and lector.orb.state=='Attention'
    QTest.mouseDClick(lector.orb,Qt.LeftButton);assert lector.capture_pending
    lector.stop_lector()

def test_escape_capture_does_not_change_text(lector,monkeypatch):
    spoken=prepare_capture(lector,monkeypatch);lector.input.setPlainText('Conserver mon texte.')
    QTest.mouseDClick(lector.orb,Qt.LeftButton);QTest.qWait(300)
    lector.lector_capture.overlay.cancelled.emit()
    assert not lector.capture_pending and not lector.lector_capture.busy
    assert not lector.lector_active and spoken==[] and lector.input.toPlainText()=='Conserver mon texte.'

def test_cancelled_ocr_error_does_not_override_stopped_state(lector,monkeypatch):
    import shared.reading_layout,threading
    prepare_capture(lector,monkeypatch);release=threading.Event();started=threading.Event()
    def recognize(path,double_page=False):started.set();release.wait(2);raise ValueError('Erreur arrivée après annulation')
    monkeypatch.setattr(shared.reading_layout,'recognize_reading',recognize)
    QTest.mouseDClick(lector.orb,Qt.LeftButton);QTest.qWait(300);emit_capture(lector)
    assert started.wait(1)
    lector.stop_lector();release.set();wait_capture(lector)
    assert lector.orb.state=='Activée' and lector.status.text()=='Lecture arrêtée.'


def test_lector_keeps_reading_controls_without_camera(lector):
    from PySide6.QtWidgets import QPushButton
    labels={button.text() for button in lector.findChildren(QPushButton)}
    assert {'Lire','Arrêter'} <= labels
    assert not any('livre' in label.lower() or 'webcam' in label.lower() for label in labels)


def test_compact_controls_and_speed_keyboard(lector):
    from PySide6.QtWidgets import QPushButton,QLineEdit
    from PySide6.QtCore import Qt
    labels={b.text() for b in lector.findChildren(QPushButton)}
    assert not {'Plus d’options','Moins d’options','Lire une zone de l’écran','Charger la page Web'} & labels
    assert not lector.findChildren(QLineEdit)
    assert [lector.voice_choice.itemText(i) for i in range(lector.voice_choice.count())]==['Femme','Homme']
    lector.voice_choice.setCurrentText('Homme');assert lector.voice_name=='Homme · naturelle'
    before=lector.rate_slider.value();QTest.keyClick(lector.rate_slider,Qt.Key_Right)
    assert lector.speech_rate==before+1 and lector.preferences['speech_rate']==before+1
