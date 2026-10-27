//! Focused, responsive editors with a live preview and a fixed action row.
use super::*;
use dialogs::Dialog;
use ecrinator::{blocks, pedagogy};
use wordcraft_doc::props::Rgb;
fn rgb(c: Rgb) -> Color32 {
    Color32::from_rgb(c.0, c.1, c.2)
}
fn label(ui: &mut egui::Ui, text: &str) {
    ui.label(RichText::new(text).size(11.5).strong().color(INK));
}
fn field(ui: &mut egui::Ui, value: &mut String, hint: &str) {
    ui.add(
        egui::TextEdit::singleline(value)
            .hint_text(hint)
            .desired_width(ui.available_width())
            .margin(egui::vec2(9., 8.)),
    );
}
fn checkbox(ui: &mut egui::Ui, value: &mut bool, text: &str) {
    ui.scope(|ui| {
        let v = ui.visuals_mut();
        v.widgets.inactive.corner_radius = 3.into();
        v.widgets.hovered.corner_radius = 3.into();
        v.widgets.active.corner_radius = 3.into();
        ui.checkbox(value, text);
    });
}
fn input_frame() -> egui::Frame {
    egui::Frame::new()
        .fill(Color32::from_rgb(247, 249, 252))
        .corner_radius(10.)
        .inner_margin(10.)
}
impl App {
    pub(super) fn design_dialog(&mut self, ctx: &egui::Context, dialog: &mut Dialog) -> bool {
        let mut close = false;
        let mut apply = false;
        let (title, subtitle, icon, action) = match dialog {
            Dialog::Header(_) => (
                "Le bandeau du cours",
                "Les repères de votre page.",
                "header",
                "Appliquer",
            ),
            Dialog::Box(_) => (
                "Mon encadré",
                "Un repère clair dans votre cours.",
                "frame",
                "Appliquer",
            ),
            Dialog::Formula { .. } => (
                "Une formule",
                "Choisissez une forme, puis complétez-la.",
                "formula",
                "Insérer",
            ),
            Dialog::Calculation(_) => (
                "Une opération à compléter",
                "Des cases pour écrire ton raisonnement.",
                "calculation",
                "Insérer les cases",
            ),
            Dialog::Table { .. } => (
                "Un tableau",
                "Choisissez le nombre de lignes et de colonnes.",
                "table",
                "Insérer",
            ),
            Dialog::Page { .. } => (
                "Ma page",
                "L’espace pour écrire, à votre rythme.",
                "layout",
                "Appliquer",
            ),
            Dialog::Timeline(_) => (
                "Une frise chronologique",
                "Des dates, des repères, une histoire.",
                "timeline",
                "Appliquer",
            ),
            Dialog::Chart { .. } => (
                "Un graphique",
                "Comparez vos mesures en un regard.",
                "graph",
                "Insérer",
            ),
            _ => return true,
        };
        let response = egui::Modal::new(egui::Id::new("ecr-design-dialog"))
            .backdrop_color(Color32::from_rgba_unmultiplied(30, 49, 73, 12))
            .frame(
                egui::Frame::new()
                    .fill(Color32::WHITE)
                    .stroke(egui::Stroke::new(0.8, Color32::from_rgb(227, 232, 240)))
                    .corner_radius(16.)
                    .inner_margin(20.),
            )
            .show(ctx, |ui| {
                ui.set_width((ctx.content_rect().width() - 88.).clamp(260., 500.));
                ui.spacing_mut().item_spacing = egui::vec2(10., 9.);
                ui.horizontal(|ui| {
                    let badge = ui.allocate_space(egui::vec2(40., 40.)).1;
                    ui.painter()
                        .rect_filled(badge, 12., Color32::from_rgb(237, 243, 255));
                    glyph::paint(ui, icon, badge.shrink(9.));
                    ui.vertical(|ui| {
                        ui.label(RichText::new(title).size(20.).strong());
                        ui.label(RichText::new(subtitle).size(11.).color(ribbon::MUTED));
                    });
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::TOP), |ui| {
                        if ribbon::control(ui, "close", "", "Fermer", false).clicked() {
                            close = true;
                        }
                    });
                });
                ui.add_space(6.);
                egui::ScrollArea::vertical()
                    .id_salt("design-dialog-scroll")
                    .max_height((ctx.content_rect().height() - 195.).clamp(120., 480.))
                    .show(ui, |ui| match dialog {
                        Dialog::Header(s) => header_fields(ui, s),
                        Dialog::Box(style) => box_fields(ui, style),
                        Dialog::Formula { kind, a, b } => {
                            super::tool_fields::formula(ui, kind, a, b)
                        }
                        Dialog::Calculation(c) => super::tool_fields::calculation(ui, c),
                        Dialog::Table { rows, cols } => super::tool_fields::table(ui, rows, cols),
                        Dialog::Timeline(t) => super::visual_tools::timeline_fields(ui, t),
                        Dialog::Chart { labels, values } => {
                            super::visual_tools::chart_fields(ui, labels, values)
                        }
                        Dialog::Page {
                            margin,
                            line,
                            spacing,
                        } => super::tool_fields::page(ui, margin, line, spacing),
                        _ => {}
                    });
                ui.add_space(8.);
                ui.separator();
                ui.add_space(5.);
                ui.horizontal(|ui| {
                    if ui
                        .add_sized(
                            [90., 36.],
                            egui::Button::new("Annuler")
                                .fill(Color32::TRANSPARENT)
                                .stroke(egui::Stroke::NONE),
                        )
                        .clicked()
                    {
                        close = true;
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        let ready = super::tool_fields::ready(dialog);
                        let r = ui.add_enabled(
                            ready,
                            egui::Button::new(RichText::new(action).color(Color32::WHITE).strong())
                                .min_size(egui::vec2(132., 38.))
                                .fill(BLUE)
                                .stroke(egui::Stroke::NONE)
                                .corner_radius(10.),
                        );
                        ctx.data_mut(|d| {
                            d.insert_temp(egui::Id::new("ecr-design-apply-rect"), r.rect)
                        });
                        apply = r.clicked();
                    });
                });
            });
        if apply {
            let result = match dialog {
                Dialog::Header(s) => core::update_header(&mut self.word.session, s),
                Dialog::Box(style) => blocks::change(&mut self.word.session, style),
                Dialog::Formula { kind, a, b } => self
                    .word
                    .session
                    .run(
                        "insert.equation",
                        &json!({"linear":super::tool_fields::linear(*kind,a,b),"edit":false}),
                    )
                    .map(|_| ())
                    .map_err(|e| e.to_string()),
                Dialog::Table { rows, cols } => self
                    .word
                    .session
                    .run("insert.table", &json!({"rows":rows,"cols":cols}))
                    .map(|_| ())
                    .map_err(|e| e.to_string()),
                Dialog::Calculation(c) => ecrinator::arithmetic::apply(&mut self.word.session, c),
                Dialog::Timeline(t) => ecrinator::timeline::apply(&mut self.word.session, t),
                Dialog::Chart { labels, values } => {
                    super::visual_tools::insert_chart(&mut self.word.session, labels, values)
                }
                Dialog::Page {
                    margin,
                    line,
                    spacing,
                } => {
                    let pt = *margin * 72. / 25.4;
                    self.command(
                        "layout.margins",
                        json!({"top":pt,"bottom":pt,"left":pt,"right":pt}),
                    );
                    self.command("para.lineSpacing", json!({"value":line}));
                    self.command("format.spacing", json!({"points":spacing}));
                    Ok(())
                }
                _ => Ok(()),
            };
            close = result.is_ok();
            self.message(result, "Modification appliquée");
        }
        close || response.should_close()
    }
}
fn header_fields(ui: &mut egui::Ui, s: &mut School) {
    banner_preview(ui, s);
    ui.add_space(4.);
    label(ui, "Matière");
    let previous = s.subject.clone();
    egui::ComboBox::from_id_salt("design-subject")
        .width(ui.available_width() - 12.)
        .height(300.)
        .selected_text(&s.subject)
        .show_ui(ui, |ui| {
            for name in core::SUBJECTS {
                ui.selectable_value(&mut s.subject, (*name).into(), *name);
            }
        });
    if previous != s.subject {
        if s.subject == core::BLANK {
            s.show_banner = false;
        } else if previous == core::BLANK {
            s.show_banner = true;
        }
    }
    if s.subject == core::BLANK {
        ui.add_space(8.);
        ui.label(
            RichText::new("Une feuille libre, sans illustration ni titre imposé.")
                .size(12.)
                .color(ribbon::MUTED),
        );
        return;
    }
    if s.subject == "Autre matière" || !core::SUBJECTS.contains(&s.subject.as_str()) {
        label(ui, "Nom de la matière");
        field(ui, &mut s.subject, "Ma matière");
    }
    ui.add_space(3.);
    label(ui, "Chapitre :");
    egui::ComboBox::from_id_salt("chapter-number")
        .width(90.)
        .height(240.)
        .selected_text(s.chapter.to_string())
        .show_ui(ui, |ui| {
            if s.chapter > 99 {
                let current = s.chapter;
                ui.selectable_value(&mut s.chapter, current, current.to_string());
            }
            for n in 1..=99 {
                ui.selectable_value(&mut s.chapter, n, n.to_string());
            }
        });
    ui.add_space(6.);
    label(ui, "Titre du cours · facultatif");
    field(ui, &mut s.title, "Ex. Le récit d’aventure");
    ui.add_space(4.);
    ui.columns(2, |cols| {
        checkbox(&mut cols[0], &mut s.show_date, "Afficher la date");
        field(&mut cols[0], &mut s.date, "jj/mm/aaaa");
        checkbox(&mut cols[1], &mut s.show_time, "Afficher l’heure");
        field(&mut cols[1], &mut s.time, "hh:mm");
    });
    ui.add_space(5.);
    label(ui, "Type de travail");
    let mut kind = s.work_kind();
    input_frame().show(ui, |ui| {
        ui.set_min_width(ui.available_width());
        ui.horizontal_wrapped(|ui| {
            for option in core::WorkKind::ALL {
                ui.radio_value(&mut kind, option, option.label());
            }
        });
    });
    s.set_work_kind(kind);
    ui.label(
        RichText::new(format!("Dossier Organisator : {}", s.folder_kind()))
            .size(11.)
            .color(ribbon::MUTED),
    );
    checkbox(
        ui,
        &mut s.show_banner,
        "Afficher le bandeau sur la première page",
    );
}
fn banner_preview(ui: &mut egui::Ui, s: &School) {
    if !s.banner_visible() {
        input_frame().show(ui, |ui| {
            ui.label("Une page blanche, sans bandeau");
        });
        return;
    }
    let art = ecrinator::subjects::for_subject(&s.subject);
    let w = ui.available_width();
    let h = w * core::BANNER_HEIGHT / 595.276;
    let r = ui.allocate_space(egui::vec2(w, h)).1;
    let crop = ecrinator::subjects::background_crop(art.background, w, h);
    egui::Image::from_bytes(format!("bytes://background/{}", art.slug), art.background)
        .uv(egui::Rect::from_min_max(
            egui::pos2(crop[0], crop[1]),
            egui::pos2(1. - crop[2], 1. - crop[3]),
        ))
        .paint_at(ui, r);
    let boundary = r.left() + w * 224. / 595.276;
    let fade = w * 32. / 595.276;
    let mut previous: f32 = 0.;
    for n in 0..=16 {
        let target = 0.88 * ((n as f32 + 0.5) / 16.).min(1.);
        let alpha = ((target - previous) / (1. - previous).max(0.001)).clamp(0., 1.);
        let x = boundary - fade + n as f32 * fade / 16.;
        ui.painter().rect_filled(
            egui::Rect::from_min_max(egui::pos2(x, r.top()), r.right_bottom()),
            0.,
            Color32::from_white_alpha((alpha * 255.).round() as u8),
        );
        previous = target;
    }
    let x = r.left() + w * 0.4;
    ui.painter().text(
        egui::pos2(x, r.top() + h * 0.21),
        egui::Align2::LEFT_CENTER,
        &s.subject,
        egui::FontId::proportional(13.),
        rgb(s.color()),
    );
    let title = if s.title.trim().is_empty() {
        "Votre titre · facultatif"
    } else {
        &s.title
    };
    let galley = ui
        .painter()
        .layout(title.into(), egui::FontId::proportional(11.), INK, w * 0.54);
    ui.painter()
        .galley(egui::pos2(x, r.top() + h * 0.38), galley, INK);
    ui.painter().text(
        egui::pos2(x, r.top() + h * 0.75),
        egui::Align2::LEFT_CENTER,
        format!("Chapitre : {}", s.chapter),
        egui::FontId::proportional(10.),
        INK,
    );
}
fn box_fields(ui: &mut egui::Ui, style: &mut blocks::Appearance) {
    let t = pedagogy::theme(&style.model);
    egui::Frame::new()
        .fill(Color32::from_rgb(
            style.background[0],
            style.background[1],
            style.background[2],
        ))
        .stroke(egui::Stroke::new(
            0.7,
            rgb(pedagogy::outline(Rgb(
                style.border[0],
                style.border[1],
                style.border[2],
            ))),
        ))
        .corner_radius(style.radius)
        .inner_margin(14.)
        .show(ui, |ui| {
            ui.set_min_width(ui.available_width());
            ui.horizontal(|ui| {
                ui.add(
                    egui::Image::from_bytes(
                        format!("bytes://box-preview/{}", t.icon),
                        pedagogy::icon_png(&style.model),
                    )
                    .fit_to_exact_size(egui::vec2(28., 28.)),
                );
                ui.label(
                    RichText::new(&style.title)
                        .size(16.)
                        .strong()
                        .color(Color32::from_rgb(
                            style.border[0],
                            style.border[1],
                            style.border[2],
                        )),
                );
            });
            ui.label(RichText::new("Votre texte reste entièrement modifiable.").size(12.));
        });
    ui.add_space(3.);
    label(ui, "Modèle");
    let previous = style.model.clone();
    egui::ComboBox::from_id_salt("design-box-model")
        .width(ui.available_width() - 12.)
        .selected_text(&style.model)
        .show_ui(ui, |ui| {
            for model in blocks::TEMPLATES {
                ui.selectable_value(&mut style.model, (*model).into(), *model);
            }
        });
    if style.model != previous {
        if style.title == previous {
            style.title = style.model.clone();
        }
        style.use_model_colors();
    }
    label(ui, "Titre de l’encadré");
    field(ui, &mut style.title, "Mon titre");
    ui.add_space(5.);
    egui::CollapsingHeader::new("Couleurs et bordure").show(ui, |ui| {
        ui.horizontal(|ui| {
            ui.label("Fond");
            ui.color_edit_button_srgb(&mut style.background);
            ui.label("Accent");
            ui.color_edit_button_srgb(&mut style.border);
        });
        ui.horizontal(|ui| {
            ui.label("Arrondi");
            ui.add(egui::Slider::new(&mut style.radius, 0. ..=16.).suffix(" pt"));
        });
        ui.horizontal(|ui| {
            ui.label("Bordure");
            ui.add(egui::Slider::new(&mut style.width, 0.5..=3.).suffix(" pt"));
        });
        if ui.button("Rétablir les couleurs du modèle").clicked() {
            style.use_model_colors();
        }
    });
}
