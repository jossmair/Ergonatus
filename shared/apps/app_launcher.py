"""User-configured Windows application shortcuts and dismissible desktop launcher."""
from pathlib import Path
import os,json,re,subprocess,unicodedata
from PySide6.QtCore import Qt,QSize,QUrl,QTimer,QFileInfo,QStandardPaths
from PySide6.QtGui import QColor,QPainter,QCursor,QDesktopServices,QIcon,QPixmap,QFont
from PySide6.QtWidgets import (QApplication,QWidget,QFrame,QLabel,QPushButton,QToolButton,QVBoxLayout,QHBoxLayout,QGridLayout,QListWidget,QListWidgetItem,QLineEdit,QDialog,QFileDialog,QFileIconProvider,QSlider,QAbstractItemView,QScrollArea,QLayout,QMenu,QComboBox,QGraphicsDropShadowEffect)
from shared.apps.base import ApplicationWindow
from shared.jobs import background
from shared.catalog import suite_root
from shared.ui.theme import APP_THEMES

EXTENSIONS={'.exe','.lnk','.appref-ms','.url','.bat','.cmd','.com','.msc'}
STYLE="""
QWidget {font-family:'Segoe UI';font-size:10pt;color:#EDF8FF;}
QLabel {background:transparent;border:none;}
QPushButton,QToolButton {background:#193E4C;border:1px solid #3D7183;border-radius:10px;padding:7px 12px;min-height:20px;}
QPushButton:hover,QToolButton:hover {background:#285D70;border-color:#95DAED;}
QPushButton:disabled {color:#7C929B;}
QListWidget,QLineEdit {background:#142A34;border:1px solid #3D6170;border-radius:12px;padding:8px;}
QListWidget::item {padding:8px;border-radius:8px;}
QListWidget::item:selected {background:#285D70;}
QDialog {background:#10232C;}
QFrame#LauncherCard {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #202D38,stop:1 #111A23);border:1px solid #475360;border-radius:24px;}
QPushButton#WidgetAction {background:transparent;border:1px solid transparent;border-radius:10px;min-width:20px;min-height:20px;padding:5px;color:#BBCBD5;}
QPushButton#WidgetAction:hover {background:#34424F;color:white;}
QLineEdit#WidgetSearch {background:#17232D;border:1px solid #384651;border-radius:11px;padding:9px 12px;color:#DBE6ED;}
QScrollArea,QScrollArea>QWidget>QWidget {background:transparent;border:none;}
QToolButton#AppTile {background:rgba(255,255,255,3);border:1px solid transparent;border-radius:18px;padding:10px;min-height:98px;max-height:98px;min-width:108px;max-width:108px;font-size:9.5pt;color:#E9EFF4;}
QListWidget::indicator {width:20px;height:20px;border:1px solid #6F9DAE;border-radius:6px;background:#142A34;}
QListWidget::indicator:checked {background:#499DB2;image:url(CHECK_ASSET);}
QComboBox {background:#183541;border:1px solid #456B7B;border-radius:9px;padding:8px;}
QComboBox QAbstractItemView {background:#183541;color:white;selection-background-color:#34677B;}
QMenu {background:#142B36;color:#EDF8FF;border:1px solid #4D7B8D;border-radius:10px;padding:7px;}
QMenu::item {background:transparent;color:#EDF8FF;padding:9px 22px;border-radius:6px;}
QMenu::item:selected {background:#2A596B;color:#FFFFFF;}
QMenu::separator {height:1px;background:#3B5D6B;margin:5px 8px;}
QScrollBar:vertical {width:7px;background:#122A35;border:none;}
QScrollBar::handle:vertical {background:#4C788B;min-height:30px;border-radius:3px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QToolButton#AppTile:hover {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #344955,stop:1 #25343F);border-color:#5B798B;}
QToolButton#AppTile:pressed {background:#20303B;border-color:#85C5DD;}
"""

def shortcut(path):
    if str(path).startswith('shell:AppsFolder\\'):
        app_id=str(path).split('\\',1)[1]
        if not re.fullmatch(r'[\w.{}!+\-]+',app_id) or '!' not in app_id:raise ValueError('Application Windows invalide.')
        return dict(name=app_id.split('!')[-1],path=str(path))
    path=Path(path).absolute()
    if not path.is_file() or path.suffix.lower() not in EXTENSIONS:raise ValueError('Choisissez un logiciel ou un raccourci Windows.')
    return dict(name=path.stem,path=str(path))

def discover_apps():
    roots=[Path(os.environ[key])/'Microsoft/Windows/Start Menu/Programs' for key in ('APPDATA','PROGRAMDATA') if os.environ.get(key)]
    desktop=Path(QStandardPaths.writableLocation(QStandardPaths.DesktopLocation));roots.extend([desktop])
    found={}
    for root in roots:
        if not root.is_dir():continue
        for directory,folders,files in os.walk(root,followlinks=False):
            folders[:]=[] if root==desktop else [f for f in folders if not (Path(directory)/f).is_symlink() and not (Path(directory)/f).is_junction()]
            for name in files:
                path=Path(directory)/name
                if path.suffix.lower() not in {'.lnk','.appref-ms','.url'}:continue
                key=str(path).casefold()
                found[key]=dict(name=path.stem,path=str(path))
                if len(found)>=2000:return preload_entries(list(found.values()))
    try:
        result=subprocess.run([str(Path(os.environ.get('WINDIR','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoProfile','-NonInteractive','-Command','[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); Get-StartApps | ConvertTo-Json -Compress'],capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        apps=json.loads(result.stdout.decode('utf-8-sig')) if result.returncode==0 else []
        if isinstance(apps,dict):apps=[apps]
        for app in apps:
            if isinstance(app,dict) and isinstance(app.get('AppID'),str) and '!' in app['AppID'] and re.fullmatch(r'[\w.{}!+\-]+',app['AppID']):
                target='shell:AppsFolder\\'+app['AppID'];found[target]=dict(name=str(app.get('Name') or app['AppID']),path=target)
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
    return preload_entries(list(found.values()))


def normalized_name(value):return ' '.join(unicodedata.normalize('NFKD',value.casefold()).encode('ascii','ignore').decode().split())


def app_category(name):
    name=normalized_name(name)
    groups=[('Internet',('firefox','chrome','edge','bittorrent')),('Bureautique',('word','excel','powerpoint','outlook','office','onenote','notepad','bloc-notes','acrobat','visio','project','pense-betes','sticky','calendrier','to do')),('Communication',('chatgpt','teams','whatsapp','skype','courrier','lifesize','mobile connecte')),('Création et médias',('paint','photo','camera','music','media','vlc','clipchamp','sweet home','xbox','solitaire','iptv')),('École et accessibilité',('pronote','activinspire','amical','voxirys','voiceaccess','livecaptions','handy','magnify','narrator','keyboard','lunii','transcri','tnt2'))]
    if name=='ergonatus':return 'Ergonatus'
    return next((category for category,words in groups if any(w in name for w in words)),'Utilitaires')


def preload_entries(entries):
    suite_names={normalized_name(a['name']) for a in APP_THEMES.values()}|{'dictator','gestinator','copinator'}
    technical=('help','aide','faq','documentation','manuals','module docs','website','readme','release notes','uninstall','desinstall','installer','install additional','mise a jour','updater','download assistant','diagnostic','debug','verifier','command prompt','powershell','native tools','cross tools','redistributable','nsight','gpuview','profiler','software development kit','cert kit','sample desktop','sample uwp','tools for desktop','tools for uwp','mode sans echec','reset preferences','skinned','distiller','server accounts','preferences linguistiques','convention de droits')
    exact={'administrative tools','character map','component services','computer management','control panel','database compare','dfrgui','disk cleanup','event viewer','hyper-v manager','iscsi initiator','odbc data sources (32-bit)','odbc data sources (64-bit)','performance monitor','print management','recoverydrive','registry editor','resource monitor','run','security configuration management','services','spreadsheet compare','steps recorder','system configuration','system information','task manager','task scheduler','vmcreate','windows performance analyzer','windows performance recorder','windows defender firewall with advanced security','node.js','terminal'}
    result=[];seen=set()
    for entry in entries:
        name=normalized_name(entry['name'])
        if any(re.search(r'\b'+re.escape(n)+r'\b',name) for n in suite_names):continue
        if any(word in name for word in technical) or name in exact or re.match(r'^(python |idle |navigation privee)',name):continue
        if Path(entry['path']).suffix.lower()=='.url':continue
        canonical=re.sub(r'\s*\((?:personal|x64|x86|32-bit|64-bit)\)','',name)
        if canonical in seen:continue
        seen.add(canonical);result.append(dict(entry,category=app_category(entry['name'])))
    hub=suite_root()/'Hub/Ergonatus.exe'
    if hub.is_file():result.append(dict(name='Ergonatus',path=str(hub),category='Ergonatus'))
    return sorted(result,key=lambda a:(a['category'],normalized_name(a['name'])))

class LauncherOverlay(QWidget):
    def __init__(self,owner):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.owner=owner;self.setAttribute(Qt.WA_TranslucentBackground);self.setWindowTitle('Applinator · Raccourcis');self.setStyleSheet(STYLE.replace('CHECK_ASSET',(suite_root()/'assets/check.svg').as_posix()))
        layout=QVBoxLayout(self);layout.setContentsMargins(28,28,28,28);layout.addStretch()
        row=QHBoxLayout();row.addStretch();self.card=QFrame();self.card.setObjectName('LauncherCard');self.card.setMaximumWidth(740);self.card.setMinimumWidth(280);row.addWidget(self.card,1);row.addStretch();layout.addLayout(row);layout.addStretch()
        shadow=QGraphicsDropShadowEffect(self.card);shadow.setBlurRadius(48);shadow.setOffset(0,14);shadow.setColor(QColor(0,0,0,110));self.card.setGraphicsEffect(shadow)
        content=QVBoxLayout(self.card);content.setContentsMargins(22,18,22,16);content.setSpacing(14);header=QHBoxLayout();title=QLabel('Mes raccourcis');title.setStyleSheet('font-size:16pt;font-weight:600;color:#F3F6F9;');header.addWidget(title,1)
        settings=QPushButton('⚙');settings.setObjectName('WidgetAction');settings.setFixedSize(32,32);settings.setToolTip('Configurer mes raccourcis');settings.setAccessibleName('Configurer mes raccourcis');settings.clicked.connect(owner.open_settings);header.addWidget(settings);close=QPushButton('×');close.setObjectName('WidgetAction');close.setFixedSize(32,32);close.setAccessibleName('Masquer les raccourcis');close.clicked.connect(self.hide);header.addWidget(close);content.addLayout(header)
        self.search=QLineEdit();self.search.setObjectName('WidgetSearch');self.search.setPlaceholderText('Rechercher une application…');self.search.setAccessibleName('Rechercher parmi mes applications');self.search.textChanged.connect(self.rebuild);content.addWidget(self.search)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);content.addWidget(self.scroll)

    def rebuild(self):
        grid_widget=QWidget();grid=QGridLayout(grid_widget);grid.setContentsMargins(0,0,0,0);grid.setSpacing(12);grid.setSizeConstraint(QLayout.SetMinimumSize);grid.setAlignment(Qt.AlignTop)
        entries=[a for a in self.owner.shortcuts if normalized_name(self.search.text()) in normalized_name(a['name'])]
        columns=min(5,max(1,len(self.owner.shortcuts)));self.search.setVisible(len(self.owner.shortcuts)>8)
        self.card.setFixedWidth(max(310,min(740,columns*130+(columns-1)*12+44)))
        for index,item in enumerate(entries):
            button=QToolButton();button.setObjectName('AppTile');button.setText(item['name'] if len(item['name'])<=20 else item['name'][:18]+'…');button.setToolTip(item['name']+'\n'+item['path']);button.setAccessibleName('Lancer '+item['name']);button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon);button.setIcon(self.owner.entry_icon(item));button.setIconSize(QSize(54,54));button.setMinimumSize(128,120);button.setMaximumWidth(130)
            button.clicked.connect(lambda checked=False,a=dict(item):self.owner.launch_shortcut(a));grid.addWidget(button,index//columns,index%columns)
        if self.owner.shortcuts and not entries:grid.addWidget(QLabel('Aucune application trouvée.'),0,0)
        if not self.owner.shortcuts:
            button=QPushButton('+ Ajouter mes applications');button.clicked.connect(self.owner.open_settings);grid.addWidget(button,0,0)
        previous=self.scroll.takeWidget()
        if previous:previous.deleteLater()
        self.scroll.setWidget(grid_widget);rows=max(1,(len(entries)+columns-1)//columns);self.scroll.setFixedHeight(min(max(124,rows*132-12),max(124,min(510,self.height()-250))))

    def reveal(self):
        screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen();self.setGeometry(screen.availableGeometry());self.search.clear();self.rebuild();self.show();self.raise_();self.activateWindow();self.setFocus();self.owner.orb.raise_()
    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),QColor(240,245,252,max(1,round(255*self.owner.opacity.value()/100))))
    def mousePressEvent(self,event):
        if not self.card.geometry().contains(event.position().toPoint()):self.hide()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape:self.hide()
        else:super().keyPressEvent(event)

class ApplinatorWindow(ApplicationWindow):
    def __init__(self,preload=True):
        super().__init__('applinator');self.setStyleSheet(STYLE.replace('CHECK_ASSET',(suite_root()/'assets/check.svg').as_posix()));self.resize(700,620);self.setMinimumSize(550,490);self.icons=QFileIconProvider();self.icon_cache={}
        saved=self.preferences.get('launcher_shortcuts',[])
        self.shortcuts=[dict(name=a['name'][:100],path=a['path']) for a in saved if isinstance(a,dict) and isinstance(a.get('name'),str) and isinstance(a.get('path'),str)][:2000] if isinstance(saved,list) else []
        previous=list(self.shortcuts)
        stored_catalog=self.preferences.get('launcher_catalog',previous)
        self.catalog=(preload_entries(stored_catalog) if self.preferences.get('launcher_catalog_version',0)<2 else list(stored_catalog)) if preload else list(previous)
        if preload and self.preferences.get('launcher_selection_version',0)<2:
            self.shortcuts=[a for a in self.catalog if a['name']=='Ergonatus']
            self.persist_selection()
        self.status.setText('Cochez les applications à afficher dans votre widget.')
        header=QHBoxLayout();add=QPushButton('+ Ajouter un logiciel');add.clicked.connect(self.choose_application);header.addWidget(add);header.addStretch();self.selected_count=QLabel();header.addWidget(self.selected_count);clear=QPushButton('Tout décocher');clear.clicked.connect(self.clear_selection);header.addWidget(clear);self.content.addLayout(header)
        row=QHBoxLayout();self.app_search=QLineEdit();self.app_search.setPlaceholderText('Rechercher une application du PC…');row.addWidget(self.app_search,1);self.categories=QComboBox();self.categories.addItems(['Toutes les catégories','Ergonatus','Internet','Bureautique','Communication','Création et médias','École et accessibilité','Utilitaires']);row.addWidget(self.categories);self.content.addLayout(row)
        self.list=QListWidget();self.list.setIconSize(QSize(34,34));self.list.setDragDropMode(QAbstractItemView.InternalMove);self.list.setDefaultDropAction(Qt.MoveAction);self.content.addWidget(self.list,1)
        self.list.model().rowsMoved.connect(self.save_order);self.list.itemChanged.connect(self.selection_changed);self.app_search.textChanged.connect(self.filter_catalog);self.categories.currentTextChanged.connect(self.filter_catalog)
        self.content.addWidget(QLabel('Coché = visible dans le widget · glissez pour changer l’ordre.'))
        row=QHBoxLayout();row.addWidget(QLabel('Fond du widget'));self.opacity=QSlider(Qt.Horizontal);self.opacity.setRange(0,100);self.opacity.setValue(int(self.preferences.get('launcher_opacity',45)));self.opacity.setAccessibleName('Opacité du fond du widget');row.addWidget(self.opacity,1);self.opacity_label=QLabel();row.addWidget(self.opacity_label);self.content.addLayout(row)
        row=QHBoxLayout();row.addWidget(QLabel('Transparent'));row.addStretch();row.addWidget(QLabel('Opaque'));self.content.addLayout(row)
        preview=QPushButton('Afficher mes raccourcis');preview.clicked.connect(self.activate);self.content.addWidget(preview)
        self.overlay=LauncherOverlay(self);self.opacity.valueChanged.connect(self.opacity_changed);self.opacity_changed(self.opacity.value());self.refresh();self.orb.doubleActivated.connect(self.open_settings)
        self.setAcceptDrops(True)
        if preload and self.preferences.get('launcher_catalog_version',0)<2:
            self.status.setText('Préparation de vos applications du PC…');background(self,discover_apps,self.apply_preload)

    def entry_icon(self,entry):
        key=entry['path']
        if key not in self.icon_cache:
            if key.startswith('shell:AppsFolder'):
                from shared.launcher_icons import app_pictogram
                icon=app_pictogram(entry['name'],entry.get('category',app_category(entry['name'])))
            else:
                from shared.launcher_icons import native_app_icon
                icon=native_app_icon(key)
                if icon.isNull():icon=self.icons.icon(QFileInfo(key))
            self.icon_cache[key]=icon
        return self.icon_cache[key]
    def persist_selection(self):
        self.remember('launcher_catalog',self.catalog);self.remember('launcher_shortcuts',self.shortcuts);self.remember('launcher_selection_version',2)
    def apply_preload(self,entries):
        if self.closing:return
        selected={a['path'].casefold() for a in self.shortcuts}
        self.catalog=preload_entries(self.catalog+entries)
        self.shortcuts=[a for a in self.catalog if a['path'].casefold() in selected]
        self.persist_selection();self.remember('launcher_catalog_version',2);self.remember('launcher_preloaded_version',1);self.refresh()
        self.status.setText(str(len(self.catalog))+' applications classées · cochez celles à afficher.')
        if self.overlay.isVisible():self.overlay.rebuild()

    def create_orb_menu(self):
        menu=QMenu(self);menu.setStyleSheet(STYLE)
        menu.addAction('Afficher / masquer les applications',self.activate)
        menu.addAction('Configurer mes raccourcis',self.open_settings)
        menu.addSeparator();menu.addAction('Quitter Applinator',self.quit)
        return menu

    def opacity_changed(self,value):
        self.opacity_label.setText(str(value)+' %');self.remember('launcher_opacity',value);self.overlay.update()
    def refresh(self):
        self.list.blockSignals(True);self.list.clear();selected={a['path'].casefold() for a in self.shortcuts}
        for entry in self.catalog:
            category=entry.get('category',app_category(entry['name']));entry=dict(entry,category=category)
            item=QListWidgetItem(self.entry_icon(entry),entry['name']+'  ·  '+category);item.setData(Qt.UserRole,dict(entry));item.setToolTip(entry['path']);item.setFlags(item.flags()|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Checked if entry['path'].casefold() in selected else Qt.Unchecked);item.setSizeHint(QSize(0,52));self.list.addItem(item)
        self.list.blockSignals(False);self.selected_count.setText(str(len(self.shortcuts))+' dans le widget');self.filter_catalog()
    def filter_catalog(self,*_):
        query=normalized_name(self.app_search.text());category=self.categories.currentText()
        for index in range(self.list.count()):
            item=self.list.item(index);entry=item.data(Qt.UserRole);item.setHidden(query not in normalized_name(entry['name']) or (category!='Toutes les catégories' and entry.get('category',app_category(entry['name']))!=category))
    def selection_changed(self,*_):
        self.catalog=[self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        self.shortcuts=[self.list.item(i).data(Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState()==Qt.Checked]
        self.persist_selection();self.selected_count.setText(str(len(self.shortcuts))+' dans le widget')
        if self.overlay.isVisible():self.overlay.rebuild()
    def clear_selection(self):
        self.shortcuts=[];self.persist_selection();self.refresh()
    def save_order(self,*_):self.selection_changed()
    def add_shortcut(self,path):
        entry=shortcut(path);entry['category']=app_category(entry['name'])
        existing=next((a for a in self.catalog if a['path'].casefold()==entry['path'].casefold()),None)
        if existing:entry=existing
        else:self.catalog.append(entry)
        if not any(a['path'].casefold()==entry['path'].casefold() for a in self.shortcuts):self.shortcuts.append(entry)
        self.persist_selection();self.refresh();self.status.setText(entry['name']+' ajouté au widget.')
    def remove_selected(self):
        row=self.list.currentRow()
        if row>=0:
            path=self.list.item(row).data(Qt.UserRole)['path'];self.catalog=[a for a in self.catalog if a['path']!=path];self.shortcuts=[a for a in self.shortcuts if a['path']!=path];self.persist_selection();self.refresh()
    def activate(self,*_):
        if self.overlay.isVisible():self.overlay.hide()
        else:self.hide();self.overlay.reveal()
    def open_settings(self,*_):
        self.overlay.hide();ApplicationWindow.activate(self)
    def launch_shortcut(self,entry):
        self.overlay.hide()
        def launch():
            try:
                item=shortcut(entry['path'])
                if item['path'].startswith('shell:AppsFolder'):
                    os.startfile(item['path'])
                elif not QDesktopServices.openUrl(QUrl.fromLocalFile(item['path'])):raise ValueError('Windows n’a pas pu ouvrir ce raccourci.')
                self.status.setText(entry['name']+' lancé.')
            except (OSError,ValueError) as error:self.open_settings();self.error(str(error))
        QTimer.singleShot(0,launch)
    def choose_application(self):
        path,_=QFileDialog.getOpenFileName(self,'Ajouter un logiciel ou un raccourci',str(Path.home()),'Applications (*.exe *.lnk *.appref-ms *.url *.bat *.cmd *.com *.msc)')
        if path:
            try:self.add_shortcut(path)
            except (OSError,ValueError) as error:self.error(str(error))
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():event.acceptProposedAction()
    def dropEvent(self,event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                try:self.add_shortcut(url.toLocalFile())
                except (OSError,ValueError) as error:self.error(str(error))
        event.acceptProposedAction()
    def cleanup(self):self.overlay.close()
