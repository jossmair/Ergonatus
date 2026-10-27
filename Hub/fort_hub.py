"""Fortinator's compact hub composition in Ergonatus blue, with a native hub Orb."""
from pathlib import Path
import json,os
from PySide6.QtCore import Qt,QTimer,QSize,QPoint,QThreadPool
from PySide6.QtGui import QPixmap,QColor,QIcon,QPainter,QLinearGradient,QPen,QPainterPath,QFont
from PySide6.QtWidgets import (QWidget,QLabel,QFrame,QPushButton,QCheckBox,QVBoxLayout,QHBoxLayout,QGridLayout,QScrollArea,QStackedWidget,QApplication,QGraphicsColorizeEffect,QToolButton,QMenu,QLayout,QComboBox,QSlider,QLineEdit,QSizePolicy)
from Hub.window import HubWindow as AdvancedHub
from shared.catalog import suite_root
from shared.ui.components import ErgoOrb
from shared.ui.theme import APP_THEMES
from orb_manager.manager import selected_stack

PRESETS={
    'Élève DYS':['dictionnator','explicator','tablinator','lector','scanator','corrector','redactor','calculinator','planinator','temporator'],
    'Handicap moteur':['claviernator','precisionator','transcrinator','applinator','communicator'],
    'Déficience visuelle':['precisionator','lector','scanator','applinator'],
    'Fatigabilité':['temporator','concentrator','lector','transcrinator','memorinator'],
    'Élève allophone':['traductor','lector','scanator','redactor','planinator'],
    'Communication':['communicator','lector','applinator'],
    'Organisation au quotidien':['planinator','memorinator','organisator','temporator','applinator'],
    'Lecture et concentration':['lector','pdfinator','concentrator','temporator'],
}

STYLE="""
QWidget {font-family:'Segoe UI';font-size:10pt;color:#EAF0FC;}
QLabel {background:transparent;border:none;}
QWidget#FortSurface,QWidget#MainPage {background:transparent;}
QFrame#FortRow {background:rgba(19,32,58,239);border:none;border-radius:10px;}
QFrame#HubTitleBar {background:transparent;border:none;}
QPushButton#Quiet {background:transparent;color:#B8C6DF;border:none;padding:7px 10px;min-height:22px;}
QPushButton#Quiet:hover {background:rgba(65,90,140,120);color:white;border-radius:7px;}
QPushButton#AppName {background:transparent;border:none;text-align:left;font-size:11pt;font-weight:600;padding:0;}
QPushButton#AppName:hover {color:#A9C7FF;}
QCheckBox#Switch,QCheckBox#Switch:focus {background:transparent;border:none;outline:none;padding:0;spacing:0;min-height:24px;}
QCheckBox#Switch::indicator {width:46px;height:24px;border-radius:12px;border:none;background:#344854;image:url(SWITCH_OFF);}
QCheckBox#Switch::indicator:checked {background:#478FA5;image:url(SWITCH_ON);}
QCheckBox#Switch::indicator:hover {background:#425D6B;}
QCheckBox#Switch::indicator:checked:hover {background:#58A1B6;}
QCheckBox#Windows {background:transparent;font-size:8pt;spacing:7px;min-height:24px;}
QCheckBox#Windows::indicator {width:16px;height:16px;border:1px solid #8EABC7;border-radius:4px;background:transparent;image:none;}
QCheckBox#Windows::indicator:checked {background:#AAC7FF;image:url(CHECK);}
QScrollArea,QScrollArea>QWidget>QWidget {background:transparent;border:none;}
QScrollBar:vertical {width:5px;background:transparent;}
QScrollBar::handle:vertical {background:#526785;border-radius:2px;min-height:25px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QComboBox {background:#172A48;color:#EAF0FC;border:1px solid #415C82;border-radius:7px;padding:5px 9px;}
QComboBox QAbstractItemView {background:#14233D;color:#EAF0FC;selection-background-color:#345581;}
QMenu {background:#13203A;color:#EAF0FC;border:1px solid #526785;padding:7px;}
QMenu::item {padding:9px 20px;}
QMenu::item:selected {background:#304B76;}
QToolButton#HelpIcon {background:#223754;border:1px solid #526C91;border-radius:10px;padding:0;min-width:20px;max-width:20px;min-height:20px;max-height:20px;color:#D0DFFF;font-size:9pt;}
QToolButton#HelpIcon:hover {background:#416393;border-color:#B8D1FF;}
QSlider::groove:horizontal {height:5px;background:#344854;border-radius:2px;}
QSlider::sub-page:horizontal {background:#478FA5;border-radius:2px;}
QSlider::handle:horizontal {width:14px;margin:-5px 0;background:#D6EAF0;border:1px solid #478FA5;border-radius:7px;}
"""

def style():
    root=suite_root()/'assets'
    return STYLE.replace('SWITCH_OFF',(root/'switch-off.svg').as_posix()).replace('SWITCH_ON',(root/'switch-on.svg').as_posix()).replace('CHECK',(root/'check.svg').as_posix())

class HubAction(QPushButton):
    """Outlined controls with explicit hover, press and keyboard focus states."""
    def __init__(self,text,callback):
        super().__init__(text);self.setObjectName('HubAction');self.setCursor(Qt.PointingHandCursor);self.setMinimumHeight(32);self.setStyleSheet('QPushButton#HubAction {background:transparent;border:none;padding:5px 12px;min-height:22px;font-size:9pt;font-weight:600;}');self.clicked.connect(callback)
        if text in ('×','—'):self.setFixedSize(36,32);self.setToolTip('Masquer cette fenêtre' if text=='×' else 'Réduire la fenêtre');self.setAccessibleName(self.toolTip())
    def enterEvent(self,event):super().enterEvent(event);self.update()
    def leaveEvent(self,event):super().leaveEvent(event);self.update()
    def paintEvent(self,event):
        from PySide6.QtCore import QRectF
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);close=self.text()=='×';hover=self.underMouse();down=self.isDown();primary=self.property('primary') is True;background='#FADCE0' if close and down else '#FFF0F2' if close and hover else '#CCDDF4' if down else '#E6EEFA' if hover else '#FFFFFF';border='#B65A68' if close and hover else '#25487F' if down or hover or self.isChecked() else '#8FA5C4';background=('#192D59' if down else '#365B96' if hover else '#253B70') if primary else '#DCE7F8' if self.isChecked() and not down else background;p.setBrush(QColor(background));p.setPen(QPen(QColor(border),1.2));r=QRectF(self.rect()).adjusted(1,1,-1,-2);p.drawRoundedRect(r,9,9);p.setPen(QPen(QColor('#FFFFFF') if primary else QColor('#A33D50') if close and hover else QColor('#253B58'),1.7,Qt.SolidLine,Qt.RoundCap));center=r.center()
        if close:p.drawLine(center.x()-4,center.y()-4,center.x()+4,center.y()+4);p.drawLine(center.x()-4,center.y()+4,center.x()+4,center.y()-4)
        elif self.text()=='—':p.drawLine(center.x()-5,center.y(),center.x()+5,center.y())
        else:p.setFont(self.font());p.drawText(r,Qt.AlignCenter,self.text())
        if self.hasFocus():p.setPen(QPen(QColor('#25487F'),1,Qt.DotLine));p.setBrush(Qt.NoBrush);p.drawRoundedRect(r.adjusted(3,3,-3,-3),6,6)
        p.end()

def quiet(text,callback):
    return HubAction(text,callback)

class HubHelpButton(QToolButton):
    def enterEvent(self,event):super().enterEvent(event);self.update()
    def leaveEvent(self,event):super().leaveEvent(event);self.update()
    def paintEvent(self,event):
        from PySide6.QtCore import QRectF
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setBrush(QColor('#C9DBF4') if self.isDown() else QColor('#E4EDFA') if self.underMouse() else QColor('#FFFFFF'));p.setPen(QPen(QColor('#31568E') if self.underMouse() else QColor('#9AAECC'),1));r=QRectF(self.rect()).adjusted(1,1,-1,-1);p.drawEllipse(r);p.setPen(QColor('#253B70'));p.setFont(self.font());p.drawText(r,Qt.AlignCenter,'?');p.end()

def help_button(hub,key):
    button=HubHelpButton();button.setObjectName('HelpIcon');button.setText('?');button.setCursor(Qt.PointingHandCursor);button.setAccessibleName('À quoi sert '+APP_THEMES[key]['name']+' ?');button.clicked.connect(lambda:hub.show_app_help(key,button));return button

class FortSurface(QWidget):
    def __init__(self):
        super().__init__();self.setObjectName('FortSurface');self.setAutoFillBackground(False);self.setAttribute(Qt.WA_TranslucentBackground)
    def resizeEvent(self,event):
        super().resizeEvent(event)

class HubProfileBox(QComboBox):
    def paintEvent(self,event):
        from PySide6.QtCore import QRectF,QPointF
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setBrush(QColor('#FFFFFF'));p.setPen(QPen(QColor('#93A8C8') if self.hasFocus() else QColor('#D4DEED'),1));p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),9,9);p.setPen(QColor('#253B53'));p.drawText(self.rect().adjusted(10,0,-30,0),Qt.AlignVCenter|Qt.AlignLeft,self.fontMetrics().elidedText(self.currentText(),Qt.ElideRight,max(0,self.width()-42)));p.setPen(QPen(QColor('#68829E'),1.6,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));x=self.width()-17;y=self.height()/2;p.drawPolyline([QPointF(x-4,y-2),QPointF(x,y+2),QPointF(x+4,y-2)]);p.end()

class HubSwitch(QCheckBox):
    """A real switch track, independent of the older tiny SVG indicators."""
    def __init__(self,color,parent=None):
        super().__init__(parent);self.color=QColor(color);self.setFixedSize(40,24);self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=self.rect().adjusted(1,3,-1,-3);p.setPen(Qt.NoPen);p.setBrush(self.color if self.isChecked() else QColor('#DCE4ED'));p.drawRoundedRect(r,9,9);p.setBrush(QColor('white'));p.drawEllipse(23 if self.isChecked() else 3,5,14,14)
        if self.hasFocus():p.setPen(QPen(self.color,1,Qt.DotLine));p.setBrush(Qt.NoBrush);p.drawRoundedRect(self.rect().adjusted(0,1,-1,-2),11,11)
        p.end()

class HubAppCard(QFrame):
    def __init__(self,key):
        super().__init__();self.color=QColor(APP_THEMES[key]['accent']);self.selected=False;self.setObjectName('HubAppCard');self.setMinimumHeight(86);self.setStyleSheet('QFrame#HubAppCard {background:transparent;border:none;}')
    def paintEvent(self,event):
        from PySide6.QtCore import QRectF
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=QRectF(self.rect()).adjusted(1,1,-1,-3);p.setPen(Qt.NoPen);p.setBrush(QColor(25,50,80,13));p.drawRoundedRect(r.translated(0,2),12,12);g=QLinearGradient(r.topLeft(),r.bottomRight());g.setColorAt(0,QColor('#FFFFFF'));c=QColor(self.color);c.setAlpha(12 if self.selected else 4);g.setColorAt(1,QColor(round(255*(1-c.alphaF())+c.red()*c.alphaF()),round(255*(1-c.alphaF())+c.green()*c.alphaF()),round(255*(1-c.alphaF())+c.blue()*c.alphaF())));p.setBrush(g);edge=QColor(self.color);edge.setAlpha(145 if self.selected else 48);p.setPen(QPen(edge,1));p.drawRoundedRect(r,12,12);p.setPen(QPen(self.color,3,Qt.SolidLine,Qt.RoundCap));p.drawLine(4,17,4,self.height()-20);p.end()

class HubTile(QPushButton):
    def __init__(self,key):
        super().__init__();self.color=QColor(APP_THEMES[key]['accent']);self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self,event):
        from PySide6.QtCore import QRectF
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=QRectF(self.rect()).adjusted(1,1,-1,-3);p.setPen(Qt.NoPen);p.setBrush(QColor(20,45,80,14));p.drawRoundedRect(r.translated(0,2),15,15);g=QLinearGradient(r.topLeft(),r.bottomRight());g.setColorAt(0,QColor('#FFFFFF'));c=self.color;amount=.09 if self.underMouse() else .035;g.setColorAt(1,QColor(round(255*(1-amount)+c.red()*amount),round(255*(1-amount)+c.green()*amount),round(255*(1-amount)+c.blue()*amount)));p.setBrush(g);edge=QColor(c);edge.setAlpha(150 if self.underMouse() else 65);p.setPen(QPen(edge,1));p.drawRoundedRect(r,15,15);p.setPen(QPen(c,2,Qt.SolidLine,Qt.RoundCap));p.drawLine(17,self.height()-10,self.width()-17,self.height()-10)
        if self.hasFocus():p.setPen(QPen(c,1,Qt.DotLine));p.setBrush(Qt.NoBrush);p.drawRoundedRect(r.adjusted(3,3,-3,-3),12,12)
        p.end()

class SuiteLauncher(QWidget):
    def __init__(self,hub):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);self.hub=hub;self.setAttribute(Qt.WA_TranslucentBackground);self.setWindowTitle('Ergonatus · Tous mes logiciels');self.setStyleSheet(style()+"QWidget#SuiteLauncher {background:transparent;} QToolButton {background:#17253C;border:1px solid #304563;border-radius:16px;padding:12px;min-height:100px;max-height:100px;min-width:140px;color:white;font-size:10pt;} QToolButton:hover {background:#263E63;border-color:#A9C7FF;}");self.setObjectName('SuiteLauncher')
        outer=QVBoxLayout(self);outer.setContentsMargins(36,28,36,28);header=QHBoxLayout();title=QLabel('ERGONATUS');title.setStyleSheet('font-size:20pt;font-weight:600;');header.addWidget(title);header.addStretch();self.open_hub_button=quiet('Ouvrir le hub',hub.reveal);self.open_hub_button.setToolTip('Choisir les logiciels, le profil et le démarrage');header.addWidget(self.open_hub_button);self.close_button=quiet('×',self.hide);self.close_button.setToolTip('Fermer le panneau des logiciels');self.close_button.setAccessibleName('Fermer le panneau des logiciels');header.addWidget(self.close_button);outer.addLayout(header);outer.addStretch()
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);outer.addWidget(self.scroll);outer.addStretch()
        controls=QHBoxLayout();controls.addStretch();controls.addWidget(QLabel('Fond'));self.opacity_slider=QSlider(Qt.Horizontal);self.opacity_slider.setRange(10,100);self.opacity_slider.setValue(hub.launcher_opacity);self.opacity_slider.setFixedWidth(180);self.opacity_slider.setAccessibleName('Opacité du fond');self.opacity_value=QLabel(str(hub.launcher_opacity)+' %');self.opacity_value.setFixedWidth(50);controls.addWidget(self.opacity_slider);controls.addWidget(self.opacity_value);controls.addStretch();outer.addLayout(controls);self.opacity_slider.valueChanged.connect(self.set_background_opacity)
    def set_background_opacity(self,value):
        self.hub.launcher_opacity=value;self.opacity_value.setText(str(value)+' %');self.update();self.hub.save_hub_settings()
    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),QColor(240,245,252,round(self.hub.launcher_opacity*2.55)));painter.end()
    def rebuild(self):
        import math
        panel=QWidget();grid=QGridLayout(panel);grid.setSpacing(12);grid.setContentsMargins(10,10,10,10)
        self.tiles={};columns=max(3,min(7,(self.width()-100)//158));count=len(APP_THEMES)-1;rows=math.ceil(count/columns);available=max(300,self.height()-160);tile_height=max(106,min(140,(available-24-(rows-1)*12)//rows))
        for index,(key,app) in enumerate((k,a) for k,a in APP_THEMES.items() if k!='ergonatus'):
            tile=HubTile(key);tile.setObjectName('SuiteTile');tile.setFixedHeight(tile_height);tile.setMinimumWidth(140);tile.setStyleSheet('QPushButton#SuiteTile {background:transparent;border:none;padding:0;} QLabel {background:transparent;border:none;color:#1E3149;}')
            content=QVBoxLayout(tile);content.setContentsMargins(12,13,19,16);content.setSpacing(6);heading=QHBoxLayout();heading.setSpacing(7)
            icon=QLabel();icon.setPixmap(QPixmap(str(suite_root()/'assets/orbs'/f'{key}.png')).scaled(30,30,Qt.KeepAspectRatio,Qt.SmoothTransformation));icon.setFixedSize(30,30);heading.addWidget(icon)
            title=QLabel(app['name']);title.setObjectName('TileName');title.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);title.setMinimumWidth(0);title.setStyleSheet('font-size:9pt;font-weight:600;color:#1E3149;');heading.addWidget(title,1);content.addLayout(heading)
            description=QLabel(app['description']);description.setObjectName('TileDescription');description.setWordWrap(True);description.setStyleSheet('font-size:8pt;color:#566B80;');content.addWidget(description,1)
            for label in (icon,title,description):label.setAttribute(Qt.WA_TransparentForMouseEvents)
            tile.setAccessibleName('Ouvrir '+app['name']);tile.setAccessibleDescription(app['description']);tile.setToolTip(app['description']);tile.setEnabled(self.hub.catalog.detect(key) is not None);tile.clicked.connect(lambda checked=False,k=key:self.choose(k));grid.addWidget(tile,index//columns,index%columns);self.tiles[key]=tile
            helper=help_button(self.hub,key);grid.addWidget(helper,index//columns,index%columns,Qt.AlignTop|Qt.AlignRight);helper.raise_()
        old=self.scroll.takeWidget()
        if old:old.deleteLater()
        self.scroll.setWidget(panel);self.scroll.setFixedHeight(min(rows*(tile_height+12)+12,available))
    def choose(self,key):self.hide();self.hub.launch(key,minimized=False)
    def reveal(self):
        screen=QApplication.screenAt(self.hub.hub_orb.geometry().center()) or QApplication.primaryScreen();self.setGeometry(screen.availableGeometry());self.rebuild();self.show();self.raise_();self.activateWindow();self.hub.hub_orb.raise_()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape:self.hide()
        else:super().keyPressEvent(event)
    def mousePressEvent(self,event):self.hide()

class HubWindow(AdvancedHub):
    def __init__(self,data_dir=None):
        self._clean_hub_frame=True;self.launch_queue=[];self.launch_busy=False;self.starting_key=None;self.external_orbs={}
        self.launcher_opacity=90;self.startup_apps=[];self.preset_seeded=[];self.launched_order=[];self.native_positions={};self.last_running=();self.shutting_down=False
        super().__init__(data_dir)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setAutoFillBackground(False);self.clearMask();self.setStyleSheet(self.styleSheet()+' QMainWindow {background:transparent;border:none;} QStackedWidget {background:transparent;border:none;}')
        if not self.manager.listening:
            self.tray.hide();return
        self.previous_layout_env=os.environ.get('ERGONATUS_ORB_LAYOUT');self.catalog.layout_path=(self.store.path.parent/'live-layout.json') if data_dir else self.catalog.root/'orb_manager/live-layout.json'
        self.setMinimumSize(560,400);self.resize(600,480)
        self.hub_orb=ErgoOrb('ergonatus',floating=True,preview=False);self.hub_orb.setWindowTitle('Ergonatus · Orbe du hub');self.hub_orb.activated.connect(self.toggle_launcher);self.hub_orb.doubleActivated.connect(self.reveal);self.hub_orb.setContextMenuPolicy(Qt.CustomContextMenu);self.hub_orb.customContextMenuRequested.connect(self.orb_menu)
        self.hub_orb.image=QPixmap(str(suite_root()/'assets/orbs/ergonatus-orb.png')).scaled(128,128,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        self.launcher=SuiteLauncher(self);self.hub_orb.show();self.arrange_orbs();QApplication.primaryScreen().availableGeometryChanged.connect(self.arrange_orbs)
        self.layout_timer=QTimer(self);self.layout_timer.setInterval(1500);self.layout_timer.timeout.connect(self.sync_stack);self.layout_timer.start()
        settings=self.store.path.parent/'hub-launcher.json'
        try:
            config=json.loads(settings.read_text());self.launcher_opacity=max(10,min(100,int(config.get('launcher_opacity',90))));self.startup_apps=[k for k in config.get('windows_apps',[]) if k in APP_THEMES and k!='ergonatus'];self.preset_seeded=[n for n in config.get('preset_seeded',[]) if n in PRESETS]
        except (OSError,ValueError,AttributeError):pass
        self.launcher.opacity_slider.setValue(self.launcher_opacity)
        self.sync_rows()
        self.manager.show_requested.disconnect();self.manager.show_requested.connect(self.reveal)
        self.tray.setIcon(QIcon(str(suite_root()/'assets/orbs/ergonatus.png')))
        menu=QMenu(self);menu.addAction('Ouvrir Ergonatus',self.reveal);menu.addAction('Tous les logiciels',self.toggle_launcher);menu.addSeparator();menu.addAction('Quitter Ergonatus',self.close);menu.setStyleSheet(style());self.tray.setContextMenu(menu)
    def build(self):
        # The retired settings page contains two full sets of animated Orb
        # previews. Build it only when explicitly requested, not on startup.
        self.advanced_page=None
        self.notice=QLabel(self);self.notice.hide()
        self.profile_box=QComboBox(self);self.profile_box.addItems([p['name'] for p in self.profiles]);self.profile_box.setCurrentText(self.profile['name']);self.profile_box.hide()
        self.start_windows=QCheckBox(self);self.start_windows.hide()
        try:
            from shared.startup import enabled
            self.start_windows.setChecked(enabled())
        except OSError:pass
        self.pages=QStackedWidget();self.pages.setObjectName('HubPages');self.pages.setStyleSheet('QStackedWidget#HubPages {background:transparent;border:none;}');self.setCentralWidget(self.pages);self.surface=FortSurface();self.surface.setStyleSheet(style());self.pages.addWidget(self.surface)
        body=QVBoxLayout(self.surface);body.setContentsMargins(18,10,18,10);body.setSpacing(6)
        self.header_bar=QFrame();self.header_bar.setObjectName('HubTitleBar');header=QHBoxLayout(self.header_bar);header.setContentsMargins(0,0,0,0);header.setSpacing(8);self.drag_area(self.header_bar);self.header_bar.setCursor(Qt.ArrowCursor);self.header_bar.setToolTip('Glisser pour déplacer la fenêtre')
        logo=QLabel();logo.setPixmap(QPixmap(str(suite_root()/'assets/orbs/ergonatus.png')).scaled(30,30,Qt.KeepAspectRatio,Qt.SmoothTransformation));header.addWidget(logo);self.drag_area(logo)
        title=QLabel('ERGONATUS');title.setStyleSheet('font-size:14pt;font-weight:600;');header.addWidget(title);self.drag_area(title);header.addStretch();self.compact_summary=QLabel();self.compact_summary.setStyleSheet('font-size:9pt;color:#B8C6DF;');header.addWidget(self.compact_summary);self.drag_area(self.compact_summary)
        for label in (logo,title,self.compact_summary):label.setCursor(Qt.ArrowCursor);label.setToolTip('Glisser pour déplacer la fenêtre')
        header.addWidget(quiet('—',self.hide));header.addWidget(quiet('×',self.hide));body.addWidget(self.header_bar)
        profile_row=QHBoxLayout();profile_row.addWidget(QLabel('Profil'));self.preset_box=HubProfileBox();self.preset_box.addItems(['Personnalisé']+list(PRESETS)+[p['name'] for p in self.profiles if p['name'] not in PRESETS and p['name']!='Personnalisé']);self.preset_box.setCurrentText(self.profile['name']);self.preset_box.setAccessibleName('Profil d’usage');self.preset_box.currentTextChanged.connect(self.prepare_profile);profile_row.addWidget(self.preset_box,1);load_profile=HubAction('Lancer le profil',self.load_chosen_profile);load_profile.setProperty('primary',True);load_profile.setObjectName('Primary');load_profile.setStyleSheet('QPushButton#Primary {background:#253B70;color:#FFFFFF;border:1px solid #253B70;border-radius:9px;padding:6px 10px;min-height:24px;font-weight:600;}');profile_row.addWidget(load_profile);body.addLayout(profile_row)
        tools=QHBoxLayout();self.hub_search=QLineEdit();self.hub_search.setPlaceholderText('Rechercher un logiciel…');self.hub_search.setAccessibleName('Rechercher dans les 21 logiciels');self.hub_search.setStyleSheet('QLineEdit {background:#FFFFFF;border:1px solid #D8E2EF;border-radius:10px;padding:6px 10px;min-height:22px;}');self.hub_search.textChanged.connect(self.filter_compact);tools.addWidget(self.hub_search,1);self.selection_filter=HubAction('Sélectionnés',lambda:None);self.selection_filter.setCheckable(True);self.selection_filter.toggled.connect(self.filter_compact);tools.addWidget(self.selection_filter);body.addLayout(tools)
        self.launch_status=QLabel('Les outils sélectionnés démarrent avec Ergonatus.');self.launch_status.setWordWrap(True);self.launch_status.setStyleSheet('font-size:8pt;color:#63758B;');body.addWidget(self.launch_status)
        area=QScrollArea();area.setWidgetResizable(True);area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.app_panel=QWidget();self.app_grid=QGridLayout(self.app_panel);self.app_grid.setContentsMargins(1,1,3,3);self.app_grid.setSpacing(8);self.app_grid.setColumnStretch(0,1);self.app_grid.setColumnStretch(1,1);self.compact_cards={}
        for index,(key,app) in enumerate((k,a) for k,a in APP_THEMES.items() if k!='ergonatus'):
            card=HubAppCard(key);box=QVBoxLayout(card);box.setContentsMargins(12,7,9,7);box.setSpacing(3);row=QHBoxLayout();row.setSpacing(6);icon=QLabel();icon.setPixmap(QPixmap(str(suite_root()/'assets/orbs'/f'{key}.png')).scaled(25,25,Qt.KeepAspectRatio,Qt.SmoothTransformation));icon.setFixedSize(25,25);icon.setStyleSheet('background:transparent;border:none;');row.addWidget(icon)
            name=QPushButton(app['name']);name.setObjectName('AppName');name.setStyleSheet('QPushButton {background:transparent;border:none;text-align:left;font-size:10pt;font-weight:600;padding:0;min-height:22px;}');name.clicked.connect(lambda checked=False,k=key:self.launch(k));row.addWidget(name,1)
            toggle=HubSwitch(app['accent']);toggle.setObjectName('Switch');toggle.setAccessibleName('Lancer et afficher l’Orb de '+app['name']);toggle.toggled.connect(lambda enabled,k=key:self.toggle_active(k,enabled));row.addWidget(toggle);box.addLayout(row)
            description=QLabel(app['description']);description.setWordWrap(True);description.setStyleSheet('background:transparent;border:none;font-size:8pt;color:#596D82;');description.setMaximumHeight(31);box.addWidget(description)
            bottom=QHBoxLayout();status=QLabel('Prêt');status.setStyleSheet('background:transparent;border:none;font-size:8pt;color:#657A91;');bottom.addWidget(status,1);helper=help_button(self,key);bottom.addWidget(helper)
            startup=QCheckBox('Windows');startup.setObjectName('Windows');startup.setToolTip('Démarrer '+app['name']+' avec Windows');startup.setAccessibleName('Démarrer '+app['name']+' avec Windows');startup.toggled.connect(lambda enabled,k=key:self.set_app_startup(k,enabled));bottom.addWidget(startup);box.addLayout(bottom);self.app_grid.addWidget(card,index//2,index%2);self.compact_cards[key]=dict(active=toggle,startup=startup,status=status,help=helper,card=card)
        area.setWidget(self.app_panel);body.addWidget(area,1);footer=QHBoxLayout();footer.addWidget(quiet('Tous les logiciels  ↗',self.toggle_launcher));footer.addStretch();footer.addWidget(quiet('Quitter la suite',self.close));body.addLayout(footer)
    def filter_compact(self,*_):
        if not hasattr(self,'compact_cards'):return
        query=self.hub_search.text().strip().casefold();selected=self.selection_filter.isChecked();visible=0
        for key,row in self.compact_cards.items():
            self.app_grid.removeWidget(row['card']);match=query in (APP_THEMES[key]['name']+' '+APP_THEMES[key]['description']).casefold() and (not selected or key in self.profile['active']);row['card'].setVisible(match)
            if match:self.app_grid.addWidget(row['card'],visible//2,visible%2);visible+=1
    def show_app_help(self,key,anchor):
        if getattr(self,'help_popup',None):self.help_popup.close()
        popup=QFrame(anchor.window(),Qt.Popup|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);popup.setAttribute(Qt.WA_NoMouseReplay);popup.setObjectName('AppHelp');popup.setStyleSheet(style()+'QFrame#AppHelp {background:#14233B;border:1px solid #526C91;border-radius:14px;}');popup.setFixedWidth(340)
        box=QVBoxLayout(popup);box.setContentsMargins(20,16,20,18);heading=QHBoxLayout();title=QLabel(APP_THEMES[key]['name']);title.setStyleSheet('font-size:13pt;font-weight:600');heading.addWidget(title);heading.addStretch();heading.addWidget(quiet('×',popup.close));box.addLayout(heading)
        description=QLabel(APP_THEMES[key]['description']);description.setWordWrap(True);description.setMinimumWidth(290);box.addWidget(description);popup.adjustSize();area=anchor.screen().availableGeometry();point=anchor.mapToGlobal(QPoint(0,anchor.height()+8));popup.move(max(area.left(),min(point.x(),area.right()-popup.width())),max(area.top(),min(point.y(),area.bottom()-popup.height())));self.help_popup=popup;popup.show()
    def show_options(self):
        if self.advanced_page is None:
            pages=self.takeCentralWidget();previous_notice=self.notice
            super().build();self.advanced_page=self.takeCentralWidget();self.setCentralWidget(pages)
            try:self.behavior.message.disconnect(previous_notice.setText)
            except (RuntimeError,TypeError):pass
            self.behavior.message.connect(self.notice.setText)
            wrapper=QWidget();options=QVBoxLayout(wrapper);options.setContentsMargins(0,0,0,0);options.addWidget(quiet('‹ Mes logiciels',self.show_home));options.addWidget(self.advanced_page);self.pages.addWidget(wrapper);self.apply_profile()
        self.pages.setCurrentIndex(1);self.setMinimumSize(720,560);self.resize(1060,800)
    def show_home(self):self.pages.setCurrentIndex(0);self.setMinimumSize(560,400);self.resize(600,480)
    def reveal(self,*_):
        if hasattr(self,'launcher'):self.launcher.hide()
        self.show_home();self.showNormal();self.raise_();self.activateWindow()
    def apply_theme(self,*_):
        super().apply_theme(*_)
        if hasattr(self,'surface'):self.surface.setStyleSheet(style())
    def sync_rows(self):
        running=0
        for key,row in self.compact_cards.items():
            opened=bool(self.catalog.running(key));running+=opened
            queued=any(k==key for k,_ in self.launch_queue)
            state='Démarrage…' if key==self.starting_key else 'En attente…' if queued else 'Échec · réessayer' if key in self.catalog.errors else 'Ouvert' if opened else 'Prêt' if self.catalog.detect(key) else 'Non installé'
            row['card'].selected=key in self.profile['active'];row['card'].update()
            row['status'].setText(state);row['status'].setToolTip(self.catalog.errors.get(key,''))
            row['active'].blockSignals(True);row['active'].setChecked(key in self.profile['active']);row['active'].blockSignals(False)
            row['startup'].blockSignals(True);row['startup'].setChecked(key in self.startup_apps);row['startup'].blockSignals(False)
        self.compact_summary.setText(f'{running} ouverts · {len(APP_THEMES)-1} logiciels')
        if hasattr(self,'selection_filter') and self.selection_filter.isChecked():self.filter_compact()
    def refresh(self):
        if self.advanced_page is not None:super().refresh()
        else:self.catalog.poll()
        if hasattr(self,'compact_cards'):self.sync_rows()
    def apply_profile(self):
        if self.advanced_page is not None:super().apply_profile()
        else:self.toggle_animations(self.profile['animations']);self.apply_theme();self.refresh()
        if hasattr(self,'compact_cards'):self.sync_rows()
        if hasattr(self,'preset_box'):
            self.preset_box.blockSignals(True)
            if self.preset_box.findText(self.profile['name'])<0:self.preset_box.addItem(self.profile['name'])
            self.preset_box.setCurrentText(self.profile['name']);self.preset_box.blockSignals(False)
    def launch(self,key,minimized=False):
        if key not in self.profile['active']:self.profile['active'].append(key)
        if key not in self.launched_order:self.launched_order.append(key)
        self.profile['hidden']=[k for k in self.profile['hidden'] if k!=key]
        if key==self.starting_key:return
        for index,(queued,background) in enumerate(self.launch_queue):
            if queued==key:
                self.launch_queue[index]=(key,background and minimized);return
        if minimized:self.launch_queue.append((key,minimized))
        else:self.launch_queue.insert(0,(key,minimized))
        self.save();self.sync_rows()
        if not self.launch_busy:QTimer.singleShot(0,self._launch_next)
    def _launch_next(self):
        if self.shutting_down or self.launch_busy:return
        if not self.launch_queue:
            self.launch_status.setText('Votre sélection est prête.' if not self.catalog.errors else 'Certains logiciels n’ont pas démarré. Voir leur état dans la liste.');return
        key,minimized=self.launch_queue.pop(0);self.starting_key=key;self.launch_busy=True
        self.launch_status.setText('Démarrage de '+APP_THEMES[key]['name']+'…');self.sync_rows()
        from shared.jobs import Job
        job=Job(lambda:self.catalog.launch(key,minimized=minimized));self.pending.add(job);delay=[1100]
        def succeeded(started):
            if not started:delay[0]=0
            self.catalog.errors.pop(key,None)
            self.launch_status.setText(APP_THEMES[key]['name']+' · lancement effectué')
        def failed(message):
            self.catalog.errors[key]=message;self.launch_status.setText(APP_THEMES[key]['name']+' : '+message)
        def finished():
            self.pending.discard(job);self.launch_busy=False;self.starting_key=None
            if self.shutting_down:self.close();return
            if not self.shutting_down:
                self.sync_rows();QTimer.singleShot(500,self.sync_stack);QTimer.singleShot(delay[0],self._launch_next)
        job.signals.done.connect(succeeded);job.signals.error.connect(failed);job.signals.finished.connect(finished);QThreadPool.globalInstance().start(job)
    def toggle_active(self,key,enabled):
        self.list_choice('active',key,enabled)
        if enabled:self.launch(key,minimized=True)
        else:self.profile['hidden']=list(set(self.profile['hidden']+[key]));self.arrange_orbs();self.save()
        self.sync_rows()
    def save_hub_settings(self):
        path=self.store.path.parent/'hub-launcher.json';path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(dict(windows_apps=self.startup_apps,preset_seeded=self.preset_seeded,launcher_opacity=self.launcher_opacity)));temporary.replace(path)
    def prepare_profile(self,name):
        from shared.profiles import default_profile
        profile=next((p for p in self.profiles if p['name']==name),None)
        if profile is None:
            profile=default_profile(name);self.profiles.append(profile);self.profile_box.addItem(name)
        if name in PRESETS and name not in self.preset_seeded:
            if not profile['active']:profile['active']=list(PRESETS[name])
            self.preset_seeded.append(name);self.save_hub_settings()
        self.profile=profile;self.profile_box.blockSignals(True);self.profile_box.setCurrentIndex(self.profiles.index(profile));self.profile_box.blockSignals(False);self.apply_profile();self.save()
        self.notice.setText('Profil préparé · Charger le profil lance les logiciels cochés.')
    def load_chosen_profile(self):
        self.prepare_profile(self.preset_box.currentText());self.launch_active()
    def set_app_startup(self,key,enabled):
        if enabled and key not in self.startup_apps:self.startup_apps.append(key)
        elif not enabled and key in self.startup_apps:self.startup_apps.remove(key)
        self.save_hub_settings()
        try:
            from shared.startup import set_enabled
            set_enabled(bool(self.startup_apps) or self.start_windows.isChecked())
        except OSError as error:self.notice.setText(str(error))
    def launch_windows_apps(self):
        for index,key in enumerate(self.startup_apps):QTimer.singleShot(index*250,lambda k=key:self.launch(k,minimized=True))
    def launch_selected_on_startup(self,windows_startup=False):
        selected=list(dict.fromkeys(self.profile['active']+(self.startup_apps if windows_startup else [])))
        for key in selected:self.launch(key,minimized=True)
        QTimer.singleShot(1000+len(selected)*250,self.arrange_orbs)
    def toggle_launcher(self,*_):
        if self.launcher.isVisible():self.launcher.hide()
        else:self.hide();self.launcher.reveal()
    def orb_menu(self,*_):
        menu=QMenu(self);menu.setStyleSheet(style());menu.addAction('Tous les logiciels',self.toggle_launcher);menu.addAction('Ouvrir Ergonatus',self.reveal);menu.addSeparator();menu.addAction('Quitter Ergonatus',self.close);menu.exec(self.hub_orb.mapToGlobal(QPoint(0,0)))
    def sync_stack(self):
        if self.shutting_down:return
        if os.environ.get('ERGONATUS_TEST_MODE')!='1':self.catalog.settle_native_background()
        running=tuple(k for k in APP_THEMES if k!='ergonatus' and self.catalog.running(k))
        if running!=self.last_running:self.last_running=running;self.arrange_orbs()
        try:
            if self.catalog.layout_path.stat().st_size<=32000:self.native_positions=json.loads(self.catalog.layout_path.read_text()).get('apps',self.native_positions)
        except (OSError,ValueError):pass
        self.place_native_orbs()
        for key,orb in self.external_orbs.items():
            entry=self.native_positions.get(key,{})
            if entry.get('visible') and entry.get('position'):orb.move(*entry['position'])
        if hasattr(self,'hub_orb'):
            from shared.orb_layout import read_layout
            entry=read_layout('ergonatus')
            if entry and entry.get('position'):self.hub_orb.move(*entry['position'])
    def arrange_orbs(self):
        if self.shutting_down or not hasattr(self,'hub_orb'):return
        running=[k for k in APP_THEMES if k!='ergonatus' and self.catalog.running(k)]
        order=['ergonatus']+[k for k in self.launched_order if k in running and k not in self.profile['hidden']]
        order +=[k for k in running if k not in order and k not in self.profile['hidden']]
        area=QApplication.primaryScreen().availableGeometry();positions=selected_stack(area,order)
        entries={key:dict(visible=key in order,position=positions[order.index(key)] if key in order else None) for key in APP_THEMES}
        self.hub_orb.move(*positions[0]);path=self.catalog.layout_path;path.parent.mkdir(exist_ok=True);temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(dict(version=1,apps=entries)));temporary.replace(path);os.environ['ERGONATUS_ORB_LAYOUT']=str(path)
        self.native_positions=entries;self.place_native_orbs()
        for key in ('ecrinator','pdfinator'):
            visible=entries[key]['visible']
            if visible and key not in self.external_orbs:
                orb=ErgoOrb(key,floating=True,preview=False);orb.setWindowTitle(APP_THEMES[key]['name']+' · Orb Ergonatus')
                orb.activated.connect(lambda *_,k=key:self.launch(k));orb.doubleActivated.connect(lambda *_,k=key:self.launch(k));self.external_orbs[key]=orb
                orb.setContextMenuPolicy(Qt.CustomContextMenu);orb.customContextMenuRequested.connect(lambda *_,k=key:self.external_orb_menu(k))
            if key in self.external_orbs:
                orb=self.external_orbs[key]
                if visible:orb.move(*entries[key]['position']);orb.show()
                else:orb.hide()
    def external_orb_menu(self,key):
        menu=QMenu(self);menu.setStyleSheet(style());menu.addAction('Ouvrir '+APP_THEMES[key]['name'],lambda:self.launch(key));menu.addAction('Quitter '+APP_THEMES[key]['name'],lambda:self.catalog.stop(key));menu.exec(self.external_orbs[key].mapToGlobal(QPoint(0,0)))
    def place_native_orbs(self):
        # Existing native Orbs also join the stack, even if launched before the hub.
        if os.environ.get('ERGONATUS_TEST_MODE')=='1':return
        try:
            import win32gui,win32con
            for orb in self.manager.native_orbs():
                entry=self.native_positions.get(orb['app'])
                if entry and entry['visible']:
                    x,y=entry['position'];ratio=QApplication.primaryScreen().devicePixelRatio();target=(round(x*ratio),round(y*ratio))
                    if win32gui.GetWindowRect(orb['hwnd'])[:2]!=target:win32gui.SetWindowPos(orb['hwnd'],win32con.HWND_TOPMOST,*target,0,0,win32con.SWP_NOACTIVATE|win32con.SWP_NOSIZE)
        except (ImportError,OSError):pass
    def closeEvent(self,event):
        if self.launch_busy:
            self.shutting_down=True;self.launch_queue.clear();self.launch_status.setText('Fermeture de la suite…');event.ignore();return
        self.shutting_down=True
        if os.environ.get('ERGONATUS_TEST_MODE')!='1':self.catalog.quit_suite()
        if hasattr(self,'layout_timer'):self.layout_timer.stop()
        if hasattr(self,'launcher'):self.launcher.close()
        if hasattr(self,'hub_orb'):self.hub_orb.close()
        for orb in self.external_orbs.values():orb.close()
        if getattr(self,'previous_layout_env',None):os.environ['ERGONATUS_ORB_LAYOUT']=self.previous_layout_env
        else:os.environ.pop('ERGONATUS_ORB_LAYOUT',None)
        super().closeEvent(event);QApplication.instance().quit()
