"""Planinator: a mouse-first local calendar and translucent two-day companion."""
from datetime import date, datetime, time, timedelta
import sqlite3
from PySide6.QtCore import Qt, QDate, QDateTime, QTimer, QRectF, QLocale, QSize, QRect, QEvent
from PySide6.QtGui import QColor, QPainter, QPen, QShortcut, QKeySequence, QPixmap, QIcon, QTextCharFormat, QFont, QBrush
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QScrollArea, QDialog, QLineEdit, QPlainTextEdit,
    QDateTimeEdit, QCheckBox, QComboBox, QDialogButtonBox, QMainWindow, QSlider, QSizePolicy, QColorDialog, QTextEdit, QApplication, QListView, QStyledItemDelegate)
from shared.apps.base import ApplicationWindow
from shared.ui.components import ErgoWindow
from shared.domain import app_data
from shared.planner import Agenda, CATEGORIES, SUBJECTS, month_days, event_time

LOCALE = QLocale(QLocale.French, QLocale.France)
STYLE = """
QWidget {font-family:'Segoe UI';font-size:10pt;color:#F7F1E7;}
QLabel {background:transparent;border:none;}
QPushButton {min-height:0px;padding:7px 10px;background:#302C27;border:1px solid #51473A;border-radius:9px;}
QPushButton:hover {background:#493D2C;border-color:#CBA365;}
QPushButton:focus {border:2px solid #E7BC79;}
QPushButton:checked,QPushButton#Primary {background:#775A32;border:1px solid #D7AB68;}
QPushButton#DayNumber {background:transparent;border:none;text-align:left;font-weight:600;}
QPushButton#Today {background:#72552F;border:1px solid #D7AB68;text-align:left;font-weight:600;}
QPushButton#AddDay {background:transparent;border:1px solid #51473A;color:#E1BE88;}
QFrame#Day {background:rgba(30,28,25,235);border:1px solid #51483B;border-radius:12px;}
QFrame#OtherDay {background:rgba(24,24,23,220);border:1px solid #38352F;border-radius:12px;}
QFrame#Panel {background:rgba(28,26,23,240);border:1px solid #544738;border-radius:14px;}
QLineEdit,QPlainTextEdit,QTextEdit,QDateTimeEdit,QComboBox {min-height:0px;background:#272621;color:#FFF7EC;border:1px solid #65523A;border-radius:8px;padding:8px;selection-background-color:#8B683B;}
QScrollArea {background:transparent;border:none;}
QScrollBar:vertical {background:transparent;width:7px;margin:2px;}
QScrollBar::handle:vertical {background:#756046;border-radius:3px;min-height:24px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;}
QCheckBox {background:transparent;spacing:8px;}
QDialog {background:#201E1B;}
QMenu {background:#25231F;color:#FFF5E6;border:1px solid #A58350;border-radius:8px;padding:6px;}
QMenu::item {background:transparent;color:#FFF5E6;padding:8px 18px;border-radius:5px;}
QMenu::item:selected {background:#775A32;color:#FFFFFF;}
QMenu::item:disabled {color:#A79E90;}
QMenu::separator {height:1px;background:#5A4B37;margin:5px 8px;}
QFrame#Toolbar {background:rgba(30,28,25,240);border:1px solid #544738;border-radius:12px;}
QCheckBox::indicator {width:18px;height:18px;background:#302C27;border:1px solid #A58350;border-radius:5px;}
QCheckBox::indicator:checked {background:#C39C60;image:none;border:3px solid #FFF0D4;}
QComboBox QAbstractItemView {background:#282620;color:#FFF6E8;border:1px solid #9F8051;outline:none;selection-background-color:#705733;selection-color:#FFFFFF;}
"""


def button(text, callback, name='', tip=''):
    b = QPushButton(text); b.clicked.connect(callback)
    if name: b.setObjectName(name)
    b.setAccessibleName(tip or text); b.setToolTip(tip)
    return b


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget(): item.widget().hide();item.widget().deleteLater()
        elif item.layout(): clear_layout(item.layout())


def note_icon(kind):
    pix=QPixmap(48,48);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.scale(2,2)
    p.setPen(QPen(QColor('#8F6426'),1.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    if kind=='strike':
        p.setFont(QFont('Segoe UI',12,QFont.DemiBold));p.drawText(QRect(3,1,18,21),Qt.AlignCenter,'S');p.drawLine(3,12,21,12)
    else:
        p.drawLine(7,16,16,7);p.drawLine(16,7,20,11);p.drawLine(20,11,11,20);p.drawLine(11,20,7,16);p.drawLine(5,21,9,21)
        p.setPen(QPen(QColor('#F2CD67'),3,Qt.SolidLine,Qt.RoundCap));p.drawLine(3,23,21,23)
    p.end();return QIcon(pix)


def format_notes(editor,kind):
    cursor=editor.textCursor()
    if not cursor.hasSelection():return
    current=cursor.charFormat();style=QTextCharFormat()
    if kind=='strike':style.setFontStrikeOut(not current.fontStrikeOut())
    else:
        if current.background().style()!=Qt.NoBrush:style.setBackground(QBrush());style.setForeground(QColor('#1E3149'))
        else:style.setBackground(QColor('#F1D477'));style.setForeground(QColor('#211D18'))
    cursor.mergeCharFormat(style);editor.setTextCursor(cursor);editor.setFocus()


class SubjectDelegate(QStyledItemDelegate):
    def sizeHint(self,option,index):return QSize(240,max(34,option.fontMetrics.height()+16))
    def paint(self,painter,option,index):
        from PySide6.QtWidgets import QStyle
        chosen=bool(option.state & QStyle.State_Selected);selected=chosen or bool(option.state & QStyle.State_MouseOver)
        painter.save();painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(option.rect,QColor('#F5EBD9' if selected else '#FFFFFF'))
        center=option.rect.center();painter.setPen(Qt.NoPen);painter.setBrush(QColor(SUBJECTS.get(index.data(),'#D8AA61')))
        painter.drawEllipse(QRectF(option.rect.left()+13,center.y()-4,8,8))
        painter.setFont(option.font);painter.setPen(QColor('#1E3149'))
        painter.drawText(option.rect.adjusted(34,0,-28,0),Qt.AlignLeft|Qt.AlignVCenter,str(index.data()))
        if chosen:painter.drawText(option.rect.adjusted(option.rect.width()-26,0,-8,0),Qt.AlignCenter,'✓')
        painter.restore()


class SubjectPicker(QComboBox):
    def __init__(self):
        super().__init__();self.addItems(list(SUBJECTS));self.setMaxVisibleItems(8)
        view=QListView();view.setMouseTracking(True);view.setSpacing(0);view.setItemDelegate(SubjectDelegate(view));self.setView(view)
        self.popup_style='QListView {background:#282620;color:#FFF6E8;border:none;outline:none;padding:4px;} QScrollBar:vertical {background:#282620;width:7px;margin:3px;} QScrollBar::handle:vertical {background:#927344;border-radius:3px;min-height:26px;} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;}'
        view.setStyleSheet(self.popup_style)
    def showPopup(self):
        self.view().setMinimumWidth(max(240,self.width()-2))
        popup=self.view().window()
        if popup!=self.window():
            popup.setWindowFlag(Qt.WindowStaysOnTopHint,True)
            popup.setStyleSheet('QFrame {background:#282620;border:1px solid #A58350;border-radius:9px;}'+self.popup_style)
        super().showPopup()


class SchoolEditor(QDialog):
    """One subject, one note, one save. Dates come from the calendar gesture."""
    def __init__(self,owner,day,key=None,event=None,days=None):
        super().__init__(owner);self.owner=owner;self.key=key;self.original=event;self.day=day;self.days=days or [day]
        self.school=True;self.color=SUBJECTS.get((event or {}).get('subject','Français'),SUBJECTS['Français']);self.drag_origin=None
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(STYLE+'QTextEdit {background:#2B2924;color:#FFF6E8;border:1px solid #66543B;border-radius:12px;padding:12px;selection-background-color:#85623B;}')
        self.resize(430,365);self.setMinimumSize(390,340);self.setWindowTitle('Ma note')
        layout=QVBoxLayout(self);layout.setContentsMargins(20,16,20,18);layout.setSpacing(12)
        header=QHBoxLayout();heading=QLabel('Ma note');heading.setStyleSheet('font-size:16pt;font-weight:600;');header.addWidget(heading,1);header.addWidget(button('×',self.reject,tip='Fermer'));layout.addLayout(header);heading.installEventFilter(self)
        caption=LOCALE.toString(QDate(day),'dddd d MMMM') if len(self.days)==1 else str(len(self.days))+' jours sélectionnés'
        label=QLabel(caption.capitalize());label.setStyleSheet('color:#D4B482;font-size:10pt;');layout.addWidget(label)
        self.subject=SubjectPicker();self.subject.setAccessibleName('Matière ou rendez-vous');self.subject.setCurrentText((event or {}).get('subject') or ('Rendez-vous' if event else 'Français'));layout.addWidget(self.subject)
        self.notes=QTextEdit();self.notes.setAcceptRichText(False);self.notes.setPlaceholderText('Écrire ici…');self.notes.setAccessibleName('Consignes et informations')
        if event:
            if event.get('notes_html'):self.notes.setHtml(event['notes_html'])
            else:self.notes.setPlainText(event.get('notes') or (event['name'] if event['name']!=event.get('subject') else ''))
            if event['name']!=event.get('subject') and event['name'] not in self.notes.toPlainText():
                cursor=self.notes.textCursor();cursor.movePosition(cursor.Start);cursor.insertText(event['name']+'\n')
        layout.addWidget(self.notes,1)
        tools=QHBoxLayout();self.format_buttons={}
        for kind,tip in (('highlight','Surligner la sélection'),('strike','Barrer la sélection')):
            control=button('',lambda checked=False,k=kind:format_notes(self.notes,k),tip=tip);control.setIcon(note_icon(kind));control.setFixedSize(34,32);control.setFocusPolicy(Qt.NoFocus);tools.addWidget(control);self.format_buttons[kind]=control
        tools.addStretch()
        if event:tools.addWidget(button('Supprimer',self.remove))
        self.save_button=button('Enregistrer',self.save,'Primary');tools.addWidget(self.save_button);layout.addLayout(tools)
        self.error=QLabel();self.error.setStyleSheet('color:#FFBAA6;');self.error.hide();layout.addWidget(self.error)
        self.subject.currentTextChanged.connect(self.subject_changed);self.subject_changed(self.subject.currentText());self.notes.setFocus()

    def eventFilter(self,watched,event):
        if event.type()==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:self.drag_origin=event.globalPosition().toPoint()-self.pos();return True
        if event.type()==QEvent.MouseMove and self.drag_origin is not None and event.buttons()&Qt.LeftButton:self.move(event.globalPosition().toPoint()-self.drag_origin);return True
        if event.type()==QEvent.MouseButtonRelease:self.drag_origin=None
        return super().eventFilter(watched,event)

    def subject_changed(self,subject):
        self.color=SUBJECTS[subject];self.subject.setStyleSheet(f'QComboBox {{border:1px solid {self.color};border-left:5px solid {self.color};padding:8px;background:#302D28;}}')

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setBrush(QColor('#FFFFFF'));p.setPen(QPen(QColor(self.color),1));p.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),18,18)

    def save(self):
        subject=self.subject.currentText();notes=self.notes.toPlainText().strip()
        data=dict(self.original or {},name=subject,subject=subject,color=SUBJECTS[subject],notes=notes,notes_html=self.notes.toHtml())
        if not self.original:
            start=datetime.combine(self.day,time.min);data.update(when=start.timestamp(),end=(start+timedelta(days=1)).timestamp(),all_day=True,category='École',school_kind='',done=False)
        try:
            if self.original:self.owner.agenda.save(data,self.key)
            else:
                import json
                from shared.planner import normalize_event
                with self.owner.records.db:
                    for day in self.days:
                        first=datetime.combine(day,time.min);record=normalize_event(dict(data,when=first.timestamp(),end=(first+timedelta(days=1)).timestamp()))
                        self.owner.records.db.execute('INSERT INTO records(kind,data) VALUES (?,?)',('event',json.dumps(record,ensure_ascii=False)))
        except (ValueError,OSError,sqlite3.Error) as error:self.error.setText(str(error));self.error.show();return
        self.owner.selected_days.clear();self.owner.multi_select=False;self.owner.changed();self.accept()

    def remove(self):self.owner.delete_event(self.key,self.original);self.accept()


class EventEditor(QDialog):
    def __init__(self, owner, day, key=None, event=None, days=None):
        super().__init__(owner); self.owner=owner; self.key=key; self.original=event
        self.days=days or [];self.school=bool((event or {}).get('subject')) if event else owner.student_mode
        self.color=(event or {}).get('color','') or CATEGORIES[(event or {}).get('category','Personnel')]
        self.setWindowTitle(('Modifier' if key else 'Ajouter')+(' une matière' if self.school else ' un rendez-vous'))
        self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);self.setStyleSheet(STYLE+'QDialog {border:1px solid #A58350;border-radius:16px;}')
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(470,610 if self.school else 530); self.setMinimumWidth(420)
        layout=QVBoxLayout(self);layout.setContentsMargins(20,18,20,18);layout.setSpacing(10)
        header=QHBoxLayout();heading=QLabel(self.windowTitle());heading.setStyleSheet('font-size:15pt;font-weight:600;');header.addWidget(heading,1);header.addWidget(button('×',self.reject,tip='Fermer'));layout.addLayout(header)
        self.drag_origin=None;heading.installEventFilter(self)
        if len(self.days)>1:
            info=QLabel(str(len(self.days))+' jours sélectionnés · mêmes horaires sur chaque jour');info.setStyleSheet('color:#D8B986;font-size:9pt;');layout.addWidget(info)
        self.subject=QComboBox();self.subject.addItems(list(SUBJECTS));self.subject.setEditable(True);self.subject.setAccessibleName('Matière')
        self.school_kind=QComboBox();self.school_kind.addItems(['Devoirs','Cours','Évaluation','À apporter']);self.school_kind.setAccessibleName('Type de travail')
        if self.school:
            row=QHBoxLayout();row.addWidget(self.subject,2);row.addWidget(self.school_kind,1);layout.addLayout(row)
        else:self.subject.hide();self.school_kind.hide()
        self.title=QLineEdit();self.title.setPlaceholderText('Exercice, chapitre… (facultatif)' if self.school else 'Titre du rendez-vous');self.title.setAccessibleName('Titre');layout.addWidget(self.title)
        start=datetime.combine(day,time(9));end=start+timedelta(hours=1)
        if event:
            start=datetime.fromtimestamp(event['when']);end=datetime.fromtimestamp(event['end'])
            if event['all_day']:end-=timedelta(days=1)
        self.start=QDateTimeEdit(QDateTime(start));self.end=QDateTimeEdit(QDateTime(end))
        for name,field in (('Début',self.start),('Fin',self.end)):
            row=QHBoxLayout();label=QLabel(name);label.setFixedWidth(42);row.addWidget(label)
            field.setLocale(LOCALE);field.setDisplayFormat('ddd dd MMM yyyy · HH:mm');field.setCalendarPopup(True);field.setAccessibleName(name);row.addWidget(field,1);layout.addLayout(row)
        self.all_day=QCheckBox('Toute la journée');layout.addWidget(self.all_day)
        self.category=QComboBox();self.category.addItems(list(CATEGORIES));self.category.setAccessibleName('Catégorie')
        if not self.school:layout.addWidget(self.category)
        else:self.category.hide()
        colors=QHBoxLayout();colors.addWidget(QLabel('Couleur'));self.swatches=[]
        for color in ('#D8AA61','#E49B91','#85B7E9','#C4A0E1','#82C8B8','#97C892','#D698C7'):
            swatch=button('',lambda checked=False,c=color:self.choose_color(c),tip='Couleur '+color);swatch.setFixedSize(24,24);self.swatches.append((swatch,color));colors.addWidget(swatch)
        colors.addWidget(button('…',self.custom_color,tip='Autre couleur'));colors.addStretch();layout.addLayout(colors)
        self.place=QLineEdit();self.place.setPlaceholderText('Salle, professeur… (facultatif)' if self.school else 'Lieu (facultatif)');self.place.setAccessibleName('Lieu');layout.addWidget(self.place)
        self.notes=QTextEdit();self.notes.setAcceptRichText(False);self.notes.setPlaceholderText('Notes, informations utiles…');self.notes.setAccessibleName('Notes');layout.addWidget(self.notes,1)
        formatting=QHBoxLayout()
        for kind,tip in (('highlight','Surligner la sélection'),('strike','Barrer la sélection')):
            control=button('',lambda checked=False,k=kind:format_notes(self.notes,k),tip=tip);control.setIcon(note_icon(kind));control.setFixedSize(34,32);control.setFocusPolicy(Qt.NoFocus);formatting.addWidget(control)
        formatting.addStretch();layout.addLayout(formatting)
        self.completed=QCheckBox('Terminé');layout.addWidget(self.completed)
        self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#FFBBA8;');layout.addWidget(self.error)
        actions=QHBoxLayout()
        if event:
            self.title.setText(event['name']);self.place.setText(event['place']);self.notes.setPlainText(event['notes'])
            if event.get('notes_html'):self.notes.setHtml(event['notes_html'])
            self.category.setCurrentText(event['category']);self.all_day.setChecked(event['all_day']);self.completed.setChecked(event['done'])
            self.subject.setCurrentText(event.get('subject') or 'Français');self.school_kind.setCurrentText(event.get('school_kind','Devoirs'))
            actions.addWidget(button('Supprimer',self.remove))
        actions.addStretch();actions.addWidget(button('Annuler',self.reject));self.save_button=button('Enregistrer',self.save,'Primary');actions.addWidget(self.save_button);layout.addLayout(actions)
        if self.school and not event:self.all_day.setChecked(True);self.color=SUBJECTS['Français']
        self.subject.currentTextChanged.connect(lambda subject:self.choose_color(SUBJECTS.get(subject,self.color)))
        self.choose_color(self.color);self.all_day.toggled.connect(self.day_mode);self.day_mode(self.all_day.isChecked())
        if not self.school:self.category.currentTextChanged.connect(lambda category:self.choose_color(CATEGORIES[category]))
        self.start.dateTimeChanged.connect(self.adjust_end);self.title.setFocus()

    def eventFilter(self,watched,event):
        if event.type()==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:self.drag_origin=event.globalPosition().toPoint()-self.pos();return True
        if event.type()==QEvent.MouseMove and self.drag_origin is not None and event.buttons()&Qt.LeftButton:self.move(event.globalPosition().toPoint()-self.drag_origin);return True
        if event.type()==QEvent.MouseButtonRelease:self.drag_origin=None
        return super().eventFilter(watched,event)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing);painter.setPen(QPen(QColor('#A58350'),1));painter.setBrush(QColor('#201E1B'));painter.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),16,16)

    def choose_color(self,color):
        self.color=color
        for swatch,value in self.swatches:swatch.setStyleSheet(f'background:{value};border:{"3px solid #FFF6E6" if value==color else "1px solid #665A49"};border-radius:12px;padding:0px;')

    def custom_color(self):
        color=QColorDialog.getColor(QColor(self.color),self,'Couleur du rendez-vous')
        if color.isValid():self.choose_color(color.name())

    def day_mode(self,checked):
        for field in (self.start,self.end):field.setDisplayFormat('ddd dd MMM yyyy' if checked else 'ddd dd MMM yyyy · HH:mm')

    def adjust_end(self,start):
        if self.end.dateTime()<=start:self.end.setDateTime(start.addSecs(3600))

    def save(self):
        start=self.start.dateTime();end=self.end.dateTime()
        if self.all_day.isChecked():
            start=QDateTime(start.date(),time_to_qt());end=QDateTime(end.date().addDays(1),time_to_qt())
        if self.school and not self.subject.currentText().strip():self.error.setText('Choisissez une matière.');return
        data=dict(name=self.title.text().strip() or (self.subject.currentText().strip() if self.school else ''),when=start.toSecsSinceEpoch(),end=end.toSecsSinceEpoch(),
                  all_day=self.all_day.isChecked(),category='École' if self.school else self.category.currentText(),place=self.place.text().strip(),
                  notes=self.notes.toPlainText(),notes_html=self.notes.toHtml(),done=self.completed.isChecked(),color=self.color,
                  subject=self.subject.currentText().strip() if self.school else '',school_kind=self.school_kind.currentText())
        try:
            if self.days and self.key is None:
                duration_days=start.date().daysTo(end.date())
                with self.owner.records.db:
                    # Prevalidate before the first write; each selected date remains independent.
                    if not data['name'] or end<=start:raise ValueError('Vérifiez le titre et les horaires.')
                    import json
                    from shared.planner import normalize_event
                    for day in self.days:
                        first=QDateTime(QDate(day),start.time());last=QDateTime(QDate(day).addDays(duration_days),end.time())
                        record=normalize_event(dict(data,when=first.toSecsSinceEpoch(),end=last.toSecsSinceEpoch()))
                        self.owner.records.db.execute('INSERT INTO records(kind,data) VALUES (?,?)',('event',json.dumps(record,ensure_ascii=False)))
            else:self.key=self.owner.agenda.save(data,self.key)
        except (ValueError,OSError,sqlite3.Error) as error:self.error.setText(str(error));return
        self.owner.selected_days.clear();self.owner.multi_select=False;self.owner.selection_button.setChecked(False)
        self.owner.changed();self.accept()

    def remove(self):
        self.owner.delete_event(self.key,self.original);self.accept()


def time_to_qt():
    from PySide6.QtCore import QTime
    return QTime(0,0)


class EventTitle(QPushButton):
    """A wrapping, keyboard-activatable title, including in narrow week columns."""
    def __init__(self,text,callback,compact=False):
        super().__init__(text);self.compact=compact;self.clicked.connect(callback);self.setAccessibleName(text)
        policy=QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred);policy.setHeightForWidth(True);self.setSizePolicy(policy)
        self.setMinimumWidth(0)
    def sizeHint(self):return QSize(100,24 if self.compact else 32)
    def minimumSizeHint(self):return QSize(0,24)
    def heightForWidth(self,width):
        if self.compact:return 24
        return max(26,self.fontMetrics().boundingRect(QRect(0,0,max(30,width-4),2000),Qt.TextWordWrap,self.text()).height()+6)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(QColor('#8F6426' if self.underMouse() else '#1E3149'))
        if self.compact:p.drawText(self.rect().adjusted(2,2,-2,-2),Qt.AlignLeft|Qt.AlignVCenter,self.fontMetrics().elidedText(self.text(),Qt.ElideRight,self.width()-4))
        else:p.drawText(self.rect().adjusted(2,2,-2,-2),Qt.TextWordWrap|Qt.AlignLeft|Qt.AlignVCenter,self.text())
        if self.hasFocus():p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor('#E7BC79'),1));p.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),4,4)


class EventCard(QFrame):
    def __init__(self,owner,key,event,day,compact=False):
        super().__init__();self.owner=owner;self.key=key;self.event_data=event;self.day=day;color=SUBJECTS.get(event.get('subject')) or event.get('color') or CATEGORIES[event['category']]
        tint=QColor(color);base=QColor('#FFFFFF');surface=QColor(*[round(tint.getRgb()[i]*.20+base.getRgb()[i]*.80) for i in range(3)]).name()
        self.setStyleSheet(f'EventCard {{background:{surface};border:1px solid #5B4D39;border-left:3px solid {color};border-radius:8px;}}')
        layout=QVBoxLayout(self);layout.setContentsMargins(8,5,8,5);layout.setSpacing(2)
        title=('✓ ' if event['done'] else '')+event['name']
        if event.get('subject') and event['name']!=event['subject']:title=event['subject']+' · '+title
        short={'Mathématiques':'Maths','Histoire-géographie':'Histoire-géo','Éducation musicale':'Musique','Arts plastiques':'Arts','Physique-chimie':'Physique','Documentation':'CDI'}
        label=short.get(event.get('subject'),title) if compact else title
        if compact and event['done'] and not label.startswith('✓'):label='✓ '+label
        self.open_button=EventTitle(label,lambda:owner.edit_event(day,key,event),compact);self.open_button.setStyleSheet('QPushButton {background:transparent;border:none;padding:0px;text-align:left;font-weight:600;}')
        font=self.open_button.font();font.setStrikeOut(event['done']);self.open_button.setFont(font)
        if event.get('highlight'):self.setStyleSheet(f'EventCard {{background:#53442C;border:1px solid {color};border-left:3px solid {color};border-radius:8px;}}')
        self.open_button.setToolTip(title+'\n'+event_time(event,day)+('\n'+event['place'] if event['place'] else '')+('\n'+event['notes'] if event.get('notes') else ''))
        layout.addWidget(self.open_button)
        if not compact:
            sub=QLabel((event['school_kind']+' · ' if event.get('subject') and event.get('school_kind') else '')+event_time(event,day));sub.setStyleSheet(f'color:{color};font-size:9pt;');layout.addWidget(sub)
        if event['place'] and not compact:
            place=QLabel(event['place']);place.setWordWrap(True);place.setStyleSheet('color:#C8BEAD;font-size:9pt;');layout.addWidget(place)
        if not compact:
            if event.get('notes'):
                preview=QLabel();preview.setWordWrap(True);preview.setTextFormat(Qt.RichText)
                if event.get('notes_html'):preview.setText(event['notes_html'])
                else:preview.setTextFormat(Qt.PlainText);preview.setText(event['notes'])
                preview.setMaximumHeight(95);layout.addWidget(preview)
            actions=QHBoxLayout();actions.addStretch();self.format_buttons={}
            for kind,tip in (('highlight','Mettre en évidence'),('strike','Barrer / rétablir cet élément')):
                control=button('',lambda checked=False,k=kind:owner.format_event(key,event,k),tip=tip);control.setIcon(note_icon(kind));control.setFixedSize(28,26);actions.addWidget(control);self.format_buttons[kind]=control
            layout.addLayout(actions)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.LeftButton:self.owner.edit_event(self.day,self.key,self.event_data)
        else:super().mouseReleaseEvent(event)


class DayColumn(QFrame):
    def __init__(self,owner,day,compact=False,muted=False):
        super().__init__();self.owner=owner;self.day=day;self.setObjectName('OtherDay' if muted else 'Day');self.setMinimumWidth(0)
        layout=QVBoxLayout(self);layout.setContentsMargins(6,5,6,6);layout.setSpacing(5)
        today=date.today();week_start=today-timedelta(days=today.weekday());self.current_week=week_start<=day<week_start+timedelta(days=7)
        if self.current_week:self.setStyleSheet('QFrame#Day,QFrame#OtherDay {background:#FFF2D4;border:1px solid #D6AF64;border-radius:12px;}')
        if day==today:self.setStyleSheet('QFrame#Day,QFrame#OtherDay {background:#FFE8B5;border:2px solid #996713;border-radius:12px;}')
        rows=owner.agenda.on(day)
        title=LOCALE.toString(QDate(day),'ddd d') if not compact else str(day.day)+(f'  · {len(rows)}' if len(rows)>1 else '')
        self.day_button=button(title,lambda:owner.choose_day(day),'Today' if day==date.today() else 'DayNumber',LOCALE.toString(QDate(day),'dddd d MMMM yyyy'))
        if day==today:
            self.day_button.setProperty('suitePrimary',True);self.day_button.setStyleSheet('QPushButton[suitePrimary="true"] {background:#95651F;color:#FFFFFF;border:1px solid #95651F;border-radius:7px;font-weight:700;padding:3px;}')
        if day in owner.selected_days:self.setStyleSheet('DayColumn {border:2px solid #EAC689;background:#433929;border-radius:12px;}')
        header=QHBoxLayout();header.setSpacing(2);header.addWidget(self.day_button,1)
        self.add_button=button('+',lambda:owner.edit_event(day),'AddDay','Ajouter le '+day.strftime('%d/%m/%Y'));self.add_button.setFixedWidth(28);header.addWidget(self.add_button);layout.addLayout(header)
        if compact:
            self.day_button.setFixedHeight(20);self.add_button.setFixedHeight(20)
            self.day_button.setStyleSheet('padding:1px 3px;text-align:left;');self.add_button.setStyleSheet('padding:0px;')
        limit=1 if compact else len(rows)
        for key,event in rows[:limit]:layout.addWidget(EventCard(owner,key,event,day,compact))
        if not rows and not compact:
            empty=QLabel('Rien de prévu');empty.setStyleSheet('color:#9D9587;font-size:9pt;padding:6px;');layout.addWidget(empty)
        layout.addStretch()

    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.LeftButton:self.owner.edit_event(self.day)
        else:super().mouseDoubleClickEvent(event)


class Companion(ErgoWindow):
    def __init__(self,owner):
        super().__init__();self.owner=owner
        self.setWindowFlags(Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle('Planinator · Aujourd’hui et demain');self.setWindowIcon(owner.windowIcon())
        self.setMinimumSize(320,180);self.resize(370,260);self.setStyleSheet(STYLE+'QMainWindow {background:transparent;}')
        root=QWidget();root.setAttribute(Qt.WA_TranslucentBackground);self.setCentralWidget(root)
        layout=QVBoxLayout(root);layout.setContentsMargins(16,14,16,14);layout.setSpacing(12)
        header=QHBoxLayout();label=QLabel('MON AGENDA');label.setStyleSheet('font-size:11pt;font-weight:600;letter-spacing:2px;color:#E6C48E;');header.addWidget(label,1)
        header.addWidget(button('↗',owner.open_agenda,tip='Ouvrir l’agenda'));header.addWidget(button('×',self.hide,tip='Masquer le widget'));layout.addLayout(header)
        self.drag_area(label);label.setCursor(Qt.ArrowCursor);label.setToolTip('');label.installEventFilter(self)
        scroll=QScrollArea();scroll.setWidgetResizable(True);self.body=QWidget();self.days=QVBoxLayout(self.body);self.days.setContentsMargins(0,0,0,0);self.days.setSpacing(12);scroll.setWidget(self.body);self.body.setAutoFillBackground(False);scroll.viewport().setAutoFillBackground(False);scroll.viewport().setAttribute(Qt.WA_TranslucentBackground);layout.addWidget(scroll,1)
        self.scroll=scroll;self.body.installEventFilter(self);scroll.viewport().installEventFilter(self)
        self.fit_timer=QTimer(self);self.fit_timer.setSingleShot(True);self.fit_timer.timeout.connect(self.fit_content)
        footer=QHBoxLayout();opacity=QLabel('Fond');footer.addWidget(opacity)
        self.opacity=QSlider(Qt.Horizontal);self.opacity.setRange(35,95);self.opacity.setValue(owner.preferences.get('planner_opacity',80));self.opacity.setAccessibleName('Opacité du fond du widget')
        self.opacity.setStyleSheet('QSlider {background:transparent;min-height:24px;} QSlider::groove:horizontal {height:4px;background:#5A4C39;border-radius:2px;} QSlider::handle:horizontal {width:14px;height:14px;margin:-5px 0;background:#E8BC79;border-radius:7px;} QSlider::sub-page:horizontal {background:#B48A50;border-radius:2px;}')
        self.opacity.valueChanged.connect(self.set_opacity);footer.addWidget(self.opacity,1);layout.addLayout(footer)
        self.behavior.configure(app_data('planinator')/'widget.json');QShortcut(QKeySequence('Esc'),self,activated=self.hide)

    def set_opacity(self,value):self.owner.remember('planner_opacity',value);self.update()

    def refresh(self):
        position=self.scroll.verticalScrollBar().value();clear_layout(self.days)
        for offset,title in ((0,'Aujourd’hui'),(1,'Demain')):
            day=date.today()+timedelta(days=offset);heading=QHBoxLayout()
            label=QLabel(title+' · '+LOCALE.toString(QDate(day),'d MMM'));label.setStyleSheet('font-size:12pt;font-weight:600;');heading.addWidget(label,1)
            heading.addWidget(button('+',lambda checked=False,d=day:self.owner.edit_event(d),tip='Ajouter un rendez-vous '+title.lower()));self.days.addLayout(heading)
            rows=self.owner.agenda.on(day)
            if not rows:
                empty=QLabel('Rien de prévu');empty.setStyleSheet('color:#C1B8A7;padding:6px 2px;');self.days.addWidget(empty)
            for key,event in rows:self.days.addWidget(EventCard(self.owner,key,event,day))
        self.days.addStretch();self.days.invalidate();self.fit_content();self.fit_timer.start(0)
        self.scroll.verticalScrollBar().setValue(position)

    def fit_content(self):
        if not hasattr(self,'opacity'):return
        self.ensurePolished();self.body.ensurePolished()
        width=max(280,self.width()-32)
        natural=self.days.totalHeightForWidth(width) if self.days.hasHeightForWidth() else self.days.sizeHint().height()
        natural=max(100,natural)
        self.body.setMinimumHeight(natural)
        chrome=28+24+max(34,self.centralWidget().layout().itemAt(0).sizeHint().height())+max(24,self.opacity.sizeHint().height())
        area=self.screen().availableGeometry();height=min(area.height()-20,max(180,natural+chrome+4))
        self.resize(min(self.width(),area.width()-20),height)
        self.move(max(area.left(),min(self.x(),area.right()-self.width()+1)),max(area.top(),min(self.y(),area.bottom()-self.height()+1)))

    def eventFilter(self,watched,event):
        if event.type()==QEvent.MouseButtonDblClick and event.button()==Qt.LeftButton:
            self.owner.open_agenda();return True
        return super().eventFilter(watched,event)

    def showEvent(self,event):
        super().showEvent(event);self.fit_timer.start(0)

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        color=QColor('#F6F9FD');color.setAlpha(round(self.opacity.value()*2.55));p.setBrush(color);p.setPen(QPen(QColor('#DCE3ED'),1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),20,20)

    def resizeEvent(self,event):
        QMainWindow.resizeEvent(self,event);self.clearMask()
        if hasattr(self,'fit_timer') and event.oldSize().width()!=event.size().width():self.fit_timer.start(0)

    def closeEvent(self,event):self.hide();event.ignore()


class PlaninatorWindow(ApplicationWindow):
    def __init__(self):
        super().__init__('planinator');self.agenda=Agenda(self.records);self.selected=date.today();self.deleted=None;self.dialog=None
        self.student_mode=bool(self.preferences.get('planner_student',False));self.selected_days=set();self.multi_select=False
        self.setStyleSheet(STYLE);self.setMinimumSize(760,590);self.resize(1050,740)
        self.status.setText('Votre agenda · enregistré sur cet ordinateur')
        self.status.hide();self.layout.setContentsMargins(14,10,14,10)
        for target in (self.findChild(QFrame,'WindowHeader'),):
            if target:target.setCursor(Qt.ArrowCursor);target.setToolTip('')
        panel=QFrame();panel.setObjectName('Toolbar');toolbar=QHBoxLayout(panel);toolbar.setContentsMargins(8,6,8,6);toolbar.setSpacing(5)
        self.previous=button('‹',lambda:self.navigate(-1),tip='Période précédente');self.next=button('›',lambda:self.navigate(1),tip='Période suivante')
        toolbar.addWidget(self.previous);toolbar.addWidget(button('Aujourd’hui',self.today));toolbar.addWidget(self.next)
        self.period=QLabel();self.period.setStyleSheet('font-size:14pt;font-weight:600;padding-left:6px;');toolbar.addWidget(self.period,1)
        self.views={};self.mode=self.preferences.get('planner_view','Semaine')
        if self.mode not in ('Jour','Semaine','Mois'):self.mode='Semaine'
        for mode in ('Jour','Semaine','Mois'):
            control=button(mode,lambda checked=False,m=mode:self.set_view(m));control.setCheckable(True);toolbar.addWidget(control);self.views[mode]=control
        self.content.addWidget(panel)
        actions=QHBoxLayout();self.add_event_button=button('+  Matière' if self.student_mode else '+  Rendez-vous',lambda:self.edit_event(self.selected),'Primary');actions.addWidget(self.add_event_button)
        self.selection_button=button('Plusieurs jours',self.toggle_selection);self.selection_button.setCheckable(True);self.selection_button.hide()
        for control in (self.add_event_button,self.selection_button):control.setStyleSheet('QPushButton {min-height:22px;padding:5px 10px;}')
        self.selection_count=QLabel();actions.addWidget(self.selection_count);actions.addStretch()
        self.student_choice=QCheckBox('Mode Élève');self.student_choice.setChecked(self.student_mode);self.student_choice.toggled.connect(self.set_student);actions.addWidget(self.student_choice)
        self.undo_button=button('Annuler la suppression',self.undo_delete);self.undo_button.hide();actions.addWidget(self.undo_button)
        self.content.addLayout(actions)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.grid_root=QWidget();self.grid_root.setAutoFillBackground(True)
        self.grid=QGridLayout(self.grid_root);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(8);self.scroll.setWidget(self.grid_root);self.content.addWidget(self.scroll,1)
        self.widget=Companion(self);self.orb.doubleActivated.connect(self.open_agenda)
        self.drag_anchor=None;self.drag_origin=None;self.drag_has_moved=False;QApplication.instance().installEventFilter(self)
        self.orb.setAccessibleDescription('Un clic : aujourd’hui et demain. Double-clic : agenda. Clic droit : menu.')
        self.orb.setToolTip('Planinator · clic : aujourd’hui / demain · double-clic : agenda')
        self.refresh_timer=QTimer(self);self.refresh_timer.setInterval(30000);self.refresh_timer.timeout.connect(self.clock_refresh);self.refresh_timer.start();self.last_day=date.today();self.notified=set()
        QShortcut(QKeySequence('Ctrl+N'),self,activated=lambda:self.edit_event(self.selected))
        QShortcut(QKeySequence('Alt+Left'),self,activated=lambda:self.navigate(-1));QShortcut(QKeySequence('Alt+Right'),self,activated=lambda:self.navigate(1))
        self.changed()

    def activate(self,*_):
        if not hasattr(self,'widget'):return
        if self.widget.isVisible():self.widget.hide()
        else:self.widget.refresh();self.widget.show();self.widget.raise_()

    def open_agenda(self,*_):self.widget.hide();ApplicationWindow.activate(self)

    def create_orb_menu(self):
        menu=super().create_orb_menu();menu.actions()[0].triggered.disconnect();menu.actions()[0].triggered.connect(self.open_agenda)
        menu.setWindowOpacity(1);menu.setAttribute(Qt.WA_TranslucentBackground,False)
        menu.insertAction(menu.actions()[1],menu.addAction('Afficher / masquer aujourd’hui et demain',self.activate));return menu

    def set_view(self,mode):self.mode=mode;self.remember('planner_view',mode);self.refresh()
    def eventFilter(self,watched,event):
        if not hasattr(self,'drag_anchor') or self.closing:return super().eventFilter(watched,event)
        kind=event.type()
        if kind==QEvent.MouseButtonPress and event.button()==Qt.LeftButton and isinstance(watched,QWidget):
            target=watched;cell=None
            while target and target!=self.grid_root:
                if isinstance(target,EventCard):break
                if isinstance(target,DayColumn):cell=target;break
                target=target.parentWidget()
            if cell and watched!=cell.add_button:
                self.drag_anchor=cell.day;self.drag_origin=event.globalPosition().toPoint();self.drag_has_moved=False;self.drag_header=watched==cell.day_button
                return True
        if self.drag_anchor is not None and kind==QEvent.MouseMove:
            if (event.globalPosition().toPoint()-self.drag_origin).manhattanLength()<5:return True
            for index in range(self.grid.count()):
                cell=self.grid.itemAt(index).widget()
                if isinstance(cell,DayColumn) and cell.rect().contains(cell.mapFromGlobal(event.globalPosition().toPoint())):
                    first,last=sorted((self.drag_anchor,cell.day));self.selected_days={first+timedelta(days=i) for i in range((last-first).days+1)};self.multi_select=True;self.drag_has_moved=True
                    self.selection_count.setText(str(len(self.selected_days))+' jours')
                    for j in range(self.grid.count()):
                        day_cell=self.grid.itemAt(j).widget()
                        if isinstance(day_cell,DayColumn):day_cell.setStyleSheet('DayColumn {border:2px solid #EAC689;background:#433929;border-radius:12px;}' if day_cell.day in self.selected_days else '')
                    break
            return True
        if self.drag_anchor is not None and kind==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton:
            day=self.drag_anchor;self.drag_anchor=None
            if self.drag_has_moved:self.edit_event(min(self.selected_days))
            elif self.drag_header:self.choose_day(day)
            else:self.selected_days.clear();self.multi_select=False;self.edit_event(day)
            return True
        return super().eventFilter(watched,event)

    def format_event(self,key,event,kind):
        field='done' if kind=='strike' else 'highlight';self.agenda.save(dict(event,**{field:not event.get(field,False)}),key);self.changed()
    def set_student(self,enabled):
        self.student_mode=enabled;self.remember('planner_student',enabled);self.add_event_button.setText('+  Matière' if enabled else '+  Rendez-vous');self.refresh();self.widget.refresh()

    def toggle_selection(self):
        self.multi_select=self.selection_button.isChecked()
        if not self.multi_select:self.selected_days.clear()
        if self.multi_select and self.mode=='Jour':self.mode='Mois'
        self.refresh()

    def choose_day(self,day):
        self.selected_days.clear();self.multi_select=False;self.show_day(day)
    def today(self):self.selected=date.today();self.refresh()
    def show_day(self,day):self.selected=day;self.set_view('Jour')

    def navigate(self,direction):
        if self.mode=='Mois':
            q=QDate(self.selected).addMonths(direction);self.selected=q.toPython()
        else:self.selected+=timedelta(days=direction*(7 if self.mode=='Semaine' else 1))
        self.refresh()

    def refresh(self):
        clear_layout(self.grid)
        for row in range(7):self.grid.setRowStretch(row,0)
        for mode,control in self.views.items():control.setChecked(mode==self.mode)
        self.selection_count.setText(str(len(self.selected_days))+' jours' if self.selected_days else 'Glisser pour sélectionner des jours')
        self.selection_count.setStyleSheet('color:#C8B89D;font-size:9pt;')
        if self.mode=='Mois':
            self.period.setText(LOCALE.toString(QDate(self.selected),'MMMM yyyy').capitalize())
            first=self.selected.replace(day=1);start=first-timedelta(days=first.weekday())
            for col in range(7):
                label=QLabel(LOCALE.dayName(col+1,QLocale.ShortFormat));label.setAlignment(Qt.AlignCenter);label.setStyleSheet('color:#D5B782;');self.grid.addWidget(label,0,col)
            weeks=month_days(self.selected)
            for row,week in enumerate(weeks,1):
                for col,day in enumerate(week):self.grid.addWidget(DayColumn(self,day,True,day.month!=self.selected.month),row,col)
                self.grid.setRowStretch(row,1)
            self.grid_root.setMinimumHeight(0)
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            start=self.selected-timedelta(days=self.selected.weekday()) if self.mode=='Semaine' else self.selected
            count=7 if self.mode=='Semaine' else 1
            end=start+timedelta(days=count-1)
            self.period.setText(LOCALE.toString(QDate(start),'d MMM')+' – '+LOCALE.toString(QDate(end),'d MMM yyyy') if count==7 else LOCALE.toString(QDate(start),'dddd d MMMM yyyy').capitalize())
            for col in range(count):self.grid.addWidget(DayColumn(self,start+timedelta(days=col)),0,col)
            self.grid_root.setMinimumHeight(380)
        # Remove stretch left by the previous view without retaining phantom columns.
        for col in range(7):self.grid.setColumnStretch(col,1 if self.mode!='Jour' or col==0 else 0)
        QTimer.singleShot(0,self.fit_calendar)

    def fit_calendar(self):
        if self.closing or self.isMaximized():return
        width=max(300,self.scroll.viewport().width())
        natural=self.grid.totalHeightForWidth(width) if self.grid.hasHeightForWidth() else self.grid.sizeHint().height()
        needed=natural+self.height()-self.scroll.height()+8
        area=self.screen().availableGeometry()
        if needed>self.height():
            self.resize(self.width(),min(needed,area.height()-20));self.behavior.ensure_visible()

    def edit_event(self,day,key=None,event=None):
        if self.dialog and self.dialog.isVisible():self.dialog.raise_();self.dialog.activateWindow();return
        days=sorted(self.selected_days) if key is None and self.multi_select else []
        editor=SchoolEditor if self.student_mode or bool((event or {}).get('subject')) else EventEditor
        self.dialog=editor(self,days[0] if days else day,key,event,days);self.dialog.setWindowModality(Qt.ApplicationModal);self.dialog.show();self.dialog.raise_();self.dialog.activateWindow()
        self.dialog.finished.connect(self.dialog.deleteLater)
        self.dialog.finished.connect(lambda *_:setattr(self,'dialog',None))

    def changed(self):self.refresh();self.widget.refresh()
    def delete_event(self,key,event):self.agenda.delete(key,event);self.deleted=(key,event);self.undo_button.show();self.changed()
    def undo_delete(self):
        if self.deleted:self.agenda.restore(*self.deleted);self.deleted=None;self.undo_button.hide();self.changed()

    def clock_refresh(self):
        now=datetime.now().timestamp()
        for key,event in self.agenda.events():
            if not event['done'] and not event['all_day'] and key not in self.notified and 0<=now-event['when']<60:
                self.notified.add(key);self.status.setText('Maintenant : '+event['name']);self.widget.show();self.widget.raise_()
        if self.widget.isVisible():self.widget.refresh()
        if self.last_day!=date.today():self.last_day=date.today();self.refresh()

    def cleanup(self):
        QApplication.instance().removeEventFilter(self)
        self.refresh_timer.stop();self.widget.fit_timer.stop();self.widget.behavior.save();self.widget.hide()
        if self.dialog:self.dialog.reject()
        self.widget.deleteLater()
