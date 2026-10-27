"""Three compact learning tools, sharing the suite UI, OCR and language host."""
import math,threading,uuid
from html import escape
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QVariantAnimation,QRectF,Signal,QStringListModel
from PySide6.QtGui import QColor,QPainter,QPen,QFont,QLinearGradient,QKeySequence,QShortcut,QPixmap,QIcon
from PySide6.QtWidgets import (QApplication,QWidget,QFrame,QLabel,QLineEdit,QPushButton,QTextBrowser,QPlainTextEdit,QProgressBar,QHBoxLayout,QVBoxLayout,QGridLayout,QComboBox,QSlider,QScrollArea,QSizePolicy,QSizeGrip,QCompleter)
from shared.ui.choices import ChoiceBox
from shared.apps.base import ApplicationWindow
from shared.jobs import background
from shared.domain import app_data
from ergoai.learning import ask,messages,LEVELS

def action_icon(kind):
    pix=QPixmap(48,48);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setPen(QPen(QColor('#236D63'),3.5,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    if kind=='reset':
        p.drawArc(QRectF(10,10,28,28),45*16,295*16);p.drawLine(34,8,34,18);p.drawLine(34,18,24,18)
    else:
        for x,y,dx,dy in [(9,9,1,1),(39,9,-1,1),(9,39,1,-1),(39,39,-1,-1)]:p.drawLine(x,y,x+dx*10,y);p.drawLine(x,y,x,y+dy*10)
    p.end();return QIcon(pix)

class LearningWindow(ApplicationWindow):
    def __init__(self,key):
        super().__init__(key);self.cancel_event=threading.Event();self.generation=0;self.busy=False
        self.resize(680,660);self.setMinimumSize(480,460)
        self.status.setText('');self.status.hide()
        self.setStyleSheet(self.styleSheet()+'''QFrame#LearningCard {background:#FFFFFF;border:1px solid #D5E1E5;border-radius:18px;} QLineEdit {font-size:17pt;padding:12px;} QTextBrowser {background:#FFFFFF;border:1px solid #D5E1E5;border-radius:16px;padding:18px;font-size:12pt;} QPushButton#Small {min-height:22px;padding:4px 12px;}''')
        self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.setFixedHeight(4);self.progress.setTextVisible(False);self.progress.hide();self.content.addWidget(self.progress)
    def title(self,title,subtitle):
        h=QLabel(title);h.setStyleSheet('font-size:25pt;font-weight:600;');self.content.addWidget(h)
        sub=QLabel(subtitle);sub.setWordWrap(True);sub.setStyleSheet('color:#63758A;font-size:10pt;');self.content.addWidget(sub)
    def set_busy(self,value):
        self.busy=value;self.progress.setVisible(value)
        for widget in getattr(self,'actions',[]):widget.setEnabled(not value)
        if hasattr(self,'cancel_button'):self.cancel_button.setVisible(value)
    def start_task(self,work,done):
        self.cancel_event.set();self.cancel_event=threading.Event();event=self.cancel_event;self.generation+=1;token=self.generation;self.set_busy(True);self.status.hide();self.state('Traitement en cours')
        def success(result):
            if self.closing or token!=self.generation or event.is_set():return
            self.set_busy(False);self.state('Activée');done(result)
        job=background(self,lambda:work(event),success);job.signals.error.disconnect(self.error)
        def failed(error):
            if self.closing or token!=self.generation:return
            self.set_busy(False);self.error(error)
        job.signals.error.connect(failed)
    def cancel_task(self):
        self.cancel_event.set();self.generation+=1;self.set_busy(False);self.state('Activée')
    def error(self,text):
        if not self.closing:self.status.setText(str(text));self.status.show();self.state('Attention')
    def cleanup(self):
        self.cancel_event.set();self.generation+=1

class DictionaryWindow(LearningWindow):
    def __init__(self):
        super().__init__('dictionnator');self.resize(640,560)
        row=self.row();self.word=QLineEdit();self.word.setPlaceholderText('Rechercher un mot…');self.word.setMaxLength(100);self.word.setClearButtonEnabled(True);self.word.setAccessibleName('Mot à chercher');self.word.setFixedHeight(54);row.addWidget(self.word,1);self.search_button=self.button('Trouver',self.lookup,row);self.search_button.setFixedHeight(54);self.word.returnPressed.connect(self.lookup)
        self.completion_model=QStringListModel(self);self.completer=QCompleter(self.completion_model,self);self.completer.setCaseSensitivity(Qt.CaseInsensitive);self.completer.setMaxVisibleItems(8);self.word.setCompleter(self.completer);self.completer.popup().setStyleSheet('QListView {background:#FFFFFF;color:#21364D;border:1px solid #A8BCCF;border-radius:10px;padding:6px;outline:none;} QListView::item {padding:9px 12px;} QListView::item:selected {background:#E5EFF8;color:#173D62;}');self.completion_timer=QTimer(self);self.completion_timer.setSingleShot(True);self.completion_timer.setInterval(140);self.completion_timer.timeout.connect(self.complete_word);self.word.textEdited.connect(lambda text:self.completion_timer.start())
        self.result=QTextBrowser();self.result.setOpenExternalLinks(True);self.result.setPlainText('Écrivez un mot pour découvrir sa définition.');self.content.addWidget(self.result,1)
        self.suggestions=ChoiceBox();self.suggestions.setAccessibleName('Orthographes proposées');self.suggestions.hide();self.suggestions.activated.connect(self.choose_suggestion);self.content.addWidget(self.suggestions)
        row=self.row();self.recent=ChoiceBox();self.recent.setAccessibleName('Mots déjà consultés');row.addWidget(self.recent,1);self.copy_button=self.button('Copier',lambda:QApplication.clipboard().setText(self.result.toPlainText()),row);self.copy_button.setEnabled(False);self.cancel_button=self.button('Annuler',self.cancel_task,row);self.cancel_button.hide()
        self.history=[data['word'] for _,data in self.records.all('dictionary_history') if isinstance(data,dict) and isinstance(data.get('word'),str)][-100:];self.fill_recent();self.recent.activated.connect(self.from_recent);self.actions=[self.search_button,self.recent]
        note=QLabel('Wiktionnaire · données Kaikki · définitions locales sans IA');note.setStyleSheet('font-size:8pt;color:#65788B;');self.content.addWidget(note)
    def cleanup(self):
        self.completion_timer.stop();super().cleanup()
    def complete_word(self):
        from shared.dictionary import complete
        text=self.word.text()
        def done(words):
            if self.closing or self.word.text()!=text:return
            self.completion_model.setStringList(words);self.completer.setCompletionPrefix(text)
            if words and self.word.hasFocus():self.completer.complete()
        background(self,lambda:complete(text),done)
    def fill_recent(self):
        self.recent.clear();self.recent.addItem('Mots consultés',None)
        for word in list(dict.fromkeys(reversed(self.history))):self.recent.addItem(word,word)
    def from_recent(self,index):
        word=self.recent.itemData(index)
        if word:self.word.setText(word);self.lookup()
    def choose_suggestion(self,index):
        word=self.suggestions.itemData(index)
        if word:self.word.setText(word);self.lookup()
    def lookup(self):
        if self.busy:return
        word=self.word.text().strip()
        if not word:self.word.setFocus();return
        from shared.dictionary import lookup
        def done(result):
            self.result.setHtml(result['html']);self.copy_button.setEnabled(result['found']);self.suggestions.clear();self.suggestions.addItem('Vouliez-vous dire…',None)
            for item in result['suggestions']:self.suggestions.addItem(item,item)
            self.suggestions.setVisible(bool(result['suggestions']))
            if result['found']:
                self.history.append(result['word']);self.history=self.history[-100:];self.records.add('dictionary_history',dict(word=result['word']));self.fill_recent()
        self.start_task(lambda event:lookup(word),done)

class ExplainWindow(LearningWindow):
    def __init__(self):
        super().__init__('explicator');self.resize(680,640);self.overlay=None;self.capture_pending=False;self.hint=1;self.last_source=''
        row=self.row();capture_row=row;self.capture_button=self.button('Capturer une zone',self.capture,row);self.capture_button.setIcon(action_icon('capture'));self.level=ChoiceBox();self.level.addItems(LEVELS);self.level.setCurrentText(self.preferences.get('learning_level','Collège'));self.level.setAccessibleName('Niveau scolaire');row.addWidget(self.level);self.level.currentTextChanged.connect(lambda value:self.remember('learning_level',value))
        self.source=self.editor('Énoncé reconnu — vous pouvez le corriger ou coller votre texte ici.');self.source.setMaximumHeight(150);self.source.setAccessibleName('Énoncé à comprendre');self.source.textChanged.connect(self.source_changed)
        row=self.row();self.explain_button=self.button('Comprendre',self.explain,row);self.next_button=self.button('Un autre indice',self.next_hint,row);self.next_button.setEnabled(False);self.cancel_button=self.button('Annuler',self.cancel_task,row);self.cancel_button.hide()
        self.result=QTextBrowser();self.result.setPlainText('Votre piste de réflexion apparaîtra ici.');self.content.addWidget(self.result,2);self.actions=[self.capture_button,self.explain_button,self.level]
        from shared.ui.conversation import arrange_conversation
        arrange_conversation(self,self.source,self.result,self.explain_button,row,'Une piste pour avancer')
        self.content.removeItem(capture_row);self.content.insertLayout(0,capture_row)
        self.click_timer=QTimer(self);self.click_timer.setSingleShot(True);self.click_timer.setInterval(QApplication.doubleClickInterval());self.click_timer.timeout.connect(self.capture);self.orb.doubleActivated.connect(self.open_main_window);self.orb.setToolTip('Explicator · clic : capturer · double-clic : ouvrir')
    def activate(self,*_):self.click_timer.start()
    def open_main_window(self):
        self.click_timer.stop();ApplicationWindow.activate(self)
    def source_changed(self):
        self.hint=1;self.next_button.setEnabled(False)
        if self.busy:self.cancel_task()
    def explain(self):
        if self.busy:return
        text=self.source.toPlainText().strip() or (self.last_source if self.hint>1 else '');level=self.level.currentText();hint=self.hint
        try:messages('explain',text,level,hint)
        except ValueError as error:self.error(error);return
        self.chat.begin(text,regenerate=hint>1 and self.chat.current is not None);self.last_source=text;self.source.blockSignals(True);self.source.clear();self.source.blockSignals(False)
        self.next_button.setEnabled(False)
        def done(result):
            self.show_explanation(result['text']);self.next_button.setEnabled(hint<3);self.last_source=text
            if result.get('warning'):self.status.setText(result['warning']);self.status.show();self.state('Attention')
        self.start_task(lambda event:ask('explain',text,event,level,hint),done)
    def show_explanation(self,text):
        headings={"Ce qu'on cherche","Ce qu’on cherche",'Un indice','À toi'}
        self.result.setHtml(''.join('<h3 style="color:#995C1C">'+escape(line)+'</h3>' if line.strip().rstrip(':') in headings else '<p>'+escape(line)+'</p>' for line in text.splitlines() if line.strip()))
    def next_hint(self):
        if not self.busy and self.hint<3:self.hint+=1;self.explain()
    def capture(self):
        if self.capture_pending or self.busy:return
        self.click_timer.stop();self.capture_pending=True;self.return_orb=self.orb.isVisible();self.hide();self.orb.hide()
        def begin():
            if self.closing or not self.capture_pending:return
            try:
                from shared.apps.overlays import CaptureOverlay
                self.overlay=CaptureOverlay();self.overlay.captured.connect(self.captured);self.overlay.cancelled.connect(self.capture_cancelled);self.overlay.show();self.overlay.raise_();self.overlay.activateWindow()
            except Exception as error:self.capture_cancelled();self.error(error)
        QTimer.singleShot(250,begin)
    def restore_capture(self):
        self.capture_pending=False
        if self.overlay:self.overlay.close();self.overlay.deleteLater();self.overlay=None
        if self.return_orb and not self.closing:self.orb.show()
        if not self.closing:ApplicationWindow.activate(self)
    def capture_cancelled(self):self.restore_capture()
    def captured(self,image):
        self.restore_capture();path=app_data('explicator')/('capture-'+uuid.uuid4().hex+'.png')
        if image.isNull() or not image.save(str(path)):self.error('Capture vide. Réessayez.');return
        from shared.ocr import recognize
        def work(event):
            try:return recognize(path)
            finally:path.unlink(missing_ok=True)
        def done(text):
            if not text.strip():self.error('Aucun texte reconnu. Capturez une zone plus nette.');return
            self.source.setPlainText(text);self.hint=1;self.explain()
        self.start_task(work,done)
    def cleanup(self):
        super().cleanup();self.click_timer.stop();self.capture_pending=False
        if self.overlay:self.overlay.close();self.overlay.deleteLater();self.overlay=None

class FlipCard(QPushButton):
    flipped=Signal()
    def __init__(self,a,b,color,parent=None):
        super().__init__(parent);self.a=a;self.b=b;self.color=QColor(color);self.revealed=False;self.progress=0.;self.anim=QVariantAnimation(self);self.anim.setDuration(340);self.anim.valueChanged.connect(self.animate);self.anim.finished.connect(self.finish);self.clicked.connect(self.flip);self.setCursor(Qt.PointingHandCursor);self.setMinimumSize(42,36);self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);self.setAccessibleName(f'{a} fois {b}');self.setStyleSheet('QPushButton {padding:0;min-height:0;border:0;background:transparent;}')
    def flip(self):
        if self.anim.state()==QVariantAnimation.Running:return
        if not getattr(self,'animations',True):self.revealed=not self.revealed;self.finish();return
        self.anim.setStartValue(0.);self.anim.setEndValue(1.);self.anim.start()
    def animate(self,value):self.progress=float(value);self.update()
    def finish(self):
        if self.progress:self.revealed=not self.revealed
        self.progress=0.;self.setAccessibleName(f'{self.a} fois {self.b}'+(f' égale {self.a*self.b}' if self.revealed else ' — retourner'));self.update();self.flipped.emit()
    def reset(self):self.anim.stop();self.revealed=False;self.progress=0.;self.setAccessibleName(f'{self.a} fois {self.b} — retourner');self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);compact=getattr(self,'compact',False);r=QRectF(self.rect()).adjusted(1 if compact else 3,1 if compact else 3,-1 if compact else -3,-3 if compact else -6);t=self.progress;back=self.revealed ^ (t>=.5);scale=max(.035,abs(math.cos(math.pi*t)));p.translate(r.center());p.scale(scale,1);p.translate(-r.center());shadow=r.translated(0,3);p.setPen(Qt.NoPen);p.setBrush(QColor(20,70,68,25));p.drawRoundedRect(shadow,7 if compact else 12,7 if compact else 12)
        g=QLinearGradient(r.topLeft(),r.bottomRight());g.setColorAt(0,self.color.lighter(115) if back else QColor('#FFFFFF'));g.setColorAt(1,self.color.darker(110) if back else QColor('#EBF5F3'));p.setBrush(g);p.setPen(QPen(self.color.lighter(145),1));p.drawRoundedRect(r,7 if compact else 12,7 if compact else 12)
        p.setPen(QColor('#FFFFFF') if back else self.color.darker(150));f=QFont('Segoe UI');f.setPixelSize(max(11,min(16,int(r.height()*.48),int(r.width()*.28))) if compact else max(14,min(42,int(r.height()*.34),int(r.width()*.22))));f.setWeight(QFont.DemiBold);p.setFont(f);p.drawText(r,Qt.AlignCenter,str(self.a*self.b) if back else (f'{self.a}×{self.b}' if compact else f'{self.a} × {self.b}'))
        if self.hasFocus():p.setPen(QPen(self.color.darker(150),1.2,Qt.SolidLine));p.setBrush(Qt.NoBrush);p.drawRoundedRect(r.adjusted(2,2,-2,-2),7,7)
        p.end()

class TablesBoard(QWidget):
    def __init__(self,owner):
        super().__init__();self.owner=owner;self.cards=[];self.by_product={};layout=QVBoxLayout(self);layout.setContentsMargins(4,0,4,2);layout.setSpacing(6)
        row=QHBoxLayout();self.heading=QLabel('Toutes les tables · 1 à 12');self.heading.setStyleSheet('font-size:16pt;font-weight:600;color:#155F5B;');row.addWidget(self.heading,1);reset=QPushButton();reset.setIcon(action_icon('reset'));reset.setToolTip('Remettre tous les calculs');reset.setAccessibleName('Réinitialiser les cartes');reset.clicked.connect(self.reset);reset.setFixedSize(30,30);reset.setStyleSheet('QPushButton {min-height:0;padding:2px;border-radius:8px;}');row.addWidget(reset);layout.addLayout(row)
        self.grid=QGridLayout();self.grid.setHorizontalSpacing(3);self.grid.setVerticalSpacing(2);layout.addLayout(self.grid,1)
        def header(text,r,c):
            label=QLabel(text);label.setAlignment(Qt.AlignCenter);label.setStyleSheet('font-size:10pt;font-weight:600;color:#246D67;background:transparent;');self.grid.addWidget(label,r,c)
        header('×',0,0);self.grid.setColumnMinimumWidth(0,24);self.grid.setRowMinimumHeight(0,20)
        for n in range(1,13):header(str(n),0,n);header(str(n),n,0);self.grid.setColumnStretch(n,1);self.grid.setRowStretch(n,1)
        for a in range(1,13):
            for b in range(1,13):
                card=FlipCard(a,b,'#218C83');card.compact=True;card.setMinimumSize(40,25);card.animations=self.owner.preferences.get('animations',True);card.setToolTip('');self.grid.addWidget(card,a,b);self.cards.append(card);self.by_product[a,b]=card
    def card_for(self,a,b):return self.by_product[a,b]
    def reset(self):
        for card in self.cards:card.reset()

class TablesWidget(QWidget):
    def __init__(self,owner):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);self.owner=owner;self.setAttribute(Qt.WA_TranslucentBackground);self.setWindowTitle('Tablinator · Toutes les tables');self.setMinimumSize(650,450);self.resize(720,520)
        self.setStyleSheet(owner.styleSheet()+"QWidget {background:transparent;} QFrame#TablesGlass {background:transparent;border:1px solid #9BCBC2;border-radius:18px;} QPushButton {color:#185F58;background:#FFFFFF;border:1px solid #BEDBD4;border-radius:8px;padding:3px;min-height:20px;}")
        layout=QVBoxLayout(self);layout.setContentsMargins(8,8,8,8);self.panel=QFrame();self.panel.setObjectName('TablesGlass');box=QVBoxLayout(self.panel);box.setContentsMargins(12,8,12,5);box.setSpacing(3);header=QHBoxLayout();brand=QLabel('TABLINATOR');brand.setStyleSheet('font-size:9pt;font-weight:600;letter-spacing:1px;color:#256E67;');header.addWidget(brand);header.addStretch();header.addWidget(QLabel('Fond'));self.opacity=QSlider(Qt.Horizontal);self.opacity.setRange(0,100);self.opacity.setValue(int(owner.preferences.get('tables_opacity',85)));self.opacity.setFixedWidth(90);self.opacity.setAccessibleName('Opacité du fond');self.opacity.valueChanged.connect(self.change_opacity);header.addWidget(self.opacity);close=QPushButton('×');close.setFixedSize(28,28);close.setStyleSheet('QPushButton {min-height:0;padding:0;}');close.setAccessibleName('Fermer les tables');close.clicked.connect(self.hide);header.addWidget(close);box.addLayout(header);self.board=TablesBoard(owner);box.addWidget(self.board,1);grip=QSizeGrip(self);grip.setFixedSize(12,9);box.addWidget(grip,0,Qt.AlignRight);layout.addWidget(self.panel);QShortcut(QKeySequence('Escape'),self,activated=self.hide)
    def change_opacity(self,value):self.owner.remember('tables_opacity',value);self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen);p.setBrush(QColor(20,60,55,20));r=QRectF(self.panel.geometry());p.drawRoundedRect(r.translated(0,3),18,18);p.setBrush(QColor(244,251,249,round(self.opacity.value()*2.55)));p.drawRoundedRect(r,18,18);p.end()
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton and event.position().y()<48 and self.windowHandle():self.windowHandle().startSystemMove()
        elif not self.panel.geometry().contains(event.position().toPoint()):self.hide()
        else:super().mousePressEvent(event)
    def reveal(self):
        screen=self.owner.orb.screen() or QApplication.primaryScreen();area=screen.availableGeometry();self.resize(min(720,area.width()-24),min(520,area.height()-24));self.move(area.center().x()-self.width()//2,area.center().y()-self.height()//2);self.showNormal();self.raise_();self.activateWindow()

class TablesWindow(ApplicationWindow):
    def __init__(self):
        super().__init__('tablinator');self.setMinimumSize(680,500);self.resize(740,560);self.status.hide();self.layout.setContentsMargins(12,10,12,8);self.layout.setSpacing(5);self.board=TablesBoard(self);self.content.addWidget(self.board,1);button=self.button('Widget compact',self.toggle_widget);button.setObjectName('CompactAction');button.setMaximumHeight(32);button.setMinimumHeight(26);self.widget=None;self.click_timer=QTimer(self);self.click_timer.setSingleShot(True);self.click_timer.setInterval(QApplication.doubleClickInterval());self.click_timer.timeout.connect(self.toggle_widget);self.orb.doubleActivated.connect(self.open_main_window);self.orb.setToolTip('Tablinator · clic : les tables · double-clic : ouvrir')
    def activate(self,*_):self.click_timer.start()
    def open_main_window(self):
        self.click_timer.stop()
        self.hide_orb(False)
        if self.widget:self.widget.hide()
        ApplicationWindow.activate(self)
    def toggle_widget(self):
        self.hide_orb(False)
        if self.widget is None:self.widget=TablesWidget(self)
        if self.widget.isVisible():self.widget.hide()
        else:self.hide();self.widget.reveal()
    def cleanup(self):
        self.click_timer.stop()
        if self.widget:self.widget.hide();self.widget.deleteLater();self.widget=None
