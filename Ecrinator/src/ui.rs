//! Accessible school workspace over Wordcraft; see vendor/wordcraft/ECRINATOR-PATCHES.md.
mod college_panel;
mod contextual;
mod design_dialogs;
mod dialogs;
mod hourglass;
mod library_picker;
mod math_table_tools;
mod organizer_panel;
mod pages;
mod ribbon;
mod subject_actions;
mod tabs;
mod tasks;
mod tool_fields;
mod visual_tools;
use crate::school_icons as glyph;
use ecrinator::{
    core::{self, School},
    storage,
};
use eframe::egui::{self, Color32, Key, Modifiers, RichText};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::{
    path::PathBuf,
    sync::mpsc::{self, Receiver, Sender},
    time::{Duration, Instant},
};
use tasks::{Action, Event, Pick};
use wordcraft_engine::{Selection, Session};
use wordcraft_ui_egui::{Services, WordApp};
const INK: Color32 = Color32::from_rgb(30, 49, 73);
const BLUE: Color32 = Color32::from_rgb(55, 113, 249);
#[cfg(test)]
mod tests;

#[derive(Default, Serialize, Deserialize)]
#[serde(default)]
struct Preferences {
    pages: bool,
    space: Option<PathBuf>,
    organize: bool,
    cream: bool,
    profile: usize,
    tools: bool,
}
pub struct App {
    active_id: u64,
    tab_order: Vec<u64>,
    inactive: Vec<tabs::DocumentState>,
    closing_all: bool,
    word: WordApp,
    prefs: Preferences,
    school: School,
    path: Option<PathBuf>,
    file_job: Option<PathBuf>,
    stamp: Option<storage::Stamp>,
    last_routing: Option<(String, core::WorkKind)>,
    tx: Sender<Event>,
    rx: Receiver<Event>,
    busy: bool,
    status: String,
    focus: bool,
    tools: bool,
    dialog: Option<dialogs::Dialog>,
    pending: Option<Action>,
    recovery: PathBuf,
    recoveries: Vec<PathBuf>,
    last_backup: Instant,
    backup_rev: u64,
    font: String,
    size: f32,
    search: String,
    replace: String,
    printed: Vec<std::thread::JoinHandle<()>>,
    qa: Option<PathBuf>,
    frames: u32,
    closing: bool,
    ribbon_tab: usize,
    pages: pages::PagePane,
}
impl App {
    pub fn new(ctx: &egui::Context, path: Option<PathBuf>, qa: Option<PathBuf>) -> Self {
        egui_extras::install_image_loaders(ctx);
        let data_error = std::fs::create_dir_all(storage::data_dir()).err();
        let prefs = std::fs::read(storage::data_dir().join("preferences.json"))
            .ok()
            .and_then(|b| serde_json::from_slice(&b).ok())
            .unwrap_or_default();
        ecrinator::verification::init_fonts();
        let school = School::default();
        let last_routing = Some((school.subject.clone(), school.work_kind()));
        let active_id = tabs::next_id();
        let doc = core::new_document(&school).unwrap_or_default();
        let word = tabs::editor(doc);
        let (tx, rx) = mpsc::channel();
        let recovery = storage::data_dir().join(format!(
            "recovery-{}-{}-{active_id}.ecr",
            std::process::id(),
            chrono::Local::now().timestamp_millis()
        ));
        let recoveries = std::fs::read_dir(storage::data_dir())
            .into_iter()
            .flatten()
            .filter_map(Result::ok)
            .map(|d| d.path())
            .filter(|p| {
                p.file_name()
                    .is_some_and(|s| s.to_string_lossy().starts_with("recovery-"))
                    && p.extension().is_some_and(|s| s == "ecr")
            })
            .collect();
        let mut app = Self {
            active_id,
            tab_order: vec![active_id],
            inactive: Vec::new(),
            closing_all: false,
            word,
            prefs,
            school,
            path: None,
            file_job: None,
            stamp: None,
            last_routing,
            tx,
            rx,
            busy: false,
            status: "Prêt à écrire · travail local".into(),
            focus: false,
            tools: false,
            dialog: None,
            pending: None,
            recovery,
            recoveries,
            last_backup: Instant::now(),
            backup_rev: 0,
            font: "Arial".into(),
            size: 12.,
            search: String::new(),
            replace: String::new(),
            printed: Vec::new(),
            qa,
            frames: 0,
            closing: false,
            ribbon_tab: 0,
            pages: Default::default(),
        };
        if let Some(p) = path {
            app.open(p, ctx);
        } else if !app.recoveries.is_empty() {
            app.dialog = Some(dialogs::Dialog::Recovery);
        }
        app.check_organizer();
        app.pages.visible = app.prefs.pages;
        app.tools = app.prefs.tools;
        if let Some(e) = data_error {
            app.status = format!(
                "Sauvegarde automatique impossible : dossier de données inaccessible ({e}). Enregistrez votre cours dans un dossier disponible."
            );
        }
        app
    }
    fn command(&mut self, id: &str, params: serde_json::Value) {
        match self.word.run(id, params) {
            Ok(_) => {
                self.word.canvas.want_focus = true;
            }
            Err(e) => {
                ecrinator::diagnostics::record(&format!("Commande {id} : {e}"));
                self.status = format!("Action impossible : {e}");
            }
        }
    }
    fn message(&mut self, result: Result<(), String>, success: &str) {
        self.status =
            result.map_or_else(|e| format!("Action impossible : {e}"), |_| success.into());
        self.word.canvas.want_focus = true;
    }
    fn remember(&mut self) {
        if let Ok(bytes) = serde_json::to_vec(&self.prefs) {
            if let Err(e) =
                storage::atomic_write(&storage::data_dir().join("preferences.json"), &bytes)
            {
                self.status = format!("Préférences non enregistrées : {e}");
            }
        }
    }
    fn shortcuts(&mut self, ctx: &egui::Context) {
        if self.dialog.is_some() || self.pending.is_some() {
            return;
        }
        let ctrl = Modifiers {
            ctrl: true,
            command: true,
            ..Default::default()
        };
        if core::School::present(&self.word.session.doc)
            && self.school.show_banner
            && ctx.input_mut(|i| i.consume_key(ctrl, Key::A))
        {
            self.word.session.sel = Selection {
                anchor: core::writing_position(&self.word.session.doc),
                focus: self.word.session.doc.end_of(wordcraft_doc::StoryRef::Body),
            };
        }
        if ctx.input_mut(|i| i.consume_key(ctrl, Key::W)) {
            self.request(Action::CloseTab, ctx);
            return;
        }
        if ctx.input_mut(|i| i.consume_key(ctrl, Key::Tab)) {
            self.next_tab(false);
        }
        if ctx.input_mut(|i| {
            i.consume_key(
                Modifiers {
                    shift: true,
                    ..ctrl
                },
                Key::Tab,
            )
        }) {
            self.next_tab(true);
        }
        for (key, shift, action) in [
            (Key::N, false, 0),
            (Key::O, false, 1),
            (Key::S, false, 2),
            (Key::S, true, 3),
            (Key::P, false, 4),
            (Key::F, false, 5),
            (Key::H, false, 5),
        ] {
            let m = Modifiers {
                ctrl: true,
                command: true,
                shift,
                ..Default::default()
            };
            if ctx.input_mut(|i| i.consume_key(m, key)) {
                match action {
                    0 => self.request(Action::New, ctx),
                    1 => self.pick(Pick::Open, ctx),
                    2 => self.save(false, ctx),
                    3 => self.save(true, ctx),
                    4 => self.print_dialog(ctx),
                    _ => self.dialog = Some(dialogs::Dialog::Search),
                }
            }
        }
        if ctx.input_mut(|i| i.consume_key(Modifiers::NONE, Key::F11)) {
            self.focus = !self.focus;
        }
        if self.focus && ctx.input_mut(|i| i.consume_key(Modifiers::NONE, Key::Escape)) {
            self.focus = false;
        }
    }
    fn style(&self, ctx: &egui::Context) {
        ctx.style_mut_of(egui::Theme::Light, |s| {
            s.animation_time = 0.;
            s.spacing.interact_size = egui::vec2(32., 30.);
            s.spacing.button_padding = egui::vec2(8., 5.);
            s.visuals.override_text_color = Some(INK);
            s.visuals.window_fill = Color32::WHITE;
            s.visuals.panel_fill = Color32::from_rgb(246, 249, 253);
            s.visuals.widgets.inactive.bg_fill = Color32::WHITE;
            s.visuals.widgets.inactive.bg_stroke =
                egui::Stroke::new(0.8, Color32::from_rgb(225, 230, 238));
            s.visuals.widgets.inactive.corner_radius = 8.into();
            s.visuals.widgets.hovered.bg_fill = Color32::from_rgb(244, 247, 253);
            s.visuals.widgets.hovered.bg_stroke =
                egui::Stroke::new(1., Color32::from_rgb(159, 183, 227));
            s.visuals.widgets.hovered.corner_radius = 8.into();
            s.visuals.widgets.active.bg_fill = Color32::from_rgb(235, 242, 255);
            s.visuals.widgets.active.bg_stroke = egui::Stroke::new(1.2, BLUE);
            s.visuals.widgets.active.corner_radius = 8.into();
            s.visuals.selection.bg_fill = Color32::from_rgb(198, 222, 255);
            s.visuals.selection.stroke = egui::Stroke::new(1., BLUE);
            s.text_styles
                .insert(egui::TextStyle::Body, egui::FontId::proportional(13.));
            s.text_styles
                .insert(egui::TextStyle::Button, egui::FontId::proportional(13.));
        });
    }
    fn show(&mut self, root: &mut egui::Ui) {
        let ctx = &root.ctx().clone();
        self.maintain_tabs(ctx);
        // File drops must use the same document identity and unsaved-work guard
        // as Open, before Wordcraft can consume them through its own file menu.
        let dropped = ctx.input_mut(|i| std::mem::take(&mut i.raw.dropped_files));
        if let Some(file) = dropped.first() {
            self.dropped_file(file.path().to_path_buf(), ctx);
        }
        self.word.logic(ctx);
        self.style(ctx);
        self.shortcuts(ctx);
        self.school = School::read(&self.word.session.doc);
        if self.dialog.is_some() || self.pending.is_some() {
            // Input is disabled; the workspace must keep its normal colours.
            root.visuals_mut().disabled_alpha = 1.;
            root.disable();
        }
        let pages = self.word.session.layout().pages.len();
        self.header_bar(root);
        self.document_tabs(root);
        if !self.focus {
            self.editing_bar(root);
        }
        egui::Panel::bottom("status")
            .exact_size(34.)
            .frame(
                egui::Frame::new()
                    .fill(Color32::from_rgb(249, 251, 254))
                    .inner_margin(egui::Margin::symmetric(12, 1)),
            )
            .show(root, |ui| {
                ui.horizontal(|ui| {
                    ui.spacing_mut().item_spacing.x = 6.;
                    ui.label(
                        RichText::new(format!(
                            "Page {} / {}",
                            self.word
                                .session
                                .page_hint
                                .saturating_add(1)
                                .min(pages.max(1)),
                            pages
                        ))
                        .size(12.),
                    );
                    if self.word.word_count.0 != self.word.session.rev() {
                        self.word.word_count = (
                            self.word.session.rev(),
                            self.word
                                .session
                                .doc
                                .plain_text(wordcraft_doc::StoryRef::Body)
                                .split_whitespace()
                                .count(),
                        );
                    }
                    if ctx.content_rect().width() > 950. {
                        ui.separator();
                        ui.label(
                            RichText::new(format!("{} mots", self.word.word_count.1))
                                .size(11.)
                                .color(Color32::from_rgb(105, 119, 139)),
                        );
                    }
                    ui.separator();
                    let state = if self.busy {
                        "En cours…"
                    } else if self.word.session.dirty {
                        "À enregistrer"
                    } else if self.path.is_none() {
                        "Nouveau"
                    } else {
                        "Enregistré"
                    };
                    ui.label(
                        RichText::new(state)
                            .size(11.)
                            .color(Color32::from_rgb(84, 104, 125)),
                    )
                    .on_hover_text(&self.status);
                    ui.separator();
                    let organize = ui
                        .add_enabled_ui(self.school.subject != core::BLANK, |ui| {
                            ribbon::control(
                                ui,
                                "folder",
                                if ctx.content_rect().width() > 950. {
                                    "Classer"
                                } else {
                                    ""
                                },
                                "Ranger avec Organisator",
                                false,
                            )
                        })
                        .inner;
                    if organize.clicked() {
                        self.dialog = Some(dialogs::Dialog::organizer());
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ribbon::control(
                            ui,
                            "pages",
                            "",
                            "Afficher les vignettes",
                            self.pages.visible,
                        )
                        .clicked()
                        {
                            self.pages.visible = !self.pages.visible;
                            self.prefs.pages = self.pages.visible;
                            self.remember();
                        }
                        if ribbon::control(ui, "zoom", "", "Ajuster à la largeur", false).clicked()
                        {
                            self.command("view.pageWidth", json!({}));
                        }
                        let mut zoom = self.word.session.view.zoom * 100.;
                        if ui
                            .add(
                                egui::DragValue::new(&mut zoom)
                                    .range(40. ..=200.)
                                    .suffix(" %")
                                    .speed(1.),
                            )
                            .changed()
                        {
                            self.command("view.zoom", json!({"value":zoom}));
                        }
                    });
                });
            });
        if !self.focus && self.tools && ctx.content_rect().width() > 1000. {
            self.subject_tools(root);
        }
        if !self.focus {
            self.pages.sync(&mut self.word, ctx);
            if let Some(page) = self.pages.show(root, pages, self.word.session.page_hint) {
                let layout = self.word.session.layout();
                if let Some(p) = layout.pages.get(page) {
                    if let Some(pos) = layout.hit(
                        page,
                        p.body.x + 2.,
                        p.body.y + 2.,
                        wordcraft_doc::StoryRef::Body,
                    ) {
                        self.word.session.sel = Selection::caret(pos);
                        self.word.session.page_hint = page;
                        self.word.canvas.scroll_to_caret = true;
                        self.word.canvas.want_focus = true;
                    }
                }
            }
        }
        if self.status.to_lowercase().contains("impossible")
            || self.status.to_lowercase().contains("indisponible")
            || self.status.to_lowercase().contains("échoué")
            || self.status.to_lowercase().contains("a changé")
        {
            egui::Panel::bottom("error-notice")
                .frame(
                    egui::Frame::new()
                        .fill(Color32::from_rgb(255, 241, 234))
                        .inner_margin(8.),
                )
                .show(root, |ui| {
                    ui.add(
                        egui::Label::new(
                            RichText::new(&self.status).color(Color32::from_rgb(137, 41, 25)),
                        )
                        .wrap(),
                    );
                });
        }
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE.fill(if self.prefs.cream {
                Color32::from_rgb(239, 236, 220)
            } else {
                Color32::from_rgb(216, 224, 233)
            }))
            .show(root, |ui| {
                // Block edits while a dialog owns focus, but keep paper and colours intact.
                ui.visuals_mut().disabled_alpha = 1.;
                ui.add_enabled_ui(self.pending.is_none() && self.dialog.is_none(), |ui| {
                    // egui also stores scroll/focus state outside WordApp. Give
                    // every document its own namespace for that persistent state.
                    ui.push_id(("document-canvas", self.active_id), |ui| {
                        wordcraft_ui_egui::canvas::show(&mut self.word, ui)
                    });
                });
            });
        wordcraft_ui_egui::dialogs::show(&mut self.word, ctx);
        wordcraft_ui_egui::colors::show(&mut self.word, ctx);
        wordcraft_ui_egui::content_controls::popup(&mut self.word, ctx);
        self.box_context(ctx);
        self.show_dialog(ctx);
        self.unsaved_dialog(ctx);
        if self.dialog.is_none() && self.pending.is_none() {
            wordcraft_ui_egui::keys::global_shortcuts(&mut self.word, ctx);
        }
        if !self.closing && ctx.input(|i| i.viewport().close_requested()) {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.request(Action::Close, ctx);
        }
        self.sync_routing();
        self.autosave(ctx);
        ctx.request_repaint_after(Duration::from_millis(500));
    }
}
impl eframe::App for App {
    fn ui(&mut self, root: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = &root.ctx().clone();
        self.show(root);
        if self.busy {
            hourglass::show(ctx, "Écrinator", Color32::from_rgb(11, 87, 237), true);
        }
        self.frames += 1;
        if self.qa.is_some() && self.frames == 4 {
            if std::env::var("ECRINATOR_QA_TABS").as_deref() == Ok("1") {
                let original = self.active_id;
                for subject in ["SVT", "Français"] {
                    let _ = self.new_tab(School {
                        subject: subject.into(),
                        ..Default::default()
                    });
                }
                self.activate_tab(original);
                if let Some(i) = self.word.session.doc.body.iter().position(|b| {
                    b.as_table().is_some_and(|t| {
                        t.props.description.as_deref() == Some(ecrinator::blocks::DESIGN)
                    })
                }) {
                    self.word.session.sel = Selection::caret(wordcraft_doc::Pos::new(
                        wordcraft_doc::StoryRef::Body,
                        wordcraft_doc::Path(vec![i as u32, 0, 0, 1]),
                        0,
                    ));
                }
                self.tools = true;
            }
            match std::env::var("ECRINATOR_QA_DIALOG").as_deref() {
                Ok("calculation") => {
                    self.dialog = Some(dialogs::Dialog::Calculation(
                        ecrinator::arithmetic::Calculation {
                            operation: ecrinator::arithmetic::Operation::Multiply,
                            a: "12,3".into(),
                            b: "4,5".into(),
                            ..Default::default()
                        },
                    ))
                }
                Ok("timeline") => self.dialog = Some(dialogs::Dialog::Timeline(Default::default())),
                Ok("chart") => {
                    self.dialog = Some(dialogs::Dialog::Chart {
                        labels: "Janvier;Février;Mars".into(),
                        values: "12;18;15".into(),
                    })
                }
                Ok("library") => {
                    self.dialog = Some(dialogs::Dialog::Library {
                        category: "SVT".into(),
                        query: String::new(),
                        selected: Some("cellule-animale".into()),
                        topic: String::new(),
                        page: 0,
                    })
                }
                Ok("formula") => {
                    self.dialog = Some(dialogs::Dialog::Formula {
                        kind: 0,
                        a: "3".into(),
                        b: "4".into(),
                    })
                }
                Ok("table") => self.dialog = Some(dialogs::Dialog::Table { rows: 3, cols: 4 }),
                Ok("header") => self.dialog = Some(dialogs::Dialog::Header(self.school.clone())),
                Ok("box") => {
                    if let Some(i) = self.word.session.doc.body.iter().position(|b| {
                        b.as_table().is_some_and(|t| {
                            t.props.description.as_deref() == Some(ecrinator::blocks::DESIGN)
                        })
                    }) {
                        self.word.session.sel = Selection::caret(wordcraft_doc::Pos::new(
                            wordcraft_doc::StoryRef::Body,
                            wordcraft_doc::Path(vec![i as u32, 0, 0, 1]),
                            0,
                        ));
                        if let Ok(style) = ecrinator::blocks::appearance(&self.word.session) {
                            self.dialog = Some(dialogs::Dialog::Box(style));
                        }
                    }
                }
                _ => {}
            }
        }
        if self.qa.is_some() && self.frames == 30 {
            ctx.send_viewport_cmd(egui::ViewportCommand::Screenshot(egui::UserData::default()));
        }
        for e in ctx.input(|i| i.events.clone()) {
            if let egui::Event::Screenshot { image, .. } = e {
                if let Some(path) = self.qa.take() {
                    let rgba: Vec<u8> = image.pixels.iter().flat_map(|p| p.to_array()).collect();
                    let result = image::save_buffer(
                        &path,
                        &rgba,
                        image.size[0] as u32,
                        image.size[1] as u32,
                        image::ColorType::Rgba8,
                    );
                    if let Err(e) = result {
                        self.status = e.to_string();
                    }
                    self.closing = true;
                    ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                }
            }
        }
    }
    fn raw_input_hook(&mut self, _ctx: &egui::Context, raw: &mut egui::RawInput) {
        self.word.raw_input_hook(raw);
    }
    fn on_exit(&mut self, _gl: Option<&eframe::glow::Context>) {
        for worker in self.printed.drain(..) {
            let _ = worker.join();
        }
    }
}
