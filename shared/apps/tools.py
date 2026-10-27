from pathlib import Path
import datetime as dt
import time
from fractions import Fraction
from PySide6.QtCore import Qt,QTimer,QDateTime,QRectF
from PySide6.QtGui import QPixmap,QImage
from PySide6.QtWidgets import (QLabel,QLineEdit,QPlainTextEdit,QComboBox,QSpinBox,QListWidget,
    QDateTimeEdit,QFileDialog,QMessageBox,QProgressBar,QInputDialog,QScrollArea,QWidget,QVBoxLayout,QGridLayout,QStackedWidget,QSizePolicy,QSlider,QFrame,QHBoxLayout)
from shared.apps.base import ApplicationWindow
from shared.domain import calculate,FOLDER_TEMPLATES,folder_plan,create_folders,atomic_text

from shared.apps.communication import CommunicationMixin

class ToolsApplication(CommunicationMixin,ApplicationWindow):
    def __init__(self,app_id):
        super().__init__(app_id)
        {'calculinator':self.calculator,'organisator':self.organizer,'temporator':self.timer_panel,
         'planinator':self.planner,'communicator':self.communicator,
         'concentrator':self.focus,
         'pdfinator':self.pdf}[app_id]()

    def calculator(self):
        from shared.ui.components import ErgoButton,ErgoCard,ErgoOptions
        from shared.ui.math_display import MathInput,MathResult,FractionField
        self.setMinimumSize(380,650);self.resize(420,650);self.calculated=False
        self.layout.setContentsMargins(16,10,16,10);self.content.setSpacing(6)
        self.setStyleSheet(self.styleSheet()+'''
            QPushButton#CalculatorKey {background:#20313E;border:1px solid #2A414F;border-radius:11px;padding:0px;font-size:19pt;font-weight:500;}
            QPushButton#CalculatorOperator {background:#233D4F;border:1px solid #34566A;border-radius:11px;padding:0px;font-size:20pt;}
            QPushButton#CalculatorKey:hover, QPushButton#CalculatorOperator:hover {background:#2D4C60;border-color:#7FB8D5;}
            QPushButton#CalculatorKey:pressed, QPushButton#CalculatorOperator:pressed {background:#38627B;}
            QPushButton#CalculatorKey:focus, QPushButton#CalculatorOperator:focus {border:2px solid #91D3EA;}
            QPushButton#CalculatorEquals {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #417C9D,stop:1 #2D5C78);border:1px solid #76AFCB;border-radius:11px;padding:0px;font-size:25pt;font-weight:500;}
            QPushButton#CalculatorEquals:hover {background:#4A87A7;}
            QPushButton#CalculatorEquals:pressed {background:#2D5C78;}
            QPushButton#CalculatorEquals:focus {border:2px solid #C3E7F7;}
        ''')
        display=ErgoCard();display.setObjectName('CalculatorScreen');display.setStyleSheet('QFrame#CalculatorScreen {background:#EDF4FA;border:1px solid #A5BFD0;border-radius:18px;}');display_layout=QVBoxLayout(display);display_layout.setContentsMargins(16,12,16,12);display_layout.setSpacing(6);self.content.addWidget(display)
        self.expression=MathInput();self.expression.setObjectName('CalculatorDisplay');self.expression.setPlaceholderText('0');self.expression.setAlignment(Qt.AlignRight);self.expression.setAccessibleName('Calcul');display_layout.addWidget(self.expression)
        self.expression.returnPressed.connect(self.compute);self.expression.textEdited.connect(lambda _:setattr(self,'calculated',False))
        self.expression.setMinimumHeight(48);self.expression.setStyleSheet("QLineEdit#CalculatorDisplay {background:transparent;border:none;font-size:22pt;padding:3px;font-family:'Times New Roman';font-style:italic;}")
        self.result=MathResult('0');self.result.setMinimumHeight(48);self.result.setObjectName('CalculatorResult');self.result.setAlignment(Qt.AlignRight);self.result.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.TextSelectableByKeyboard);self.result.setAccessibleName('Résultat exact');display_layout.addWidget(self.result)
        self.fraction_active=False;self.fraction_stack=[]
        self.fraction_editor=QWidget();fraction_layout=QVBoxLayout(self.fraction_editor);fraction_layout.setContentsMargins(0,0,0,0);fraction_layout.setSpacing(2)
        fraction_row=QHBoxLayout();fraction_layout.addLayout(fraction_row);fraction_row.addStretch()
        fraction_body=QWidget();fraction_body.setMinimumWidth(180);fraction_body.setMaximumWidth(280);fraction_body_layout=QVBoxLayout(fraction_body);fraction_body_layout.setContentsMargins(6,0,6,0);fraction_body_layout.setSpacing(2);fraction_row.addWidget(fraction_body,1);fraction_row.addStretch()
        self.fraction_fields=[]
        for name in ('Numérateur','Dénominateur'):
            field=FractionField();field.setPlaceholderText(name);field.setAccessibleName(name);field.setAlignment(Qt.AlignCenter);field.setFixedHeight(28)
            field.returnPressed.connect(self.compute)
            field.activated.connect(lambda field=field:self.select_fraction_field(field));fraction_body_layout.addWidget(field);self.fraction_fields.append(field)
            if name=='Numérateur':
                line=QFrame();line.setFrameShape(QFrame.HLine);line.setFixedHeight(2);line.setStyleSheet('background:#B5DDED;');fraction_body_layout.addWidget(line)
        fraction_buttons=QHBoxLayout();fraction_layout.addLayout(fraction_buttons)
        fraction_buttons.addStretch();self.fraction_next=ErgoButton('↓ En bas');self.fraction_next.setAccessibleName('Passer au dénominateur');self.fraction_next.clicked.connect(self.next_fraction_field);self.fraction_next.setFixedHeight(26);fraction_buttons.addWidget(self.fraction_next)
        self.fraction_confirm=ErgoButton('✓ Insérer');self.fraction_confirm.clicked.connect(self.commit_fraction);fraction_buttons.addWidget(self.fraction_confirm)
        self.fraction_cancel=ErgoButton('×');self.fraction_cancel.setAccessibleName('Annuler la fraction');self.fraction_cancel.setToolTip('Annuler la fraction');self.fraction_cancel.setFixedWidth(30);self.fraction_cancel.clicked.connect(self.cancel_fraction);fraction_buttons.addWidget(self.fraction_cancel);fraction_buttons.addStretch()
        self.fraction_editor.setStyleSheet("QWidget {background:transparent;} QLineEdit {min-height:0px;padding:2px 6px;font-family:'Times New Roman';font-style:italic;font-size:14pt;} QPushButton {min-height:0px;padding:2px 8px;font-size:10pt;background:#294B5D;border:1px solid #557C91;border-radius:6px;} QPushButton:focus {border:2px solid #91D3EA;}")
        self.fraction_confirm.setFixedHeight(26);self.fraction_cancel.setFixedHeight(26);display_layout.addWidget(self.fraction_editor);self.fraction_editor.hide()
        self.calculator_views=QStackedWidget();self.calculator_views.setMinimumHeight(304);self.content.addWidget(self.calculator_views,1)
        key_page=QWidget();key_row=QHBoxLayout(key_page);key_row.setContentsMargins(0,0,0,0);key_row.setSpacing(10)
        self.keypad=QWidget();self.keypad.setMinimumHeight(304);grid=QGridLayout(self.keypad);grid.setContentsMargins(0,0,0,0);grid.setSpacing(8);key_row.addWidget(self.keypad,2);self.calculator_views.addWidget(key_page);self.keys={}
        rows=[['C','⌫','(',')'],['7','8','9','÷'],['4','5','6','×'],['1','2','3','−'],['0',',','±','+']]
        names={'C':'Tout effacer','⌫':'Effacer le dernier caractère','÷':'Diviser','×':'Multiplier','−':'Soustraire','+':'Additionner','±':'Changer le signe',',':'Virgule décimale','(':'Ouvrir une parenthèse',')':'Fermer la parenthèse'}
        for row,labels in enumerate(rows):
            grid.setRowMinimumHeight(row,44)
            for column,label in enumerate(labels):
                button=ErgoButton(label);button.setObjectName('CalculatorKey' if label.isdigit() or label==',' else 'CalculatorOperator');button.setAccessibleName(names.get(label,label));button.setMinimumHeight(44)
                button.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
                button.clicked.connect(lambda checked=False,key=label:self.calculator_key(key));grid.addWidget(button,row,column);self.keys[label]=button
        equals=ErgoButton('=');equals.setObjectName('CalculatorEquals');equals.setAccessibleName('Calculer le résultat');equals.clicked.connect(self.compute);grid.addWidget(equals,5,0,1,4);self.keys['=']=equals
        equals.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        grid.setRowMinimumHeight(5,44)
        self.student_panel=ErgoCard();self.student_panel.setStyleSheet('QPushButton {min-height:0px;padding:3px 5px;font-size:11pt;background:#223846;border:1px solid #304C5C;border-radius:10px;} QPushButton:hover {background:#304F63;border-color:#7FB8D5;} QPushButton:pressed {background:#38627B;} QPushButton:focus {border:2px solid #91D3EA;}')
        student=QVBoxLayout(self.student_panel);student.setContentsMargins(8,8,8,8);student.setSpacing(6)
        student.addWidget(QLabel('Outils élève'))
        student_grid=QGridLayout();student_grid.setSpacing(6);student.addLayout(student_grid);self.student_keys={}
        for index,(label,insert) in enumerate([('x','x'),('x²','x²'),('y','y'),('y²','y²'),('√','√'),('π','π'),('sin','sin'),('cos','cos'),('tan','tan'),('a/b','fraction')]):
            button=ErgoButton(label);button.setMinimumHeight(34);button.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);button.setAccessibleName({'√':'Racine carrée','a/b':'Insérer une fraction'}.get(label,label))
            if label in ('x','x²','y','y²'):button.setStyleSheet("font-family:'Times New Roman';font-style:italic;font-size:16pt;")
            button.clicked.connect(lambda checked=False,token=insert:self.student_insert(token));student_grid.addWidget(button,index//3,index%3,1,3 if index==9 else 1);self.student_keys[label]=button
        for row in range(4):student_grid.setRowMinimumHeight(row,34)
        key_row.addWidget(self.student_panel,1);self.student_panel.hide();self.math_busy=False
        toolbar=QFrame();toolbar.setObjectName('CalculatorToolbar');toolbar.setStyleSheet('QFrame#CalculatorToolbar {background:rgba(19,32,42,235);border:1px solid #304956;border-radius:13px;} QPushButton {min-height:0px;padding:5px 12px;border:1px solid transparent;border-radius:8px;background:transparent;color:#D9E8F0;font-size:10pt;} QPushButton:hover {background:#273F50;} QPushButton:checked {background:#2D566D;color:#F1FAFF;border-color:#5C91AD;} QPushButton:pressed {background:#38627B;} QPushButton:focus {border:2px solid #91D3EA;}')
        controls=QHBoxLayout(toolbar);controls.setContentsMargins(6,6,6,6);controls.setSpacing(6);self.content.addWidget(toolbar)
        self.calculator_copy_button=ErgoButton('Copier');self.calculator_copy_button.setAccessibleName('Copier le résultat');self.calculator_copy_button.clicked.connect(lambda:__import__('PySide6.QtWidgets',fromlist=['QApplication']).QApplication.clipboard().setText(self.result.text()));controls.addWidget(self.calculator_copy_button,1)
        self.history=QListWidget();self.history.setAccessibleName('Historique des calculs');self.calculator_views.addWidget(self.history)
        self.student_toggle=ErgoButton('Élève');self.student_toggle.setAccessibleName('Mode Élève');self.student_toggle.clicked.connect(self.toggle_student_mode);controls.addWidget(self.student_toggle,1);self.student_toggle.setCheckable(True)
        self.history_toggle=ErgoButton('Historique');self.history_toggle.clicked.connect(self.toggle_calculator_history);controls.addWidget(self.history_toggle,1);self.history_toggle.setCheckable(True)
        for button in (self.calculator_copy_button,self.student_toggle,self.history_toggle):
            button.setFixedHeight(40);button.setStyleSheet('QPushButton {background:#E6F0F6;color:#234A65;border:1px solid #ABC2D1;border-radius:11px;font-size:10pt;font-weight:600;padding:4px 8px;} QPushButton:hover {background:#D1E5F1;} QPushButton:checked {background:#C1DCEB;border:1px solid #487DA1;}')
        self.student_toggle.setChecked(bool(self.preferences.get('student_mode',False)));self.toggle_student_mode()
        for _,item in self.records.all('calculation'):self.history.addItem(item['expression']+' = '+item['result'])
        self.history.itemActivated.connect(lambda item:(self.expression.setText(item.text().split(' = ')[0]),setattr(self,'calculated',False)))
        self.status.setText('Cliquez sur les chiffres ou utilisez le clavier.')
        self.expression.setFocus()

    def toggle_student_mode(self):
        enabled=self.student_toggle.isChecked();self.student_panel.setVisible(enabled);self.remember('student_mode',enabled)
        self.student_toggle.setText('✓ Élève' if enabled else 'Élève')
        if not enabled:
            while self.fraction_active:self.cancel_fraction()
        self.setMinimumWidth(620 if enabled else 380);self.resize(650 if enabled else 420,self.height())
        self.expression.setPlaceholderText('Ex. : (x + 1)² ou 1/2 + 1/3' if enabled else '0')

    def student_insert(self,token):
        if token=='fraction':
            self.begin_fraction();return
        selected=self.calculator_entry().selectedText()
        if token in ('√','sin','cos','tan'):
            self.insert_student_text(token+'('+selected+')',inside=not bool(selected))
        else:self.insert_student_text(token)

    def insert_student_text(self,text,inside=False):
        entry=self.calculator_entry()
        if self.calculated and not self.fraction_active:entry.clear()
        entry.insert(text)
        if inside:entry.setCursorPosition(entry.cursorPosition()-1)
        self.calculated=False;entry.setFocus()

    def calculator_entry(self):return self.fraction_target if self.fraction_active else self.expression

    def select_fraction_field(self,field):
        self.fraction_target=field
        for item in self.fraction_fields:
            active=item is field
            item.setStyleSheet('QLineEdit {border:2px solid '+('#91D3EA' if active else '#3B5665')+';border-radius:6px;background:'+('#294B5D' if active else '#1D303C')+';}')
        bottom=field is self.fraction_fields[1]
        self.fraction_next.setText('↑ En haut' if bottom else '↓ En bas');self.fraction_next.setAccessibleName('Passer au numérateur' if bottom else 'Passer au dénominateur')

    def next_fraction_field(self):
        field=self.fraction_fields[0 if self.fraction_target is self.fraction_fields[1] else 1]
        self.select_fraction_field(field);field.setFocus()

    def begin_fraction(self):
        entry=self.calculator_entry()
        if self.fraction_active:
            if len(self.fraction_stack)>=3:self.status.setText('Terminez cette fraction avant d’en ajouter une autre.');return
            self.fraction_stack.append(dict(values=[f.text() for f in self.fraction_fields],target=self.fraction_fields.index(entry),cursor=entry.cursorPosition(),start=entry.selectionStart(),length=len(entry.selectedText())))
        elif self.calculated:entry.clear();self.calculated=False
        selected=entry.selectedText();self.fraction_active=True
        self.expression.hide();self.result.hide();self.fraction_editor.show()
        self.fraction_fields[0].setText(selected);self.fraction_fields[1].clear();self.select_fraction_field(self.fraction_fields[0]);self.fraction_fields[0].setFocus()
        self.status.setText('Fraction : touchez une case, puis les touches. = termine le calcul.')

    def restore_fraction_parent(self,state):
        for field,value in zip(self.fraction_fields,state['values']):field.setText(value)
        entry=self.fraction_fields[state['target']];self.select_fraction_field(entry)
        if state['start']>=0:entry.setSelection(state['start'],state['length'])
        else:entry.setCursorPosition(state['cursor'])
        return entry

    def commit_fraction(self):
        if not self.fraction_active:return True
        for field in self.fraction_fields:
            if not field.text().strip():
                self.select_fraction_field(field);field.setFocus();self.status.setText('Complétez le '+field.accessibleName().lower()+' avec les touches.');return False
        value='('+self.fraction_fields[0].text()+')/('+self.fraction_fields[1].text()+')'
        if self.fraction_stack:self.restore_fraction_parent(self.fraction_stack.pop()).insert(value)
        else:
            self.fraction_active=False;self.fraction_editor.hide();self.expression.show();self.result.show();self.expression.insert(value);self.expression.clearFocus()
        self.calculated=False;self.status.setText('Fraction insérée. Continuez le calcul ou appuyez sur =.');return True

    def cancel_fraction(self):
        if self.fraction_stack:self.restore_fraction_parent(self.fraction_stack.pop())
        else:self.fraction_active=False;self.fraction_editor.hide();self.expression.show();self.result.show()
        self.status.setText('Fraction annulée.')

    def compute_student(self,action='calculate'):
        if self.math_busy:return
        from shared.jobs import background
        from shared.student_math import solve
        expression=self.expression.text()
        self.math_busy=True;self.keys['='].setEnabled(False)
        self.status.setText('Calcul en cours…')
        def done(answer):
            if self.closing:return
            if self.expression.text()!=expression:
                self.status.setText('Expression modifiée : relancez le calcul.');return
            result=answer['text'];self.result.setText(result);self.result.setToolTip(result);self.result.setStyleSheet('font-size:18pt;' if len(result)>18 else '')
            self.calculated=True;self.records.add('calculation',dict(expression=expression,result=result,action=action,degrees=True));self.history.addItem(expression+' = '+result)
            label='Résultat exact.'
            self.status.setText(label+(' Conditions : '+answer['conditions'] if answer['conditions'] else ''));self.state('Action réussie')
        job=background(self,lambda:solve(expression,action),done)
        def finished():
            self.math_busy=False;self.keys['='].setEnabled(True)
        job.signals.finished.connect(finished)

    def toggle_calculator_history(self):
        history=self.history_toggle.isChecked();self.calculator_views.setCurrentIndex(1 if history else 0)
        self.history_toggle.setText('Clavier' if history else 'Historique')
        self.history_toggle.setAccessibleName('Revenir au clavier' if history else 'Historique')
        if history:self.history.setFocus()
        else:self.expression.setFocus()

    def keyPressEvent(self,event):
        if self.app_id=='calculinator':
            key=event.text()
            if key and key in '0123456789,+-*/().':
                self.calculator_key({'-':'−','*':'×','/':'÷','.':','}.get(key,key));event.accept();return
            if event.key() in (Qt.Key_Return,Qt.Key_Enter,Qt.Key_Equal):self.compute();event.accept();return
            if event.key()==Qt.Key_Backspace:self.calculator_key('⌫');event.accept();return
            if event.key()==Qt.Key_Escape:self.calculator_key('C');event.accept();return
        super().keyPressEvent(event)

    def calculator_key(self,key):
        if self.fraction_active:
            entry=self.calculator_entry()
            if key=='C':entry.clear()
            elif key=='⌫':entry.backspace()
            elif key=='±':entry.setText('-('+(entry.text() or '0')+')')
            else:entry.insert(key)
            return
        if key=='C':self.expression.clear();self.result.setText('0');self.calculated=False;self.status.setText('Nouveau calcul.');return
        if key=='⌫':self.expression.backspace();self.calculated=False;return
        if key=='±':
            text=self.expression.text() or '0';self.expression.setText(text[2:-1] if text.startswith('-(') and text.endswith(')') else '-('+text+')');self.calculated=False;return
        if self.calculated:
            self.expression.setText(self.result.text() if key in ('+','−','×','÷') else '')
        self.expression.insert(key);self.calculated=False

    def compute(self):
        while self.fraction_active:
            if not self.commit_fraction():return
        if self.student_toggle.isChecked():self.compute_student();return
        try:
            value=calculate(self.expression.text());result=str(value.numerator) if value.denominator==1 else str(value.numerator)+' / '+str(value.denominator)
            self.result.setText(result);self.result.setToolTip(result);self.calculated=True;self.records.add('calculation',dict(expression=self.expression.text(),result=result));self.history.addItem(self.expression.text()+' = '+result);self.status.setText('Résultat exact.');self.state('Action réussie')
        except ZeroDivisionError:self.error('Impossible de diviser par zéro.')
        except (ValueError,SyntaxError,OverflowError):self.error('Vérifiez le calcul et les parenthèses.')

    def organizer(self):
        self.root_folder=QLineEdit();self.root_folder.setReadOnly(True);self.root_folder.setPlaceholderText('Dossier à organiser');self.content.addWidget(self.root_folder)
        self.button('Choisir un dossier',self.choose_folder)
        self.template=QComboBox();self.template.addItems(FOLDER_TEMPLATES);self.content.addWidget(self.template)
        self.folder_preview=QPlainTextEdit();self.folder_preview.setReadOnly(True);self.content.addWidget(self.folder_preview,1)
        self.button('Prévisualiser les dossiers à créer',self.preview_folders);self.button('Créer après confirmation',self.make_folders)
    def choose_folder(self):
        path=QFileDialog.getExistingDirectory(self,'Choisir le dossier parent')
        if path:self.root_folder.setText(path);self.preview_folders()
    def preview_folders(self):
        try:self.folder_preview.setPlainText('\n'.join(str(p) for p in folder_plan(self.root_folder.text(),self.template.currentText())) or 'Tous les dossiers existent déjà.')
        except ValueError as error:self.error(str(error))
    def make_folders(self):
        try:
            plan=folder_plan(self.root_folder.text(),self.template.currentText())
            if not plan:self.status.setText('Aucun dossier à créer.');return
            if QMessageBox.question(self,'Valider la création','Créer uniquement ces dossiers, sans déplacer aucun document ?\n\n'+'\n'.join(p.name for p in plan))!=QMessageBox.Yes:return
            created=create_folders(self.root_folder.text(),self.template.currentText());self.status.setText(f'{len(created)} dossiers créés. Aucun fichier déplacé.');self.preview_folders()
        except (ValueError,OSError) as error:self.error(str(error))

    def timer_panel(self):
        row=self.row();row.addWidget(QLabel('Travail (minutes)'));self.work_minutes=QSpinBox();self.work_minutes.setRange(1,240);self.work_minutes.setValue(25);row.addWidget(self.work_minutes)
        row.addWidget(QLabel('Pause (minutes)'));self.break_minutes=QSpinBox();self.break_minutes.setRange(1,120);self.break_minutes.setValue(5);row.addWidget(self.break_minutes)
        self.countdown=QLabel('Prêt');self.countdown.setAlignment(Qt.AlignCenter);self.countdown.setStyleSheet('font-size:54pt');self.content.addWidget(self.countdown,1)
        self.progress=QProgressBar();self.progress.setRange(0,1000);self.content.addWidget(self.progress)
        self.timer=QTimer(self);self.timer.setInterval(200);self.timer.timeout.connect(self.timer_tick);self.deadline=None;self.remaining=None;self.phase='Travail'
        row=self.row();self.button('Démarrer',self.timer_start,row);self.button('Pause / reprendre',self.timer_pause,row);self.button('Arrêter',self.timer_stop,row)
    def timer_start(self):self.phase='Travail';self.duration=self.work_minutes.value()*60;self.deadline=time.monotonic()+self.duration;self.remaining=None;self.timer.start();self.timer_tick()
    def timer_tick(self):
        if self.deadline is None:return
        remaining=max(0,self.deadline-time.monotonic());seconds=int(remaining+.99)
        self.countdown.setText(f'{self.phase}\n{seconds//60:02}:{seconds%60:02}');self.progress.setValue(round(remaining/self.duration*1000))
        if remaining==0:
            self.phase='Pause' if self.phase=='Travail' else 'Travail';self.duration=(self.break_minutes.value() if self.phase=='Pause' else self.work_minutes.value())*60;self.deadline=time.monotonic()+self.duration
            self.tray.showMessage('Temporator',self.phase+' : nouvelle période.');self.state('Action réussie')
    def timer_pause(self):
        if self.deadline is not None:self.remaining=max(0,self.deadline-time.monotonic());self.deadline=None;self.timer.stop();self.status.setText('Minuteur en pause.')
        elif self.remaining is not None:self.deadline=time.monotonic()+self.remaining;self.timer.start();self.remaining=None
    def timer_stop(self):self.timer.stop();self.deadline=None;self.remaining=None;self.countdown.setText('Arrêté');self.progress.setValue(0)

    def planner(self):
        row=self.row();self.event_name=QLineEdit();self.event_name.setPlaceholderText('Activité ou rendez-vous');row.addWidget(self.event_name,1)
        self.event_time=QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600));self.event_time.setCalendarPopup(True);row.addWidget(self.event_time)
        self.button('Ajouter',self.add_event,row);self.events=QListWidget();self.content.addWidget(self.events,1)
        self.button('Marquer comme terminé',self.complete_event)
        self.content.addWidget(QLabel('Les rappels sont affichés tant que Planinator reste ouvert, même masqué dans son Orb.'))
        self.notified=set();self.reminder_timer=QTimer(self);self.reminder_timer.setInterval(15000);self.reminder_timer.timeout.connect(self.check_events);self.reminder_timer.start();self.refresh_events()
    def add_event(self):
        if not self.event_name.text().strip():self.error('Donnez un nom à l’activité.');return
        self.records.add('event',dict(name=self.event_name.text(),when=self.event_time.dateTime().toSecsSinceEpoch(),done=False));self.event_name.clear();self.refresh_events()
    def refresh_events(self):
        self.events.clear();self.event_items=sorted(self.records.all('event'),key=lambda x:x[1]['when'])
        for key,item in self.event_items:self.events.addItem(('✓ ' if item['done'] else '□ ')+dt.datetime.fromtimestamp(item['when']).strftime('%d/%m %H:%M')+' · '+item['name'])
    def complete_event(self):
        index=self.events.currentRow()
        if index>=0:
            key,item=self.event_items[index];item['done']=True;self.records.update(key,'event',item);self.refresh_events()
    def check_events(self):
        for key,item in self.records.all('event'):
            if not item['done'] and key not in self.notified and 0<=time.time()-item['when']<86400:
                self.notified.add(key);self.tray.showMessage('Planinator',item['name']);self.status.setText('Rappel : '+item['name']);self.state('Attention')

    def focus(self):
        self.focus_overlays=[];self.focus_selector=None;self.focus_pending=False
        self.setMinimumSize(440,280);self.resize(500,300)
        self.layout.setContentsMargins(16,12,16,12)
        self.setStyleSheet(self.styleSheet()+"QPushButton {min-height:24px;padding:5px 10px;} QSlider {background:transparent;min-height:34px;}")
        if not self.preferences.get('compact_focus_v1'):
            QTimer.singleShot(0,lambda:(self.resize(500,300),self.behavior.ensure_visible(),self.remember('compact_focus_v1',True)))
        self.status.setText('Gardez uniquement votre zone de travail visible.')
        card=QFrame();card.setObjectName('Card');layout=QVBoxLayout(card);layout.setContentsMargins(16,12,16,12)
        layout.addWidget(QLabel('Assombrissement'))
        row=QHBoxLayout();layout.addLayout(row)
        row.addWidget(QLabel('Léger'));self.dim_slider=QSlider(Qt.Horizontal);self.dim_slider.setAccessibleName('Niveau d’assombrissement');self.dim_slider.setRange(40,100)
        value=self.preferences.get('focus_darkness',85);self.dim_slider.setValue(value if type(value) is int and 40<=value<=100 else 85)
        row.addWidget(self.dim_slider,1);row.addWidget(QLabel('Opaque'));self.content.addWidget(card)
        self.dim_slider.valueChanged.connect(self.set_focus_darkness)
        self.button('Choisir ma zone',self.show_focus)
        hint=QLabel('Orb : tracer une zone.\nPour sortir : clic dans le sombre ou Échap.');hint.setWordWrap(True);self.content.addWidget(hint);self.content.addStretch()
        self.focus_escape=QTimer(self);self.focus_escape.setInterval(30);self.focus_escape.timeout.connect(self.check_focus_escape)
        self.orb.doubleActivated.connect(lambda *_:(self.hide_focus(),ApplicationWindow.activate(self)))
    def activate(self,*args):
        if self.app_id=='concentrator':self.show_focus()
        else:super().activate(*args)
    def set_focus_darkness(self,value):
        self.remember('focus_darkness',value)
        for overlay in self.focus_overlays:overlay.opacity=value;overlay.update()
    def check_focus_escape(self):
        import ctypes
        if ctypes.windll.user32.GetAsyncKeyState(0x1B)&0x8000:self.hide_focus()
    def show_focus(self):
        from shared.apps.overlays import FocusSelector
        self.hide_focus();self.hide();self.focus_pending=True
        def select():
            if not self.focus_pending or self.closing:return
            self.focus_selector=FocusSelector();self.focus_selector.selected.connect(self.apply_focus);self.focus_selector.cancelled.connect(self.hide_focus)
            self.focus_selector.show();self.focus_selector.raise_();self.focus_selector.activateWindow()
        QTimer.singleShot(180,select)
    def apply_focus(self,screen,rect):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QRect
        from shared.apps.overlays import FocusOverlay
        self.focus_pending=False
        if self.focus_selector:self.focus_selector.deleteLater();self.focus_selector=None
        for display in QApplication.screens():
            overlay=FocusOverlay(display,rect if display==screen else QRect(),self.dim_slider.value())
            overlay.dismissed.connect(self.hide_focus);self.focus_overlays.append(overlay);overlay.show()
        self.focus_escape.start();self.state('Activée');self.status.setText('Concentration active · clic dans le sombre ou Échap pour sortir.')
    def hide_focus(self):
        self.focus_pending=False
        if getattr(self,'focus_selector',None):self.focus_selector.close();self.focus_selector.deleteLater();self.focus_selector=None
        for overlay in getattr(self,'focus_overlays',[]):overlay.close();overlay.deleteLater()
        self.focus_overlays=[]
        if hasattr(self,'focus_escape'):self.focus_escape.stop()
        if self.app_id=='concentrator':self.status.setText('Choisissez une zone depuis l’Orb.')
    def cleanup(self):
        self.hide_focus()
        if getattr(self,'pdf_document',None):self.pdf_document.close()

    def pdf(self):
        self.pdf_document=None;self.pdf_page=0
        row=self.row();self.button('Ouvrir un PDF',self.open_pdf,row);self.button('Page précédente',lambda:self.change_page(-1),row);self.button('Page suivante',lambda:self.change_page(1),row);self.button('Enregistrer une copie',self.save_pdf,row)
        scroll=QScrollArea();scroll.setWidgetResizable(True);self.pdf_image=QLabel('Ouvrez un PDF.');self.pdf_image.setAlignment(Qt.AlignCenter);scroll.setWidget(self.pdf_image);self.content.addWidget(scroll,1)
        row=self.row();self.annotation=QLineEdit();self.annotation.setPlaceholderText('Note à ajouter sur cette page');row.addWidget(self.annotation,1);self.button('Ajouter la note',self.annotate_pdf,row)
        row=self.row();self.fields=QComboBox();row.addWidget(self.fields,1);self.field_value=QLineEdit();self.field_value.setPlaceholderText('Valeur du champ');row.addWidget(self.field_value,1);self.button('Remplir',self.fill_pdf,row)
        self.button('Écouter cette page',lambda:self.speak(self.pdf_document[self.pdf_page].get_text()) if self.pdf_document else None)
    def open_pdf(self):
        path,_=QFileDialog.getOpenFileName(self,'Ouvrir un PDF','','PDF (*.pdf)')
        if not path:return
        try:
            import pymupdf
            document=pymupdf.open(path)
            if document.needs_pass:document.close();raise ValueError('PDF protégé : ouvrez une copie déverrouillée.')
            if self.pdf_document:self.pdf_document.close()
            self.pdf_document=document;self.pdf_source=Path(path).resolve();self.pdf_page=0;self.render_pdf()
        except Exception as error:self.error(str(error))
    def render_pdf(self):
        if not self.pdf_document:return
        page=self.pdf_document[self.pdf_page];pixmap=page.get_pixmap(matrix=__import__('pymupdf').Matrix(1.4,1.4),alpha=False)
        image=QImage(pixmap.samples,pixmap.width,pixmap.height,pixmap.stride,QImage.Format_RGB888).copy();self.pdf_image.setPixmap(QPixmap.fromImage(image));self.fields.clear()
        for widget in page.widgets() or []:
            if widget.field_type_string=='Text':self.fields.addItem(widget.field_name,str(widget.xref))
        self.status.setText(f'Page {self.pdf_page+1} / {len(self.pdf_document)} · notes ajoutées en haut de page')
    def change_page(self,delta):
        if self.pdf_document:self.pdf_page=max(0,min(len(self.pdf_document)-1,self.pdf_page+delta));self.render_pdf()
    def annotate_pdf(self):
        if self.pdf_document and self.annotation.text().strip():
            try:self.pdf_document[self.pdf_page].add_text_annot((24,24),self.annotation.text());self.render_pdf()
            except Exception as error:self.error(str(error))
    def fill_pdf(self):
        if not self.pdf_document or self.fields.currentData() is None:return
        try:
            page=self.pdf_document[self.pdf_page];widget=page.load_widget(int(self.fields.currentData()));widget.field_value=self.field_value.text();widget.update();self.render_pdf()
        except Exception as error:self.error(str(error))
    def save_pdf(self):
        if not self.pdf_document:return
        path,_=QFileDialog.getSaveFileName(self,'Enregistrer une copie','','PDF (*.pdf)')
        if path:
            if Path(path).resolve()==self.pdf_source:self.error('Choisissez un autre nom pour conserver le document original.');return
            try:self.pdf_document.save(path,garbage=4,deflate=True);self.status.setText('Copie PDF enregistrée.')
            except Exception as error:self.error(str(error))
