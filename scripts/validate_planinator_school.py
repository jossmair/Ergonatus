"""Capture the compact month and student editor with isolated synthetic data."""
import os,sys,uuid
from pathlib import Path
from datetime import date
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
os.environ['ERGONATUS_DATA']=str(root/'.qa'/('planner-school-'+uuid.uuid4().hex))
os.environ['ERGONATUS_NO_HOTKEYS']='1';os.environ['USERDOMAIN']='QA-'+uuid.uuid4().hex
from PySide6.QtWidgets import QApplication
from shared.apps.planner_agenda import PlaninatorWindow
app=QApplication([]);w=PlaninatorWindow();w.selected=date(2026,12,1);w.set_view('Mois');w.resize(800,610);w.show();app.processEvents()
w.grab().save(str(root/'docs/validation/planinator-december-fit.png'))
w.student_choice.setChecked(True);w.edit_event(date(2026,12,1));d=w.dialog
d.subject.setCurrentText('Mathématiques')
d.notes.setPlainText('Exercices 3 et 4 page 42.\nApporter le cahier et la calculatrice.');d.notes.selectAll();d.format_buttons['highlight'].click();cursor=d.notes.textCursor();cursor.clearSelection();d.notes.setTextCursor(cursor);app.processEvents()
d.grab().save(str(root/'docs/validation/planinator-school-editor.png'));d.save();app.processEvents()
w.grab().save(str(root/'docs/validation/planinator-school-month.png'))
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
a=w.grid.itemAtPosition(2,1).widget();b=w.grid.itemAtPosition(2,3).widget();end=a.mapFromGlobal(b.mapToGlobal(b.rect().center()))
QTest.mousePress(a,Qt.LeftButton,pos=a.rect().center());QTest.mouseMove(a,end,20);QTest.mouseRelease(a,Qt.LeftButton,pos=end);app.processEvents()
w.grab().save(str(root/'docs/validation/planinator-selected-days.png'))
if w.dialog:w.dialog.reject();app.processEvents()
w.show_day(date(2026,12,1));app.processEvents();w.grab().save(str(root/'docs/validation/planinator-simple-day.png'))
w.cleanup();w.closing=True;w.layout_timer.stop();w.orb.close();w.tray.hide();w.server.close();w.records.close();w.close();app.processEvents()
