from datetime import date,datetime,time,timedelta
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QDateTime
from PySide6.QtTest import QTest
from shared.domain import Records
from shared.planner import Agenda,event_time


def data(day=None,**changes):
    start=datetime.combine(day or date.today(),time(10)).timestamp()
    return dict(name='Rendez-vous',when=start,end=start+3600,**changes)


def test_legacy_is_read_without_rewriting(tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));records=Records('planinator');agenda=Agenda(records)
    original={'name':'Ancien rendez-vous','when':datetime.now().timestamp(),'done':True}
    key=records.add('event',original);event=agenda.events()[0][1]
    assert event['done'] and event['notes']=='' and event['end']==original['when']+3600
    assert records.all('event')==[(key,original)];records.close()


def test_midnight_multiday_and_soft_delete(tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));records=Records('planinator');agenda=Agenda(records)
    today=date(2026,10,19);event=data(today);event['end']=datetime.combine(today+timedelta(days=2),time.min).timestamp()
    key=agenda.save(event)
    assert len(agenda.on(today))==len(agenda.on(today+timedelta(days=1)))==1
    assert not agenda.on(today+timedelta(days=2))
    saved=agenda.events()[0][1];agenda.delete(key,saved);assert not agenda.events()
    assert records.all('event')[0][1]['deleted'];agenda.restore(key,saved);assert len(agenda.events())==1
    records.close()


def test_validation_and_details_persist(tmp_path,monkeypatch):
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));records=Records('planinator');agenda=Agenda(records)
    event=data(notes='Apporter le dossier\nTéléphone : 0102030405',place='Cabinet',category='Santé')
    for invalid in (dict(event,name=' '),dict(event,end=event['when'])):
        with pytest.raises(ValueError):agenda.save(invalid)
    key=agenda.save(event);records.close();records=Records('planinator');agenda=Agenda(records)
    restored=agenda.events()[0][1];assert restored['notes']==event['notes'] and restored['place']=='Cabinet'
    agenda.save(dict(restored,name='Modifié',done=True),key);assert agenda.events()[0][1]['done'];records.close()


def test_calendar_reuses_snapshot_and_observes_database_changes(tmp_path,monkeypatch):
    import sqlite3,json
    monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));records=Records('planinator');agenda=Agenda(records)
    calls=[];original=records.all
    monkeypatch.setattr(records,'all',lambda kind:(calls.append(kind),original(kind))[1])
    agenda.save(data());agenda.on(date.today());agenda.on(date.today()+timedelta(days=1))
    assert calls==['event']
    records.add('event',data());assert len(agenda.events())==2 and len(calls)==2
    external=sqlite3.connect(records.path);external.execute('INSERT INTO records(kind,data) VALUES (?,?)',('event',json.dumps(data())));external.commit();external.close()
    assert len(agenda.events())==3 and len(calls)==3;records.close()


@pytest.fixture
def window(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([]);monkeypatch.setenv('ERGONATUS_DATA',str(tmp_path));monkeypatch.setenv('ERGONATUS_NO_HOTKEYS','1')
    from shared.apps.planner_agenda import PlaninatorWindow
    w=PlaninatorWindow();w.show();app.processEvents();yield w
    w.cleanup();w.closing=True;w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()


def test_orb_single_double_and_right_menu(window):
    w=window;w.hide();w.orb.activated.emit('planinator');assert w.widget.isVisible() and not w.isVisible()
    w.orb.activated.emit('planinator');assert not w.widget.isVisible()
    w.orb.doubleActivated.emit('planinator');assert w.isVisible() and not w.widget.isVisible()
    w.hide();menu=w.create_orb_menu();menu.actions()[0].trigger();assert w.isVisible();menu.deleteLater()


def test_calendar_mouse_add_edit_delete_restore(window):
    from shared.apps.planner_agenda import DayColumn
    w=window;tomorrow=date.today()+timedelta(days=1);w.show_day(tomorrow);QApplication.processEvents()
    day=w.grid.itemAtPosition(0,0).widget();assert isinstance(day,DayColumn)
    QTest.mouseClick(day.add_button,Qt.LeftButton);dialog=w.dialog;assert dialog.start.date().toPython()==tomorrow
    dialog.title.setText('Réunion école');dialog.place.setText('Salle 2');dialog.notes.setPlainText('Apporter le cahier.');dialog.category.setCurrentText('École')
    QTest.mouseClick(dialog.save_button,Qt.LeftButton);QApplication.processEvents()
    key,event=w.agenda.on(tomorrow)[0];assert event['place']=='Salle 2' and event['notes']=='Apporter le cahier.'
    w.edit_event(tomorrow,key,event);w.dialog.title.setText('Équipe école');w.dialog.save();QApplication.processEvents()
    assert w.agenda.on(tomorrow)[0][1]['name']=='Équipe école'
    w.delete_event(key,w.agenda.on(tomorrow)[0][1]);assert not w.agenda.on(tomorrow)
    w.undo_button.click();assert w.agenda.on(tomorrow)[0][0]==key


def test_all_day_edit_does_not_grow(window):
    w=window;today=date.today();w.edit_event(today);d=w.dialog;d.title.setText('Journée libre');d.all_day.setChecked(True);d.save();QApplication.processEvents()
    key,event=w.agenda.on(today)[0];assert not w.agenda.on(today+timedelta(days=1)) and event_time(event)=='Toute la journée'
    w.edit_event(today,key,event);w.dialog.save();QApplication.processEvents();assert not w.agenda.on(today+timedelta(days=1))


def test_navigation_views_and_widget_transparency(window):
    w=window;w.selected=date(2026,1,31);w.set_view('Mois');w.navigate(1);assert w.selected==date(2026,2,28)
    assert w.grid.count()==42
    w.set_view('Semaine');assert w.grid.count()==7;w.navigate(1);assert w.selected==date(2026,3,7)
    w.set_view('Jour');assert w.grid.count()==1
    w.activate();QApplication.processEvents();image=w.widget.grab().toImage()
    assert image.pixelColor(0,0).alpha()==0 and 80<image.pixelColor(4,w.widget.height()//2).alpha()<250
    w.widget.opacity.setValue(55);assert w.preferences['planner_opacity']==55 and w.widget.windowOpacity()==1


def test_due_event_shows_companion_without_windows_notification(window):
    w=window;now=datetime.now().timestamp();w.agenda.save(dict(name='Maintenant',when=now-2,end=now+120))
    w.tray.showMessage=lambda *_:pytest.fail('Pas de notification Windows')
    w.clock_refresh();assert w.widget.isVisible() and 'Maintenant' in w.status.text()
    w.widget.hide();w.clock_refresh();assert not w.widget.isVisible()


def test_real_orb_double_click_opens_agenda(window):
    w=window;w.hide();QTest.mouseClick(w.orb,Qt.LeftButton);assert w.widget.isVisible()
    QTest.mouseDClick(w.orb,Qt.LeftButton);QApplication.processEvents()
    assert w.isVisible() and not w.widget.isVisible()


def test_widget_grows_shrinks_and_stays_inside_screen(window):
    w=window;w.activate();QApplication.processEvents();small=w.widget.height()
    assert small<360 and w.widget.scroll.verticalScrollBar().maximum()==0
    keys=[]
    for i in range(5):keys.append(w.agenda.save(data(notes='Informations',place='Lieu du rendez-vous')))
    w.changed();QApplication.processEvents();w.widget.fit_content();QApplication.processEvents()
    assert w.widget.height()>small
    area=w.widget.screen().availableGeometry();assert w.widget.height()<=area.height()-20
    for key,event in w.agenda.events():w.agenda.delete(key,event)
    w.changed();QApplication.processEvents();assert w.widget.height()==small
    assert w.widget.scroll.verticalScrollBar().maximum()==0


def test_menu_has_opaque_dark_background_and_opens_main(window):
    from PySide6.QtGui import QColor
    w=window;w.hide();w.activate();menu=w.create_orb_menu();menu.show();QApplication.processEvents()
    pixel=menu.grab().toImage().pixelColor(10,10)
    assert pixel.alpha()==255 and pixel.lightness()<100 and menu.windowOpacity()==1
    menu.actions()[0].trigger();assert w.isVisible() and not w.widget.isVisible();menu.close();menu.deleteLater()


def test_exact_month_weeks_and_no_hidden_last_row(window):
    from shared.planner import month_days
    w=window
    for day,weeks in ((date(2026,12,1),5),(date(2026,8,1),6),(date(2027,2,1),4)):
        w.selected=day;w.set_view('Mois');w.resize(800,610);QApplication.processEvents()
        assert w.add_event_button.height()>=w.add_event_button.fontMetrics().height()+8
        assert len(month_days(day))==weeks and w.grid.count()==7+7*weeks
        last=w.grid.itemAtPosition(weeks,6).widget()
        assert last.geometry().bottom()<=w.scroll.viewport().height()
        assert w.scroll.verticalScrollBar().maximum()==0


def test_mouse_drag_selects_range_and_opens_editor(window):
    w=window;w.selected=date(2026,12,1);w.set_view('Mois');QApplication.processEvents()
    first=w.grid.itemAtPosition(1,1).widget();last=w.grid.itemAtPosition(1,3).widget()
    start=first.rect().center();end=first.mapFromGlobal(last.mapToGlobal(last.rect().center()))
    QTest.mousePress(first,Qt.LeftButton,pos=start);QTest.mouseMove(first,end,20);QTest.mouseRelease(first,Qt.LeftButton,pos=end)
    assert w.selected_days=={date(2026,12,1),date(2026,12,2),date(2026,12,3)} and w.dialog.isVisible()
    w.dialog.title.setText('Trois jours');w.dialog.save();QApplication.processEvents()
    assert len(w.agenda.events())==3 and not w.selected_days


def test_simple_student_editor_and_automatic_colors(window):
    from shared.planner import SUBJECTS
    from shared.apps.planner_agenda import SchoolEditor
    w=window;w.student_choice.setChecked(True);w.edit_event(date.today());d=w.dialog
    assert isinstance(d,SchoolEditor) and not hasattr(d,'title') and not hasattr(d,'school_kind')
    assert d.subject.findText('Rendez-vous')>=0 and not d.subject.isEditable()
    d.subject.setCurrentText('Mathématiques');assert d.color==SUBJECTS['Mathématiques']
    d.notes.setPlainText('Réviser les fractions');d.save();QApplication.processEvents()
    key,event=w.agenda.events()[0];assert event['subject']=='Mathématiques' and event['color']==SUBJECTS['Mathématiques'] and event['notes']=='Réviser les fractions'
    w.student_choice.setChecked(False);w.edit_event(date.today(),key,event);assert isinstance(w.dialog,SchoolEditor)
    w.dialog.subject.setCurrentText('Rendez-vous');w.dialog.save();QApplication.processEvents()
    assert w.agenda.events()[0][1]['color']==SUBJECTS['Rendez-vous']


def test_note_strike_highlight_persist_and_item_actions(window):
    from shared.apps.planner_agenda import EventCard
    w=window;w.student_choice.setChecked(True);w.edit_event(date.today());d=w.dialog
    d.notes.setPlainText('Lire le chapitre trois');d.notes.selectAll()
    d.format_buttons['highlight'].click();d.format_buttons['strike'].click()
    assert d.notes.textCursor().charFormat().fontStrikeOut()
    d.save();QApplication.processEvents();key,event=w.agenda.events()[0]
    assert event['notes_html'] and event['notes']=='Lire le chapitre trois'
    w.edit_event(date.today(),key,event);d=w.dialog;d.notes.selectAll();style=d.notes.textCursor().charFormat()
    assert style.fontStrikeOut() and style.background().color().name()=='#f1d477'
    d.format_buttons['highlight'].click();assert d.notes.textCursor().charFormat().background().style()==Qt.NoBrush
    d.save();QApplication.processEvents()
    w.format_event(key,w.agenda.events()[0][1],'strike');assert w.agenda.events()[0][1]['done']
    w.format_event(key,w.agenda.events()[0][1],'highlight');assert w.agenda.events()[0][1]['highlight']


def test_editors_stay_above_companion_and_other_windows(window):
    native=pytest.importorskip('win32gui');w=window;w.hide();w.activate()
    for student in (False,True):
        w.student_choice.setChecked(student);w.edit_event(date.today());QApplication.processEvents()
        dialog=w.dialog;assert dialog.windowFlags() & Qt.WindowStaysOnTopHint
        assert native.GetWindowLong(int(dialog.winId()),-20) & 8  # WS_EX_TOPMOST
        dialog.reject();QApplication.processEvents()


def test_subject_popup_light_rows_and_selection(window):
    w=window;w.student_choice.setChecked(True);w.edit_event(date.today());d=w.dialog
    d.subject.showPopup();QTest.qWait(150);QApplication.processEvents();view=d.subject.view();image=view.viewport().grab().toImage()
    row=view.visualRect(view.model().index(0,0));assert row.height()>=34
    assert image.pixelColor(6,row.center().y()).lightness()>180
    index=view.model().index(1,0);rect=view.visualRect(index)
    QTest.mouseMove(view.viewport(),rect.center());QTest.mouseClick(view.viewport(),Qt.LeftButton,pos=rect.center());QTest.qWait(50);QApplication.processEvents()
    assert d.subject.currentText()=='Mathématiques' and d.isVisible()

