from PySide6.QtWidgets import QApplication,QTextEdit
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import QTimer
import sys,json
from pathlib import Path
app=QApplication([]);editor=QTextEdit();editor.setPlainText('Avant Les réunion sont terminé. Après');editor.resize(520,160);editor.setWindowTitle('Corrector · fixture éditable isolée');editor.show();editor.activateWindow();editor.setFocus()
cursor=editor.textCursor();cursor.setPosition(6);cursor.setPosition(30,QTextCursor.KeepAnchor);editor.setTextCursor(cursor)
QTimer.singleShot(150,lambda:Path(sys.argv[1]).write_text(json.dumps(dict(root=int(editor.winId()),pid=__import__('os').getpid()))))
QTimer.singleShot(60000,app.quit);app.exec()
