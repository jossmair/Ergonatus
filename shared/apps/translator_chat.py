"""Traductor: compact SMS conversation in the visual family of Redactor."""
import threading,uuid
from PySide6.QtCore import Qt,QTimer,Signal,QThreadPool,QSize,QPointF,QRectF
from PySide6.QtGui import QPainter,QPixmap,QColor,QPen,QPolygonF,QIcon
from PySide6.QtWidgets import (QWidget,QFrame,QLabel,QPushButton,QComboBox,QScrollArea,
    QVBoxLayout,QHBoxLayout,QPlainTextEdit,QSizePolicy,QFileDialog)
from shared.apps.base import ApplicationWindow
from shared.jobs import Job
from shared.translation import LANGUAGES
from shared.ui.choices import ChoiceBox


def chat_icon(kind):
    pix=QPixmap(48,48);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.scale(2,2)
    p.setPen(QPen(QColor('#1E3149'),1.6,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    if kind=='copy':p.drawRoundedRect(8,7,12,14,2,2);p.drawLine(5,16,4,16);p.drawLine(4,16,4,3);p.drawLine(4,3,15,3)
    elif kind=='speaker':
        p.drawPolygon(QPolygonF([QPointF(4,10),QPointF(8,10),QPointF(13,6),QPointF(13,19),QPointF(8,15),QPointF(4,15)]));p.drawArc(QRectF(10,5,9,15),-65*16,130*16);p.drawArc(QRectF(11,2,12,21),-65*16,130*16)
    elif kind=='stop':p.setBrush(QColor('#1E3149'));p.drawRoundedRect(6,6,12,12,2,2)
    else:p.drawPolygon(QPolygonF([QPointF(4,3),QPointF(21,12),QPointF(4,21),QPointF(7,12)]));p.drawLine(7,12,16,12)
    p.end();return QIcon(pix)


class Composer(QPlainTextEdit):
    submitted=Signal()
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key_Return,Qt.Key_Enter) and not event.modifiers()&Qt.ShiftModifier:self.submitted.emit();event.accept()
        else:super().keyPressEvent(event)


class Bubble(QFrame):
    def __init__(self,owner,text,language,user=False,pending=False):
        super().__init__();self.owner=owner;self.text=text;self.language=language;self.pending=pending
        self.setObjectName('UserBubble' if user else 'AssistantBubble');self.setMaximumWidth(340);self.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum)
        layout=QVBoxLayout(self);layout.setContentsMargins(13,9,13,8);layout.setSpacing(5)
        self.label=QLabel();self.label.setWordWrap(True);self.label.setTextFormat(Qt.PlainText);self.label.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.TextSelectableByKeyboard);layout.addWidget(self.label)
        actions=QHBoxLayout();actions.setSpacing(4);language_label=QLabel(LANGUAGES[language][0]);language_label.setObjectName('BubbleLanguage');actions.addWidget(language_label);actions.addStretch()
        self.listen_button=QPushButton();self.copy_button=QPushButton()
        for button,icon,name in ((self.listen_button,'speaker','Écouter en '+LANGUAGES[language][0].lower()),(self.copy_button,'copy','Copier ce message')):
            button.setObjectName('BubbleAction');button.setIcon(chat_icon(icon));button.setIconSize(QSize(18,18));button.setFixedSize(30,28);button.setAccessibleName(name);button.setToolTip(name);actions.addWidget(button)
        layout.addLayout(actions);self.copy_button.clicked.connect(lambda:owner.copy_bubble(self));self.listen_button.clicked.connect(lambda:owner.listen_bubble(self));self.set_message(text,not pending)
    def set_message(self,text,ready=True):
        self.text=text;self.pending=not ready;self.label.setText(text);self.label.setLayoutDirection(Qt.RightToLeft if self.language=='ar' else Qt.LeftToRight)
        self.listen_button.setEnabled(ready);self.copy_button.setEnabled(ready)


class TraductorWindow(ApplicationWindow):
    def __init__(self):
        super().__init__('traductor');self.bubbles=[];self.job_id=None;self.translation_stop=threading.Event();self.current_request={};self.voice_generation=0;self.current_speaker=None;self.playing=None
        root=QWidget();root.setLayout(self.layout);self.setCentralWidget(root)
        self.setMinimumSize(380,440);self.resize(440,560);self.layout.setContentsMargins(10,10,10,10);self.layout.setSpacing(6);self.content.setSpacing(8)
        header=self.layout.itemAt(0).widget().layout();brand=header.itemAt(1).widget();brand.setText('Traductor');brand.setStyleSheet('font-size:13pt;font-weight:600;letter-spacing:0px;')
        for index in (2,3):header.itemAt(index).widget().setFixedSize(32,32)
        self.status.setText('Traduction locale prête.');self.status.setStyleSheet('font-size:9pt;color:#9CB2C0;')
        languages=QHBoxLayout();languages.setSpacing(6);self.content.addLayout(languages)
        self.source=ChoiceBox();self.destination=ChoiceBox()
        for combo,name,key,default in ((self.source,'Langue de l’utilisateur','source_language','fr'),(self.destination,'Langue de sortie','target_language','en')):
            for code,(caption,_,_) in LANGUAGES.items():combo.addItem(caption,code)
            value=self.preferences.get(key,default);combo.setCurrentIndex(max(0,combo.findData(value)));combo.setAccessibleName(name);combo.setToolTip(name)
        self.swap=QPushButton('⇄');self.swap.setFixedSize(30,34);self.swap.setAccessibleName('Inverser les langues');self.swap.setToolTip('Inverser les langues')
        for title,combo in (('De',self.source),('Vers',self.destination)):
            box=QVBoxLayout();box.setSpacing(3);label=QLabel(title);label.setObjectName('Muted');box.addWidget(label);box.addWidget(combo);languages.addLayout(box,1)
            if combo is self.source:languages.addWidget(self.swap,0,Qt.AlignBottom)
        self.source.currentIndexChanged.connect(lambda:self.remember('source_language',self.source.currentData()));self.destination.currentIndexChanged.connect(lambda:self.remember('target_language',self.destination.currentData()));self.swap.clicked.connect(self.swap_languages)
        self.conversation=QScrollArea();self.conversation.setWidgetResizable(True);self.conversation.setFrameShape(QFrame.NoFrame);self.conversation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.conversation.setAccessibleName('Discussion de traduction')
        chat=QWidget();self.flow=QVBoxLayout(chat);self.flow.setContentsMargins(0,6,3,6);self.flow.setSpacing(9);self.flow.setAlignment(Qt.AlignTop);self.conversation.setWidget(chat);self.content.addWidget(self.conversation,1)
        self.conversation.verticalScrollBar().rangeChanged.connect(lambda *_:QTimer.singleShot(0,self.scroll_latest))
        composer=QFrame();composer.setObjectName('Composer');entry=QHBoxLayout(composer);entry.setContentsMargins(10,8,8,8);entry.setSpacing(6)
        self.input=Composer();self.input.setObjectName('ComposerInput');self.input.setPlaceholderText('Votre message…');self.input.setAccessibleName('Message à traduire');self.input.setFixedHeight(58);self.input.submitted.connect(self.send_message);entry.addWidget(self.input,1)
        self.send_button=QPushButton();self.send_button.setObjectName('Send');self.send_button.setIcon(chat_icon('send'));self.send_button.setIconSize(QSize(23,23));self.send_button.setFixedSize(36,36);self.send_button.setAccessibleName('Envoyer le message');self.send_button.setToolTip('Envoyer · Entrée / nouvelle ligne · Maj+Entrée');self.send_button.clicked.connect(lambda:self.cancel_translation() if self.job_id else self.send_message());entry.addWidget(self.send_button,0,Qt.AlignBottom);self.content.addWidget(composer)
        self.setStyleSheet(self.styleSheet()+'''QWidget {background:transparent;font-family:'Segoe UI';font-size:10pt;color:#EAF0F5;} QMainWindow {background:#13191F;} QMainWindow>QWidget {background:#13191F;} QLabel {background:transparent;border:none;} QLabel#Muted,QLabel#BubbleLanguage {font-size:8pt;color:#9DB6C6;} QFrame#UserBubble {background:#204C65;border:none;border-radius:16px;} QFrame#AssistantBubble {background:#232C35;border:none;border-radius:16px;} QFrame#Composer {background:#1C252E;border:1px solid #384B5B;border-radius:18px;} QPlainTextEdit#ComposerInput {background:transparent;border:none;padding:2px;font-size:11pt;} QPushButton,QComboBox {min-height:0px;padding:5px 9px;background:#222E38;border:1px solid #344958;border-radius:8px;} QComboBox {min-height:23px;} QPushButton#BubbleAction {padding:0px;background:transparent;border:1px solid transparent;border-radius:7px;} QPushButton#BubbleAction:hover {background:#365365;} QPushButton#Send {padding:0px;background:#245B78;border-color:#3A8AB2;border-radius:10px;} QPushButton:focus,QComboBox:focus,QPlainTextEdit:focus {border:2px solid #7ABEE1;} QScrollArea {background:transparent;border:none;} QScrollBar:vertical {background:transparent;width:8px;} QScrollBar::handle:vertical {background:#3C4C58;border-radius:4px;min-height:25px;} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;}''')
        self.orb.doubleActivated.connect(self.activate);self.orb.setToolTip('Traductor · ouvrir la discussion de traduction')
    def swap_languages(self):
        source,target=self.source.currentData(),self.destination.currentData();self.source.setCurrentIndex(self.source.findData(target));self.destination.setCurrentIndex(self.destination.findData(source))
    def scroll_latest(self):bar=self.conversation.verticalScrollBar();bar.setValue(bar.maximum())
    def add_bubble(self,text,language,user=False,pending=False):
        bubble=Bubble(self,text,language,user,pending);row=QWidget();layout=QHBoxLayout(row);layout.setContentsMargins(0,0,0,0)
        if not user:layout.addStretch(1)
        layout.addWidget(bubble,8)
        if user:layout.addStretch(1)
        self.flow.addWidget(row);self.bubbles.append(bubble);return bubble
    def task(self,function,done,error,finished=None):
        job=Job(function);self.pending.add(job)
        job.signals.done.connect(lambda result:None if self.closing else done(result));job.signals.error.connect(lambda message:None if self.closing else error(message))
        def end():
            self.pending.discard(job)
            if not self.closing and finished:finished()
        job.signals.finished.connect(end);QThreadPool.globalInstance().start(job);return job
    def send_message(self):
        if self.job_id:return
        text=self.input.toPlainText().strip()
        if not text:return
        source,target=self.source.currentData(),self.destination.currentData();self.add_bubble(text,source,True);reply=self.add_bubble('Traduction…',target,pending=True);self.input.clear()
        identifier=uuid.uuid4().hex;self.job_id=identifier;self.translation_stop=threading.Event();stop=self.translation_stop;current={};self.current_request=current;self.current_reply=reply
        self.send_button.setIcon(chat_icon('stop'));self.send_button.setAccessibleName('Annuler la traduction');self.status.setText('Traduction en cours…');self.state('Traitement en cours')
        from shared.translation import translate
        def done(result):
            if self.job_id==identifier:reply.set_message(result);self.status.setText('Traduction prête.');self.state('Action réussie')
        def error(message):
            if self.job_id==identifier:reply.set_message('Traduction indisponible.',False);self.error(message)
        def finished():
            if self.job_id==identifier:self.job_id=None;self.reset_send()
        self.task(lambda:translate(text,source,target,identifier,stop,current),done,error,finished)
    def reset_send(self):self.send_button.setIcon(chat_icon('send'));self.send_button.setAccessibleName('Envoyer le message')
    def cancel_translation(self):
        if not self.job_id:return
        self.translation_stop.set();self.job_id=None;self.current_reply.set_message('Traduction annulée.',False);self.reset_send();self.status.setText('Traduction annulée.')
    def copy_bubble(self,bubble):
        if not bubble.pending:
            QApplication=__import__('PySide6.QtWidgets',fromlist=['QApplication']).QApplication
            QApplication.clipboard().setText(bubble.text);self.status.setText('Message copié.')
    def stop_voice(self):
        self.voice_generation+=1
        if self.current_speaker:self.current_speaker.cancel()
        if self.playing:self.playing.listen_button.setIcon(chat_icon('speaker'))
        self.playing=None
    def listen_bubble(self,bubble):
        if bubble.pending:return
        if self.playing is bubble:self.stop_voice();self.status.setText('Lecture arrêtée.');return
        self.stop_voice();generation=self.voice_generation;self.playing=bubble
        from shared.speech import Speaker
        from shared.translation import speak_language
        speaker=Speaker();self.current_speaker=speaker;bubble.listen_button.setIcon(chat_icon('stop'));self.status.setText('Lecture en '+LANGUAGES[bubble.language][0].lower()+'…')
        def finish():
            if generation==self.voice_generation:bubble.listen_button.setIcon(chat_icon('speaker'));self.playing=None
        def error(message):
            if generation==self.voice_generation:self.error(message)
        def done(played):
            if generation==self.voice_generation:self.status.setText('Lecture terminée.' if played else 'Lecture arrêtée.')
        self.task(lambda:speak_language(speaker,bubble.text,bubble.language),done,error,finish)
    def create_orb_menu(self):
        menu=super().create_orb_menu();menu.addSeparator();menu.addAction('Ouvrir un document',self.open_document);menu.addAction('Enregistrer la dernière traduction',self.save_translation);return menu
    def open_document(self):
        path,_=QFileDialog.getOpenFileName(self,'Ouvrir un document','','Documents (*.txt *.md *.docx *.pdf)')
        if path:
            from shared.documents import read_text
            self.task(lambda:read_text(path),lambda text:(self.activate(),self.input.setPlainText(text)),self.error)
    def save_translation(self):
        replies=[bubble for index,bubble in enumerate(self.bubbles) if index%2 and not bubble.pending]
        if not replies:return
        text=replies[-1].text;path,_=QFileDialog.getSaveFileName(self,'Enregistrer la traduction','','Texte (*.txt);;Word (*.docx)')
        if path:
            from shared.domain import atomic_text
            from shared.documents import save_docx
            try:save_docx(path,text) if path.lower().endswith('.docx') else atomic_text(path,text)
            except Exception as error:self.error(str(error))
    def cleanup(self):self.cancel_translation();self.stop_voice()
