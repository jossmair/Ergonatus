from datetime import date,timedelta
import pytest
from PySide6.QtCore import Qt,QThreadPool
from PySide6.QtWidgets import QApplication,QPushButton,QLabel
from PySide6.QtTest import QTest

@pytest.fixture(scope='module')
def app():
    app=QApplication.instance() or QApplication([])
    from suite_design import install
    install(app);return app

@pytest.fixture
def make(app,tmp_path,monkeypatch):
    monkeypatch.setenv('USERDOMAIN','RequestedUI');monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_TEST_MODE','1');monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1');windows=[]
    def create(factory):
        w=factory();windows.append(w);w.show();QTest.qWait(100);return w
    yield create
    for w in windows:
        w.closing=True
        if hasattr(w,'cleanup'):w.cleanup()
        QThreadPool.globalInstance().waitForDone(10000)
        if hasattr(w,'layout_timer'):w.layout_timer.stop()
        w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close()
    app.processEvents()

def test_sms_direction_history_and_copy_are_inside_response(make,app):
    from shared.apps.corrector import CorrectorWindow
    w=make(CorrectorWindow);w.chat.begin('Un message envoyé.');w.output.setPlainText('Une réponse corrigée.');QTest.qWait(80)
    copy=w.chat.current.parentWidget().findChild(QPushButton,'MessageCopy');assert copy is not None
    QTest.mouseClick(copy,Qt.LeftButton);assert app.clipboard().text()=='Une réponse corrigée.'
    w.chat.begin('Un autre message.');w.output.setPlainText('Une autre réponse.');QTest.qWait(80)
    assert len(w.chat.findChildren(QPushButton,'MessageCopy'))==2
    QTest.mouseClick(copy,Qt.LeftButton);assert app.clipboard().text()=='Une réponse corrigée.'
    rows=[w.chat.flow.itemAt(i).widget() for i in range(w.chat.flow.count()) if w.chat.flow.itemAt(i).widget() is not w.chat.thinking]
    assert rows[0].layout().itemAt(0).widget() is not None and rows[1].layout().itemAt(0).spacerItem() is not None

def test_open_corrector_disarms_external_picker_and_text_remains_selectable(make,monkeypatch):
    from shared.apps.corrector import CorrectorWindow
    w=make(CorrectorWindow);w.picker.poll=lambda:None;w.activate();assert w.active
    w.open_main_window();assert not w.active and not w.picker.armed
    w.input.setPlainText('Texte à sélectionner');w.input.setFocus();QTest.keyClick(w.input,Qt.Key_A,Qt.ControlModifier);assert w.input.textCursor().hasSelection()
    w.output.setPlainText('Réponse à sélectionner');w.output.setFocus();QTest.keyClick(w.output,Qt.Key_A,Qt.ControlModifier);assert w.output.textCursor().hasSelection()

def test_timer_double_click_opens_settings_from_face_and_orb(make):
    from shared.apps.timer_widget import TemporatorWindow
    w=make(TemporatorWindow);w.hide();w.show_widget();QTest.mouseDClick(w.widget.face,Qt.LeftButton);QTest.qWait(60);assert w.isVisible()
    w.hide();QTest.mouseDClick(w.orb,Qt.LeftButton);QTest.qWait(60);assert w.isVisible()
    assert w.widget.face.cursor().shape()==Qt.ArrowCursor

def test_dictionary_search_and_local_completion(make):
    from shared.apps.learning import DictionaryWindow
    from shared.dictionary import complete
    w=make(DictionaryWindow);assert w.search_button.text()=='Trouver' and w.search_button.height()==w.word.height()
    assert not any('Un mot. Tous ses sens.' in l.text() for l in w.findChildren(QLabel))
    assert complete('math') and all(word.casefold().startswith('math') for word in complete('math'))

def test_current_week_and_today_are_distinct(make):
    from shared.apps.planner_agenda import PlaninatorWindow,DayColumn
    w=make(PlaninatorWindow);today=DayColumn(w,date.today());other=DayColumn(w,date.today()-timedelta(days=date.today().weekday()+7));assert today.current_week and not other.current_week
    assert '#FFE8B5' in today.styleSheet() and today.day_button.property('suitePrimary')

def test_translation_processing_keeps_hourglass_until_cancel(make,app):
    from shared.apps.translator_chat import TraductorWindow
    w=make(TraductorWindow);w.job_id='test-pending';app._suite_interactions.poll();QTest.qWait(380);app._suite_interactions.poll();assert app._suite_interactions.hourglass.isVisible()
    w.job_id=None;app._suite_interactions.poll();assert not app._suite_interactions.hourglass.isVisible()

def test_help_has_speech_control_and_no_native_messagebox(make,app,monkeypatch):
    from shared.apps.base import ApplicationWindow
    w=make(lambda:ApplicationWindow('temporator'));app._suite_interactions.show_help(w,'temporator');dialog=w._suite_help_dialog;seen=[]
    monkeypatch.setattr(dialog.speaker,'speak',lambda text,**kwargs:seen.append(text));QTest.mouseClick(dialog.read_button,Qt.LeftButton);QTest.qWait(80)
    assert seen and 'minuteur' in seen[0] and dialog.isVisible();dialog.close()

def test_hub_launch_restores_saved_orb_visibility(make,monkeypatch,tmp_path):
    from shared.domain import Records
    for key in ['dictionnator','explicator','tablinator']:
        records=Records(key);records.add('settings',{'orb_hidden':True});records.close()
    monkeypatch.setenv('ERGONATUS_SHARED_AI','1')
    from shared.apps.learning import DictionaryWindow,ExplainWindow,TablesWindow
    for factory in [DictionaryWindow,ExplainWindow,TablesWindow]:
        w=make(factory);assert not w.preferences.get('orb_hidden') and w.orb.isVisible()
