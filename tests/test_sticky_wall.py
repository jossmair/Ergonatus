import pytest
from PySide6.QtCore import Qt,QPoint
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest


@pytest.fixture
def wall(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.sticky_wall import MemorinatorWindow
    w=MemorinatorWindow();w.show();app.processEvents()
    yield w
    w.cleanup();w.closing=True;w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()


def test_orb_translucent_fullscreen_and_escape(wall):
    assert wall.isFullScreen()
    wall.orb.activated.emit('memorinator');assert not wall.isVisible()
    wall.orb.activated.emit('memorinator');assert wall.isVisible() and wall.isFullScreen()
    assert wall.testAttribute(Qt.WA_TranslucentBackground) and wall.windowOpacity()==1
    QTest.keyClick(wall,Qt.Key_Escape);assert not wall.isVisible()


def test_plus_colours_dates_and_old_interface_removed(wall):
    for _ in range(12):QTest.mouseClick(wall.add_button,Qt.LeftButton)
    assert len(wall.notes)==12
    assert len({n.data['colour'] for n in wall.notes.values()})==12
    rectangles=[n.geometry() for n in wall.notes.values()]
    assert all(not first.intersects(last) for i,first in enumerate(rectangles) for last in rectangles[i+1:])
    assert all(n.date_text() and n.delete_button.icon().isNull() is False for n in wall.notes.values())
    assert not hasattr(wall,'question') and not hasattr(wall,'grade')


def test_grows_with_text_and_canvas_follows(wall):
    note=wall.add_note();QApplication.processEvents();before=note.height()
    note.editor.setPlainText('\n'.join('Une longue idée à conserver.' for _ in range(45)))
    QTest.qWait(100);QApplication.processEvents()
    assert note.height()>before*2 and note.editor.verticalScrollBarPolicy()==Qt.ScrollBarAlwaysOff
    assert wall.canvas.height()>note.y()+note.height()


def test_drag_header_and_persist_positions(wall):
    note=wall.add_note();QApplication.processEvents();start=note.pos()
    QTest.mousePress(note.drag_bar,Qt.LeftButton,pos=QPoint(40,14))
    QTest.mouseMove(note.drag_bar,QPoint(160,90),delay=30)
    QTest.mouseRelease(note.drag_bar,Qt.LeftButton,pos=QPoint(160,90))
    assert note.pos()!=start
    stored=dict(wall.records.all('sticky_note'))[note.key]
    assert (stored['x'],stored['y'])==(note.x(),note.y())


def test_highlight_and_strike_selection_only_and_toggle(wall):
    note=wall.add_note();note.editor.setPlainText('Un message important.');wall.select_note(note)
    cursor=note.editor.textCursor();cursor.setPosition(3);cursor.setPosition(10,QTextCursor.KeepAnchor);note.editor.setTextCursor(cursor)
    QTest.mouseClick(wall.highlight_button,Qt.LeftButton);QTest.mouseClick(wall.strike_button,Qt.LeftButton)
    cursor=QTextCursor(note.editor.document());cursor.setPosition(5);assert cursor.charFormat().fontStrikeOut() and cursor.charFormat().background().color().name()=='#fff36a'
    cursor.setPosition(1);assert not cursor.charFormat().fontStrikeOut() and cursor.charFormat().background().style()==Qt.NoBrush
    QTest.mouseClick(wall.highlight_button,Qt.LeftButton);QTest.mouseClick(wall.strike_button,Qt.LeftButton)
    cursor.setPosition(5);assert not cursor.charFormat().fontStrikeOut() and cursor.charFormat().background().style()==Qt.NoBrush
    assert note.editor.toPlainText()=='Un message important.'


def test_trash_and_undo_do_not_lose_content(wall):
    note=wall.add_note();note.editor.setPlainText('À retrouver');key=note.key
    QTest.mouseClick(note.delete_button,Qt.LeftButton)
    assert key not in wall.notes and dict(wall.records.all('sticky_note'))[key]['trashed']
    QTest.mouseClick(wall.undo_button,Qt.LeftButton)
    assert wall.notes[key].editor.toPlainText()=='À retrouver'
    assert not dict(wall.records.all('sticky_note'))[key]['trashed']


def test_flush_on_hide_and_html_roundtrip(wall):
    note=wall.add_note();note.editor.setPlainText('Mémo enregistré');note.editor.selectAll();wall.select_note(note);wall.format_selection('strike');wall.hide()
    from shared.apps.sticky_wall import StickyNote
    stored=dict(wall.records.all('sticky_note'))[note.key]
    restored=StickyNote(wall,999,stored)
    assert restored.editor.toPlainText()=='Mémo enregistré'
    cursor=restored.editor.textCursor();cursor.setPosition(4);assert cursor.charFormat().fontStrikeOut()
    restored.save_timer.stop();restored.deleteLater()


def test_keyboard_movement_and_selection_toolbar(wall):
    note=wall.add_note();before=note.x();note.drag_bar.setFocus();QTest.keyClick(note.drag_bar,Qt.Key_Right)
    assert note.x()==before+16
    assert not wall.highlight_button.isEnabled()
    note.editor.setPlainText('À surligner');note.editor.selectAll()
    assert wall.highlight_button.isEnabled() and wall.strike_button.isEnabled()


def test_legacy_cards_are_archived_without_old_ui(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.domain import Records
    store=Records('memorinator');store.add('card',dict(question='Ancienne question',answer='À préserver'));store.close()
    from shared.apps.sticky_wall import MemorinatorWindow
    w=MemorinatorWindow()
    try:
        assert (tmp_path/'memorinator/archive-revisions-v1.sqlite3').is_file()
        assert not w.notes and w.records.all('card')[0][1]['answer']=='À préserver'
    finally:
        w.cleanup();w.closing=True;w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()


def test_restart_preserves_notes_format_position_date_and_trash(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.sticky_wall import MemorinatorWindow
    def close(w):
        w.cleanup();w.closing=True;w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()
    first=MemorinatorWindow();note=first.add_note();note.editor.setPlainText('Mon souvenir');note.move(125,180);note.editor.selectAll();first.select_note(note);first.format_selection('highlight');key=note.key;created=note.data['created'];colour=note.data['colour']
    removed=first.add_note();removed.editor.setPlainText('Dans la corbeille');removed_key=removed.key;first.trash_note(removed);close(first)
    second=MemorinatorWindow()
    try:
        restored=second.notes[key];assert restored.editor.toPlainText()=='Mon souvenir'
        assert restored.pos()==QPoint(125,180) and restored.data['created']==created and restored.data['colour']==colour
        cursor=restored.editor.textCursor();cursor.setPosition(3);assert cursor.charFormat().background().color().name()=='#fff36a'
        assert removed_key not in second.notes;second.restore_note(removed_key);assert second.notes[removed_key].editor.toPlainText()=='Dans la corbeille'
    finally:close(second)


def test_opacity_changes_only_background_and_is_saved(wall):
    from shared.apps.sticky_wall import DimBackdrop
    backdrop=DimBackdrop(25);backdrop.resize(100,100)
    faint=backdrop.grab().toImage().pixelColor(40,40).alpha()
    backdrop.opacity=100;opaque=backdrop.grab().toImage().pixelColor(40,40).alpha()
    assert faint<opaque and opaque==255
    note=wall.add_note();QApplication.processEvents()
    wall.opacity_slider.setValue(35)
    assert wall.preferences['wall_opacity']==35 and wall.backdrop.opacity==35 and wall.windowOpacity()==1
    assert note.grab().toImage().pixelColor(50,80).alpha()==255
    point=wall.scroll.mapTo(wall,QPoint(wall.scroll.width()-25,wall.scroll.height()-25))
    assert wall.grab().toImage().pixelColor(point).alpha()<150
    backdrop.close()
