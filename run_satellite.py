import argparse
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QTimer,Qt
from PySide6.QtNetwork import QLocalSocket
from shared.ui.theme import APP_THEMES
from shared.apps.base import instance_name

TEXT_APPS={'corrector','traductor','lector','ecrinator','scanator'}
NEW_APPS=set(APP_THEMES)-{'ergonatus','claviernator','precisionator','transcrinator','redactor'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app',choices=sorted(NEW_APPS))
    parser.add_argument('--quit-running',action='store_true')
    parser.add_argument('--smoke-test',action='store_true')
    parser.add_argument('--snapshot',type=Path)
    parser.add_argument('--minimized',action='store_true')
    args=parser.parse_args()
    app_id=args.app or Path(sys.executable).stem.lower()
    if app_id not in NEW_APPS:parser.error('Précisez --app pour le lancement depuis Python.')
    app=QApplication(sys.argv[:1]);app.setApplicationName(APP_THEMES[app_id]['name']);app.setQuitOnLastWindowClosed(False)
    from shared.design_bootstrap import install
    install(app)
    socket=QLocalSocket();socket.connectToServer(instance_name(app_id))
    if socket.waitForConnected(200):
        import json
        socket.write((json.dumps({'version':1,'command':'quit' if args.quit_running else 'show'})+'\n').encode());socket.waitForBytesWritten(500);socket.disconnectFromServer();return 0
    if args.quit_running:return 0
    try:
        if app_id in ('dictionnator','explicator','tablinator'):
            from shared.apps.learning import DictionaryWindow,ExplainWindow,TablesWindow
            window={'dictionnator':DictionaryWindow,'explicator':ExplainWindow,'tablinator':TablesWindow}[app_id]()
        elif app_id=='applinator':
            from shared.apps.app_launcher import ApplinatorWindow
            window=ApplinatorWindow()
        elif app_id=='organisator':
            from shared.apps.organizer_workspace import OrganisatorWindow
            from shared.domain import app_data
            desktop=app_data('organisator')/'smoke-desktop' if args.smoke_test else None
            if desktop is not None:desktop.mkdir(exist_ok=True)
            window=OrganisatorWindow(desktop=desktop)
        elif app_id=='planinator':
            from shared.apps.planner_agenda import PlaninatorWindow
            window=PlaninatorWindow()
        elif app_id=='temporator':
            from shared.apps.timer_widget import TemporatorWindow
            window=TemporatorWindow()
        elif app_id=='traductor':
            from shared.apps.translator_chat import TraductorWindow
            window=TraductorWindow()
        elif app_id=='memorinator':
            from shared.apps.sticky_wall import MemorinatorWindow
            window=MemorinatorWindow()
        elif app_id=='corrector':
            from shared.apps.corrector import CorrectorWindow
            window=CorrectorWindow()
        elif app_id in TEXT_APPS:
            from shared.apps.text import TextApplication
            window=TextApplication(app_id)
        else:
            from shared.apps.tools import ToolsApplication
            window=ToolsApplication(app_id)
    except Exception as error:
        if args.smoke_test:raise
        QMessageBox.critical(None,APP_THEMES[app_id]['name'],str(error));return 1
    if not args.minimized:window.show()
    if args.snapshot:
        def snapshot():args.snapshot.parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(args.snapshot))
        QTimer.singleShot(600,snapshot)
    if args.smoke_test and app_id=='applinator':
        def check_launcher():
            if window.preferences.get('launcher_catalog_version',0)<2:
                QTimer.singleShot(100,check_launcher);return
            try:
                assert window.catalog and len(window.shortcuts)<=1
                candidate=next((window.list.item(i) for i in range(window.list.count()) if window.list.item(i).data(Qt.UserRole)['name']!='Ergonatus'),None)
                if candidate is not None:
                    candidate.setCheckState(Qt.Checked);assert len(window.shortcuts)==2
                window.activate();assert window.overlay.isVisible()
                window.activate();assert not window.overlay.isVisible()
                window.open_settings();assert window.isVisible()
                window.cleanup();app.exit(0)
            except Exception as error:
                print(error,file=sys.stderr);app.exit(1)
        QTimer.singleShot(800,check_launcher);QTimer.singleShot(25000,lambda:app.exit(2))
    elif args.smoke_test and app_id=='organisator':
        from shared.organizer import INBOX
        window.profile.setCurrentText('Collège');window.name.setText('Espace de validation');window.create();step=[0]
        def verify_organizer():
            try:
                if window.busy:QTimer.singleShot(80,verify_organizer);return
                if step[0]==0:
                    assert window.root and (window.root/'Mathématiques/Cours').is_dir()
                    (window.root/INBOX/'exercice maths.txt').write_text('Fractions : exercices de mathématiques.',encoding='utf-8')
                    (window.root/INBOX/'document inconnu.txt').write_text('Document sans indication de sujet.',encoding='utf-8')
                    step[0]=1;window.scan()
                elif step[0]==1:
                    assert len(window.proposals)==2 and any(p.destination.startswith('Mathématiques') for p in window.proposals)
                    window.sort_selected();step[0]=2
                elif step[0]==2:
                    assert (window.root/'Mathématiques/Exercices/exercice maths.txt').read_text(encoding='utf-8').startswith('Fractions')
                    assert (window.root/INBOX/'document inconnu.txt').is_file()
                    window.undo();step[0]=3
                else:
                    assert (window.root/INBOX/'exercice maths.txt').is_file()
                    assert not window.auto.isChecked();window.cleanup();app.exit(0);return
                QTimer.singleShot(100,verify_organizer)
            except Exception:
                import traceback;traceback.print_exc();app.exit(1)
        QTimer.singleShot(500,verify_organizer);QTimer.singleShot(30000,lambda:app.exit(2))
    elif args.smoke_test and app_id=='planinator':
        def verify_agenda():
            try:
                from datetime import date,timedelta
                day=date.today()+timedelta(days=1)
                window.edit_event(day);assert window.dialog.windowFlags() & Qt.WindowStaysOnTopHint;window.dialog.title.setText('Validation agenda');window.dialog.place.setText('Salle 2');window.dialog.notes.setPlainText('Informations conservées localement.');window.dialog.save()
                QApplication.processEvents();key,event=window.agenda.on(day)[0]
                assert event['name']=='Validation agenda' and event['place']=='Salle 2'
                window.delete_event(key,event);assert not window.agenda.on(day)
                window.undo_delete();assert len(window.agenda.on(day))==1
                from shared.planner import month_days
                for mode,count in [('Mois',7+7*len(month_days(window.selected))),('Semaine',7),('Jour',1)]:
                    window.set_view(mode);assert window.grid.count()==count
                window.hide();window.orb.activated.emit('planinator');assert window.widget.isVisible()
                assert window.widget.grab().toImage().pixelColor(0,0).alpha()==0
                window.orb.activated.emit('planinator');assert not window.widget.isVisible()
                from PySide6.QtTest import QTest
                QTest.mouseDClick(window.orb,Qt.LeftButton);QApplication.processEvents()
                assert window.isVisible() and not window.widget.isVisible()
                assert window.widget.height()<window.widget.screen().availableGeometry().height()
                window.student_choice.setChecked(True);window.selected=date(2026,12,1);window.set_view('Mois');QApplication.processEvents()
                first=window.grid.itemAtPosition(2,1).widget();last=window.grid.itemAtPosition(2,3).widget();end=first.mapFromGlobal(last.mapToGlobal(last.rect().center()))
                QTest.mousePress(first,Qt.LeftButton,pos=first.rect().center());QTest.mouseMove(first,end,20);QTest.mouseRelease(first,Qt.LeftButton,pos=end)
                days=[date(2026,12,i) for i in (8,9,10)];assert window.selected_days==set(days) and window.dialog.isVisible()
                assert window.dialog.windowFlags() & Qt.WindowStaysOnTopHint
                window.dialog.subject.showPopup();QApplication.processEvents();assert window.dialog.subject.view().viewport().grab().toImage().pixelColor(6,8).lightness()>180;window.dialog.subject.hidePopup()
                window.dialog.subject.setCurrentText('Mathématiques');window.dialog.notes.setPlainText('Réviser les fractions');window.dialog.notes.selectAll();window.dialog.format_buttons['highlight'].click();window.dialog.save();QApplication.processEvents()
                assert all(any(e['subject']=='Mathématiques' and e['color']=='#85B7E9' and e['notes_html'] for k,e in window.agenda.on(day)) for day in days)
                window.selected=date(2026,12,1);window.set_view('Mois');QApplication.processEvents()
                assert window.grid.count()==42 and window.scroll.verticalScrollBar().maximum()==0
                window.cleanup();app.exit(0)
            except Exception:
                import traceback;traceback.print_exc();app.exit(1)
        QTimer.singleShot(700,verify_agenda);QTimer.singleShot(15000,lambda:app.exit(2))
    elif args.smoke_test and app_id=='temporator':
        def verify_timer():
            try:
                window.preset(65);window.start_button.click()
                assert window.widget.isVisible() and window.model.state=='running' and window.mode=='dial'
                window.widget.play.click();assert window.model.state=='paused'
                window.widget.play.click();assert window.model.state=='running'
                window.widget.reset.click();assert window.model.state=='ready'
                assert window.widget.grab().toImage().pixelColor(0,0).alpha()==0
                window.tray.showMessage=lambda *args:None;QApplication.beep=lambda:None
                window.start_timer();window.model.deadline=window.model.clock()-1;window.tick()
                assert window.blink_timer.isActive() and window.widget.face.flash_on
                window.blink();assert not window.widget.face.flash_on
                window.widget.reset.click();assert not window.blink_timer.isActive()
                window.visual_choice.click();assert window.visual and window.widget.grab().toImage().pixelColor(0,0).alpha()==0
                window.size_slider.setValue(180);assert window.widget.width()==180
                window.activate();assert not window.widget.isVisible()
                window.activate();assert window.widget.isVisible()
                window.cleanup();app.exit(0)
            except Exception:app.exit(1)
        QTimer.singleShot(700,verify_timer);QTimer.singleShot(10000,lambda:app.exit(2))
    elif args.smoke_test and app_id=='traductor':
        window.source.setCurrentIndex(window.source.findData('en'));window.destination.setCurrentIndex(window.destination.findData('fr'))
        window.input.setPlainText('I would like a glass of water, please.');window.send_message()
        def verify_translation():
            if window.job_id:QTimer.singleShot(100,verify_translation);return
            try:
                bubble=window.bubbles[-1];text=bubble.text.casefold()
                assert not bubble.pending and bubble.language=='fr' and 'eau' in text and 'vin' not in text and 'verre' in text
                bubble.copy_button.click();assert app.clipboard().text()==bubble.text
                assert all(b.listen_button.isEnabled() and b.copy_button.isEnabled() for b in window.bubbles)
                window.cleanup();app.exit(0)
            except Exception:app.exit(1)
        QTimer.singleShot(1200,verify_translation);QTimer.singleShot(90000,lambda:app.exit(2))
    elif args.smoke_test and app_id=='corrector':
        window.input.setPlainText("Hier, je suis aller au magasin avec mes amis. On a acheter plusieurs chose mais les prix était trop chère. Ensuite, nous somme rentrer chez nous parce qu'il commencer à pleuvoir. J'ai oublier mon sac dans la voiture et personne ne la retrouver. Demain, je retournerais le chercher si j'ai le temp.");window.correct_manual()
        def verify_correction():
            if window.busy:QTimer.singleShot(100,verify_correction);return
            text=window.output.toPlainText().replace('’',"'")
            success=all(fragment in text for fragment in ('je suis allé','a acheté plusieurs choses','les prix étaient trop chers','nous sommes rentrés',"il commençait à pleuvoir","J'ai oublié mon sac","personne ne l'a retrouvé","je retournerai le chercher si j'ai le temps"))
            window.cleanup();app.exit(0 if success else 1)
        QTimer.singleShot(1200,verify_correction)
        QTimer.singleShot(90000,lambda:app.exit(2))
    elif args.smoke_test and app_id=='memorinator':
        def verify_wall():
            try:
                note=window.add_note();note.editor.setPlainText('Mon message important.');note.editor.selectAll();window.select_note(note);window.format_selection('highlight');window.format_selection('strike')
                cursor=note.editor.textCursor();cursor.setPosition(5)
                assert cursor.charFormat().fontStrikeOut() and cursor.charFormat().background().style()!=Qt.NoBrush
                key=note.key;window.trash_note(note);assert key not in window.notes;window.restore_last();assert window.notes[key].editor.toPlainText()=='Mon message important.'
                window.opacity_slider.setValue(55)
                assert window.isFullScreen() and window.backdrop.opacity==55 and window.windowOpacity()==1
                assert window.notes[key].grab().toImage().pixelColor(50,80).alpha()==255
                window.cleanup();app.exit(0)
            except Exception:app.exit(1)
        QTimer.singleShot(700,verify_wall);QTimer.singleShot(15000,lambda:app.exit(2))
    elif args.smoke_test and app_id=='calculinator':
        window.student_toggle.setChecked(True);window.toggle_student_mode()
        cases=iter([('(x+1)²','calculate','x² + 2x + 1'),('1/2+1/3','calculate','5/6'),('sin(30)','calculate','1/2'),('(x²-1)/(x-1)','calculate','x + 1')])
        expected=['']
        fraction_checked=[False]
        def next_calculation():
            if window.math_busy:QTimer.singleShot(50,next_calculation);return
            if expected[0] and window.result.text()!=expected[0]:app.exit(1);return
            try:source,action,result=next(cases)
            except StopIteration:
                if fraction_checked[0]:app.exit(0);return
                fraction_checked[0]=True;expected[0]='1/2'
                window.student_keys['a/b'].click();window.keys['1'].click();window.select_fraction_field(window.fraction_fields[1]);window.keys['2'].click();window.keys['='].click()
                QTimer.singleShot(100,next_calculation);return
            expected[0]=result;window.expression.setText(source);window.compute_student(action);QTimer.singleShot(100,next_calculation)
        QTimer.singleShot(600,next_calculation);QTimer.singleShot(30000,lambda:app.exit(2))
    elif args.smoke_test:QTimer.singleShot(1200,window.quit)
    return app.exec()

if __name__=='__main__':raise SystemExit(main())
