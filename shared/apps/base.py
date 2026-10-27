from pathlib import Path
import json
import hashlib
import os
import sys
from PySide6.QtCore import Qt,QTimer,QPoint,Signal
from PySide6.QtGui import QIcon,QGuiApplication,QActionGroup
from PySide6.QtWidgets import (QApplication,QWidget,QVBoxLayout,QHBoxLayout,QMenu,QSystemTrayIcon,
    QLabel,QPlainTextEdit,QFileDialog,QMessageBox,QSizeGrip,QFrame)
from PySide6.QtNetwork import QLocalServer,QLocalSocket
from shared.catalog import suite_root
from shared.ui.theme import APP_THEMES,stylesheet,accent_button_style
from shared.ui.components import ErgoWindow,ErgoButton,ErgoOrb,ErgoBackdrop
from shared.domain import Records,app_data
from shared.jobs import background
from shared.speech import Speaker
from orb_manager.manager import stack_positions,clamp_position

def instance_name(app_id):
    identity=os.environ.get('USERNAME','local')+os.environ.get('USERDOMAIN','')+str(app_data('ipc').parent.resolve())
    return 'Ergonatus.App.v1.'+hashlib.sha256(identity.encode()).hexdigest()[:16]+'.'+app_id

class ApplicationWindow(ErgoWindow):
    speech_segment=Signal(str)
    def __init__(self,app_id):
        super().__init__();self.app_id=app_id;self.theme=APP_THEMES[app_id];self.pending=set();self.speaker=Speaker();self.action_count=0
        self.records=Records(app_id);self.closing=False
        self.setWindowTitle(self.theme['name']);self.setAccessibleName(self.theme['name'])
        icon=QIcon(str(suite_root()/'assets/orbs'/f'{app_id}.png'));self.setWindowIcon(icon)
        self.setStyleSheet(stylesheet(True,accent=self.theme['accent']))
        root=ErgoBackdrop(app_id);self.setCentralWidget(root);self.layout=QVBoxLayout(root);self.layout.setContentsMargins(20,16,20,16)
        header_area=QFrame();header_area.setObjectName('WindowHeader');header=QHBoxLayout(header_area);header.setContentsMargins(0,0,0,0);self.drag_area(header_area)
        badge=QLabel();badge.setPixmap(icon.pixmap(24,24));badge.setFixedWidth(26);header.addWidget(badge);self.drag_area(badge)
        brand=QLabel(self.theme['name'].upper());brand.setStyleSheet('font-size:16pt;font-weight:600;letter-spacing:1px;color:#F0F5F7;');self.drag_area(brand);header.addWidget(brand,1)
        hide=self.button('−',self.hide,header);hide.setFixedWidth(44);hide.setAccessibleName('Masquer la fenêtre')
        close=self.button('×',self.hide,header);close.setFixedWidth(44);close.setAccessibleName('Fermer la fenêtre sans arrêter l’aide');close.setToolTip('Fermer la fenêtre · retrouver le logiciel avec son Orb');self.layout.addWidget(header_area)
        self.status=QLabel('Prêt.');self.status.setWordWrap(True);self.layout.addWidget(self.status)
        self.behavior.message.connect(self.status.setText);self.behavior.configure(app_data(app_id)/'window.json')
        self.content=QVBoxLayout();self.layout.addLayout(self.content,1)
        self.layout.addWidget(QSizeGrip(self),0,Qt.AlignRight)
        self.orb=ErgoOrb(app_id,floating=True,preview=False);self.orb.setWindowTitle(self.theme['name']+' · Orbe')
        self.orb.activated.connect(self.activate);self.orb.moved.connect(self.store_position)
        self.orb.setContextMenuPolicy(Qt.CustomContextMenu);self.orb.customContextMenuRequested.connect(self.orb_menu)
        self.orb.setAccessibleDescription('Ouvrir le logiciel. Glisser pour déplacer. Clic droit pour le menu.')
        settings=self.records.all('settings');self.preferences=settings[0][1] if settings else {}
        self.settings_id=settings[0][0] if settings else self.records.add('settings',{})
        if os.environ.get('ERGONATUS_SHARED_AI')=='1' and self.preferences.get('orb_hidden'):
            self.preferences['orb_hidden']=False;self.records.update(self.settings_id,'settings',self.preferences)
        area=QApplication.primaryScreen().availableGeometry();rank=list(APP_THEMES).index(app_id)-1
        pos=self.preferences.get('position',stack_positions(area,len(APP_THEMES))[rank]);screen=QApplication.screenAt(QPoint(*pos)) or QApplication.primaryScreen()
        self.orb.move(*clamp_position(pos,screen.availableGeometry()));self.orb.set_animations(self.preferences.get('animations',True))
        self.orb.setVisible(not self.preferences.get('orb_hidden',False))
        self.tray=QSystemTrayIcon(icon,self);menu=QMenu();menu.addAction('Ouvrir '+self.theme['name'],lambda:ApplicationWindow.activate(self));menu.addAction('Afficher l’Orb',lambda:self.hide_orb(False));menu.addAction('Quitter',self.quit);self.tray.setContextMenu(menu)
        self.tray.hide()  # Ergonatus alone owns the suite notification icon.
        self.tray.activated.connect(lambda reason:ApplicationWindow.activate(self) if reason==QSystemTrayIcon.Trigger else None)
        self.server=QLocalServer(self);self.server.setSocketOptions(QLocalServer.UserAccessOption)
        if not self.server.listen(instance_name(app_id)):raise ValueError('Une autre instance est ouverte ou le service local est inaccessible.')
        self.sockets=set();self.server.newConnection.connect(self.accept)
        self.state('Activée')
        self.hotkey=None
        from shared.hotkey import KEYS
        if app_id in KEYS and os.environ.get('ERGONATUS_NO_HOTKEYS')!='1':self.set_hotkey(self.preferences.get('hotkey',True))
        self.layout_timer=QTimer(self);self.layout_timer.setInterval(350);self.layout_timer.timeout.connect(self.apply_live_layout);self.layout_timer.start();self.apply_live_layout()

    def button(self,text,callback,layout=None):
        widget=ErgoButton(text);widget.clicked.connect(callback);(layout or self.content).addWidget(widget);self.action_count+=1
        if self.action_count==3:widget.setStyleSheet(accent_button_style(self.theme['accent']))
        return widget
    def row(self):
        row=QHBoxLayout();self.content.addLayout(row);return row
    def remember(self,key,value):
        self.preferences[key]=value
        self.records.update(self.settings_id,'settings',self.preferences)
    def editor(self,placeholder=''):
        widget=QPlainTextEdit();widget.setPlaceholderText(placeholder);widget.setAccessibleName(placeholder or 'Texte');self.content.addWidget(widget,1);return widget
    def error(self,text):
        if not self.closing:self.status.setText(str(text));self.state('Erreur')
    def run(self,function,done):
        self.state('Traitement en cours');self.status.setText('Traitement local en cours…')
        def result(value):
            if self.closing:return
            self.state('Action réussie');self.status.setText('Terminé.');done(value)
        return background(self,function,result)
    def state(self,value):
        self.orb.update_state(value)
        identity=os.environ.get('USERNAME','local')+os.environ.get('USERDOMAIN','')
        name='Ergonatus.Orbs.v1.'+hashlib.sha256(identity.encode()).hexdigest()[:16]
        socket=QLocalSocket(self);socket.connectToServer(name)
        # Asynchronous: no waiting on the GUI thread when the hub is absent.
        socket.connected.connect(lambda:(socket.write((json.dumps(dict(version=1,app=self.app_id,state=value))+'\n').encode()),socket.flush(),socket.disconnectFromServer()))
        QTimer.singleShot(1000,socket,socket.deleteLater)
    def activate(self,*_):self.showNormal();self.raise_();self.activateWindow()
    def open_main_window(self):self.hide_orb(False);ApplicationWindow.activate(self)
    def store_position(self,key,pos):
        screen=QApplication.screenAt(QPoint(*pos)) or QApplication.primaryScreen();pos=clamp_position(pos,screen.availableGeometry())
        self.orb.move(*pos);self.preferences['position']=pos;self.records.update(self.settings_id,'settings',self.preferences)
        from shared.orb_layout import move_stack
        move_stack(self.app_id,pos)
    def apply_live_layout(self):
        if self.orb.press_pos is not None or getattr(self,'capture_pending',False):return
        from shared.orb_layout import read_layout
        entry=read_layout(self.app_id)
        if entry is None:return
        self.orb.setVisible(entry['visible'] and not self.preferences.get('orb_hidden',False))
        if entry['position'] is not None:
            screen=QApplication.screenAt(QPoint(*entry['position'])) or QApplication.primaryScreen();self.orb.move(*clamp_position(entry['position'],screen.availableGeometry(),36))
    def create_orb_menu(self):
        menu=QMenu(self);menu.addAction('Ouvrir '+self.theme['name'],self.open_main_window)
        if self.app_id=='scanator':menu.addAction('Capturer du texte',self.activate)
        if self.app_id=='lector':menu.addAction('Arrêter la lecture' if getattr(self,'lector_active',False) else 'Sélectionner et écouter',self.activate)
        if self.app_id=='lector' and hasattr(self,'lector_capture'):menu.addAction('Lire une zone de l’écran',self.lector_capture.start)
        if self.app_id=='lector' and hasattr(self,'voice_choice'):
            from ergoai.voice_models import installed_voices
            voices=installed_voices()
            if voices:
                submenu=menu.addMenu('Voix');group=QActionGroup(submenu);group.setExclusive(True)
                for label in voices:
                    action=submenu.addAction(label.split(' ·')[0]);action.setCheckable(True);action.setChecked(self.voice_name==label);group.addAction(action)
                    action.triggered.connect(lambda checked=False,name=label:self.voice_choice.setCurrentIndex(self.voice_choice.findData(name)))
        menu.addSeparator();menu.addAction('Masquer l’Orb',lambda:self.hide_orb(True))
        menu.addAction('Recentrer la fenêtre',lambda:(self.behavior.center(),self.open_main_window()));menu.addAction('Aide · F1',self.behavior.help)
        action=menu.addAction('Animations');action.setCheckable(True);action.setChecked(self.orb.animations)
        def animations(value):
            self.orb.set_animations(value);self.preferences['animations']=value;self.records.update(self.settings_id,'settings',self.preferences)
        action.toggled.connect(animations)
        from shared.hotkey import KEYS
        if self.app_id in KEYS:
            shortcut=menu.addAction('Raccourci '+KEYS[self.app_id][2]);shortcut.setCheckable(True);shortcut.setChecked(self.hotkey is not None and self.hotkey.active);shortcut.toggled.connect(self.set_hotkey)
        menu.addSeparator();menu.addAction('Quitter '+self.theme['name'],self.quit)
        return menu
    def orb_menu(self,point):
        menu=self.create_orb_menu()
        try:menu.exec(self.orb.mapToGlobal(point))
        finally:menu.deleteLater()
    def set_hotkey(self,enabled):
        from shared.hotkey import Hotkey
        if self.hotkey:
            QApplication.instance().removeNativeEventFilter(self.hotkey);self.hotkey.close();self.hotkey=None
        if enabled:
            self.hotkey=Hotkey(self.app_id,self.activate);QApplication.instance().installNativeEventFilter(self.hotkey)
            self.status.setText(('Raccourci : '+self.hotkey.label) if self.hotkey.active else 'Ce raccourci est déjà utilisé. L’Orb reste disponible.')
        self.preferences['hotkey']=enabled;self.records.update(self.settings_id,'settings',self.preferences)
    def hide_orb(self,hidden):
        self.preferences['orb_hidden']=hidden;self.records.update(self.settings_id,'settings',self.preferences);self.orb.setVisible(not hidden)
    def accept(self):
        socket=self.server.nextPendingConnection();self.sockets.add(socket);buffer=bytearray()
        def read():
            buffer.extend(bytes(socket.readAll()))
            if len(buffer)>2048:socket.abort();return
            if b'\n' not in buffer:return
            try:
                message=json.loads(buffer)
                if not isinstance(message,dict) or message.get('version')!=1:raise ValueError()
                command=message.get('command')
                if command=='show':self.open_main_window()
                elif command=='quit':QTimer.singleShot(50,self.quit)
                elif command=='orb_show':self.hide_orb(False)
                elif command=='orb_hide':self.hide_orb(True)
                elif command=='animations' and type(message.get('enabled')) is bool:self.orb.set_animations(message['enabled'])
                elif command=='position' and isinstance(message.get('position'),list) and len(message['position'])==2 and all(type(x) is int and abs(x)<100000 for x in message['position']):self.store_position(self.app_id,message['position'])
                else:raise ValueError()
                reply={'ok':True}
            except (ValueError,TypeError):reply={'ok':False}
            socket.write((json.dumps(reply)+'\n').encode());socket.flush();socket.disconnectFromServer()
        socket.readyRead.connect(read);socket.disconnected.connect(lambda:(self.sockets.discard(socket),socket.deleteLater()));QTimer.singleShot(2000,socket.abort)
        if socket.bytesAvailable():read()
    def copy(self,editor):QApplication.clipboard().setText(editor.toPlainText());self.status.setText('Texte copié. Collez-le dans l’application de votre choix.')
    def speak(self,text):
        if not text.strip():self.error('Saisissez un texte.');return
        if getattr(self,'speaking',False):self.error('Une lecture est déjà en cours. Arrêtez-la avant de recommencer.');return
        self.speaking=True;self.speaker.stop.clear()
        rate=getattr(self,'speech_rate',0);voice=getattr(self,'voice_name','')
        self.state('Traitement en cours');self.status.setText('Lecture en cours · clic sur l’Orb pour arrêter.')
        def completed(played):
            if self.closing:return
            self.speech_segment.emit('');self.state('Action réussie' if played else 'Activée');self.status.setText('Lecture terminée.' if played else 'Lecture arrêtée.')
        job=background(self,lambda:self.speaker.speak(text,rate=rate,voice=voice,on_segment=self.speech_segment.emit,gentle=self.app_id=='lector'),completed)
        job.signals.finished.connect(lambda:setattr(self,'speaking',False))
        return job
    def quit(self):
        self.behavior.save()
        self.closing=True;self.speaker.cancel()
        if self.hotkey:self.hotkey.close();QApplication.instance().removeNativeEventFilter(self.hotkey)
        if hasattr(self,'cancel'):self.cancel()
        if hasattr(self,'cleanup'):self.cleanup()
        self.orb.close();self.tray.hide();self.server.close()
        QApplication.instance().quit()
    def closeEvent(self,event):
        if self.closing:event.accept()
        else:self.hide();event.ignore()
