"""Live suite interaction layer, shared by independently frozen Qt applications."""
import math,time,sys,types,weakref,json,threading,os,subprocess
from pathlib import Path
from PySide6.QtCore import Qt,QObject,QTimer,QEvent,QRectF,QPointF,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QPainterPath,QPolygonF,QPixmap
from PySide6.QtWidgets import QApplication,QWidget,QMenu,QLabel,QWidgetAction,QMessageBox,QDialog,QPushButton,QFrame,QVBoxLayout,QHBoxLayout

ROOT=Path(__file__).resolve().parent
GUIDE=json.loads((ROOT/'suite_interactions.json').read_text(encoding='utf-8'))

class Hourglass(QWidget):
    def __init__(self):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowTransparentForInput|Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_ShowWithoutActivating);self.setFocusPolicy(Qt.NoFocus);self.setFixedSize(136,160);self.setWindowTitle('Ergonatus · Traitement en cours');self.setAccessibleName('Traitement en cours, veuillez patienter');self.started=0;self.color=QColor('#253B70');self.name='';self.animated=True;self.timer=QTimer(self);self.timer.setInterval(40);self.timer.timeout.connect(self.update)
    def begin(self,owner,key,animated=True):
        data=GUIDE.get(key,GUIDE['ergonatus']);self.color=QColor(data['accent']);self.name=data['name'];self.animated=animated
        if not self.isVisible():
            screen=owner.screen() or QApplication.primaryScreen();area=screen.availableGeometry();self.move(area.center().x()-68,area.center().y()-80);self.started=time.monotonic();self.show()
        if animated:self.timer.start()
        else:self.timer.stop()
        self.update()
    def finish(self):self.timer.stop();self.hide()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);c=self.color;p.setPen(QPen(QColor(c.red(),c.green(),c.blue(),65),1));p.setBrush(QColor(252,254,255,248));p.drawRoundedRect(QRectF(1,1,134,158),20,20)
        p.save();p.translate(68,61);phase=(time.monotonic()-getattr(self,'started',time.monotonic()))%5.6 if self.animated else 1.8;progress=min(1,phase/4.9);turn=max(0,(phase-4.9)/.7);p.rotate(180*turn*turn*(3-2*turn))
        glass=QPainterPath();glass.moveTo(-25,-33);glass.lineTo(25,-33);glass.cubicTo(24,-16,7,-7,2,0);glass.cubicTo(7,7,24,16,25,33);glass.lineTo(-25,33);glass.cubicTo(-24,16,-7,7,-2,0);glass.cubicTo(-7,-7,-24,-16,-25,-33);glass.closeSubpath()
        p.setBrush(QColor(241,247,250));p.setPen(QPen(QColor('#B4C8D3'),1.6));p.drawPath(glass)
        p.save();p.setClipPath(glass);p.setPen(Qt.NoPen);sand=QColor(c.lighter(125));sand.setAlpha(215);p.setBrush(sand)
        surface=-31+progress*31;p.drawRect(QRectF(-26,surface,52,max(0,-surface)))
        peak=32-29*math.sqrt(progress);pile=QPainterPath();pile.moveTo(-26,34);pile.cubicTo(-17,32,-5,peak+2,0,peak);pile.cubicTo(5,peak+2,17,32,26,34);pile.closeSubpath();p.setBrush(c);p.drawPath(pile)
        if progress<.99:
            p.setPen(QPen(c,1.5,Qt.SolidLine,Qt.RoundCap))
            for n in range(9):
                y=2+(phase*65+n*4)%max(3,peak-1);p.drawPoint(QPointF(math.sin(n*3)*.55,y))
        p.restore();p.setPen(QPen(QColor(255,255,255,210),1.2));p.drawLine(QPointF(-20,-29),QPointF(-17,-17));p.drawLine(QPointF(17,18),QPointF(20,29))
        p.setPen(QPen(c.darker(120),4,Qt.SolidLine,Qt.RoundCap));p.drawLine(-30,-37,30,-37);p.drawLine(-30,37,30,37);p.restore()
        f=p.font();f.setPointSize(9);f.setBold(True);p.setFont(f);p.setPen(c.darker(130));p.drawText(QRectF(5,111,126,23),Qt.AlignCenter,self.name);f.setPointSize(8);f.setBold(False);p.setFont(f);p.setPen(QColor('#53677A'));p.drawText(QRectF(5,136,126,18),Qt.AlignCenter,'Traitement en cours');p.end()


def app_key(app,owner=None):
    key=getattr(owner,'app_id','')
    if key in GUIDE:return key
    name=app.applicationName().casefold().replace('é','e')
    if 'fortinatus' in name:return 'claviernator'
    return next((key for key in GUIDE if key in name),'ergonatus')

class HelpSpeaker:
    def __init__(self):self.stop=threading.Event();self.process=None
    def speak(self,text,**kwargs):
        if self.stop.is_set():return False
        shell=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe')
        command='[Console]::InputEncoding=[System.Text.Encoding]::UTF8; Add-Type -AssemblyName System.Speech; $voice=New-Object System.Speech.Synthesis.SpeechSynthesizer; $voice.Rate=-1; $voice.SetOutputToDefaultAudioDevice(); $voice.Speak([Console]::In.ReadToEnd())'
        self.process=subprocess.Popen([shell,'-NoProfile','-NonInteractive','-Command',command],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            _,error=self.process.communicate(text.encode('utf-8'),timeout=120)
            if self.process.returncode and not self.stop.is_set():raise ValueError('Voix locale indisponible.')
            return not self.stop.is_set()
        finally:
            if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=3)
    def cancel(self):
        self.stop.set()
        if self.process is not None and self.process.poll() is None:self.process.terminate()


class HelpDialog(QDialog):
    speech_done=Signal(str)
    def __init__(self,owner,key):
        super().__init__(owner,Qt.Dialog|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_DeleteOnClose);self._suite_clarity=True;self.setWindowTitle('Aide · '+GUIDE[key]['name']);self.setFixedWidth(490)
        try:
            from shared.speech import Speaker
            self.speaker=Speaker()
        except ImportError:self.speaker=HelpSpeaker()
        self.reading=False;data=GUIDE[key];self.spoken=data['name']+'. '+data['description']+' '+data['gestures'];outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);panel=QFrame();panel.setObjectName('HelpPanel');panel.setStyleSheet('QFrame#HelpPanel {background:#FFFFFF;border:1px solid '+data['accent']+';border-radius:18px;} QLabel {border:none;background:transparent;color:#21364D;font:11pt "Segoe UI";} QPushButton {padding:8px 14px;min-height:24px;background:#F0F5F7;color:#21364D;border:1px solid #BACBD5;border-radius:10px;} QPushButton:hover {background:#E1EDF1;}');box=QVBoxLayout(panel);box.setContentsMargins(22,18,22,20);box.setSpacing(14);outer.addWidget(panel)
        row=QHBoxLayout();badge=QLabel();badge.setPixmap(QPixmap(str(ROOT/'assets/orbs'/f'{key}.png')).scaled(36,36,Qt.KeepAspectRatio,Qt.SmoothTransformation));row.addWidget(badge);title=QLabel(data['name']);title.setStyleSheet('font-size:17pt;font-weight:600;');row.addWidget(title,1);close=QPushButton('×');close.setFixedSize(34,34);close.setAccessibleName('Fermer l’aide');close.clicked.connect(self.close);row.addWidget(close);box.addLayout(row)
        description=QLabel(data['description']);description.setWordWrap(True);description.setStyleSheet('font-size:12pt;font-weight:600;');box.addWidget(description)
        for line in data['gestures'].split('. '):
            label=QLabel(line.rstrip('.'));label.setWordWrap(True);box.addWidget(label)
        self.audio_status=QLabel('');self.audio_status.hide();box.addWidget(self.audio_status)
        row=QHBoxLayout();self.read_button=QPushButton('Écouter');self.read_button.setAccessibleName('Lire cette aide à voix haute');self.read_button.clicked.connect(self.toggle_speech);row.addWidget(self.read_button);row.addStretch();done=QPushButton('Compris');done.clicked.connect(self.close);row.addWidget(done);box.addLayout(row);self.speech_done.connect(self.speech_finished)
    def toggle_speech(self):
        if self.reading:self.speaker.cancel();return
        self.reading=True;self.speaker.stop.clear();self.read_button.setText('Arrêter')
        def read():
            error=''
            try:self.speaker.speak(self.spoken,rate=-1,gentle=True)
            except Exception as problem:error=str(problem)
            finally:
                try:self.speech_done.emit(error)
                except RuntimeError:pass
        threading.Thread(target=read,daemon=True).start()
    def speech_finished(self,error):self.reading=False;self.read_button.setText('Écouter');self.audio_status.setText('Lecture vocale indisponible.' if error else '');self.audio_status.setVisible(bool(error))
    def closeEvent(self,event):self.speaker.cancel();super().closeEvent(event)


def explain(owner,key):
    previous=getattr(owner,'_suite_help_dialog',None)
    if previous is not None:
        try:previous.close()
        except RuntimeError:pass
    dialog=HelpDialog(owner,key);owner._suite_help_dialog=dialog;dialog.adjustSize();area=owner.screen().availableGeometry();dialog.move(area.center()-dialog.rect().center());dialog.show();dialog.raise_();dialog.activateWindow()


def decorate_menu(menu,key,owner):
    if getattr(menu,'_suite_clarity',False):return
    menu._suite_clarity=True;data=GUIDE[key];menu.setStyleSheet('QMenu {background:#FFFFFF;color:#203346;border:1px solid '+data['accent']+';border-radius:12px;padding:6px;font:10pt "Segoe UI";} QMenu::item {padding:9px 16px;border-radius:7px;} QMenu::item:selected {background:#E8F2F2;} QMenu::item:disabled {color:#8B979F;} QMenu::separator {height:1px;background:#E1E8EC;margin:5px 8px;}')
    original=menu.actions();quit_action=next((a for a in original if a.text().casefold().startswith('quitter')),None)
    if isinstance(menu.parentWidget(),QMenu) or quit_action is None:return
    primary_label=PRIMARY.get(key,('',None))[0] if key in PRIMARY else ''
    opening=next((a for a in original if a.text().startswith('Ouvrir ')),None)
    primary=next((a for a in original if primary_label and a.text()==primary_label),None)
    for action in original:menu.removeAction(action)
    if opening:
        if key=='temporator':opening.setText('Régler le minuteur')
        menu.addAction(opening)
    if primary:menu.addAction(primary)
    elif key=='ergonatus':
        toggle=next((a for a in original if 'tous les logiciels' in a.text().casefold()),None)
        if toggle:menu.addAction(toggle)
    settings=QMenu('Réglages',menu);settings._suite_clarity=True;settings.setStyleSheet(menu.styleSheet());seen=set()
    for action in original:
        text=action.text();folded=text.casefold()
        if action in (opening,primary,quit_action) or action.isSeparator() or not text or folded.startswith(('aide','à quoi sert','afficher / masquer','masquer le minuteur','masquer le cadran')):continue
        if text in seen:continue
        seen.add(text);settings.addAction(action)
    if owner is not None and hasattr(owner,'hide_orb') and not owner.orb.isVisible():settings.addAction('Afficher l’Orb',lambda:owner.hide_orb(False))
    if settings.actions():menu.addMenu(settings)
    if owner is not None:menu.addAction('Aide et lecture vocale',lambda:explain(owner,key))
    menu.addSeparator();menu.addAction(quit_action)

PRIMARY={
 'tablinator':('Afficher / masquer les tables','toggle_widget'),
 'organisator':('Afficher / masquer le classeur','toggle_binder'),
 'planinator':('Afficher / masquer aujourd’hui et demain','activate'),
 'memorinator':('Afficher / masquer les notes','activate'),
 'applinator':('Afficher / masquer mes raccourcis','activate'),
 'temporator':('Afficher / masquer le minuteur','activate'),
 'explicator':('Capturer un exercice','capture'),
 'corrector':('Corriger une sélection','activate'),
}

class SuiteInteractions(QObject):
    def __init__(self,app):
        super().__init__(app);self.app=app
        theme=sys.modules.get('shared.ui.theme')
        if theme is not None:
            for key,value in GUIDE.items():
                if key in theme.APP_THEMES:theme.APP_THEMES[key]['description']=value['description']
        self.orb_owners=weakref.WeakKeyDictionary();self.audit_started=time.monotonic();self.audit_done=False;self.hourglass=Hourglass();self.since={};self.timer=QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.poll);self.timer.start();app.installEventFilter(self);app.aboutToQuit.connect(self.hourglass.finish)
    def hook_jobs(self):
        module=sys.modules.get('shared.jobs')
        if module is None or getattr(module.background,'_suite_tracked',False):return
        original=module.background
        def tracked(owner,function,done):
            owner._suite_job_count=getattr(owner,'_suite_job_count',0)+1
            try:job=original(owner,function,done)
            except Exception:owner._suite_job_count=max(0,owner._suite_job_count-1);raise
            def finish():owner._suite_job_count=max(0,getattr(owner,'_suite_job_count',1)-1)
            job.signals.finished.connect(finish);return job
        tracked._suite_tracked=True;module.background=tracked
        for name,loaded in list(sys.modules.items()):
            if name.startswith(('shared.','Hub.')) and getattr(loaded,'background',None) is original:loaded.background=tracked
    def hook_window(self,owner,key):
        if hasattr(owner,'create_orb_menu') and not getattr(owner,'_suite_menu_hooked',False):
            owner._suite_menu_hooked=True;original=owner.create_orb_menu
            if hasattr(owner,'speech_segment'):
                owner.speech_segment.connect(lambda text:setattr(owner,'_suite_speech_started',bool(text)))
            def create(_self):
                menu=original();actions=menu.actions();before=actions[1] if len(actions)>1 else None
                if key in PRIMARY:
                    label,method=PRIMARY[key];callback=getattr(owner,method,None)
                    if callable(callback):
                        action=menu.addAction(label,callback)
                        if before:menu.insertAction(before,action)
                action=menu.addAction('Masquer la fenêtre',owner.hide)
                if before:menu.insertAction(before,action)
                decorate_menu(menu,key,owner);return menu
            owner.create_orb_menu=types.MethodType(create,owner)
            # Right-click always opens the menu, including older Lector binaries.
            def show_menu(point):
                for name in ('_suite_orb_single_timer','click_timer','binder_click'):
                    timer=getattr(owner,name,None)
                    if isinstance(timer,QTimer):timer.stop()
                timer=getattr(owner.orb,'single_click',None)
                if isinstance(timer,QTimer):timer.stop()
                menu=owner.create_orb_menu()
                try:menu.exec(owner.orb.mapToGlobal(point))
                finally:menu.deleteLater()
            owner.orb.setContextMenuPolicy(Qt.CustomContextMenu);owner.orb.customContextMenuRequested.disconnect();owner.orb.customContextMenuRequested.connect(show_menu)
            if key=='lector' and hasattr(owner,'lector_capture'):
                timer=QTimer(owner);timer.setSingleShot(True);timer.setInterval(QApplication.doubleClickInterval());timer.timeout.connect(lambda:owner.activate());owner._suite_orb_single_timer=timer;self.orb_owners[owner.orb]=weakref.ref(owner)
                owner.open_main_window=types.MethodType(lambda _self:owner.open_lector_window(),owner)

            data=GUIDE[key];owner.orb.setToolTip(data['name']+'\n'+data['description']+'\n'+data['gestures']);owner.orb.setAccessibleDescription(data['gestures'])
    def hook_hub(self,owner):
        if not hasattr(owner,'hub_orb') or getattr(owner,'_suite_hub_menu',False):return
        owner._suite_hub_menu=True
        owner.show_app_help=types.MethodType(lambda _owner,key,anchor=None:explain(owner,key),owner)
        def show_hub(point):
            menu=QMenu(owner);menu.addAction('Ouvrir Ergonatus',owner.reveal);menu.addAction('Afficher / masquer tous les logiciels',owner.toggle_launcher);menu.addSeparator();menu.addAction('Quitter toute la suite',owner.close);decorate_menu(menu,'ergonatus',owner)
            try:menu.exec(owner.hub_orb.mapToGlobal(point))
            finally:menu.deleteLater()
        owner.hub_orb.customContextMenuRequested.disconnect();owner.hub_orb.customContextMenuRequested.connect(show_hub)
        def external(_owner,key):
            menu=QMenu(owner);data=GUIDE[key];menu.addAction('Ouvrir '+data['name'],lambda:owner.launch(key));menu.addSeparator();menu.addAction('Quitter '+data['name'],lambda:owner.catalog.stop(key));decorate_menu(menu,key,owner)
            try:menu.exec(owner.external_orbs[key].mapToGlobal(owner.external_orbs[key].rect().topLeft()))
            finally:menu.deleteLater()
        owner.external_orb_menu=types.MethodType(external,owner)
    def is_busy(self,owner):
        if getattr(owner,'closing',False) or hasattr(owner,'busy_indicator'):return False
        status=getattr(owner,'status',None)
        if isinstance(status,QLabel) and status.text().startswith(('Chargement local','Préparation du moteur')):return True
        for item in (owner,getattr(owner,'controller',None)):
            if item is None:continue
            if any(getattr(item,name,False) is True for name in ('busy','ocr_busy','loading','processing','recognizing','math_busy','launch_busy')):return True
            machine=getattr(item,'machine',None);state=getattr(machine,'state',None)
            if getattr(state,'value',state) in ('Préparation…','Traitement…'):return True
        if getattr(owner,'job_id',None):return True
        # Speech playback has its own preparation indicator; don't cover reading.
        if getattr(owner,'speaking',False):return not getattr(owner,'_suite_speech_started',False) and getattr(owner,'_suite_job_count',0)>0
        if getattr(owner,'playing',None):return False
        return getattr(owner,'_suite_job_count',0)>0
    def poll(self):
        self.hook_jobs();active=[];now=time.monotonic()
        for owner in self.app.topLevelWidgets():
            if owner is self.hourglass:continue
            try:
                if not (hasattr(owner,'orb') or hasattr(owner,'controller') or hasattr(owner,'busy') or hasattr(owner,'hub_orb') or hasattr(owner,'_suite_job_count')):continue
                key=app_key(self.app,owner);self.hook_window(owner,key);self.hook_hub(owner)
                if self.is_busy(owner):
                    self.since.setdefault(id(owner),now)
                    if now-self.since[id(owner)]>=.25:active.append((owner,key))
                else:self.since.pop(id(owner),None)
            except RuntimeError:continue
        import os
        audit=os.environ.get('ERGONATUS_INTERACTION_AUDIT')
        if audit and not self.audit_done and now-self.audit_started>.45:
            self.audit_done=True;menus=[]
            for owner in self.app.topLevelWidgets():
                if hasattr(owner,'create_orb_menu'):
                    menu=owner.create_orb_menu();menus.append([a.text() for a in menu.actions() if a.text()]);menu.deleteLater()
                elif isinstance(owner,QMenu) and any(a.text().startswith('Quitter') for a in owner.actions()):
                    decorate_menu(owner,app_key(self.app),None);menus.append([a.text() for a in owner.actions() if a.text()])
            Path(audit).write_text(json.dumps(dict(app=self.app.applicationName(),menus=menus,hourglass_available=True),ensure_ascii=False,indent=2),encoding='utf-8')
        if active:
            owner,key=active[0];self.hourglass.begin(owner,key,getattr(owner,'preferences',{}).get('animations',True))
        else:self.hourglass.finish()
    def show_help(self,owner,key=None):explain(owner,key or app_key(self.app,owner))
    def eventFilter(self,watched,event):
        if isinstance(watched,QWidget) and event.type() in (QEvent.ShortcutOverride,QEvent.KeyPress) and event.key()==Qt.Key_F1:
            if event.type()==QEvent.KeyPress:explain(watched.window(),app_key(self.app,watched.window()))
            event.accept();return True
        if type(watched).__name__=='ErgoOrb' and getattr(watched,'app_id',None)=='lector':
            ref=self.orb_owners.get(watched);owner=ref() if ref else None
            if owner is not None:
                if event.type()==QEvent.ToolTipChange:
                    text=watched.toolTip();fixed=text.replace('clic droit pour réessayer','double-clic pour réessayer')
                    if fixed!=text:watched.setToolTip(fixed)
                timer=owner._suite_orb_single_timer
                if event.type()==QEvent.MouseButtonDblClick and event.button()==Qt.LeftButton:
                    timer.stop();old=getattr(watched,'single_click',None)
                    if isinstance(old,QTimer):old.stop()
                    watched.press_pos=None;watched.dragged=False;owner.lector_capture.start();event.accept();return True
                if event.type()==QEvent.MouseButtonRelease and event.button()==Qt.LeftButton and watched.press_pos is not None:
                    if watched.dragged:timer.stop()
                    elif watched.rect().contains(event.position().toPoint()):
                        watched.press_pos=None;timer.start();event.accept();return True
                if event.type()==QEvent.MouseButtonPress and event.button()==Qt.RightButton:timer.stop()
        if type(watched).__name__=='ReadingBusy':
            if event.type()==QEvent.Show:
                data=GUIDE[app_key(self.app,watched)];watched.setFixedSize(136,160);watched.color=QColor(data['accent']);watched.name=data['name'];watched.setWindowTitle(data['name']+' · Traitement en cours')
            if event.type()==QEvent.Paint and hasattr(watched,'color'):
                watched.animated=watched.timer.isActive();Hourglass.paintEvent(watched,event);return True
        if isinstance(watched,QMenu):
            if event.type()==QEvent.Show:
                owner=watched.parentWidget()
                if owner is None:owner=next((w for w in self.app.topLevelWidgets() if hasattr(w,'orb') or hasattr(w,'controller') or hasattr(w,'busy')),None)
                key=app_key(self.app,owner);labels=' '.join(a.text() for a in watched.actions())
                key=next((k for k,d in GUIDE.items() if 'Ouvrir '+d['name'] in labels),key);decorate_menu(watched,key,owner)
            if event.type()==QEvent.Paint and getattr(watched,'_suite_clarity',False):
                # Bypass old custom dark-menu paints, retain Qt actions/navigation.
                QMenu.paintEvent(watched,event);return True
        return False

def install(app):
    if not getattr(app,'_suite_interactions',None):app._suite_interactions=SuiteInteractions(app)
