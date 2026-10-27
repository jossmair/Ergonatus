//! Independent editor instances, worker channels and recovery files per document.
//! The active instance stays in App; swapping preserves the complete Wordcraft
//! canvas, selection, history and view, with no document conversion.
use super::*;
use std::sync::atomic::{AtomicU64, Ordering};
static NEXT: AtomicU64 = AtomicU64::new(1);
pub(super) fn next_id() -> u64 {
    NEXT.fetch_add(1, Ordering::Relaxed)
}
pub(super) fn same_file(a: &std::path::Path, b: &std::path::Path) -> bool {
    let normalized = |p: &std::path::Path| {
        std::fs::canonicalize(p)
            .or_else(|_| {
                p.parent()
                    .zip(p.file_name())
                    .and_then(|(parent, name)| {
                        std::fs::canonicalize(parent).ok().map(|p| p.join(name))
                    })
                    .ok_or_else(|| std::io::Error::from(std::io::ErrorKind::NotFound))
            })
            .or_else(|_| std::path::absolute(p))
            .ok()
    };
    a == b
        || normalized(a).zip(normalized(b)).is_some_and(|(a, b)| {
            if cfg!(target_os = "windows") {
                a.to_string_lossy().to_lowercase() == b.to_string_lossy().to_lowercase()
            } else {
                a == b
            }
        })
}
pub(super) struct DocumentState {
    pub id: u64,
    pub word: WordApp,
    pub school: School,
    pub path: Option<PathBuf>,
    pub file_job: Option<PathBuf>,
    pub stamp: Option<storage::Stamp>,
    pub last_routing: Option<(String, core::WorkKind)>,
    pub tx: Sender<Event>,
    pub rx: Receiver<Event>,
    pub busy: bool,
    pub status: String,
    pub dialog: Option<dialogs::Dialog>,
    pub pending: Option<Action>,
    pub recovery: PathBuf,
    pub last_backup: Instant,
    pub backup_rev: u64,
    pub font: String,
    pub size: f32,
    pub search: String,
    pub replace: String,
    pub pages: pages::PagePane,
}
pub(super) fn editor(doc: wordcraft_doc::Document) -> WordApp {
    let mut session = Session::new(doc);
    session.sel = Selection::caret(core::writing_position(&session.doc));
    session.author = "Élève".into();
    session.view.ruler = false;
    session.view.proofing = false;
    session.view.marks = false;
    session.view.table_gridlines = false;
    session.view.fit = String::new();
    session.view.zoom = 1.;
    let services = Services {
        context_menu_extra: Some(Box::new(super::contextual::image_credit_menu)),
        clipboard_text: Some(Box::new(|| arboard::Clipboard::new().ok()?.get_text().ok())),
        clipboard_picture: Some(Box::new(|| {
            let img = arboard::Clipboard::new().ok()?.get_image().ok()?;
            Some(wordcraft_ui_egui::paste_picture::ClipboardPicture::Pixels {
                width: img.width,
                height: img.height,
                rgba: img.bytes.into_owned(),
            })
        })),
        animations_enabled: Some(Box::new(|| Some(false))),
        ..Default::default()
    };
    let mut word = WordApp::new(session, services);
    word.ui.language = "fr".into();
    word.ui.theme = wordcraft_ui_egui::theme::Appearance::Light;
    word.ui.animations = wordcraft_ui_egui::theme::Animations::Off;
    word.ui.mini_toolbar = false;
    word.autosave = false;
    word.session.autosave = false;
    word.canvas.want_focus = true;
    word
}
impl DocumentState {
    fn new(school: School) -> Result<Self, String> {
        let last_routing = Some((school.subject.clone(), school.work_kind()));
        let word = editor(core::new_document(&school)?);
        let id = next_id();
        let (tx, rx) = mpsc::channel();
        Ok(Self {
            id,
            word,
            school,
            path: None,
            file_job: None,
            stamp: None,
            last_routing,
            tx,
            rx,
            busy: false,
            status: "Prêt à écrire".into(),
            dialog: None,
            pending: None,
            recovery: storage::data_dir().join(format!(
                "recovery-{}-{}-{id}.ecr",
                std::process::id(),
                chrono::Local::now().timestamp_millis()
            )),
            last_backup: Instant::now(),
            backup_rev: 0,
            font: "Arial".into(),
            size: 12.,
            search: String::new(),
            replace: String::new(),
            pages: Default::default(),
        })
    }
}
impl App {
    fn swap_document(&mut self, s: &mut DocumentState) {
        use std::mem::swap;
        swap(&mut self.active_id, &mut s.id);
        macro_rules! field {($($name:ident),*)=>{$(swap(&mut self.$name,&mut s.$name);)*};}
        field!(
            word,
            school,
            path,
            file_job,
            stamp,
            last_routing,
            tx,
            rx,
            busy,
            status,
            dialog,
            pending,
            recovery,
            last_backup,
            backup_rev,
            font,
            size,
            search,
            replace,
            pages
        );
    }
    pub(super) fn activate_tab(&mut self, id: u64) {
        if id == self.active_id {
            return;
        }
        if let Some(at) = self.inactive.iter().position(|s| s.id == id) {
            let mut incoming = self.inactive.remove(at);
            self.swap_document(&mut incoming);
            self.inactive.push(incoming);
        }
    }
    pub(super) fn new_tab(&mut self, school: School) -> Result<(), String> {
        if self.tab_order.len() >= 32 {
            return Err(
                "32 documents sont déjà ouverts. Fermez un onglet avant d’en ouvrir un autre."
                    .into(),
            );
        }
        let mut incoming = DocumentState::new(school)?;
        incoming.pages.visible = self.prefs.pages;
        self.swap_document(&mut incoming);
        self.inactive.push(incoming);
        self.tab_order.push(self.active_id);
        Ok(())
    }
    pub(super) fn next_tab(&mut self, back: bool) {
        if self.tab_order.len() < 2 {
            return;
        }
        if let Some(at) = self.tab_order.iter().position(|id| *id == self.active_id) {
            let n = self.tab_order.len();
            let target = if back { (at + n - 1) % n } else { (at + 1) % n };
            if let Some(id) = self.tab_order.get(target).copied() {
                self.activate_tab(id);
                self.word.canvas.want_focus = true;
            }
        }
    }
    pub(super) fn maintain_tabs(&mut self, ctx: &egui::Context) {
        let active = self.active_id;
        for id in self.tab_order.clone() {
            if id == active {
                continue;
            }
            self.activate_tab(id);
            self.poll(ctx);
            self.sync_routing();
            self.autosave(ctx);
        }
        self.activate_tab(active);
        self.poll(ctx);
        if self.closing_all
            && !self.busy
            && self.pending.is_none()
            && self.dialog.is_none()
            && !self.closing
        {
            self.request(Action::Close, ctx);
        }
    }
    pub(super) fn already_open(&mut self, path: &std::path::Path) -> bool {
        let same = |p: &std::path::Path| same_file(p, path);
        let id = if self
            .path
            .iter()
            .chain(self.file_job.iter())
            .any(|p| same(p))
        {
            Some(self.active_id)
        } else {
            self.inactive
                .iter()
                .find(|s| s.path.iter().chain(s.file_job.iter()).any(|p| same(p)))
                .map(|s| s.id)
        };
        if let Some(id) = id {
            self.activate_tab(id);
            self.word.canvas.want_focus = true;
            true
        } else {
            false
        }
    }
    pub(super) fn path_in_another_tab(&self, path: &std::path::Path) -> bool {
        self.inactive.iter().any(|s| {
            s.path
                .iter()
                .chain(s.file_job.iter())
                .any(|p| same_file(p, path))
        })
    }
    pub(super) fn remove_current_tab(&mut self) -> Result<(), String> {
        let old = self.active_id;
        let recovery = self.recovery.clone();
        if self.tab_order.len() == 1 {
            self.new_tab(School {
                subject: self.school.subject.clone(),
                show_banner: self.school.show_banner,
                ..Default::default()
            })?;
        } else {
            let at = self.tab_order.iter().position(|id| *id == old).unwrap_or(0);
            let target = self
                .tab_order
                .get(at + 1)
                .or_else(|| at.checked_sub(1).and_then(|n| self.tab_order.get(n)))
                .copied();
            if let Some(target) = target {
                self.activate_tab(target);
            }
        }
        self.inactive.retain(|s| s.id != old);
        self.tab_order.retain(|id| *id != old);
        let _ = std::fs::remove_file(recovery);
        self.word.canvas.want_focus = true;
        Ok(())
    }
    fn tab_label(path: Option<&std::path::Path>, school: &School, id: u64) -> String {
        path.and_then(|p| p.file_stem())
            .map(|s| s.to_string_lossy().into_owned())
            .unwrap_or_else(|| {
                if school.title.trim().is_empty() || school.title == "Titre du chapitre" {
                    format!("{} · {id}", school.subject)
                } else {
                    school.title.clone()
                }
            })
    }
    pub(super) fn active_title(&self) -> String {
        Self::tab_label(self.path.as_deref(), &self.school, self.active_id)
    }
    pub(super) fn document_tabs(&mut self, root: &mut egui::Ui) {
        let ctx = root.ctx().clone();
        let items: Vec<_> = self
            .tab_order
            .iter()
            .filter_map(|id| {
                if *id == self.active_id {
                    Some((
                        *id,
                        Self::tab_label(self.path.as_deref(), &self.school, *id),
                        self.word.session.dirty,
                    ))
                } else {
                    self.inactive.iter().find(|s| s.id == *id).map(|s| {
                        (
                            *id,
                            Self::tab_label(s.path.as_deref(), &s.school, *id),
                            s.word.session.dirty,
                        )
                    })
                }
            })
            .collect();
        let mut selected = None;
        let mut closed = None;
        let mut new = false;
        egui::Panel::top("document-tabs")
            .exact_size(38.)
            .frame(
                egui::Frame::new()
                    .fill(Color32::from_rgb(240, 245, 253))
                    .inner_margin(egui::Margin::symmetric(12, 3)),
            )
            .show(root, |ui| {
                ui.horizontal(|ui| {
                    egui::ScrollArea::horizontal()
                        .id_salt("document-tab-scroll")
                        .auto_shrink([true, true])
                        .show(ui, |ui| {
                            ui.horizontal(|ui| {
                                ui.spacing_mut().item_spacing.x = 5.;
                                for (id, label, dirty) in items {
                                    let active = id == self.active_id;
                                    let base = if label.chars().count() > 24 {
                                        label.chars().take(22).collect::<String>() + "…"
                                    } else {
                                        label.clone()
                                    };
                                    let text = if dirty { format!("{base} *") } else { base };
                                    let tab = egui::Frame::new()
                                        .fill(if active {
                                            Color32::WHITE
                                        } else {
                                            Color32::TRANSPARENT
                                        })
                                        .corner_radius(7.)
                                        .inner_margin(egui::Margin::symmetric(3, 0))
                                        .show(ui, |ui| {
                                            ui.horizontal(|ui| {
                                                ui.spacing_mut().item_spacing.x = 0.;
                                                if ui
                                                    .add_sized(
                                                        [150., 28.],
                                                        egui::Button::new(
                                                            RichText::new(text).size(11.5).color(
                                                                if active {
                                                                    INK
                                                                } else {
                                                                    ribbon::MUTED
                                                                },
                                                            ),
                                                        )
                                                        .fill(Color32::TRANSPARENT)
                                                        .stroke(egui::Stroke::NONE),
                                                    )
                                                    .on_hover_text(&label)
                                                    .clicked()
                                                {
                                                    selected = Some(id);
                                                }
                                                if ribbon::control(
                                                    ui,
                                                    "close",
                                                    "",
                                                    &format!("Fermer {label}"),
                                                    false,
                                                )
                                                .clicked()
                                                {
                                                    closed = Some(id);
                                                }
                                            });
                                        });
                                    ctx.data_mut(|d| {
                                        d.insert_temp(
                                            egui::Id::new("last-tab-rect"),
                                            tab.response.rect,
                                        )
                                    });
                                }
                                ui.add_space(5.);
                                let (rect, add) = ui.allocate_exact_size(
                                    egui::vec2(32., 32.),
                                    egui::Sense::click(),
                                );
                                let fill = if add.hovered() {
                                    Color32::from_rgb(218, 232, 255)
                                } else {
                                    Color32::from_rgb(232, 240, 255)
                                };
                                ui.painter().rect_filled(rect, 10., fill);
                                ui.painter().rect_stroke(
                                    rect,
                                    10.,
                                    egui::Stroke::new(0.8, Color32::from_rgb(184, 207, 248)),
                                    egui::StrokeKind::Inside,
                                );
                                let center = rect.center();
                                let stroke = egui::Stroke::new(1.8, BLUE);
                                ui.painter().line_segment(
                                    [center - egui::vec2(5., 0.), center + egui::vec2(5., 0.)],
                                    stroke,
                                );
                                ui.painter().line_segment(
                                    [center - egui::vec2(0., 5.), center + egui::vec2(0., 5.)],
                                    stroke,
                                );
                                glyph::focus(ui, &add);
                                let add = add.on_hover_text("Nouveau document · Ctrl+N");
                                add.widget_info(|| {
                                    egui::WidgetInfo::labeled(
                                        egui::WidgetType::Button,
                                        true,
                                        "Nouveau document",
                                    )
                                });
                                ctx.data_mut(|d| {
                                    d.insert_temp(egui::Id::new("new-tab-rect"), add.rect)
                                });
                                new = add.clicked();
                            });
                        });
                });
            });
        if let Some(id) = selected {
            self.activate_tab(id);
            self.word.canvas.want_focus = true;
        }
        if let Some(id) = closed {
            self.activate_tab(id);
            self.request(Action::CloseTab, &ctx);
        }
        if new {
            self.request(Action::New, &ctx);
        }
    }
}
