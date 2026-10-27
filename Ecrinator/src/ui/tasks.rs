use super::*;
use ecrinator::{integrations, ocr};
use std::path::Path;
#[derive(Clone)]
pub(super) enum Pick {
    Open,
    Save,
    Export(String),
    Image,
    Space,
}
pub(super) enum Action {
    New,
    Open(PathBuf),
    CloseTab,
    Close,
}
pub(super) enum Event {
    Picked(Pick, Option<PathBuf>),
    Opened {
        path: PathBuf,
        result: Result<wordcraft_doc::Document, String>,
        rev: u64,
    },
    Saved {
        path: PathBuf,
        result: Result<(), String>,
        rev: u64,
        export: bool,
    },
    Routed {
        path: PathBuf,
        source: Option<PathBuf>,
        result: Result<(), String>,
        rev: u64,
    },
    Backup {
        result: Result<(), String>,
        rev: u64,
    },
    Recognized(Result<ocr::Recognition, String>),
    Printers(Vec<craft_print::Printer>),
    Printed(Result<String, String>),
    SpaceCreated(Result<ecrinator::organizer_space::Created, String>),
}
impl App {
    // Pause a stale association once, retaining its path for the repair screen.
    // The local crash-recovery save continues independently of classification.
    pub(super) fn check_organizer(&mut self) -> bool {
        if !self.prefs.organize {
            return false;
        }
        let validation = self
            .prefs
            .space
            .as_deref()
            .ok_or_else(|| "Aucun dossier associé.".to_owned())
            .and_then(integrations::validate_space);
        match validation {
            Ok(root) => {
                self.prefs.space = Some(root);
                true
            }
            Err(error) => {
                ecrinator::diagnostics::record(&format!("Classement mis en pause : {error}"));
                self.prefs.organize = false;
                self.remember();
                self.status = "Classement en pause · choisis ou crée un dossier avec Classer. Le brouillon local reste protégé.".into();
                false
            }
        }
    }
    pub(super) fn create_school_space(&mut self, name: String, ctx: &egui::Context) {
        if self.busy {
            return;
        }
        self.busy = true;
        self.status = "Création des dossiers sur le Bureau…".into();
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            let result = ecrinator::organizer_space::desktop()
                .and_then(|desktop| ecrinator::organizer_space::create(&desktop, &name, true));
            let _ = tx.send(Event::SpaceCreated(result));
            ctx.request_repaint();
        });
    }
    pub(super) fn dropped_file(&mut self, path: PathBuf, ctx: &egui::Context) {
        if self.busy || self.dialog.is_some() || self.pending.is_some() {
            self.status =
                "Ouverture impossible pendant cette opération. Réessayez après l’avoir terminée."
                    .into();
            return;
        }
        if path.extension().is_some_and(|e| {
            ["png", "jpg", "jpeg"]
                .iter()
                .any(|x| e.eq_ignore_ascii_case(x))
        }) {
            self.command(
                "insert.picture",
                json!({"path":path.to_string_lossy(),"width":300.}),
            );
        } else {
            self.request(Action::Open(path), ctx);
        }
    }
    pub(super) fn pick(&mut self, kind: Pick, ctx: &egui::Context) {
        if self.busy {
            return;
        }
        self.busy = true;
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        let suggested = integrations::filename(&self.school);
        std::thread::spawn(move || {
            let path = match &kind {
                Pick::Open => rfd::FileDialog::new()
                    .set_title("Ouvrir un document")
                    .add_filter("Documents", &["ecr", "docx", "odt", "rtf", "txt"])
                    .pick_file(),
                Pick::Save => rfd::FileDialog::new()
                    .set_title("Enregistrer le cours en ODT")
                    .add_filter("Document OpenDocument", &["odt"])
                    .set_file_name(&suggested)
                    .save_file(),
                Pick::Export(ext) => rfd::FileDialog::new()
                    .set_title("Exporter une copie")
                    .add_filter(ext.to_uppercase(), &[ext.as_str()])
                    .set_file_name(suggested.replace(".odt", &format!(".{ext}")))
                    .save_file(),
                Pick::Image => rfd::FileDialog::new()
                    .set_title("Insérer un schéma ou une image")
                    .add_filter("Images", &["png", "jpg", "jpeg"])
                    .pick_file(),
                Pick::Space => rfd::FileDialog::new()
                    .set_title("Choisir la racine d’un espace Organisator")
                    .pick_folder(),
            };
            let _ = tx.send(Event::Picked(kind, path));
            ctx.request_repaint();
        });
    }
    pub(super) fn request(&mut self, action: Action, ctx: &egui::Context) {
        if matches!(&action, Action::New | Action::Open(_)) {
            self.perform(action, ctx);
            return;
        }
        if matches!(&action, Action::Close) {
            self.closing_all = true;
            self.dialog = None;
        }
        if self.busy {
            self.status = "Attendez la fin de l’opération en cours.".into();
            return;
        }
        if self.word.session.dirty {
            self.pending = Some(action);
        } else {
            self.perform(action, ctx);
        }
    }
    pub(super) fn perform(&mut self, action: Action, ctx: &egui::Context) {
        match action {
            Action::New => {
                let s = School {
                    subject: self.school.subject.clone(),
                    show_banner: self.school.show_banner,
                    ..Default::default()
                };
                match self.new_tab(s) {
                    Ok(()) => {
                        self.status = "Nouveau cours · complétez le bandeau".into();
                        self.dialog = if self.school.subject == core::BLANK {
                            None
                        } else {
                            Some(dialogs::Dialog::Header(self.school.clone()))
                        };
                    }
                    Err(e) => self.status = e,
                }
            }
            Action::Open(path) => {
                if !self.already_open(&path) {
                    let s = School {
                        subject: core::BLANK.into(),
                        show_banner: false,
                        ..Default::default()
                    };
                    match self.new_tab(s) {
                        Ok(()) => self.open(path, ctx),
                        Err(e) => self.status = e,
                    }
                }
            }
            Action::CloseTab => {
                if let Err(e) = self.remove_current_tab() {
                    self.status = e;
                }
            }
            Action::Close => {
                if self.tab_order.len() > 1 {
                    if let Err(e) = self.remove_current_tab() {
                        self.status = e;
                        self.closing_all = false;
                        return;
                    }
                    self.request(Action::Close, ctx);
                    return;
                }
                self.closing = true;
                if !self.word.session.dirty {
                    let _ = std::fs::remove_file(&self.recovery);
                }
                ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            }
        }
    }
    pub(super) fn open(&mut self, path: PathBuf, ctx: &egui::Context) {
        if self.busy {
            return;
        }
        self.busy = true;
        self.status = "Ouverture du document…".into();
        self.file_job = Some(path.clone());
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        let rev = self.word.session.rev();
        std::thread::spawn(move || {
            let result = std::panic::catch_unwind(|| {
                if path
                    .extension()
                    .is_some_and(|x| x.eq_ignore_ascii_case("ecr"))
                {
                    storage::read(&path)
                } else {
                    if std::fs::metadata(&path).map_err(|e| e.to_string())?.len()
                        > storage::MAX_FILE
                    {
                        return Err("Document trop volumineux (64 Mo maximum).".into());
                    }
                    ecrinator::odt_project::open(
                        &path.to_string_lossy(),
                        &std::fs::read(&path).map_err(|e| e.to_string())?,
                    )
                }
            })
            .unwrap_or_else(|_| {
                Err("Le moteur n’a pas pu ouvrir ce document. L’original est conservé.".into())
            });
            let _ = tx.send(Event::Opened { path, result, rev });
            ctx.request_repaint();
        });
    }
    pub(super) fn save(&mut self, save_as: bool, ctx: &egui::Context) {
        if self.busy {
            return;
        }
        // A checkbox can change just before switching away from this tab.
        // Always route Organisator from the document, never a cached UI value.
        self.school = School::read(&self.word.session.doc);
        if save_as {
            self.pick(Pick::Save, ctx);
            return;
        }
        let path = self.path.clone();
        if self.prefs.organize && !self.check_organizer() {
            self.dialog = Some(dialogs::Dialog::organizer());
            return;
        }
        if self.prefs.organize
            && School::present(&self.word.session.doc)
            && self.school.subject != core::BLANK
        {
            if let Some(root) = &self.prefs.space {
                match integrations::destination(root, &self.school) {
                    Ok(dir) => {
                        if path
                            .as_ref()
                            .is_none_or(|p| p.parent() != Some(dir.as_path()))
                        {
                            match integrations::reserve(&dir, &self.school) {
                                Ok(p) => {
                                    self.write_routed(p, ctx);
                                    return;
                                }
                                Err(e) => {
                                    self.status = format!("Rangement impossible : {e}");
                                    return;
                                }
                            }
                        }
                    }
                    Err(e) => {
                        self.status = format!("Rangement impossible : {e}");
                        return;
                    }
                }
            } else {
                self.dialog = Some(dialogs::Dialog::organizer());
                return;
            }
        }
        if let Some(path) = path {
            self.write(path, false, ctx);
        } else {
            self.pick(Pick::Save, ctx);
        }
    }
    pub(super) fn write(&mut self, path: PathBuf, export: bool, ctx: &egui::Context) {
        if self.busy {
            return;
        }
        if self.path_in_another_tab(&path) {
            self.status = "Enregistrement impossible : ce fichier est utilisé dans un autre onglet. Choisissez un autre nom.".into();
            return;
        }
        if !export && self.path.as_ref() == Some(&path) && storage::stamp(&path) != self.stamp {
            self.status="Le fichier a changé en dehors d’Écrinator. Utilisez Enregistrer sous pour garder les deux versions.".into();
            return;
        }
        self.busy = true;
        self.file_job = Some(path.clone());
        let rev = self.word.session.rev();
        let doc = self.word.session.doc.clone();
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        let expected_stamp = storage::stamp(&path);
        self.status = if export {
            "Export en cours…"
        } else {
            "Enregistrement en cours…"
        }
        .into();
        std::thread::spawn(move || {
            let result = std::panic::catch_unwind(|| {
                let bytes=if export {ecrinator::exporters::bytes(&path.to_string_lossy(), &doc)?} else if path.extension().is_some_and(|e|e.eq_ignore_ascii_case("odt")){ecrinator::odt_project::encode(&doc)?} else {storage::encode(&doc)?};
                if !export&&bytes.len() as u64>storage::MAX_FILE {return Err("Document trop volumineux pour un enregistrement complet (64 Mo).".into());}
                if storage::stamp(&path)!=expected_stamp {return Err("Le fichier de destination a changé pendant l’écriture. Sa version est conservée ; réessayez sous un autre nom.".into());}
                storage::atomic_write(&path, &bytes)
            })
            .unwrap_or_else(|_| {
                Err(
                    "Le moteur n’a pas terminé l’écriture. Le fichier précédent est conservé."
                        .into(),
                )
            });
            let _ = tx.send(Event::Saved {
                path,
                result,
                rev,
                export,
            });
            ctx.request_repaint();
        });
    }
    fn write_routed(&mut self, path: PathBuf, ctx: &egui::Context) {
        let reserved = storage::stamp(&path);
        if self.path_in_another_tab(&path) || (self.path.is_some() && self.stamp.is_none()) {
            integrations::discard_reservation(&path, &reserved);
            self.status="Déplacement impossible : le fichier d’origine n’est pas vérifié. Utilisez Enregistrer sous.".into();
            return;
        }
        self.busy = true;
        self.file_job = Some(path.clone());
        self.status = "Classement et vérification du document…".into();
        let (source, stamp, rev, doc, tx, ctx) = (
            self.path.clone(),
            self.stamp.clone(),
            self.word.session.rev(),
            self.word.session.doc.clone(),
            self.tx.clone(),
            ctx.clone(),
        );
        std::thread::spawn(move || {
            let result = std::panic::catch_unwind(|| {
                let bytes = ecrinator::odt_project::encode(&doc)?;
                if bytes.len() as u64 > storage::MAX_FILE {
                    return Err("Document trop volumineux (64 Mo maximum).".into());
                }
                integrations::write_relocated(
                    source.as_deref().zip(stamp.as_ref()),
                    &path,
                    &reserved,
                    &bytes,
                )
            })
            .unwrap_or_else(|_| {
                Err("Le classement s’est interrompu. Le fichier d’origine est conservé.".into())
            });
            if result.is_err() {
                integrations::discard_reservation(&path, &reserved);
            }
            let _ = tx.send(Event::Routed {
                path,
                source,
                result,
                rev,
            });
            ctx.request_repaint();
        });
    }
    pub(super) fn sync_routing(&mut self) {
        let school = School::read(&self.word.session.doc);
        let route = (school.subject.clone(), school.work_kind());
        let changed = self.last_routing.as_ref().is_some_and(|old| old != &route);
        self.last_routing = Some(route);
        if changed
            && self.prefs.organize
            && School::present(&self.word.session.doc)
            && school.subject != core::BLANK
        {
            self.last_backup = Instant::now() - Duration::from_secs(11);
        }
    }
    fn chosen_write(&mut self, path: PathBuf, export: bool, ctx: &egui::Context) {
        if self.path_in_another_tab(&path) {
            self.status = "Enregistrement impossible : ce fichier est utilisé dans un autre onglet. Choisissez un autre nom.".into();
            return;
        }
        if path.exists() && (export || self.path.as_ref() != Some(&path)) {
            self.dialog = Some(dialogs::Dialog::Overwrite {
                stamp: storage::stamp(&path),
                path,
                export,
            });
        } else {
            self.write(path, export, ctx);
        }
    }
    pub(super) fn autosave(&mut self, ctx: &egui::Context) {
        if self.busy
            || !self.word.session.dirty
            || self.word.session.rev() == self.backup_rev
            || self.last_backup.elapsed() < Duration::from_secs(10)
        {
            return;
        }
        self.last_backup = Instant::now();
        let doc = self.word.session.doc.clone();
        let path = self.recovery.clone();
        let rev = self.word.session.rev();
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        self.busy = true;
        std::thread::spawn(move || {
            let result = storage::save(&path, &doc);
            let _ = tx.send(Event::Backup { result, rev });
            ctx.request_repaint();
        });
    }
    pub(super) fn recognize(&mut self, ctx: &egui::Context) {
        if self.busy {
            return;
        }
        let at = &self.word.session.sel.focus;
        let media = self
            .word
            .session
            .doc
            .para_at(at)
            .and_then(|p| {
                p.object_at(at.off)
                    .or_else(|| p.object_at(at.off.saturating_sub('\u{fffc}'.len_utf8())))
            })
            .and_then(|o| {
                if let wordcraft_doc::InlineObject::Image { media, .. } = o {
                    Some(media.clone())
                } else {
                    None
                }
            });
        let Some(bytes) = media.and_then(|k| self.word.session.doc.media.get(&k).cloned()) else {
            self.status =
                "Reconnaissance impossible : cliquez sur une image du document, puis choisissez OCR.".into();
            return;
        };
        self.busy = true;
        self.status = "Reconnaissance française locale…".into();
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            let result =
                std::panic::catch_unwind(|| ocr::recognize(&bytes, None)).unwrap_or_else(|_| {
                    Err("La reconnaissance n’a pas abouti. L’image est conservée.".into())
                });
            let _ = tx.send(Event::Recognized(result));
            ctx.request_repaint();
        });
    }
    pub(super) fn poll(&mut self, ctx: &egui::Context) {
        while let Ok(event) = self.rx.try_recv() {
            if matches!(
                &event,
                Event::Opened { .. } | Event::Saved { .. } | Event::Routed { .. }
            ) {
                self.file_job = None;
            }
            self.busy = false;
            match event{
            Event::Picked(kind,path)=>if let Some(path)=path{match kind{
                Pick::Open=>self.request(Action::Open(path),ctx),Pick::Save=>self.chosen_write(force_ext(path,"odt"),false,ctx),Pick::Export(ext)=>self.chosen_write(force_ext(path,&ext),true,ctx),
                Pick::Image=>self.command("insert.picture",json!({"path":path.to_string_lossy(),"width":300.,"alt":path.file_stem().map(|s|s.to_string_lossy()).unwrap_or_default()})),
                Pick::Space=>match integrations::validate_space(&path){Ok(root)=>{self.prefs.space=Some(root);self.prefs.organize=true;self.remember();self.status="Espace associé · classement automatique activé.".into();if self.school.subject!=core::BLANK{self.save(false,ctx);}},Err(e)=>{self.status=format!("Choisis un espace scolaire Organisator : {e}");self.dialog=Some(dialogs::Dialog::organizer());}}
            }},
            Event::Opened{path,result,rev}=>match result{
                Ok(mut doc) if rev==self.word.session.rev()=>{for block in &mut doc.body{if let wordcraft_doc::Block::Table(t)=std::sync::Arc::make_mut(block){if t.props.caption.as_deref()==Some(core::HEADER){t.props.geometry_locked=true;t.props.content_locked=true;}}}self.word.session.set_document(doc);self.last_routing=None;self.word.canvas=Default::default();self.word.canvas.want_focus=true;let recovery=path.file_name().is_some_and(|s|s.to_string_lossy().starts_with("recovery-"));
                    self.path=if !recovery&&path.extension().is_some_and(|s|s.eq_ignore_ascii_case("ecr")||s.eq_ignore_ascii_case("odt")){Some(path.clone())}else{None};self.stamp=self.path.as_ref().and_then(|p|storage::stamp(p));self.word.session.dirty=recovery;self.school=School::read(&self.word.session.doc);self.status=if recovery{"Brouillon récupéré. Enregistrez-le pour le conserver."}else{"Document ouvert"}.into();
                    if core::needs_banner_refresh(&self.word.session.doc){let school=self.school.clone();match core::update_header(&mut self.word.session,&school){Ok(())=>self.status="Bandeau modernisé ; enregistrez pour conserver cette présentation.".into(),Err(e)=>self.status=format!("Bandeau impossible : {e}")}}
                    match ecrinator::blocks::modernize(&mut self.word.session){Ok(n) if n>0=>self.status="Encadrés modernisés ; enregistrez pour conserver cette présentation.".into(),Err(e)=>self.status=format!("Encadrés : {e}"),_=>{}}
                    match ecrinator::image_credits::migrate_visible(&mut self.word.session){Ok(n)if n>0=>self.status="Sources des images déplacées dans le menu contextuel. Enregistrez le document.".into(),Err(e)=>self.status=format!("Sources : {e}"),_=>{}}self.word.session.sel=Selection::caret(core::writing_position(&self.word.session.doc));},
                Ok(_)=>self.status="Ouverture impossible : vous avez continué à écrire. Réessayez après enregistrement.".into(),Err(e)=>self.status=format!("Ouverture impossible : {e}")
            },
            Event::Saved{path,result,rev,export}=>match result{
                Ok(())=>{self.status=format!("{} : {}",if export{"Copie exportée"}else{"Enregistré"},path.display());if !export{self.path=Some(path.clone());self.stamp=storage::stamp(&path);if rev==self.word.session.rev(){self.word.session.dirty=false;let _=std::fs::remove_file(&self.recovery);if let Some(a)=self.pending.take(){self.perform(a,ctx);}}}},Err(e)=>self.status=format!("Écriture impossible : {e}")
            },
            Event::Routed{path,source,result,rev}=>match result{
                Ok(())=>{self.status=format!("{} : {}",if source.is_some(){"Document déplacé"}else{"Document classé"},path.display());self.path=Some(path.clone());self.stamp=storage::stamp(&path);if rev==self.word.session.rev(){self.word.session.dirty=false;let _=std::fs::remove_file(&self.recovery);if let Some(a)=self.pending.take(){self.perform(a,ctx);}}},
                Err(e)=>self.status=format!("Rangement impossible : {e}")
            },
            Event::Backup{result,rev}=>match result{Ok(())=>{self.backup_rev=rev;if self.prefs.organize && self.check_organizer() && School::present(&self.word.session.doc) && School::read(&self.word.session.doc).subject!=core::BLANK && rev==self.word.session.rev(){self.save(false,ctx);}},Err(e)=>self.status=format!("Récupération automatique impossible : {e}. Enregistrez votre cours.")},
            Event::Recognized(result)=>match result{Ok(r)=>{self.status=format!("{} zones reconnues · relisez le texte",r.lines.len());self.dialog=Some(dialogs::Dialog::Ocr(r.text));},Err(e)=>self.status=format!("Reconnaissance impossible : {e}")},
            Event::Printers(printers)=>self.dialog=Some(dialogs::Dialog::Print{printers,index:0,copies:1,duplex:false,gray:false}),
            Event::Printed(result)=>self.status=result.map_or_else(|e|format!("Impression impossible : {e}"),|s|format!("Transmis au spooler Windows : {s}")),
            Event::SpaceCreated(result)=>match result{Ok(made)=>{self.prefs.space=Some(made.root);self.prefs.organize=true;self.remember();self.dialog=None;if self.school.subject!=core::BLANK{self.save(false,ctx);}else{self.status="Espace créé et associé. Choisis une matière pour classer ce document.".into();}if made.icon_warnings>0{ecrinator::diagnostics::record("Espace créé : certaines icônes de dossier n’ont pas pu être appliquées.");}},Err(error)=>{self.status=error;self.dialog=Some(dialogs::Dialog::organizer());}},
        }
        }
    }
    pub(super) fn print_dialog(&mut self, ctx: &egui::Context) {
        if self.busy {
            return;
        }
        self.busy = true;
        self.status = "Recherche des imprimantes…".into();
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            let _ = tx.send(Event::Printers(craft_print::printers()));
            ctx.request_repaint();
        });
    }
    pub(super) fn submit_print(&mut self, job: craft_print::Job, ctx: &egui::Context) {
        let doc = self.word.session.doc.clone();
        let tx = self.tx.clone();
        let ctx = ctx.clone();
        self.busy = true;
        self.status = "Préparation du document et envoi à l’imprimante…".into();
        self.printed.push(std::thread::spawn(move || {
            let result = std::panic::catch_unwind(|| {
                let pdf = ecrinator::exporters::bytes("cours.pdf", &doc)?;
                craft_print::submit(&pdf, &job).map_err(|e| e.to_string())
            })
            .unwrap_or_else(|_| Err("Le service d’impression s’est arrêté.".into()));
            let _ = tx.send(Event::Printed(result));
            ctx.request_repaint();
        }));
    }
}
fn force_ext(path: PathBuf, ext: &str) -> PathBuf {
    if path
        .extension()
        .is_some_and(|s| s.eq_ignore_ascii_case(ext))
    {
        path
    } else {
        Path::new(&path).with_extension(ext)
    }
}
