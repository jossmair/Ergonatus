from test_communicator import board
from PySide6.QtWidgets import QApplication

def test_emergency_responses_remain_available_in_every_context(board,monkeypatch):
    speech=[];monkeypatch.setattr(board,'speak',speech.append)
    board.category.setCurrentText('Autonomie');board.compose_button.setChecked(True)
    board.sentence.setPlainText('Un autre message')
    board.quick_buttons['Stop'].click()
    assert board.sentence.toPlainText()=='Stop' and not speech

def test_assembly_is_explicit_and_never_speaks_on_selection(board,monkeypatch):
    speech=[];monkeypatch.setattr(board,'speak',speech.append)
    board.select_card(dict(text='Je veux boire'))
    board.compose_button.setChecked(True);board.select_card(dict(text='De l’eau, s’il vous plaît'))
    assert board.sentence.toPlainText()=='Je veux boire. De l’eau, s’il vous plaît' and not speech
    board.compose_button.setChecked(False);board.select_card(dict(text='Merci'))
    assert board.sentence.toPlainText()=='Merci'

def test_practical_communication_includes_agency_and_clarification(board):
    texts={c['text'] for c in board.cards}
    assert {'Ne parlez pas à ma place','Je ne veux pas être touché','Laissez-moi le temps de répondre','Une question à la fois, s’il vous plaît'}<=texts
    for name in ('Choisir','Autonomie','Questions'):assert name in board.situation_buttons
