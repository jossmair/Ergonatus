"""Memorinator: an opaque, local, editable wall of movable sticky notes."""
import math
from pathlib import Path
import sqlite3
from PySide6.QtCore import Qt,QTimer,QPoint,QSize,QRect,QDateTime,QTimeZone,QLocale,Signal
from PySide6.QtGui import (QColor,QPainter,QPen,QIcon,QPixmap,QLinearGradient,QCursor,
                          QTextCharFormat,QBrush,QShortcut,QKeySequence)
from PySide6.QtWidgets import (QWidget,QFrame,QLabel,QTextEdit,QPushButton,QVBoxLayout,
    QHBoxLayout,QScrollArea,QGraphicsDropShadowEffect,QApplication,QDialog,QListWidget,QDialogButtonBox,QSlider,QStyle,QStyleOptionSlider)
from shared.apps.base import ApplicationWindow


def trash_icon(colour='#243A35'):
    pix=QPixmap(48,48);pix.fill(Qt.transparent)
    p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.scale(2,2)
    p.setPen(QPen(QColor(colour),1.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    p.drawLine(5,7,19,7);p.drawLine(9,4,15,4);p.drawLine(9,4,8,7);p.drawLine(15,4,16,7)
    p.drawLine(7,9,8,20);p.drawLine(8,20,16,20);p.drawLine(16,20,17,9)
    p.drawLine(10,10,10,17);p.drawLine(14,10,14,17);p.end();return QIcon(pix)


def format_icon(kind):
    pix=QPixmap(64,64);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.scale(2,2)
    p.setPen(QPen(QColor('#1E3149'),2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    if kind=='highlight':
        p.drawLine(10,21,20,7);p.drawLine(20,7,26,12);p.drawLine(26,12,16,25);p.drawLine(16,25,10,21)
        p.drawLine(10,21,8,26);p.drawLine(8,26,13,27);p.drawLine(13,27,16,25)
        p.setPen(QPen(QColor('#F4D979'),3,Qt.SolidLine,Qt.RoundCap));p.drawLine(6,29,26,29)
    else:
        p.drawLine(9,8,24,8);p.drawLine(9,8,9,12);p.drawLine(24,8,24,12);p.drawLine(16,8,16,27);p.drawLine(12,27,20,27)
        p.setPen(QPen(QColor('#25806C'),2.4,Qt.SolidLine,Qt.RoundCap));p.drawLine(5,18,27,18)
    p.end();return QIcon(pix)


def note_colour(index,used):
    palette=['#FFE5A0','#BCEBD5','#C8DEFF','#FFCDC3','#DED0FA','#F6C8E1','#C4ECEC','#F3D3A6']
    for offset in range(10000):
        value=index+offset
        colour=palette[value] if value<len(palette) else QColor.fromHslF((value*.38196601125)%1,.57,.80+(value%7)*.008).name().upper()
        if colour not in used:return colour
    raise ValueError('Trop de couleurs utilisées.')


class DimBackdrop(QWidget):
    def __init__(self,opacity):
        super().__init__();self.opacity=opacity;self.setAutoFillBackground(False);self.setAttribute(Qt.WA_TranslucentBackground)
    def paintEvent(self,event):
        p=QPainter(self);p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(),QColor(240,245,242,round(255*self.opacity/100)))


class OpacitySlider(QSlider):
    def paintEvent(self,event):
        option=QStyleOptionSlider();self.initStyleOption(option)
        handle=self.style().subControlRect(QStyle.CC_Slider,option,QStyle.SC_SliderHandle,self)
        center=handle.center();edge=max(10,handle.width()//2);y=self.height()//2
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('#3D5949'),4,Qt.SolidLine,Qt.RoundCap));p.drawLine(edge,y,self.width()-edge,y)
        p.setPen(QPen(QColor('#BCE6BF'),4,Qt.SolidLine,Qt.RoundCap));p.drawLine(edge,y,center.x(),y)
        p.setPen(Qt.NoPen);p.setBrush(QColor('#D9F0CE'));p.drawEllipse(QPoint(center.x(),y),7,7)
        if self.hasFocus():p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor('#82C5A0'),1.5));p.drawEllipse(QPoint(center.x(),y),11,11)


class WallCanvas(QWidget):
    def __init__(self,wall):
        super().__init__();self.wall=wall;self.setMinimumSize(320,240);self.resize(320,240);self.setAccessibleName('Mur de post-it')
    def paintEvent(self,event):
        p=QPainter(self)
        p.setPen(QPen(QColor(181,224,205,22),1.2))
        rect=event.rect()
        for x in range(rect.left()//28*28,rect.right()+1,28):
            for y in range(rect.top()//28*28,rect.bottom()+1,28):p.drawPoint(x,y)
    def accommodate(self,note):
        self.resize(max(self.width(),note.x()+note.width()+60),max(self.height(),note.y()+note.height()+60))


class NoteEditor(QTextEdit):
    activated=Signal()
    def focusInEvent(self,event):super().focusInEvent(event);self.activated.emit()
    def wheelEvent(self,event):event.ignore()


class DragBar(QWidget):
    def __init__(self,note):
        super().__init__(note);self.note=note;self.offset=None;self.setCursor(Qt.OpenHandCursor);self.setFocusPolicy(Qt.StrongFocus);self.setAccessibleName('Déplacer ce post-it avec les flèches')
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            self.offset=event.globalPosition().toPoint()-self.note.mapToGlobal(QPoint());self.note.raise_();self.setCursor(Qt.ClosedHandCursor);event.accept()
    def mouseMoveEvent(self,event):
        if self.offset is not None and event.buttons()&Qt.LeftButton:
            point=self.note.parentWidget().mapFromGlobal(event.globalPosition().toPoint()-self.offset)
            self.note.move(max(12,point.x()),max(12,point.y()));self.note.wall.canvas.accommodate(self.note)
    def mouseReleaseEvent(self,event):
        if self.offset is not None:self.offset=None;self.setCursor(Qt.OpenHandCursor);self.note.save()
    def keyPressEvent(self,event):
        delta={Qt.Key_Left:(-16,0),Qt.Key_Right:(16,0),Qt.Key_Up:(0,-16),Qt.Key_Down:(0,16)}.get(event.key())
        if delta:
            self.note.move(max(12,self.note.x()+delta[0]),max(12,self.note.y()+delta[1]));self.note.wall.canvas.accommodate(self.note);self.note.save();event.accept()
        else:super().keyPressEvent(event)
    def paintEvent(self,event):
        super().paintEvent(event)
        if self.hasFocus():
            painter=QPainter(self);painter.setPen(QPen(QColor('#325C50'),1,Qt.DashLine));painter.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),5,5)


class StickyNote(QFrame):
    def __init__(self,wall,key,data):
        super().__init__(wall.canvas);self.wall=wall;self.key=key;self.data=dict(data);self.setObjectName('StickyNote')
        self.setAccessibleName('Post-it du '+self.date_text());self.setFixedWidth(280)
        colour=QColor(data['colour']);bottom=colour.darker(106).name()
        self.setStyleSheet(f'''QFrame#StickyNote {{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {colour.name()},stop:1 {bottom});border:1px solid {colour.lighter(110).name()};border-radius:15px;}}
            QLabel {{background:transparent;color:#35473F;font-size:9pt;}}
            QTextEdit {{background:transparent;color:#172C24;border:none;padding:0px;font-family:'Segoe UI';font-size:13pt;selection-background-color:#325C50;selection-color:white;}}
            QPushButton {{min-height:0px;background:transparent;border:0px;border-radius:7px;padding:3px;}}
            QPushButton:hover {{background:rgba(20,50,40,22);}} QPushButton:focus {{border:2px solid #325C50;}}
        ''')
        shadow=QGraphicsDropShadowEffect(self);shadow.setBlurRadius(25);shadow.setOffset(0,6);shadow.setColor(QColor(0,0,0,65));self.setGraphicsEffect(shadow)
        layout=QVBoxLayout(self);layout.setContentsMargins(16,10,16,15);layout.setSpacing(8)
        self.drag_bar=DragBar(self);header=QHBoxLayout(self.drag_bar);header.setContentsMargins(0,0,0,0);header.setSpacing(4)
        date=QLabel(self.date_text());date.setAttribute(Qt.WA_TransparentForMouseEvents);header.addWidget(date,1)
        grip=QLabel('⠿');grip.setAttribute(Qt.WA_TransparentForMouseEvents);grip.setStyleSheet('font-size:16pt;color:#53685C;');header.addWidget(grip)
        self.delete_button=QPushButton();self.delete_button.setIcon(trash_icon());self.delete_button.setIconSize(QSize(19,19));self.delete_button.setFixedSize(30,30);self.delete_button.setAccessibleName('Mettre ce post-it à la corbeille');self.delete_button.setToolTip('Mettre à la corbeille');self.delete_button.clicked.connect(lambda:wall.trash_note(self));header.addWidget(self.delete_button);layout.addWidget(self.drag_bar)
        self.editor=NoteEditor();self.editor.setAcceptRichText(False);self.editor.setFrameShape(QFrame.NoFrame);self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.editor.document().setDocumentMargin(0);self.editor.setPlaceholderText('Une idée, un rappel…');self.editor.setAccessibleName('Texte du post-it');self.editor.setHtml(data.get('html',''));layout.addWidget(self.editor)
        self.save_timer=QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.setInterval(350);self.save_timer.timeout.connect(self.save)
        self.editor.textChanged.connect(self.changed);self.editor.activated.connect(lambda:wall.select_note(self));self.editor.selectionChanged.connect(lambda:wall.select_note(self))
        self.editor.document().documentLayout().documentSizeChanged.connect(lambda *_:QTimer.singleShot(0,self.fit_text))
        self.move(max(12,int(data.get('x',24))),max(12,int(data.get('y',24))));self.resize(280,210);self.show();QTimer.singleShot(0,self.fit_text)
    def date_text(self):
        date=QDateTime.fromString(self.data['created'],Qt.ISODate).toTimeZone(QTimeZone(b'Europe/Paris'))
        return QLocale(QLocale.French).toString(date,'dd MMM yyyy · HH:mm')
    def changed(self):self.save_timer.start();QTimer.singleShot(0,self.fit_text)
    def fit_text(self):
        if self.wall.closing:return
        height=max(210,math.ceil(self.editor.document().size().height())+75)
        self.editor.setFixedHeight(max(130,height-75))
        if self.height()!=height:self.resize(280,height)
        self.wall.canvas.accommodate(self)
    def save(self):
        self.save_timer.stop()
        if self.wall.closing:return
        self.data.update(html=self.editor.toHtml(),x=self.x(),y=self.y());self.wall.records.update(self.key,'sticky_note',self.data)


class MemorinatorWindow(ApplicationWindow):
    def __init__(self):
        super().__init__('memorinator');self.notes={};self.active_note=None;self.trashed=[]
        self.setAttribute(Qt.WA_TranslucentBackground)
        opacity=self.preferences.get('wall_opacity',75)
        if type(opacity) is not int or not 25<=opacity<=100:opacity=75
        self.backdrop=DimBackdrop(opacity);self.backdrop.setLayout(self.layout);self.setCentralWidget(self.backdrop)
        # Preserve revision cards as an archive; the previous interface is removed.
        archive=self.records.path.parent/'archive-revisions-v1.sqlite3'
        if self.records.all('card') and not archive.exists():
            destination=sqlite3.connect(archive)
            try:self.records.db.backup(destination)
            finally:destination.close()
        self.layout.setContentsMargins(18,12,64,12);self.layout.setSpacing(10)
        self.layout.itemAt(0).widget().hide();self.status.hide();self.layout.itemAt(self.layout.count()-1).widget().hide()
        self.wall_toolbar=QFrame();self.wall_toolbar.setObjectName('WallToolbar');toolbar_layout=QVBoxLayout(self.wall_toolbar);toolbar_layout.setContentsMargins(16,12,16,12);toolbar_layout.setSpacing(10);self.content.addWidget(self.wall_toolbar)
        self.wall_toolbar.setStyleSheet('QFrame#WallToolbar {background:rgba(16,36,29,247);border:1px solid #3D5C4D;border-radius:20px;} QPushButton {background:#203F32;border:1px solid #375947;border-radius:10px;color:#1E3149;padding:6px 13px;} QPushButton:hover {background:#305640;border-color:#608B70;} QPushButton:checked {background:#46694D;border-color:#BDD8A2;} QPushButton:disabled {background:transparent;border-color:#2A4738;color:#8EA899;} QPushButton:focus {border:2px solid #C2EBCF;}')
        bar=QHBoxLayout();bar.setSpacing(8);toolbar_layout.addLayout(bar)
        self.add_button=QPushButton('＋  Nouvelle note');self.add_button.setFixedSize(172,44);self.add_button.setAccessibleName('Ajouter un post-it');self.add_button.setToolTip('');bar.addWidget(self.add_button)
        brand=QLabel('Memorinator');brand.setStyleSheet('font-size:17pt;font-weight:600;letter-spacing:0px;color:#EDF7EE;');bar.addWidget(brand);bar.addStretch()
        tools=bar
        self.highlight_button=QPushButton();self.strike_button=QPushButton()
        for button,kind,label in ((self.highlight_button,'highlight','Surligner la sélection'),(self.strike_button,'strike','Barrer la sélection')):
            button.setIcon(format_icon(kind));button.setIconSize(QSize(25,25));button.setAccessibleName(label);button.setToolTip(label);button.setFocusPolicy(Qt.TabFocus);button.setCheckable(True);button.setEnabled(False);button.setFixedSize(44,42);tools.addWidget(button)
        self.opacity_panel=QFrame();self.opacity_panel.setObjectName('OpacityPanel');self.opacity_panel.setStyleSheet('QFrame#OpacityPanel {background:#1B352B;border:1px solid #345343;border-radius:12px;} QLabel {color:#C5D8C9;font-size:10pt;} QSlider {background:transparent;min-height:22px;} QSlider::groove:horizontal {height:4px;border:none;background:#3B5748;border-radius:2px;} QSlider::sub-page:horizontal {background:#BCE6BF;border-radius:2px;} QSlider::handle:horizontal {width:14px;height:14px;margin:-5px 0;background:#D6F0CF;border:2px solid #EAF8E4;border-radius:8px;} QSlider:focus::handle:horizontal {border:2px solid #67C9A4;}')
        self.opacity_panel.setMaximumWidth(260)
        opacity_row=QHBoxLayout(self.opacity_panel);opacity_row.setContentsMargins(12,3,12,3);opacity_row.setSpacing(10);fond_label=QLabel('Fond');fond_label.setFixedWidth(32);opacity_row.addWidget(fond_label)
        self.opacity_slider=OpacitySlider(Qt.Horizontal);self.opacity_slider.setRange(25,100);self.opacity_slider.setValue(opacity);self.opacity_slider.setMinimumWidth(80);self.opacity_slider.setMaximumWidth(150);self.opacity_slider.setAccessibleName('Opacité du fond');self.opacity_slider.setToolTip('Régler la visibilité des applications derrière le mur');opacity_row.addWidget(self.opacity_slider,1)
        self.opacity_label=QLabel(str(opacity)+' %');self.opacity_label.setMinimumWidth(38);opacity_row.addWidget(self.opacity_label);self.opacity_panel.setFixedHeight(42);tools.addWidget(self.opacity_panel)
        self.trash_button=QPushButton();self.trash_button.setIcon(trash_icon('#C7E3D5'));self.trash_button.setIconSize(QSize(23,23));self.trash_button.setFixedSize(44,42);self.trash_button.setAccessibleName('Ouvrir la corbeille');tools.addWidget(self.trash_button)
        for button in (self.highlight_button,self.strike_button,self.trash_button):button.setStyleSheet('QPushButton {padding:0px;}')
        self.close_button=QPushButton('×');self.close_button.setFixedSize(42,38);self.close_button.setAccessibleName('Fermer le mur');bar.addWidget(self.close_button)
        self.setStyleSheet(self.styleSheet()+'''QWidget,QMainWindow {background:transparent;} QPushButton {min-height:0px;padding:7px 13px;background:#24473B;border:1px solid #456C59;border-radius:11px;font-size:11pt;color:#EDF9F2;} QPushButton:hover {background:#315E4B;} QPushButton:focus {border:2px solid #BCEBD5;} QPushButton:checked {background:#41674D;border-color:#BCEBD5;} QScrollArea {border:none;background:transparent;}''')
        self.add_button.setStyleSheet('QPushButton {font-size:12pt;font-weight:600;background:#DCF4E8;color:#174E3C;border:1px solid #6CB798;border-radius:13px;padding:4px 12px;} QPushButton:hover {background:#C0E8D6;}')
        self.close_button.setStyleSheet('QPushButton {font-size:22pt;background:transparent;border:1px solid #345343;border-radius:19px;padding:0px;color:#C0D9C9;} QPushButton:hover {background:#305640;color:white;} QPushButton:focus {border:2px solid #C2EBCF;}')
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(False);self.scroll.setAccessibleName('Parcourir le mur');self.scroll.viewport().setAutoFillBackground(False);self.canvas=WallCanvas(self);self.scroll.setWidget(self.canvas);self.content.addWidget(self.scroll,1)
        self.empty=QLabel('Vos idées ont leur place ici.\n\nCliquez sur + pour votre premier post-it.',self.canvas);self.empty.setStyleSheet('color:#B6CFC1;font-size:19pt;background:transparent;');self.empty.setAlignment(Qt.AlignCenter);self.empty.setGeometry(150,150,600,180)
        self.undo_button=QPushButton('↶ Annuler la suppression');self.undo_button.hide();self.content.addWidget(self.undo_button)
        for key,data in self.records.all('sticky_note'):
            if data.get('trashed'):self.trashed.append((key,data))
            else:self.notes[key]=StickyNote(self,key,data)
        self.refresh_empty();self.add_button.clicked.connect(self.add_note);self.close_button.clicked.connect(self.hide);self.highlight_button.clicked.connect(lambda:self.format_selection('highlight'));self.strike_button.clicked.connect(lambda:self.format_selection('strike'));self.trash_button.clicked.connect(self.open_trash);self.undo_button.clicked.connect(self.restore_last)
        self.opacity_slider.valueChanged.connect(self.set_opacity)
        self.orb.doubleActivated.connect(self.open_wall)
        self.orb.setAccessibleDescription('Afficher ou masquer le mur de post-it.');self.orb.setToolTip('Memorinator · afficher le mur de post-it')
        self.shortcuts=[]
        for sequence,callback in [('Escape',self.hide),('Ctrl+N',self.add_note),('Ctrl+Shift+H',lambda:self.format_selection('highlight')),('Ctrl+5',lambda:self.format_selection('strike'))]:
            shortcut=QShortcut(QKeySequence(sequence),self);shortcut.activated.connect(callback);self.shortcuts.append(shortcut)
    def show(self):self.open_wall()
    def showNormal(self):self.open_wall()
    def open_wall(self,*_):
        screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        self.setGeometry(screen.geometry());self.showFullScreen();self.raise_();self.activateWindow();self.ensure_canvas()
    def activate(self,*_):
        if self.isVisible():self.hide()
        else:self.open_wall()
    def set_opacity(self,value):
        self.backdrop.opacity=value;self.backdrop.update();self.opacity_label.setText(str(value)+' %');self.remember('wall_opacity',value)
    def ensure_canvas(self):
        size=self.scroll.viewport().size();self.canvas.resize(max(self.canvas.width(),size.width()),max(self.canvas.height(),size.height()))
    def resizeEvent(self,event):
        super().resizeEvent(event);self.clearMask()
        if hasattr(self,'canvas'):self.ensure_canvas()
    def refresh_empty(self):
        self.empty.setVisible(not self.notes);self.trash_button.setToolTip('Corbeille'+(f' · {len(self.trashed)} post-it' if self.trashed else ' vide'));self.trash_button.setEnabled(bool(self.trashed))
    def add_note(self):
        index=int(self.preferences.get('sticky_colour_index',0));colour=note_colour(index,{n.data['colour'] for n in self.notes.values()});self.remember('sticky_colour_index',index+1)
        columns=max(1,(self.scroll.viewport().width()-40)//310)
        for offset in range(10000):
            x=self.scroll.horizontalScrollBar().value()+24+(offset%columns)*306;y=self.scroll.verticalScrollBar().value()+24+(offset//columns)*234
            area=QRect(x,y,280,210)
            if not any(area.intersects(note.geometry().adjusted(-8,-8,8,8)) for note in self.notes.values()):break
        data=dict(created=QDateTime.currentDateTimeUtc().toString(Qt.ISODate),colour=colour,x=x,y=y,html='',trashed=False)
        key=self.records.add('sticky_note',data);note=StickyNote(self,key,data);self.notes[key]=note;self.refresh_empty();self.scroll.ensureWidgetVisible(note);self.select_note(note);note.editor.setFocus();return note
    def select_note(self,note):
        self.active_note=note;cursor=note.editor.textCursor()
        for button in (self.highlight_button,self.strike_button):button.setEnabled(cursor.hasSelection())
        self.strike_button.setChecked(cursor.charFormat().fontStrikeOut());self.highlight_button.setChecked(cursor.charFormat().background().style()!=Qt.NoBrush)
    def format_selection(self,kind):
        note=self.active_note
        if not note or note.key not in self.notes:return
        cursor=note.editor.textCursor()
        if not cursor.hasSelection():note.editor.setFocus();return
        fmt=QTextCharFormat()
        if kind=='strike':fmt.setFontStrikeOut(not cursor.charFormat().fontStrikeOut())
        else:fmt.setBackground(QBrush(Qt.NoBrush) if cursor.charFormat().background().style()!=Qt.NoBrush else QBrush(QColor('#FFF36A')))
        cursor.mergeCharFormat(fmt);note.editor.setTextCursor(cursor);note.save();note.editor.setFocus();self.select_note(note)
    def trash_note(self,note):
        note.save();note.data['trashed']=True;self.records.update(note.key,'sticky_note',note.data);self.trashed.append((note.key,dict(note.data)));self.notes.pop(note.key);note.hide();note.deleteLater()
        if self.active_note is note:
            self.active_note=None
            for button in (self.highlight_button,self.strike_button):button.setEnabled(False);button.setChecked(False)
        self.undo_button.show();self.refresh_empty()
    def restore_note(self,key):
        for index,(item,data) in enumerate(self.trashed):
            if item==key:
                self.trashed.pop(index);data=dict(data,trashed=False);self.records.update(key,'sticky_note',data);self.notes[key]=StickyNote(self,key,data);self.refresh_empty();self.undo_button.setVisible(bool(self.trashed));return
    def restore_last(self):
        if self.trashed:self.restore_note(self.trashed[-1][0])
    def open_trash(self):
        dialog=QDialog(self);dialog.setWindowTitle('Corbeille');dialog.resize(440,340);layout=QVBoxLayout(dialog);listing=QListWidget();layout.addWidget(listing)
        keys=[]
        for key,data in reversed(self.trashed):
            from PySide6.QtGui import QTextDocument
            document=QTextDocument();document.setHtml(data['html']);listing.addItem(document.toPlainText()[:80] or 'Post-it vide');keys.append(key)
        buttons=QDialogButtonBox(QDialogButtonBox.Close);restore=buttons.addButton('Restaurer',QDialogButtonBox.ActionRole);restore.setEnabled(bool(keys));layout.addWidget(buttons);buttons.rejected.connect(dialog.reject)
        def recover():
            row=listing.currentRow()
            if row>=0:self.restore_note(keys[row]);dialog.accept()
        restore.clicked.connect(recover)
        if keys:listing.setCurrentRow(0)
        dialog.exec()
    def hideEvent(self,event):
        if hasattr(self,'notes'):
            for note in self.notes.values():note.save()
        super().hideEvent(event)
    def cleanup(self):
        for note in self.notes.values():
            note.save_timer.stop();note.data.update(html=note.editor.toHtml(),x=note.x(),y=note.y());self.records.update(note.key,'sticky_note',note.data)
