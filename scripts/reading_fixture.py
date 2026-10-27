"""Disposable read-only rich document with a real native accessibility selection."""
from pathlib import Path
import json,sys,os
from PySide6.QtWidgets import QApplication,QTextEdit
from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
app=QApplication([])
document=QTextEdit();document.setWindowTitle('Lector QA · document riche')
document.setHtml('<h1>Lecture de document</h1><p>Avant <b>Ce passage sélectionné doit être lu.</b> Après</p>')
document.setReadOnly(True);document.resize(600,240);document.show();document.activateWindow();document.setFocus()
cursor=document.textCursor();start=document.toPlainText().index('Ce passage');cursor.setPosition(start);cursor.setPosition(start+len('Ce passage sélectionné doit être lu.'),QTextCursor.KeepAnchor);document.setTextCursor(cursor)
Path(sys.argv[1]).write_text(json.dumps(dict(root=int(document.winId()),pid=os.getpid())))
QTimer.singleShot(30000,app.quit);app.exec()
