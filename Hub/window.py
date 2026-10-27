from pathlib import Path
import json
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QPalette
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QScrollArea, QLineEdit, QComboBox, QCheckBox, QSpinBox, QTabWidget, QFileDialog,
    QMessageBox, QInputDialog, QMenu, QSystemTrayIcon, QApplication,QFrame)
from shared.catalog import Catalog, suite_root
from shared.profiles import ProfileStore, default_profile
from shared.ui.theme import APP_THEMES, stylesheet,accent_button_style
from shared.ui.components import ErgoWindow, ErgoButton, ErgoCard, ErgoOrb, ErgoStatus, ErgoBackdrop
from orb_manager.manager import OrbManager

class HubWindow(ErgoWindow):
    def __init__(self, data_dir=None):
        super().__init__()
        self.setWindowTitle('Ergonatus · Mes aides numériques')
        self.resize(1060, 800)
        self.setMinimumSize(720, 560)
        self.catalog = Catalog()
        self.store = ProfileStore(Path(data_dir)/'profiles.json' if data_dir else None)
        self.profiles = self.store.load()
        self.profile = next((p for p in self.profiles if p['name']==self.store.active_name),self.profiles[0])
        self.manager = OrbManager(self.catalog, self)
        self.manager.show_requested.connect(self.showNormal)
        self.cards = {}
        self.pending=set();self.control_sockets=set()
        self.orb_widgets = []
        self.build()
        self.behavior.message.connect(self.notice.setText);self.behavior.configure(self.store.path.parent/'windows'/'ergonatus.json')
        self.tray = QSystemTrayIcon(self)
        icon = QIcon(str(suite_root()/'assets/orbs/ergonatus.png'))
        if icon.isNull():
            icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray.setIcon(icon)
        self.tray.setToolTip('Ergonatus')
        menu = QMenu()
        menu.addAction('Ouvrir Ergonatus', self.showNormal)
        menu.addAction('Quitter Ergonatus', self.close)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.Trigger else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.apply_theme)
        self.apply_profile()
        if self.store.notice:
            self.notice.setText(self.store.notice)

    def button(self, text, callback, layout):
        button = ErgoButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def build(self):
        root = ErgoBackdrop('ergonatus'); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(24,20,24,20); layout.setSpacing(12)
        heading_area=QFrame();heading_area.setObjectName('WindowHeader');heading=QHBoxLayout(heading_area);heading.setContentsMargins(0,0,0,0);self.drag_area(heading_area)
        title = QLabel('ERGONATUS'); title.setObjectName('Title');self.drag_area(title); heading.addWidget(title)
        heading.addStretch()
        self.summary = QLabel('Tout près de vous, à votre rythme.'); self.summary.setObjectName('Muted'); heading.addWidget(self.summary)
        self.drag_area(self.summary);layout.addWidget(heading_area)
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel('Mon profil'))
        self.profile_box = QComboBox(); self.profile_box.setAccessibleName('Choisir mon profil')
        self.profile_box.addItems([p['name'] for p in self.profiles]); profile_row.addWidget(self.profile_box,1)
        self.profile_box.setCurrentIndex(self.profiles.index(self.profile))
        self.profile_box.currentIndexChanged.connect(self.select_profile)
        self.button('Enregistrer', self.save, profile_row)
        self.button('Nouveau profil', self.new_profile, profile_row)
        layout.addLayout(profile_row)
        self.notice = ErgoStatus('Les logiciels restent indépendants. Aucun démarrage automatique.')
        layout.addWidget(self.notice)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs,1)
        catalog = QWidget(); body = QVBoxLayout(catalog)
        search_row = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText('Rechercher une aide…'); self.search.setAccessibleName('Rechercher un logiciel')
        self.search.textChanged.connect(self.filter_cards); search_row.addWidget(self.search,1)
        self.only_installed = QCheckBox('Disponibles'); self.only_installed.toggled.connect(self.filter_cards); search_row.addWidget(self.only_installed)
        body.addLayout(search_row)
        area = QScrollArea(); area.setWidgetResizable(True); body.addWidget(area)
        grid_widget = QWidget(); self.grid = QGridLayout(grid_widget); self.grid.setSpacing(12); area.setWidget(grid_widget)
        for index,(app_id,item) in enumerate(APP_THEMES.items()):
            card = ErgoCard(); card_layout = QVBoxLayout(card)
            row = QHBoxLayout()
            orb = ErgoOrb(app_id); self.orb_widgets.append(orb); row.addWidget(orb)
            labels = QVBoxLayout()
            name = QLabel(item['name']); name.setStyleSheet('font-size:14pt;font-weight:600;'); labels.addWidget(name)
            description = QLabel(item['description']); description.setWordWrap(True); description.setObjectName('Muted'); labels.addWidget(description)
            row.addLayout(labels,1); card_layout.addLayout(row)
            status = ErgoStatus(); card_layout.addWidget(status)
            actions = QHBoxLayout()
            if app_id == 'ergonatus':
                actions.addWidget(QLabel('Centre de contrôle · ouvert'))
                active = open_button = stop = None
            elif self.catalog.detect(app_id):
                active = QCheckBox('Dans la pile'); active.setAccessibleName('Afficher l’Orb de '+item['name'])
                active.toggled.connect(lambda checked,key=app_id: self.toggle_active(key,checked)); actions.addWidget(active)
                open_button = self.button('Ouvrir',lambda checked=False,key=app_id:self.launch(key),actions)
                open_button.setStyleSheet(accent_button_style(item['accent']))
                open_button.setAccessibleName('Ouvrir '+item['name'])
                stop = self.button('Quitter',lambda checked=False,key=app_id:self.stop(key),actions)
                stop.setAccessibleName('Quitter '+item['name'])
            else:
                active = open_button = stop = None
                actions.addWidget(QLabel('Prévu dans la feuille de route'))
            card_layout.addLayout(actions)
            self.cards[app_id] = dict(card=card,status=status,active=active,open=open_button,stop=stop,orb=orb)
            self.grid.addWidget(card,index//2,index%2)
        self.tabs.addTab(catalog,f'Mes logiciels · {len(APP_THEMES)}')
        self.build_orbs()
        self.build_settings()
        footer = QHBoxLayout(); footer.addWidget(QLabel('Local · sans compte · sans télémétrie')); footer.addStretch()
        self.button('Réduire', self.showMinimized, footer)
        self.button('Quitter le hub', self.close, footer)
        layout.addLayout(footer)

    def build_orbs(self):
        page=QWidget(); layout=QVBoxLayout(page)
        text=QLabel('Les quatre logiciels utilisent leurs propres Orbs. Les images ci-dessous sont des aperçus graphiques ; elles ne remplacent pas leurs commandes.'); text.setWordWrap(True); layout.addWidget(text)
        controls=QHBoxLayout()
        controls.addWidget(QLabel('Seuil de confort'))
        self.limit=QSpinBox(); self.limit.setRange(1,len(APP_THEMES)-1); self.limit.setAccessibleName('Nombre conseillé d’Orbs'); controls.addWidget(self.limit)
        self.limit.valueChanged.connect(lambda value:self.profile.__setitem__('orb_limit',value))
        self.animations=QCheckBox('Animations douces'); self.animations.toggled.connect(self.toggle_animations); controls.addWidget(self.animations)
        self.button('Mode fatigue', self.fatigue, controls); controls.addStretch(); layout.addLayout(controls)
        self.native_status=ErgoStatus(); layout.addWidget(self.native_status)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); layout.addWidget(scroll)
        content=QWidget(); rows=QVBoxLayout(content); scroll.setWidget(content)
        self.orb_rows={}
        for app_id,item in APP_THEMES.items():
            row=QHBoxLayout()
            orb=ErgoOrb(app_id); self.orb_widgets.append(orb); row.addWidget(orb)
            row.addWidget(QLabel(item['name']),1)
            state=QComboBox(); state.addItems(ErgoOrb.STATES); state.setAccessibleName('État aperçu '+item['name'])
            state.currentTextChanged.connect(orb.update_state); row.addWidget(state)
            self.button('Aperçu flottant',lambda checked=False,key=app_id:self.preview(key),row)
            if app_id != 'ergonatus':
                favorite=QCheckBox('Favori'); favorite.toggled.connect(lambda value,key=app_id:self.list_choice('favorites',key,value)); row.addWidget(favorite)
                self.orb_rows[app_id]=favorite
                if app_id not in ('claviernator','precisionator','transcrinator','redactor'):
                    self.button('Afficher',lambda checked=False,key=app_id:self.orb_visibility(key,True),row)
                    self.button('Masquer',lambda checked=False,key=app_id:self.orb_visibility(key,False),row)
            rows.addLayout(row)
        rows.addStretch()
        self.tabs.addTab(page,'Orbs & animations')
        self.button('Ranger les Orbs coopératives selon le profil',self.arrange_orbs,controls)
        order_row=QHBoxLayout();layout.insertLayout(2,order_row)
        self.order_choice=QComboBox();self.order_choice.setAccessibleName('Logiciel à déplacer dans la pile')
        for key in self.profile['order']:self.order_choice.addItem(APP_THEMES[key]['name'],key)
        order_row.addWidget(self.order_choice,1)
        self.button('Monter dans la pile',lambda:self.reorder_orb(1),order_row)
        self.button('Descendre dans la pile',lambda:self.reorder_orb(-1),order_row)

    def build_settings(self):
        page=QWidget(); layout=QVBoxLayout(page)
        title=QLabel('Préférences & accompagnants'); title.setObjectName('Title'); layout.addWidget(title)
        self.theme=QComboBox(); self.theme.addItems(['Style des applications originales','Clair','Sombre']); self.theme.setAccessibleName('Apparence du hub')
        self.theme.currentIndexChanged.connect(self.change_theme); layout.addWidget(self.theme)
        self.large=QCheckBox('Texte et commandes agrandis'); self.large.toggled.connect(self.change_large); layout.addWidget(self.large)
        self.button('Exporter ce profil', self.export_profile,layout)
        self.button('Importer un profil', self.import_profile,layout)
        self.button('Diagnostics locaux',self.diagnostics,layout)
        self.button('Vérifier les modèles IA locaux',self.verify_models,layout)
        self.button('Libérer la mémoire du moteur IA',self.unload_ai,layout)
        self.button('Réparer les modèles manquants · téléchargement sur confirmation',self.repair_models,layout)
        self.button('Annuler le téléchargement',lambda:getattr(self,'download_cancel',__import__('threading').Event()).set(),layout)
        self.auto=QCheckBox('Lancer les aides actives à l’ouverture du hub');self.auto.toggled.connect(lambda value:self.profile.__setitem__('autolaunch',value));layout.addWidget(self.auto)
        self.start_windows=QCheckBox('Ouvrir Ergonatus avec Windows');layout.addWidget(self.start_windows)
        try:
            from shared.startup import enabled
            self.start_windows.setChecked(enabled())
        except OSError:pass
        self.start_windows.toggled.connect(self.set_startup)
        self.package_app=QComboBox();self.package_app.addItems([APP_THEMES[key]['name'] for key in APP_THEMES if key!='ergonatus']);layout.addWidget(self.package_app)
        self.button('Installer / mettre à jour depuis un paquet local',self.install_local,layout)
        self.button('Retirer le logiciel sélectionné',self.uninstall_local,layout)
        note=QLabel('Les mises à jour sont des paquets locaux vérifiés par empreintes. Les anciennes versions et les données personnelles sont conservées. Les quatre logiciels historiques gardent leurs commandes et réglages natifs.');note.setWordWrap(True);layout.addWidget(note)
        layout.addStretch();scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);self.tabs.addTab(scroll,'Préférences')

    def list_choice(self,key,app_id,enabled):
        values=self.profile[key]
        if enabled and app_id not in values: values.append(app_id)
        elif not enabled and app_id in values: values.remove(app_id)

    def toggle_active(self,app_id,enabled):
        self.list_choice('active',app_id,enabled)
        if enabled:
            self.launch(app_id,minimized=True)
        else:
            self.notice.setText('Retiré de ce profil. Si cette aide est ouverte, elle reste disponible jusqu’à votre commande Quitter.')
        self.refresh()
        QTimer.singleShot(600,self.arrange_orbs)

    def launch(self,app_id,minimized=False):
        try:
            started=self.catalog.launch(app_id,minimized=minimized)
            self.notice.setText('Lancement demandé.' if started else 'Ce logiciel est déjà ouvert. Son Orb reste disponible.')
        except (ValueError,OSError) as error:
            self.catalog.errors[app_id]=str(error)
            self.notice.setText('Lancement impossible : '+str(error))
        self.refresh()

    def stop(self,app_id):
        try:
            self.catalog.stop(app_id)
            self.notice.setText('Fermeture propre demandée à '+APP_THEMES[app_id]['name']+'. Les autres aides restent ouvertes.')
        except (ValueError,OSError) as error:
            self.notice.setText(str(error))

    def preview(self,app_id):
        if len(self.manager.preview)>=self.profile['orb_limit'] and app_id not in self.manager.preview:
            self.notice.setText('Seuil de confort atteint pour les aperçus. Fermez un aperçu ou ajustez ce seuil. Aucune aide active n’a été désactivée.')
            return
        self.manager.show_preview(app_id,self.profile)

    def toggle_animations(self,value):
        self.profile['animations']=value
        self.manager.set_animations(value)
        for orb in self.orb_widgets: orb.set_animations(value)
        for key in self.profile['active']:
            if key not in ('claviernator','precisionator','transcrinator','redactor'):self.app_control(key,'animations',enabled=value)

    def fatigue(self):
        self.animations.setChecked(False); self.large.setChecked(True)
        self.limit.setValue(3)
        self.notice.setText('Mode fatigue : texte agrandi et aperçus sans animation. Vos aides restent ouvertes. Les animations natives se règlent dans chaque logiciel.')

    def change_theme(self,index):
        self.profile['theme']=['system','light','dark'][index]; self.apply_theme()

    def change_large(self,value):
        self.profile['large']=value; self.apply_theme()

    def apply_theme(self,*_):
        mode=self.profile['theme']
        dark=mode!='light'
        self.setStyleSheet(stylesheet(dark,self.profile['large']))

    def apply_profile(self):
        # Loading a profile never starts or stops accessibility tools.
        for key,widgets in self.cards.items():
            if widgets['active']:
                widgets['active'].blockSignals(True); widgets['active'].setChecked(key in self.profile['active']); widgets['active'].blockSignals(False)
        for key,widget in self.orb_rows.items():
            widget.blockSignals(True); widget.setChecked(key in self.profile['favorites']); widget.blockSignals(False)
        self.limit.setValue(self.profile['orb_limit'])
        self.animations.setChecked(self.profile['animations'])
        self.large.setChecked(self.profile['large'])
        self.theme.setCurrentIndex(['system','light','dark'].index(self.profile['theme']))
        self.auto.setChecked(self.profile['autolaunch'])
        self.order_choice.clear()
        for key in self.profile['order']:self.order_choice.addItem(APP_THEMES[key]['name'],key)
        self.toggle_animations(self.profile['animations']); self.apply_theme(); self.refresh()

    def select_profile(self,index):
        if 0<=index<len(self.profiles):
            self.profile=self.profiles[index]; self.apply_profile()

    def new_profile(self):
        name,ok=QInputDialog.getText(self,'Nouveau profil','Nom du profil')
        if not ok: return
        if not name.strip() or len(name)>80 or name in [p['name'] for p in self.profiles]:
            self.notice.setText('Choisissez un nom unique, de 1 à 80 caractères.'); return
        self.profiles.append(default_profile(name.strip())); self.profile_box.addItem(name.strip()); self.profile_box.setCurrentIndex(len(self.profiles)-1)

    def save(self):
        try:
            self.store.save(self.profiles,self.profile['name']); self.notice.setText('Profils enregistrés sur cet ordinateur.')
        except (ValueError,OSError) as error:
            self.notice.setText('Enregistrement impossible : '+str(error))

    def export_profile(self):
        path,_=QFileDialog.getSaveFileName(self,'Exporter le profil','','JSON (*.json)')
        if path:
            try: self.store.export_profile(path,self.profile); self.notice.setText('Profil exporté.')
            except (ValueError,OSError) as error: self.notice.setText(str(error))

    def import_profile(self):
        path,_=QFileDialog.getOpenFileName(self,'Importer le profil','','JSON (*.json)')
        if not path: return
        try:
            profile=self.store.import_profile(path)
            if profile['name'] in [p['name'] for p in self.profiles]: profile['name'] += ' (importé)'
            if profile['name'] in [p['name'] for p in self.profiles]: raise ValueError('Ce profil importé existe déjà.')
            self.profiles.append(profile); self.profile_box.addItem(profile['name']); self.profile_box.setCurrentIndex(len(self.profiles)-1)
            self.notice.setText('Profil importé. Aucun logiciel n’a été lancé ou arrêté. Enregistrez pour le conserver.')
        except (ValueError,OSError) as error: self.notice.setText('Import refusé : '+str(error))

    def diagnostics(self):
        lines=[f"{APP_THEMES[key]['name']} : {self.catalog.state(key)}" for key in APP_THEMES]
        lines+=['','IA partagée : service local à la demande · modèles LFM2 (correction) et Qwen (traduction).',
                'IPC Orbs : '+('disponible' if self.manager.listening else 'indisponible'),
                'Aucun contenu de document, audio ou presse-papiers collecté.']
        QMessageBox.information(self,'Diagnostics locaux','\n'.join(lines))

    def filter_cards(self):
        query=self.search.text().casefold()
        for key,item in APP_THEMES.items():
            match=query in (item['name']+' '+item['description']).casefold()
            installed=key=='ergonatus' or self.catalog.detect(key) is not None
            self.cards[key]['card'].setVisible(match and (installed or not self.only_installed.isChecked()))

    def refresh(self):
        self.catalog.poll()
        running=0
        for key,widgets in self.cards.items():
            state=self.catalog.state(key,key in self.profile['active']); widgets['status'].setText(state)
            is_running=state.startswith('En cours'); running+=is_running
            if widgets['stop']:
                widgets['stop'].setEnabled(is_running)
                widgets['stop'].setToolTip('Instructions de fermeture depuis le logiciel' if key in ('claviernator','precisionator','redactor') else 'Arrêt distant propre')
        available=sum(self.catalog.detect(key) is not None for key in APP_THEMES)
        self.summary.setText(f'{running} aide(s) ouverte(s) · {available} disponibles')
        native=self.manager.native_orbs()
        labels=', '.join(APP_THEMES[item['app']]['name'] for item in native)
        self.native_status.setText(f'{len(native)} Orb(s) native(s) détectée(s)'+(' : '+labels if labels else '')+' · aucun doublon créé')
        if len(native)>self.profile['orb_limit']:
            self.notice.setText('Plus d’Orbs que votre seuil de confort. Vous pouvez les masquer depuis leurs menus ; aucune aide n’est désactivée.')

    def closeEvent(self,event):
        self.behavior.save()
        self.timer.stop(); self.manager.close(); self.tray.hide()
        # Companions intentionally outlive the hub, as in Fortinator.
        event.accept()

    def error(self,text):self.notice.setText(str(text))

    def orb_visibility(self,key,visible):
        self.list_choice('hidden',key,not visible)
        if visible and key not in self.profile['active']:
            checkbox=self.cards[key]['active']
            if checkbox is not None:checkbox.setChecked(True)
        self.arrange_orbs()

    def verify_models(self):
        from ergoai.inventory import verify
        from shared.jobs import background
        background(self,lambda:verify(self.catalog.root),lambda result:self.notice.setText(' · '.join(item['model']+(' : vérifié' if item['valid'] else ' : absent ou incorrect') for item in result)))

    def unload_ai(self):
        from shared.jobs import background
        from ergoai.service import request
        import uuid
        background(self,lambda:request(dict(op='unload',id=uuid.uuid4().hex)),lambda _:self.notice.setText('Poids IA déchargés. Le moteur les rechargera à la prochaine demande.'))

    def repair_models(self):
        from ergoai.models import download_missing,MODELS
        total=sum(model['size'] for model in MODELS)//1000000
        if QMessageBox.question(self,'Confirmer le téléchargement',f'Vérifier et télécharger uniquement les modèles manquants depuis Hugging Face ?\nMaximum {total} Mo. Les modèles présents et vérifiés ne seront pas téléchargés.\nLicences : LFM Open License v1.0 et Apache-2.0.')!=QMessageBox.Yes:return
        import threading
        if getattr(self,'downloading',False):self.notice.setText('Un téléchargement est déjà en cours.');return
        self.download_cancel=threading.Event();self.downloading=True
        from shared.jobs import background
        job=background(self,lambda:download_missing(self.catalog.root/'models',self.download_cancel),lambda results:self.notice.setText(' · '.join(results)))
        job.signals.finished.connect(lambda:setattr(self,'downloading',False))

    def app_control(self,key,command,**values):
        from PySide6.QtNetwork import QLocalSocket
        from shared.apps.base import instance_name
        socket=QLocalSocket(self);self.control_sockets.add(socket)
        def connected():
            socket.write((json.dumps(dict(version=1,command=command,**values))+'\n').encode());socket.flush();socket.disconnectFromServer()
        socket.connected.connect(connected);socket.disconnected.connect(lambda:(self.control_sockets.discard(socket),socket.deleteLater()))
        socket.connectToServer(instance_name(key));QTimer.singleShot(1000,socket.abort)

    def arrange_orbs(self):
        from orb_manager.manager import selected_stack
        order=[key for key in self.profile['order'] if key in self.profile['active'] and key not in self.profile['hidden']]
        order += [key for key in self.profile['active'] if key not in order and key not in self.profile['hidden']]
        screen=QApplication.primaryScreen();positions=selected_stack(screen.availableGeometry(),order)
        entries={}
        for key in APP_THEMES:
            if key=='ergonatus':continue
            visible=key in order and key not in self.profile['hidden']
            entries[key]=dict(visible=visible,position=positions[order.index(key)] if key in order else None)
            if key=='claviernator' and not visible:
                # Keep its independent scroll arrows clear of the selected pile.
                area=screen.availableGeometry();entries[key]['position']=[area.right()-36-16-72,area.bottom()-36-16-28]
            if key not in ('claviernator','precisionator','transcrinator','redactor'):
                self.app_control(key,'orb_show' if visible else 'orb_hide')
                if visible:self.app_control(key,'position',position=entries[key]['position'])
        path=self.catalog.root/'orb_manager/live-layout.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(dict(version=1,apps=entries)),encoding='utf-8');temp.replace(path)
        self.notice.setText('Orbs sélectionnées empilées verticalement · 36 px. Les autres aides restent ouvertes.')

    def reorder_orb(self,direction):
        key=self.order_choice.currentData()
        if key not in self.profile['order']:return
        order=self.profile['order'];index=order.index(key);target=max(0,min(len(order)-1,index+direction))
        order[index],order[target]=order[target],order[index]
        self.order_choice.clear()
        for item in order:self.order_choice.addItem(APP_THEMES[item]['name'],item)
        self.order_choice.setCurrentIndex(target);self.arrange_orbs()

    def launch_active(self):
        for index,key in enumerate(self.profile['active']):QTimer.singleShot(index*250,lambda app_id=key:self.launch(app_id,minimized=True))
        QTimer.singleShot(1000+len(self.profile['active'])*250,self.arrange_orbs)

    def set_startup(self,value):
        try:
            from shared.startup import set_enabled
            set_enabled(value);self.notice.setText('Démarrage Windows '+('activé.' if value else 'désactivé.'))
        except OSError as error:self.notice.setText('Réglage Windows impossible : '+str(error))

    def selected_package_app(self):return [key for key in APP_THEMES if key!='ergonatus'][self.package_app.currentIndex()]

    def install_local(self):
        key=self.selected_package_app()
        if self.catalog.running(key):self.notice.setText('Quittez ce logiciel avant sa mise à jour.');return
        path,_=QFileDialog.getOpenFileName(self,'Choisir un paquet logiciel','','Paquet Ergonatus (*.zip)')
        if not path:return
        if QMessageBox.question(self,'Installer un logiciel local','Installer '+APP_THEMES[key]['name']+' depuis ce paquet ?\n'+path+'\nUtilisez uniquement un paquet dont vous connaissez la provenance.')!=QMessageBox.Yes:return
        from shared.installation import install_package
        from shared.jobs import background
        background(self,lambda:install_package(self.catalog.root,path,key),lambda _:self.notice.setText('Paquet vérifié et installé. L’ancienne version est conservée.'))

    def uninstall_local(self):
        key=self.selected_package_app()
        if self.catalog.running(key):self.notice.setText('Quittez ce logiciel avant de le retirer.');return
        if QMessageBox.question(self,'Retirer le logiciel','Retirer '+APP_THEMES[key]['name']+' du catalogue installé ? Le runtime sera archivé et vos données conservées.')!=QMessageBox.Yes:return
        try:
            from shared.installation import uninstall
            uninstall(self.catalog.root,key);self.refresh();self.notice.setText('Logiciel retiré. Runtime archivé, données conservées.')
        except (ValueError,OSError) as error:self.notice.setText(str(error))
