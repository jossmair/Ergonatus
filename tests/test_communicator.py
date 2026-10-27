import pytest
from PySide6.QtWidgets import QApplication,QDialog,QLineEdit,QDialogButtonBox,QWidget
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from shared.apps.communication import validate_cards,default_cards

@pytest.fixture
def board(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.tools import ToolsApplication
    w=ToolsApplication('communicator');w.show();app.processEvents()
    yield w
    w.closing=True;w.cleanup();w.behavior.detach();w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()

def test_cards_compose_without_voice_then_optional_icon_speaks(board,monkeypatch):
    spoken=[];monkeypatch.setattr(board,'speak',spoken.append)
    QTest.mouseClick(board.card_buttons[0],Qt.LeftButton)
    assert board.sentence.toPlainText()=='Oui' and spoken==[]
    QTest.mouseClick(board.card_buttons[1],Qt.LeftButton)
    assert board.sentence.toPlainText()=='Non' and spoken==[]
    QTest.mouseClick(board.say_button,Qt.LeftButton)
    assert spoken==['Non'] and not board.say_button.icon().isNull()

def test_free_text_undo_clear_and_restore(board):
    board.sentence.setPlainText('Je préfère écrire.')
    board.clear_message();assert board.sentence.toPlainText()==''
    board.undo_message();assert board.sentence.toPlainText()=='Je préfère écrire.'
    board.select_card(dict(text='Merci'));board.undo_message()
    assert board.sentence.toPlainText()=='Je préfère écrire.'

def test_categories_favorites_are_persistent_without_speech(board,monkeypatch):
    monkeypatch.setattr(board,'speak',lambda _:pytest.fail('Unexpected speech'))
    card=board.cards[0];board.toggle_favorite(card['id'],True)
    board.category.setCurrentText('Favoris');assert board.visible_cards==[card]
    assert card['id'] in board.preferences['communication_favorites']
    board.category.setCurrentText('Besoins');assert len(board.visible_cards)==12

def test_show_large_uses_plain_text_and_returns_without_speech(board):
    board.sentence.setPlainText('<bonjour>')
    board.show_message();assert board.message_dialog.isVisible()
    from PySide6.QtWidgets import QLabel
    assert any(label.text()=='<bonjour>' and label.textFormat()==Qt.PlainText for label in board.message_dialog.findChildren(QLabel))
    board.message_dialog.accept();assert board.sentence.toPlainText()=='<bonjour>'

def test_custom_card_saved_and_legacy_cards_kept(board):
    def fill():
        dialog=QApplication.activeModalWidget();fields=dialog.findChildren(QLineEdit)
        fields[0].setText('Je veux mon carnet');fields[1].setText('📓')
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Save).click()
    QTimer.singleShot(0,fill);board.card_editor()
    board.category.setCurrentText('Mes cartes')
    assert board.visible_cards[0]['text']=='Je veux mon carnet'
    assert board.records.all('symbol')[0][1]['text']=='Je veux mon carnet'

def test_voice_is_optional_and_stop_is_explicit(board,monkeypatch):
    stopped=[];monkeypatch.setattr(board.speaker,'cancel',lambda:stopped.append(True))
    assert board.voice_name in ('Femme · naturelle','Homme · naturelle')
    board.stop_button.click();assert len(stopped)==1

@pytest.mark.parametrize('data',[None,[{'text':''}],[{'text':'x','icon':123}], [{'text':'x','category':'arbitrary'}]])
def test_import_rejects_invalid_data(data):
    with pytest.raises(ValueError):validate_cards(data)

def test_default_board_and_minimum_size_are_readable(board):
    assert len(default_cards())>=150
    board.resize(620,540);QApplication.processEvents()
    assert all(button.height()>=64 for button in board.card_buttons)
    assert all(button.accessibleName() for button in board.card_buttons)


def test_single_tap_replaces_message_and_situations_are_direct(board,monkeypatch):
    spoken=[];monkeypatch.setattr(board,'speak',spoken.append)
    board.card_buttons[0].click();board.card_buttons[1].click()
    assert board.sentence.toPlainText()=='Non' and spoken==[]
    board.situation_buttons['Repas'].click();assert board.category.currentText()=='Repas'
    assert board.sentence.height()<=96


def test_removed_emotion_sidebar_does_not_take_space_or_speak(board,monkeypatch):
    spoken=[];monkeypatch.setattr(board,'speak',spoken.append)
    board.category.setCurrentText('Ressentis');board.sentence.setPlainText('Ancien message')
    assert board.emotion_buttons==[] and spoken==[]
    assert not board.findChildren(QWidget,'QuickEmotions')
    assert board.sentence.toPlainText()=='Ancien message'


def test_each_card_has_optional_audio_without_changing_written_message(board,monkeypatch):
    spoken=[];monkeypatch.setattr(board,'speak',spoken.append)
    board.sentence.setPlainText('Mon texte personnel')
    assert len(board.card_speak_buttons)==len(board.visible_cards)
    board.card_speak_buttons[0].click()
    assert spoken==['Oui'] and board.sentence.toPlainText()=='Mon texte personnel'
    board.situation_buttons['Santé'].click();board.card_speak_buttons[0].click()
    assert spoken[-1]=='J’ai mal à la tête'
    assert all(not b.icon().isNull() and b.accessibleName().startswith('Écouter') for b in board.card_speak_buttons)


def test_audio_is_inside_card_and_school_is_second(board):
    assert board.situations.buttons()[1].text()=='École'
    for card,audio in zip(board.card_buttons,board.card_speak_buttons):
        assert card.isAncestorOf(audio)
        assert card.rect().contains(audio.mapTo(card,audio.rect().topLeft()))


def test_no_settings_or_options_in_daily_window(board):
    from PySide6.QtWidgets import QPushButton,QCheckBox
    assert not board.findChildren(QCheckBox)
    assert not {'Personnaliser','Fermer les réglages','Exporter','Importer','Afficher mes cartes'} & {b.text() for b in board.findChildren(QPushButton)}


def test_adaptive_cards_fit_without_search_or_internal_scroll(board):
    from PySide6.QtWidgets import QLineEdit
    board.resize(620,560);QApplication.processEvents()
    board.situation_buttons['Échanges'].click();QApplication.processEvents()
    assert len(board.card_buttons)==9 and not board.findChildren(QLineEdit)
    for button in board.card_buttons:
        rect=button.rect();origin=button.mapTo(board,rect.topLeft())
        assert board.rect().contains(origin) and board.rect().contains(button.mapTo(board,rect.bottomRight()))
        assert board.board_widget.rect().contains(button.mapTo(board.board_widget,rect.bottomRight()))
