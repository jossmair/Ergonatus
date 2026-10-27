"""Temporator: mouse-first settings and an independent floating timer."""
import math
from PySide6.QtCore import Qt,QTimer,QRectF,QPointF,QSize
from PySide6.QtGui import QPainter,QPen,QColor,QFont,QPixmap,QIcon,QPainterPath
from PySide6.QtWidgets import (QWidget,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame,QCheckBox,QApplication,QMainWindow,QMenu,QSlider,QStyle,QStyleOptionSlider)
from shared.apps.base import ApplicationWindow
from shared.ui.components import ErgoWindow
from shared.domain import app_data
from shared.countdown import Countdown,time_text
from shared.catalog import suite_root

STYLE="""
QWidget {color:#FAEFEC;font-family:'Segoe UI';font-size:10pt;}
QLabel {background:transparent;border:none;}
QPushButton {min-height:0px;padding:6px;background:#30272A;border:1px solid #544047;border-radius:10px;}
QPushButton:hover {background:#493038;border-color:#DB6850;}
QPushButton:checked {background:#693B39;border-color:#F49A80;}
QPushButton:focus {border:2px solid #F6B59F;}
QPushButton#Primary {background:#A84737;border:1px solid #EF947A;font-weight:600;}
QPushButton#Number {font-size:18pt;background:#29242A;}
QPushButton#TimeField {font-size:30pt;font-family:'Bahnschrift';padding:0px;}
QPushButton#Small {padding:0px;background:transparent;border:1px solid #544047;}
QCheckBox {background:transparent;spacing:8px;}
QCheckBox:focus {border:none;outline:none;}
QCheckBox::indicator:focus {border:2px solid #F6B59F;}
"""

def timer_icon(kind):
    pix=QPixmap(72,72);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.scale(3,3)
    p.setPen(QPen(QColor('#1E3149'),1.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    if kind=='pause':
        p.setBrush(QColor('#1E3149'));p.drawRoundedRect(QRectF(7,5,3,14),1,1);p.drawRoundedRect(QRectF(15,5,3,14),1,1)
    elif kind=='reset':
        p.drawArc(QRectF(5,5,14,14),-130*16,285*16);path=QPainterPath();path.moveTo(5,4);path.lineTo(5,10);path.lineTo(11,10);p.drawPath(path)
    else:
        path=QPainterPath();path.moveTo(8,5);path.lineTo(19,12);path.lineTo(8,19);path.closeSubpath();p.setBrush(QColor('#1E3149'));p.drawPath(path)
    p.end();return QIcon(pix)

class SizeSlider(QSlider):
    def __init__(self):
        super().__init__(Qt.Horizontal);self.setFixedHeight(34)
        self.setStyleSheet('QSlider {background:transparent;border:none;padding:0px;margin:0px;} QSlider:focus {border:none;outline:none;}')
    def paintEvent(self,event):
        option=QStyleOptionSlider();self.initStyleOption(option);handle=self.style().subControlRect(QStyle.CC_Slider,option,QStyle.SC_SliderHandle,self)
        edge=max(12,handle.width()/2);x=handle.center().x();y=self.height()/2
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('#E4DADD'),4,Qt.SolidLine,Qt.RoundCap));p.drawLine(QPointF(edge,y),QPointF(self.width()-edge,y))
        p.setPen(QPen(QColor('#E7866C'),4,Qt.SolidLine,Qt.RoundCap));p.drawLine(QPointF(edge,y),QPointF(x,y))
        p.setPen(Qt.NoPen);p.setBrush(QColor('#FFD2BE'));p.drawEllipse(QPointF(x,y),7,7)
        if self.hasFocus():p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor('#E99C80'),1.5));p.drawEllipse(QPointF(x,y),11,11)

class TimerFace(QWidget):
    def __init__(self,owner):
        super().__init__();self.owner=owner;self.flash_on=True;self.setAccessibleName('Temps restant');self.setAttribute(Qt.WA_TranslucentBackground)
    def paintEvent(self,event):
        model=self.owner.model;p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.scale(self.width()/240,self.height()/240)
        text=time_text(model.remaining());self.setAccessibleDescription(text+' · '+model.phase+' · '+{'ready':'Prêt','running':'En cours','paused':'En pause','finished':'Temps écoulé'}[model.state])
        accent=QColor('#F08A6C' if model.phase=='Travail' else '#78CFBA');fraction=min(1,model.remaining()/model.duration)
        rect=QRectF(0,0,240,240).adjusted(6,6,-6,-6);ring=rect.adjusted(6,6,-6,-6)
        p.setPen(Qt.NoPen);p.setBrush(QColor('#F6F9FD'));p.drawEllipse(rect);p.setBrush(Qt.NoBrush)
        center=rect.center();radius=rect.width()/2-23
        if self.owner.visual:
            disc=ring.adjusted(7,7,-7,-7);p.setPen(Qt.NoPen);p.setBrush(QColor('#DCE3ED'));p.drawEllipse(disc)
            p.setBrush(QColor('#F3C94F' if model.phase=='Travail' else '#78CFBA'));p.drawPie(disc,90*16,round(fraction*360*16))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor('#DCE3ED'),8,Qt.SolidLine,Qt.RoundCap));p.drawEllipse(ring)
        p.setPen(QPen(accent,8,Qt.SolidLine,Qt.RoundCap));p.drawArc(ring,90*16,round(fraction*360*16)*(1 if self.owner.visual else -1))
        if model.state=='finished' and self.flash_on:p.drawEllipse(ring)
        if self.owner.visual:
            angle=(1-fraction)*2*math.pi;unit=QPointF(math.sin(angle),-math.cos(angle));normal=QPointF(math.cos(angle),math.sin(angle))
            tip=center+unit*(ring.width()/2-4);base=tip-unit*17
            p.setPen(QPen(QColor('#211D24'),9,Qt.SolidLine,Qt.RoundCap));p.drawLine(center,base)
            p.setPen(QPen(QColor('#AF4937'),5,Qt.SolidLine,Qt.RoundCap));p.drawLine(center,base)
            path=QPainterPath();path.moveTo(tip);path.lineTo(base+normal*8);path.lineTo(base-normal*8);path.closeSubpath()
            p.setPen(QPen(QColor('#211D24'),2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(QColor('#D96649'));p.drawPath(path);p.drawEllipse(center,8,8);p.end();return
        p.setPen(QPen(QColor('#A78D93'),1.8,Qt.SolidLine,Qt.RoundCap))
        for i in range(12):
            angle=i*math.pi/6;p.drawLine(QPointF(center.x()+math.sin(angle)*radius,center.y()-math.cos(angle)*radius),QPointF(center.x()+math.sin(angle)*(radius-4),center.y()-math.cos(angle)*(radius-4)))
        p.setFont(QFont('Bahnschrift',29));p.setPen(QColor('#1E3149'));p.drawText(rect,Qt.AlignCenter,text);p.end()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.style_controls()
    def style_controls(self):
        if not hasattr(self,'play'):return
        background='#FFFFFF';border='#DCE3ED'
        for button in (self.play,self.reset):
            button.setStyleSheet(f'QPushButton#DialControl {{padding:0px;background:{background};border:1px solid {border};border-radius:{button.width()//2}px;}} QPushButton#DialControl:hover {{background:#EEF3F9;}} QPushButton#DialControl:focus {{border:1px solid #DB6850;}}')
    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.LeftButton:self.owner.open_settings();event.accept()
        else:super().mouseDoubleClickEvent(event)

class FloatingTimer(ErgoWindow):
    def __init__(self,owner):
        super().__init__();self.owner=owner;self.setWindowFlags(Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle('Temporator · minuteur');self.setWindowIcon(owner.windowIcon());self.setStyleSheet(STYLE+"QMainWindow {background:transparent;} QPushButton#DialControl {padding:0px;background:transparent;border:1px solid transparent;border-radius:18px;} QPushButton#DialControl:hover {background:#493038;} QPushButton#DialControl:focus {border:2px solid #F6B59F;}")
        root=QWidget();root.setAttribute(Qt.WA_TranslucentBackground);self.setCentralWidget(root)
        self.face=TimerFace(owner);self.face.setParent(root);self.drag_area(self.face);self.face.setProperty('doubleClickSettings',True);self.face.setCursor(Qt.ArrowCursor);self.face.setToolTip('')
        self.play=QPushButton(root);self.play.setIconSize(QSize(23,23));self.play.clicked.connect(owner.toggle_timer)
        self.reset=QPushButton(root);self.reset.setIconSize(QSize(21,21));self.reset.setIcon(timer_icon('reset'));self.reset.setAccessibleName('Remettre le minuteur à zéro');self.reset.setToolTip('');self.reset.clicked.connect(owner.reset_timer)
        for button in (self.play,self.reset):button.setObjectName('DialControl')
        self.face.play=self.play;self.face.reset=self.reset
        self.set_diameter(owner.widget_size)
        self.message=QLabel(self);self.message.hide()
        self.face.setContextMenuPolicy(Qt.CustomContextMenu);self.face.customContextMenuRequested.connect(self.context_menu)
        self.behavior.configure(app_data('temporator')/'widget.json')
    def resizeEvent(self,event):
        # Keep per-pixel alpha outside the painted circle, without a rectangular mask.
        QMainWindow.resizeEvent(self,event);self.clearMask()
        if hasattr(self,'play'):self.layout_controls()
    def set_diameter(self,value):
        self.setFixedSize(value,value+max(34,min(44,round(value*44/240)))+12);self.layout_controls()
    def layout_controls(self):
        side=self.width();size=max(34,min(44,round(side*44/240)));gap=12
        self.face.setGeometry(0,0,side,side)
        for button in (self.play,self.reset):button.setFixedSize(size,size)
        self.play.move((side-size*2-gap)//2,side+4);self.reset.move((side+gap)//2,side+4)
        self.face.style_controls()
    def context_menu(self,point):
        menu=QMenu(self);menu.addAction('Régler le minuteur',self.owner.open_settings);menu.addAction('Masquer le cadran',self.hide)
        visual=menu.addAction('Sans chiffres');visual.setCheckable(True);visual.setChecked(self.owner.visual);visual.toggled.connect(self.owner.visual_choice.setChecked)
        try:menu.exec(self.face.mapToGlobal(point))
        finally:menu.deleteLater()
    def closeEvent(self,event):self.hide();event.ignore()

class TemporatorWindow(ApplicationWindow):
    def __init__(self):
        super().__init__('temporator');self.model=Countdown();self.mode='dial';self.visual=bool(self.preferences.get('timer_visual',False))
        stored_size=self.preferences.get('timer_size',200);self.widget_size=stored_size if type(stored_size) is int and 160<=stored_size<=280 else 200
        self.work=self.valid_duration(self.preferences.get('timer_work'),300);self.rest=self.valid_duration(self.preferences.get('timer_break'),300)
        self.kind='work';self.field='minutes';self.buffer='';self.model.configure(self.work,self.rest,bool(self.preferences.get('timer_cycle',False)))
        self.setMinimumSize(360,540);self.setMaximumWidth(420);self.resize(380,560);self.layout.setContentsMargins(14,12,14,10);self.layout.setSpacing(7);self.content.setSpacing(7)
        header=self.layout.itemAt(0).widget().layout();header.itemAt(1).widget().setStyleSheet('font-size:14pt;font-weight:600;color:#FFEDE7;')
        for i in (2,3):header.itemAt(i).widget().setFixedSize(32,30)
        self.setStyleSheet(self.styleSheet()+STYLE);self.status.setText('Choisissez une durée, puis démarrez.');self.status.setStyleSheet('font-size:9pt;color:#D9BDB6;')
        self.visual_choice=QCheckBox('Sans chiffres · disque visuel');self.visual_choice.setChecked(self.visual);self.visual_choice.toggled.connect(self.set_visual);self.content.addWidget(self.visual_choice)
        size_row=QHBoxLayout();size_row.addWidget(QLabel('Taille'));self.size_slider=SizeSlider();self.size_slider.setRange(160,280);self.size_slider.setSingleStep(10);self.size_slider.setPageStep(20);self.size_slider.setValue(self.widget_size);self.size_slider.setAccessibleName('Taille du widget');self.size_slider.valueChanged.connect(self.set_widget_size);size_row.addWidget(self.size_slider,1);self.content.addLayout(size_row)
        self.work_button=QPushButton('Minuteur');self.rest_button=QPushButton();self.rest_button.setToolTip('Régler la durée de pause');self.rest_button.clicked.connect(lambda:self.select_kind('rest'));self.work_button.clicked.connect(lambda:self.select_kind('work'))
        self.work_button.setCheckable(True);self.rest_button.setCheckable(True)
        self.cycle=QCheckBox('Alterner travail / pause');self.cycle.setChecked(self.model.cycle);self.cycle.toggled.connect(self.cycle_changed)
        cycle_row=QHBoxLayout();cycle_row.addWidget(self.cycle,1);cycle_row.addWidget(self.rest_button);self.content.addLayout(cycle_row)
        self.content.addWidget(self.work_button);self.work_button.setFixedHeight(26)
        fields=QHBoxLayout();self.minute_button=QPushButton();self.second_button=QPushButton()
        for field,button,caption in (('minutes',self.minute_button,'Minutes'),('seconds',self.second_button,'Secondes')):
            column=QVBoxLayout();column.setSpacing(2);label=QLabel(caption);label.setAlignment(Qt.AlignCenter);column.addWidget(label);button.setObjectName('TimeField');button.setCheckable(True);button.setFixedHeight(58);button.setAccessibleName(caption);button.clicked.connect(lambda checked=False,value=field:self.select_field(value));column.addWidget(button);fields.addLayout(column,1)
            if field=='minutes':colon=QLabel(':');colon.setStyleSheet('font-size:28pt;');fields.addWidget(colon)
        self.content.addLayout(fields)
        presets=QHBoxLayout()
        for value in (1,5,10,25):
            button=QPushButton(str(value)+' min');button.setFixedHeight(30);button.clicked.connect(lambda checked=False,seconds=value*60:self.preset(seconds));presets.addWidget(button)
        self.content.addLayout(presets)
        keypad=QGridLayout();keypad.setSpacing(6);self.keys={}
        for i,key in enumerate(('1','2','3','4','5','6','7','8','9','Effacer','0','⌫')):
            button=QPushButton(key);button.setObjectName('Number' if key.isdigit() else 'Key');button.setMinimumHeight(37);button.setAccessibleName('Effacer le dernier chiffre' if key=='⌫' else key);button.clicked.connect(lambda checked=False,value=key:self.enter(value));keypad.addWidget(button,i//3,i%3);self.keys[key]=button
        self.content.addLayout(keypad,1)
        self.start_button=QPushButton('Démarrer le minuteur');self.start_button.setObjectName('Primary');self.start_button.setFixedHeight(40);self.start_button.clicked.connect(self.start_timer);self.content.addWidget(self.start_button)
        self.widget=FloatingTimer(self);self.set_visual(self.visual);self.blink_timer=QTimer(self);self.blink_timer.setInterval(750);self.blink_timer.timeout.connect(self.blink);self.refresh_fields();self.refresh_timer();self.clock_timer=QTimer(self);self.clock_timer.setInterval(100);self.clock_timer.timeout.connect(self.tick);self.clock_timer.start()
        self.orb.doubleActivated.connect(self.open_settings);self.orb.setToolTip('Temporator · clic : minuteur · double-clic : réglages')
    @staticmethod
    def valid_duration(value,default):return value if type(value) is int and 1<=value<=5999 else default
    def activate(self,*_):
        if hasattr(self,'widget'):
            if self.widget.isVisible():self.widget.hide()
            else:self.show_widget()
    def show_widget(self):self.widget.show();self.widget.raise_()
    def open_settings(self,*_):ApplicationWindow.activate(self)
    def set_widget_size(self,value):
        self.widget_size=value;self.remember('timer_size',value)
        if hasattr(self,'widget'):self.widget.set_diameter(value);self.widget.behavior.ensure_visible();self.widget.face.update()
    def set_visual(self,value):
        self.visual=value;self.remember('timer_visual',value)
        if hasattr(self,'widget'):
            self.widget.face.style_controls();self.widget.face.update()
    def create_orb_menu(self):
        menu=super().create_orb_menu();first=menu.actions()[0];first.setText('Régler le minuteur');menu.insertAction(first,menu.addAction('Masquer le minuteur' if self.widget.isVisible() else 'Afficher le minuteur',self.activate));return menu
    def selected_duration(self):return self.rest if self.kind=='rest' else self.work
    def store_duration(self,value):
        if self.kind=='rest':self.rest=value
        else:self.work=value
        if value>0:self.remember('timer_break' if self.kind=='rest' else 'timer_work',value)
        self.refresh_fields()
    def select_kind(self,kind):self.kind=kind;self.buffer='';self.refresh_fields()
    def select_field(self,field):self.field=field;self.buffer='';self.refresh_fields()
    def enter(self,key):
        value=self.selected_duration();minutes,seconds=divmod(value,60)
        if key=='Effacer':self.buffer='';self.store_duration(0);return
        if key=='⌫':self.buffer=(self.buffer or str(minutes if self.field=='minutes' else seconds))[:-1]
        else:
            candidate=(self.buffer+key)[-2:]
            if self.field=='seconds' and int(candidate)>59:self.status.setText('Les secondes vont de 00 à 59.');return
            self.buffer=candidate
        number=int(self.buffer or '0');self.store_duration(number*60+seconds if self.field=='minutes' else minutes*60+number)
    def preset(self,seconds):self.buffer='';self.store_duration(seconds)
    def cycle_changed(self,value):
        self.remember('timer_cycle',value)
        if not value:self.kind='work'
        self.refresh_fields()
    def refresh_fields(self):
        minutes,seconds=divmod(self.selected_duration(),60);self.minute_button.setText(f'{minutes:02}');self.second_button.setText(f'{seconds:02}')
        self.minute_button.setChecked(self.field=='minutes');self.second_button.setChecked(self.field=='seconds');self.rest_button.setVisible(self.cycle.isChecked());self.rest_button.setText('Pause '+time_text(self.rest));self.rest_button.setChecked(self.kind=='rest');self.work_button.setVisible(self.cycle.isChecked())
        self.work_button.setText(('● ' if self.kind=='work' else '')+'Travail '+time_text(self.work) if self.cycle.isChecked() else 'Durée du minuteur');self.work_button.setChecked(self.kind=='work')
    def start_timer(self):
        try:self.model.configure(self.work,self.rest,self.cycle.isChecked())
        except ValueError as error:self.error(str(error));return
        self.model.start();self.status.setText('En cours · réglages pour le prochain minuteur.');self.state('Activée');self.refresh_timer();self.hide();self.show_widget()
    def toggle_timer(self):
        if self.model.state=='running':
            if self.model.pause():self.notify_phase()
        elif self.model.state=='paused':self.model.resume()
        else:self.start_timer()
        self.refresh_timer()
    def reset_timer(self):self.model.reset();self.state('Activée');self.refresh_timer()
    def tick(self):
        if self.model.tick():self.notify_phase()
        self.refresh_timer()
    def notify_phase(self):
        text='Temps écoulé.' if self.model.state=='finished' else self.model.phase+' : nouvelle période.'
        QApplication.beep();self.state('Action réussie');self.status.setText(text)
        if self.model.state=='finished':self.widget.face.flash_on=True;self.blink_timer.start()
    def blink(self):
        if self.model.state=='finished':self.widget.face.flash_on=not self.widget.face.flash_on;self.widget.face.update()
    def refresh_timer(self):
        if self.model.state!='finished':self.blink_timer.stop();self.widget.face.flash_on=True
        model=self.model;label={'ready':'Prêt à démarrer','running':model.phase if model.cycle else 'En cours','paused':'En pause','finished':'Temps écoulé'}[model.state]
        self.widget.message.setText(label);action={'ready':'Démarrer','running':'Pause','paused':'Reprendre','finished':'Recommencer'}[model.state];self.widget.play.setText('');self.widget.play.setAccessibleName(action);self.widget.play.setToolTip('');self.widget.play.setIcon(timer_icon('pause' if model.state=='running' else 'play'));self.widget.face.update()
    def cleanup(self):self.clock_timer.stop();self.blink_timer.stop();self.widget.behavior.save();self.widget.hide();self.widget.deleteLater()
