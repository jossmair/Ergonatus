"""Organisator: desktop spaces, coloured folders, previews and reversible sorting."""
from pathlib import Path
from dataclasses import replace
import threading,time
from PySide6.QtCore import Qt,QTimer,QStandardPaths,QFileSystemWatcher,QUrl,QSize
from PySide6.QtGui import QIcon,QPixmap,QImage,QImageReader,QDesktopServices
from PySide6.QtWidgets import (QApplication,QWidget,QLabel,QLineEdit,QPushButton,QComboBox,QCheckBox,QHBoxLayout,QVBoxLayout,QTreeWidget,QTreeWidgetItem,QTableWidget,QTableWidgetItem,QHeaderView,QSplitter,QStackedWidget,QPlainTextEdit,QProgressBar,QFileDialog,QAbstractItemView,QFrame,QDialog,QListWidget,QListWidgetItem)
from shared.apps.base import ApplicationWindow
from shared.catalog import suite_root
from shared.jobs import background
from shared.organizer import (PROFILES,INBOX,folder_specs,create_space,load_space,inside,analyze,apply_moves,undo_last,read_text,Proposal,IMAGES,DOCUMENT_LOCK)

STYLE="""
QWidget {font-family:'Segoe UI';font-size:10pt;color:#EDF7F1;}
QLabel {background:transparent;border:none;}
QFrame#SortingBar {background:#15251D;border:1px solid #42634F;border-radius:12px;}
QPushButton {min-height:20px;padding:5px 12px;background:#203A31;border:1px solid #426354;border-radius:9px;}
QPushButton:hover {background:#2C5141;border-color:#8BC9A8;}
QPushButton:focus {border:2px solid #9BDCB9;}
QPushButton#Primary {background:#397653;border-color:#85C9A0;font-weight:600;}
QPushButton:disabled {color:#8A9C91;background:#23322B;border-color:#34483C;}
QLineEdit,QComboBox {background:#1E2B25;border:1px solid #466554;border-radius:9px;padding:7px;min-height:18px;}
QComboBox QAbstractItemView {background:#22352A;color:#F2FFF5;border:1px solid #679F7C;selection-background-color:#39664B;outline:none;}
QTreeWidget,QTableWidget,QPlainTextEdit {background:rgba(22,33,27,245);alternate-background-color:#202F26;border:1px solid #3D5949;border-radius:12px;padding:6px;selection-background-color:#395D47;selection-color:#FFFFFF;outline:none;}
QTreeWidget::item {min-height:28px;padding:2px;}
QTreeWidget::item:selected {background:#395D47;border-radius:6px;}
QHeaderView::section {background:#21362A;color:#C6DDCD;padding:7px;border:none;border-bottom:1px solid #425B4B;}
QTableWidget {gridline-color:#2E4336;}
QCheckBox {background:transparent;spacing:7px;min-height:24px;}
QCheckBox::indicator,QTreeWidget::indicator,QTableWidget::indicator {width:17px;height:17px;border:1px solid #89B99A;background:#1E3025;border-radius:5px;}
QCheckBox::indicator:checked,QTreeWidget::indicator:checked,QTableWidget::indicator:checked {background:#65A47E;image:url(CHECK_ASSET);}
QScrollBar:vertical {background:transparent;width:7px;margin:3px;}
QScrollBar::handle:vertical {background:#567561;border-radius:3px;min-height:26px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;}
QSplitter::handle {background:transparent;width:7px;}
QProgressBar {border:none;background:#263D30;max-height:3px;border-radius:1px;}
QProgressBar::chunk {background:#9DD6B4;}
"""

def control(text,callback,primary=False):
    button=QPushButton(text);button.clicked.connect(callback);button.setAccessibleName(text)
    if primary:button.setObjectName('Primary')
    return button

def folder_icon(color):return QIcon(str(suite_root()/'assets/folders'/('folder-'+color[1:].lower()+'.ico')))

def preview_file(root,proposal):
    path=inside(root,Path(root)/proposal.source,True);ext=path.suffix.lower();image=None;text=proposal.text;kind=proposal.kind
    if ext in IMAGES:
        reader=QImageReader(str(path));dimensions=reader.size()
        if dimensions.width()*dimensions.height()>80_000_000:raise ValueError('Image trop grande pour cet aperçu.')
        if dimensions.isValid():reader.setScaledSize(dimensions.scaled(1100,900,Qt.KeepAspectRatio))
        image=reader.read()
        if image.isNull():raise ValueError('Aperçu image indisponible.')
    elif ext=='.pdf':
        import pymupdf
        with DOCUMENT_LOCK,pymupdf.open(path) as document:
            if not document.needs_pass and len(document):
                page=document[0];scale=min(1100/max(1,page.rect.width),900/max(1,page.rect.height),1.4)
                pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale));image=QImage.fromData(pix.tobytes('png'))
    if not text and ext not in IMAGES:
        try:text,kind=read_text(path)
        except Exception:text='Aperçu du contenu indisponible pour ce fichier.'
    if not text and image is None:text='Aucun aperçu disponible pour ce format. Le fichier n’a pas été ouvert dans un autre logiciel.'
    return image,text,kind


class OrganisatorWindow(ApplicationWindow):
    def __init__(self,desktop=None):
        super().__init__('organisator');self.desktop=Path(desktop) if desktop is not None else Path(QStandardPaths.writableLocation(QStandardPaths.DesktopLocation))
        self.root=None;self.config=None;self.proposals=[];self.busy=False;self.cancel_event=threading.Event();self.preview_token=0;self.view_folder=INBOX;self.scan_again=False;self.after_task=None
        self.setStyleSheet(STYLE.replace('CHECK_ASSET',(suite_root()/'assets/check.svg').as_posix()));self.setMinimumSize(810,530);self.resize(1060,660)
        self.layout.setContentsMargins(16,12,16,12);self.status.setText('Un espace organisé, directement sur votre Bureau.')
        row=QHBoxLayout();self.profile=QComboBox();self.profile.addItems(list(PROFILES));self.profile.setAccessibleName('Profil d’organisation');row.addWidget(self.profile)
        self.name=QLineEdit('Mes dossiers - École primaire');self.name.setAccessibleName('Nom du dossier sur le Bureau');self.name.setPlaceholderText('Nom du dossier sur le Bureau');row.addWidget(self.name,1)
        self.create_button=control('Créer sur le Bureau',self.create,True);row.addWidget(self.create_button);self.content.addLayout(row)
        row=QHBoxLayout();self.location=QLabel('Bureau › '+self.name.text());self.location.setStyleSheet('color:#BBD8C5;font-size:9pt;');row.addWidget(self.location,1)
        self.new_button=control('Nouvel espace',self.new_space);self.new_button.hide();row.addWidget(self.new_button)
        self.load_button=control('Mes espaces',self.show_spaces);self.load_button.setToolTip('Rouvrir un espace déjà créé, ou ajouter un dossier existant à la liste.');row.addWidget(self.load_button);self.open_button=control('Ouvrir le dossier',self.open_folder);self.open_button.hide();row.addWidget(self.open_button);self.binder_button=control('Consulter mon classeur',self.toggle_binder);row.addWidget(self.binder_button);self.content.addLayout(row)
        splitter=QSplitter();self.tree=QTreeWidget();self.tree.setHeaderHidden(True);self.tree.setIconSize(QSize(28,28));self.tree.setMinimumWidth(180);splitter.addWidget(self.tree)
        self.pages=QStackedWidget();intro=QWidget();intro_layout=QVBoxLayout(intro);intro_layout.setContentsMargins(24,20,24,20)
        title=QLabel('Chaque chose à sa place.');title.setStyleSheet('font-size:23pt;font-weight:600;color:#D6F1DD;');title.setWordWrap(True);intro_layout.addWidget(title)
        explanation=QLabel('Choisissez votre profil et les dossiers utiles.\n\nVotre espace sera créé sur le Bureau, avec des dossiers colorés.\n\nDéposez ensuite vos fichiers dans « À classer » : leur aperçu et une proposition de rangement apparaîtront ici.');explanation.setWordWrap(True);explanation.setStyleSheet('font-size:11pt;color:#C4D9CB;');intro_layout.addWidget(explanation);intro_layout.addStretch();self.pages.addWidget(intro)
        workspace=QWidget();workspace_layout=QVBoxLayout(workspace);workspace_layout.setContentsMargins(0,0,0,0)
        self.instructions=QLabel('Déposez vos fichiers dans « À classer ».');self.instructions.setStyleSheet('color:#C4D9CB;');workspace_layout.addWidget(self.instructions)
        inner=QSplitter();self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['✓','Fichier','Rangement']);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setAlternatingRowColors(True);self.table.verticalHeader().hide();self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Fixed);self.table.setColumnWidth(0,32);self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch);inner.addWidget(self.table)
        preview=QWidget();preview_layout=QVBoxLayout(preview);preview_layout.setContentsMargins(8,0,0,0)
        self.preview_title=QLabel('Aperçu');self.preview_title.setWordWrap(True);self.preview_title.setStyleSheet('font-size:12pt;font-weight:600;');preview_layout.addWidget(self.preview_title)
        self.preview_image=QLabel();self.preview_image.setAlignment(Qt.AlignCenter);self.preview_image.setMaximumHeight(240);self.preview_image.hide();preview_layout.addWidget(self.preview_image)
        self.preview_text=QPlainTextEdit();self.preview_text.setReadOnly(True);self.preview_text.setPlaceholderText('Sélectionnez un fichier pour voir son contenu.');preview_layout.addWidget(self.preview_text,1);inner.addWidget(preview);inner.setSizes([460,280]);workspace_layout.addWidget(inner,1);self.pages.addWidget(workspace);splitter.addWidget(self.pages);splitter.setStretchFactor(1,1);splitter.setSizes([210,800]);self.content.addWidget(splitter,1)
        self.sorting_bar=QFrame();self.sorting_bar.setObjectName('SortingBar');bar=QVBoxLayout(self.sorting_bar);bar.setContentsMargins(12,9,12,9);bar.setSpacing(8)
        row=QHBoxLayout();self.selection_hint=QLabel('Cochez les fichiers, puis rangez-les.');self.selection_hint.setStyleSheet('color:#C4D9CB;font-size:9pt;');row.addWidget(self.selection_hint,1)
        self.auto=QCheckBox('Ranger automatiquement');self.auto.setToolTip('Activé : les fichiers reconnus sont déplacés sans clic. Les fichiers incertains restent à vérifier.');self.auto.setChecked(bool(self.preferences.get('organizer_auto',False)));row.addWidget(self.auto);bar.addLayout(row)
        row=QHBoxLayout();self.analyze_button=control('Actualiser les fichiers',self.scan);self.analyze_button.setToolTip('Relire les fichiers et mettre à jour les propositions de rangement.');row.addWidget(self.analyze_button)
        self.undo_button=control('↶ Revenir avant le dernier tri',self.undo);row.addWidget(self.undo_button);row.addStretch();self.cancel_button=control('Arrêter',self.cancel_current);self.cancel_button.hide();row.addWidget(self.cancel_button)
        self.sort_button=control('Ranger les fichiers cochés',self.sort_selected,True);row.addWidget(self.sort_button);bar.addLayout(row);self.content.addWidget(self.sorting_bar)
        self.table.itemChanged.connect(self.update_selection_action)
        self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.hide();self.content.addWidget(self.progress)
        self.watcher=QFileSystemWatcher(self);self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(900);self.debounce.timeout.connect(self.scan)
        self.watcher.directoryChanged.connect(self.changed_on_disk);self.watcher.fileChanged.connect(self.changed_on_disk)
        self.profile.currentTextChanged.connect(self.template_changed);self.name.textChanged.connect(self.name_changed);self.tree.itemClicked.connect(self.browse);self.table.currentCellChanged.connect(self.preview_selected)
        self.auto.toggled.connect(lambda checked:(self.remember('organizer_auto',checked),self.scan() if self.root else None));self.template_changed(self.profile.currentText());self.update_controls()
        self.binder=None;self.binder_click=QTimer(self);self.binder_click.setSingleShot(True);self.binder_click.setInterval(QApplication.doubleClickInterval());self.binder_click.timeout.connect(self.toggle_binder);self.orb.doubleActivated.connect(self.open_main_window)
        self.orb.setToolTip('Organisator · clic : mon classeur · double-clic : gérer');self.orb.setAccessibleDescription('Un clic ouvre ou masque le classeur. Double-clic pour gérer les fichiers.')
        saved=self.preferences.get('organizer_space')
        if saved:
            try:self.use_space(*load_space(saved))
            except (OSError,ValueError,KeyError):self.status.setText('Retrouvez votre espace ou créez-en un nouveau sur le Bureau.')

    def template_changed(self,profile):
        if self.root:return
        if self.name.text().startswith('Mes dossiers - '):self.name.setText('Mes dossiers - '+profile)
        self.fill_tree(folder_specs(profile),choosing=True)

    def activate(self,*_):
        if not self.closing:self.binder_click.start()

    def toggle_binder(self):
        if self.closing:return
        if self.binder is None:
            from shared.apps.organizer_binder import BinderWindow
            self.binder=BinderWindow(self)
        if self.binder.isVisible():self.binder.hide()
        else:self.hide();self.binder.reveal()

    def open_main_window(self):
        if hasattr(self,'binder_click'):self.binder_click.stop()
        if getattr(self,'binder',None):self.binder.hide()
        ApplicationWindow.activate(self)

    def name_changed(self,text):
        if not self.root:self.location.setText('Bureau › '+text)

    def fill_tree(self,specs,choosing=False):
        self.tree.clear();parents={}
        for spec in specs:
            parts=spec['path'].split('/');parent=parents.get(parts[0]);item=QTreeWidgetItem([parts[-1]])
            if len(parts)==1:self.tree.addTopLevelItem(item);parents[parts[0]]=item
            elif parent:parent.addChild(item)
            item.setIcon(0,folder_icon(spec['color']));item.setData(0,Qt.UserRole,spec['path'])
            if choosing and len(parts)==1:
                item.setCheckState(0,Qt.Checked)
                if parts[0]==INBOX:item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            elif choosing:item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        self.tree.setToolTip('Cochez les dossiers à créer.' if choosing else 'Cliquez un dossier pour consulter ses fichiers.')

    def update_controls(self):
        managed=self.root is not None
        self.sorting_bar.setVisible(managed)
        for item in (self.profile,self.name,self.create_button):item.setEnabled(not managed and not self.busy)
        self.create_button.setVisible(not managed);self.new_button.setVisible(managed);self.open_button.setVisible(managed)
        for item in (self.analyze_button,self.undo_button,self.sort_button,self.auto):item.setVisible(managed);item.setEnabled(managed and not self.busy)
        self.load_button.setEnabled(not self.busy);self.new_button.setEnabled(not self.busy);self.table.setEnabled(not self.busy);self.tree.setEnabled(not self.busy);self.progress.setVisible(self.busy);self.cancel_button.setVisible(self.busy)
        self.update_selection_action()

    def update_selection_action(self,*_):
        count=sum(1 for row in range(self.table.rowCount()) if self.table.item(row,0) and self.table.item(row,0).checkState()==Qt.Checked)
        self.sort_button.setText(('Ranger '+str(count)+' fichier'+('s' if count>1 else '')) if count else 'Ranger les fichiers cochés')
        self.sort_button.setEnabled(bool(self.root) and not self.busy and count>0)
        self.selection_hint.setText('Déplacement dans les dossiers proposés · aucun effacement.')

    def task(self,function,done,message):
        if self.busy or self.closing:return
        self.busy=True;self.cancel_event.clear();self.status.setText(message);self.update_controls()
        def completed(result):
            if not self.closing:done(result)
        job=background(self,function,completed)
        def finished():
            if self.closing:return
            self.busy=False;self.update_controls()
            if self.after_task:
                callback=self.after_task;self.after_task=None;QTimer.singleShot(0,callback)
            elif self.scan_again:self.scan_again=False;self.debounce.start()
        job.signals.finished.connect(finished);return job

    def create(self):
        categories=[self.tree.topLevelItem(i).data(0,Qt.UserRole) for i in range(self.tree.topLevelItemCount()) if self.tree.topLevelItem(i).checkState(0)==Qt.Checked]
        name=self.name.text();profile=self.profile.currentText()
        def create_folder():
            try:return create_space(self.desktop,name,profile,categories,suite_root()/'assets/folders')
            except FileExistsError:raise ValueError('Ce nom existe déjà sur le Bureau. Choisissez un autre nom ou retrouvez cet espace.')
        self.task(create_folder,lambda result:self.created(*result),'Création de votre espace sur le Bureau…')

    def created(self,root,config):
        self.use_space(root,config);self.status.setText('Espace créé. Déposez vos fichiers dans « À classer ».'+(' Certaines icônes Windows n’ont pas pu être appliquées.' if config.get('icon_warnings') else ''))

    def use_space(self,root,config):
        self.root=Path(root);self.config=load_space(root)[1];self.view_folder=INBOX;self.remember('organizer_space',str(root));self.remember_space();self.profile.setCurrentText(self.config['profile']);self.name.setText(self.root.name);self.location.setText("Bureau › "+self.root.name);self.location.setToolTip(str(self.root));self.pages.setCurrentIndex(1);self.fill_tree(self.config['folders']);self.update_controls();self.watch();QTimer.singleShot(300,self.scan)

    def remember_space(self):
        entries=self.preferences.get('organizer_spaces',[])
        if not isinstance(entries,list):entries=[]
        entry=dict(path=str(self.root),name=self.root.name,profile=self.config['profile'])
        entries=[item for item in entries if isinstance(item,dict) and isinstance(item.get('path'),str) and item['path'].casefold()!=entry['path'].casefold()]
        self.remember('organizer_spaces',[entry]+entries)

    def show_spaces(self):
        if self.busy:return
        if getattr(self,'spaces_window',None):self.spaces_window.close()
        dialog=QDialog(self,Qt.Dialog|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);self.spaces_window=dialog;dialog.setWindowTitle('Mes espaces');dialog.resize(620,430)
        dialog.setStyleSheet(STYLE.replace('CHECK_ASSET',(suite_root()/'assets/check.svg').as_posix())+"QDialog {background:#15251D;border:1px solid #668D73;border-radius:14px;} QListWidget {background:#182C21;border:1px solid #42634F;border-radius:10px;padding:6px;} QListWidget::item {padding:12px;border-bottom:1px solid #344F3E;} QListWidget::item:hover {background:#304F3B;} QListWidget::item:selected {background:#3E654B;}")
        layout=QVBoxLayout(dialog);layout.setContentsMargins(20,16,20,18);header=QHBoxLayout();title=QLabel('Mes espaces');title.setStyleSheet('font-size:18pt;font-weight:600;');header.addWidget(title,1);header.addWidget(control('×',dialog.close));layout.addLayout(header)
        hint=QLabel('Cliquez un espace pour le rouvrir.');hint.setWordWrap(True);layout.addWidget(hint)
        listing=QListWidget();listing.setAccessibleName('Espaces enregistrés');layout.addWidget(listing,1)
        entries=self.preferences.get('organizer_spaces',[])
        if not isinstance(entries,list):entries=[]
        for entry in entries:
            if not isinstance(entry,dict) or not isinstance(entry.get('path'),str):continue
            path=Path(entry['path']);available=(path/'.organisator/space.json').is_file()
            item=QListWidgetItem(entry.get('name',path.name)+'  ·  '+entry.get('profile','')+'\n'+str(path)+('' if available else '\nDossier introuvable · déplacé ou déconnecté'))
            item.setData(Qt.UserRole,str(path));item.setIcon(folder_icon('#82C8B8'));item.setToolTip(str(path));listing.addItem(item)
        if not listing.count():hint.setText('Vos nouveaux espaces apparaîtront ici. Vous pouvez aussi ajouter un espace déjà créé.')
        def reopen(path):
            try:self.use_space(*load_space(path))
            except (OSError,ValueError,KeyError) as error:
                hint.setText('Impossible d’ouvrir ce dossier. S’il a été déplacé, utilisez « Ajouter un espace existant ».');hint.setToolTip(str(error));return
            dialog.accept()
        listing.itemClicked.connect(lambda item:reopen(item.data(Qt.UserRole)))
        def add_existing():
            path=QFileDialog.getExistingDirectory(dialog,'Choisir un espace Organisator existant',str(self.desktop))
            if path:reopen(path)
        footer=QHBoxLayout();footer.addWidget(control('Ajouter un espace existant',add_existing));footer.addStretch();footer.addWidget(control('Fermer',dialog.close));layout.addLayout(footer)
        dialog.show();dialog.raise_();dialog.activateWindow()

    def choose_space(self):
        path=QFileDialog.getExistingDirectory(self,'Retrouver votre dossier Organisator',str(self.desktop))
        if path:
            try:self.use_space(*load_space(path))
            except (OSError,ValueError,KeyError) as error:self.error('Ce dossier n’est pas un espace Organisator : '+str(error))

    def new_space(self):
        if self.busy:return
        self.root=None;self.config=None;self.preview_token+=1;self.watcher.removePaths(self.watcher.directories());self.table.setRowCount(0);self.pages.setCurrentIndex(0);self.template_changed(self.profile.currentText());self.update_controls();self.name_changed(self.name.text())

    def open_folder(self):
        if self.root:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root)))

    def watch(self):
        if not self.root:return
        paths=[self.root,self.root/INBOX]
        for proposal in self.proposals:
            parent=(self.root/proposal.source).parent
            if (self.root/INBOX) in parent.parents or parent==self.root/INBOX:paths.append(parent)
        wanted={str(p) for p in paths if p.is_dir()};existing=set(self.watcher.directories());remove=list(existing-wanted)
        if remove:self.watcher.removePaths(remove)
        add=list(wanted-existing)
        if add:self.watcher.addPaths(add)

    def changed_on_disk(self,*_):
        if self.busy:self.scan_again=True
        else:self.debounce.start()

    def scan(self):
        if not self.root or self.closing:return
        if self.busy:self.scan_again=True;return
        root=self.root
        from shared.ocr import recognize
        self.task(lambda:analyze(root,self.cancel_event,recognize),self.scanned,'Lecture des fichiers et proposition de rangement…')

    def scanned(self,result):
        proposals,warnings=result;self.proposals=proposals;self.view_folder=INBOX;self.show_rows(proposals);self.watch()
        self.status.setText(str(len(proposals))+' fichier(s) à classer.'+(' '+str(len(warnings))+' élément(s) ignoré(s).' if warnings else ''))
        self.status.setToolTip('\n'.join(warnings));self.instructions.setText('Vérifiez les cases et le rangement proposé. Aucun fichier n’est supprimé.')
        if self.auto.isChecked() and not self.cancel_event.is_set():
            safe=[p for p in proposals if p.confidence>=.92 and p.destination!=INBOX and time.time()-p.modified/1e9>=3]
            if safe:self.after_task=lambda:self.move(safe) if not self.closing else None
            if any(p.confidence>=.92 and p.destination!=INBOX and time.time()-p.modified/1e9<3 for p in proposals):
                QTimer.singleShot(3200,lambda:self.scan() if self.auto.isChecked() and not self.closing else None)

    def show_rows(self,proposals):
        self.preview_token+=1;self.preview_image.hide();self.preview_text.clear();self.table.setRowCount(0)
        destinations=[spec['path'] for spec in self.config['folders']]
        for row,proposal in enumerate(proposals):
            self.table.insertRow(row);check=QTableWidgetItem();check.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable);check.setCheckState(Qt.Checked if proposal.destination!=INBOX and proposal.confidence>=.7 and proposal.destination!=str(Path(proposal.source).parent).replace('\\','/') else Qt.Unchecked);self.table.setItem(row,0,check)
            label=QTableWidgetItem(Path(proposal.source).name);label.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable);label.setToolTip(proposal.source+'\n'+proposal.reason);self.table.setItem(row,1,label)
            choice=QComboBox();choice.setAccessibleName('Rangement de '+Path(proposal.source).name)
            for target in destinations:choice.addItem(target.replace('/',' › '),target)
            choice.setCurrentIndex(max(0,choice.findData(proposal.destination)));choice.setToolTip(proposal.reason+'\n'+('À vérifier' if proposal.confidence<.9 else 'Classement très probable'))
            choice.currentIndexChanged.connect(lambda index,c=choice,item=check:item.setCheckState(Qt.Checked if c.currentData()!=INBOX else Qt.Unchecked));self.table.setCellWidget(row,2,choice);self.table.setRowHeight(row,42)
        if proposals:self.table.setCurrentCell(0,1)
        self.update_selection_action()

    def sort_selected(self):
        plans=[replace(self.proposals[row],destination=self.table.cellWidget(row,2).currentData()) for row in range(len(self.proposals)) if self.table.item(row,0).checkState()==Qt.Checked]
        if not plans:self.status.setText('Cochez les fichiers à classer.');return
        self.move(plans)

    def move(self,plans):
        if not self.root or self.busy:return
        self.task(lambda:apply_moves(self.root,plans,self.cancel_event),lambda result:self.moved(result,False),'Classement en cours · déplacement sans écrasement…')

    def moved(self,result,undo):
        moved,errors=result;self.status.setText(str(len(moved))+(' fichier(s) remis à leur place.' if undo else ' fichier(s) classé(s).')+(' '+str(len(errors))+' fichier(s) laissé(s) en place.' if errors else ''))
        self.status.setToolTip('\n'.join(errors));self.proposals=[];self.show_rows([]);self.scan_again=False
        # Watcher events from these moves must not immediately re-sort an undo.
        if undo:
            self.auto.blockSignals(True);self.auto.setChecked(False);self.auto.blockSignals(False);self.remember('organizer_auto',False)
        self.debounce.stop();self.watch()

    def undo(self):
        if self.root:self.task(lambda:undo_last(self.root,self.cancel_event),lambda result:self.moved(result,True),'Retour au rangement précédent…')

    def browse(self,item,column):
        if not self.root or self.busy:return
        relative=item.data(0,Qt.UserRole)
        if relative==INBOX:self.scan();return
        root=self.root
        def listing():
            directory=inside(root,root/relative);rows=[]
            for path in directory.iterdir():
                if path.name.casefold()=='desktop.ini' or path.name.startswith('.'):continue
                try:
                    inside(root,path,True);info=path.stat();rows.append(Proposal(str(path.relative_to(root)),relative,0,'Déjà classé',info.st_size,info.st_mtime_ns))
                except (OSError,ValueError):continue
                if len(rows)>=2000:break
            return sorted(rows,key=lambda p:p.source.casefold())
        def displayed(rows):self.proposals=rows;self.view_folder=relative;self.show_rows(rows);self.instructions.setText(relative.replace('/',' › ')+' · '+str(len(rows))+' fichier(s)')
        self.task(listing,displayed,'Ouverture du dossier…')

    def preview_selected(self,row,*_):
        if self.closing or row<0 or row>=len(self.proposals) or not self.root:return
        self.preview_token+=1;token=self.preview_token;proposal=self.proposals[row];root=self.root;self.preview_title.setText(Path(proposal.source).name);self.preview_text.setPlainText('Chargement de l’aperçu…');self.preview_image.hide()
        def done(result):
            if self.closing or token!=self.preview_token:return
            image,text,kind=result;self.preview_text.setPlainText(text[:60000] if text else kind)
            if image is not None and not image.isNull():self.preview_image.setPixmap(QPixmap.fromImage(image).scaled(max(160,self.preview_text.width()),240,Qt.KeepAspectRatio,Qt.SmoothTransformation));self.preview_image.show()
        def prepare():
            try:return preview_file(root,proposal)
            except (OSError,ValueError,RuntimeError) as error:return None,str(error),'Aperçu indisponible'
        background(self,prepare,done)

    def cancel_current(self):
        self.cancel_event.set();self.after_task=None;self.auto.blockSignals(True);self.auto.setChecked(False);self.auto.blockSignals(False);self.remember('organizer_auto',False);self.status.setText('Arrêt demandé · fin du fichier en cours…')
    def cleanup(self):
        self.cancel_event.set();self.debounce.stop();self.preview_token+=1;self.watcher.blockSignals(True);self.binder_click.stop()
        if self.binder:self.binder.shutdown()
