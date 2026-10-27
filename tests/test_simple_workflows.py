from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import pytest
from shared.ui.components import ErgoOptions

@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or QApplication([])


def test_secondary_options_open_from_keyboard(app):
    options=ErgoOptions();options.show();app.processEvents()
    assert not options.body.isVisible()
    options.toggle.setFocus();QTest.keyClick(options.toggle,Qt.Key_Space)
    assert options.body.isVisible()
    QTest.keyClick(options.toggle,Qt.Key_Space)
    assert not options.body.isVisible()
    options.close()


def dispose(window):
    window.closing=True;window.layout_timer.stop();window.orb.close()
    window.tray.hide();window.server.close();window.records.close();window.close()


def test_translation_language_survives_reopening(app,tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.text import TextApplication
    first=TextApplication('traductor')
    first.language.setCurrentText('Español');dispose(first)
    second=TextApplication('traductor')
    assert second.language.currentText()=='Español'
    assert not second.options.body.isVisible()
    assert second.input.toPlainText()==''
    dispose(second)


def test_lector_voice_and_rate_survive_reopening(app,tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    import shared.speech,shared.jobs
    monkeypatch.setattr(shared.speech,'available_voices',lambda:['Voix A','Voix B'])
    monkeypatch.setattr(shared.jobs,'background',lambda owner,function,done:done(function()))
    from shared.apps.text import TextApplication
    monkeypatch.setattr(TextApplication,'warm_lector_voice',lambda self:None)
    first=TextApplication('lector');first.voice_choice.setCurrentText('Homme')
    first.rate_slider.setValue(3);dispose(first)
    second=TextApplication('lector')
    assert second.voice_choice.currentText()=='Homme'
    assert second.voice_name=='Homme · naturelle'
    assert second.speech_rate==3
    dispose(second)
