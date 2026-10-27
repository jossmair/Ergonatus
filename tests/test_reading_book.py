import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QColor
from PySide6.QtTest import QTest
from shared.reading_layout import reconstruct

@pytest.fixture(scope='session')
def app():return QApplication.instance() or QApplication([])

def line(text,x,y,width=220):return dict(words=[dict(text=text,x=x,y=y,width=width,height=18)])

def test_hidden_layout_preserves_paragraphs():
    data=dict(lines=[line('Une ligne qui continue',10,10),line('sur la suivante.',10,32),line('Un autre paragraphe.',10,80)])
    assert reconstruct(data)=='Une ligne qui continue sur la suivante.\n\nUn autre paragraphe.'

def test_columns_are_read_left_then_right():
    data=dict(lines=[line('Gauche première ligne',10,10),line('Droite première ligne',380,10),line('Gauche suivante.',10,32),line('Droite suivante.',380,32)])
    assert reconstruct(data)=='Gauche première ligne Gauche suivante.\n\nDroite première ligne Droite suivante.'

def test_line_end_hyphen_is_joined_without_inventing_words():
    assert reconstruct(dict(lines=[line('Une amélio-',10,10),line('ration utile.',10,32)]))=='Une amélioration utile.'

def test_double_page_is_cropped_and_read_in_order(tmp_path,monkeypatch):
    import shared.ocr
    from shared.reading_layout import recognize_reading
    image=QImage(400,200,QImage.Format_RGB32);image.fill(QColor('white'));path=tmp_path/'photo.png';assert image.save(str(path))
    files=[]
    def recognize(part):
        files.append(part)
        assert QImage(str(part)).width()==200
        return dict(lines=[line('Gauche.' if 'page-0' in str(part) else 'Droite.',10,10)])
    monkeypatch.setattr(shared.ocr,'recognize_data',recognize)
    assert recognize_reading(path,True)=='Gauche.\n\nDroite.'
    assert len(files)==2 and all(not part.exists() for part in files)

def test_calm_pace_and_paragraph_silence():
    from ergoai.voice_service import length_scale,reading_segments
    assert 1.30<length_scale(-1)<1.38 and length_scale(-5)>length_scale(0)
    assert list(reading_segments('Premier.\n\nSecond.'))==[('Premier.',0),('Second.',.8)]
    assert all(pause==0 for _,pause in reading_segments('Une phrase. '*100))

def test_hourglass_small_moving_and_nonblocking(app):
    from shared.ui.reading_busy import ReadingBusy
    from PySide6.QtCore import Qt
    widget=ReadingBusy();widget.begin();QTest.qWait(90)
    assert widget.width()<=140 and widget.height()<=150 and widget.timer.isActive()
    assert widget.windowFlags() & Qt.WindowTransparentForInput
    widget.phase=0;first=widget.grab().toImage();widget.phase=2.5;second=widget.grab().toImage()
    assert first!=second
    widget.finish();assert not widget.isVisible() and not widget.timer.isActive()
    widget.begin(False);assert not widget.timer.isActive();widget.close()

