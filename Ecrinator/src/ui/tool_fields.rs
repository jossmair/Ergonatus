//! Small, readable tool editors. Equation previews use the document renderer.
use super::*;
use dialogs::Dialog;

pub(super) fn linear(kind: usize, a: &str, b: &str) -> String {
    match kind {
        0 => format!("({a})/({b})"),
        1 => format!("√({a})"),
        _ => format!("({a})^({b})"),
    }
}
pub(super) fn ready(dialog: &Dialog) -> bool {
    match dialog {
        Dialog::Calculation(c) => c.validate().is_ok(),
        Dialog::Timeline(t) => t.validate().is_ok(),
        Dialog::Chart { labels, values } => super::visual_tools::chart_data(labels, values).is_ok(),
        Dialog::Formula { kind, a, b } => {
            !a.trim().is_empty() && (*kind == 1 || !b.trim().is_empty())
        }
        _ => true,
    }
}
fn input(ui: &mut egui::Ui, label: &str, text: &mut String) {
    ui.label(RichText::new(label).size(12.).strong().color(INK));
    let r = ui.add(
        egui::TextEdit::singleline(text)
            .font(egui::FontId::proportional(18.))
            .desired_width(ui.available_width())
            .margin(egui::vec2(12., 10.))
            .char_limit(120),
    );
    r.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::TextEdit, true, label));
}
pub(super) fn formula(ui: &mut egui::Ui, kind: &mut usize, a: &mut String, b: &mut String) {
    egui::Frame::new()
        .fill(Color32::from_rgb(243, 246, 251))
        .corner_radius(12.)
        .inner_margin(5.)
        .show(ui, |ui| {
            let w = (ui.available_width() - 12.) / 3.;
            ui.horizontal(|ui| {
                ui.spacing_mut().item_spacing.x = 6.;
                for (i, (icon, label)) in [
                    ("fraction", "Fraction"),
                    ("root", "Racine"),
                    ("power", "Puissance"),
                ]
                .into_iter()
                .enumerate()
                {
                    let r = ui.add_sized(
                        [w, 64.],
                        egui::Button::new("")
                            .fill(if *kind == i {
                                Color32::WHITE
                            } else {
                                Color32::TRANSPARENT
                            })
                            .stroke(if *kind == i {
                                egui::Stroke::new(1., Color32::from_rgb(190, 210, 250))
                            } else {
                                egui::Stroke::NONE
                            })
                            .corner_radius(9.),
                    );
                    glyph::paint(
                        ui,
                        icon,
                        egui::Rect::from_center_size(
                            r.rect.center_top() + egui::vec2(0., 22.),
                            egui::vec2(24., 24.),
                        ),
                    );
                    ui.painter().text(
                        r.rect.center_bottom() - egui::vec2(0., 14.),
                        egui::Align2::CENTER_CENTER,
                        label,
                        egui::FontId::proportional(11.5),
                        if *kind == i { BLUE } else { INK },
                    );
                    glyph::focus(ui, &r);
                    r.widget_info(|| {
                        egui::WidgetInfo::labeled(egui::WidgetType::Button, true, label)
                    });
                    if r.clicked() {
                        *kind = i;
                    }
                }
            });
        });
    ui.add_space(8.);
    if *kind == 1 {
        input(ui, "Sous la racine", a);
    } else {
        ui.columns(2, |cols| {
            input(
                &mut cols[0],
                if *kind == 0 { "Numérateur" } else { "Base" },
                a,
            );
            input(
                &mut cols[1],
                if *kind == 0 {
                    "Dénominateur"
                } else {
                    "Exposant"
                },
                b,
            );
        });
    }
    ui.add_space(10.);
    ui.label(
        RichText::new("Dans votre cours")
            .size(11.5)
            .color(ribbon::MUTED),
    );
    egui::Frame::new()
        .fill(Color32::WHITE)
        .stroke(egui::Stroke::new(1., Color32::from_rgb(230, 235, 244)))
        .corner_radius(12.)
        .inner_margin(10.)
        .show(ui, |ui| {
            equation_preview(ui, &linear(*kind, a, b));
        });
}
fn equation_preview(ui: &mut egui::Ui, linear: &str) {
    let key = egui::Id::new("equation-preview-cache");
    let cached = ui
        .ctx()
        .data(|d| d.get_temp::<(String, egui::TextureHandle)>(key));
    let texture = cached
        .filter(|(s, _)| s == linear)
        .map(|(_, t)| t)
        .or_else(|| {
            let mut doc = wordcraft_doc::Document::new();
            doc.last_section.page_w = 420.;
            doc.last_section.page_h = 100.;
            doc.last_section.margin_left = 12.;
            doc.last_section.margin_right = 12.;
            doc.last_section.margin_top = 14.;
            doc.last_section.margin_bottom = 4.;
            doc.styles.default_chr.size = Some(26.);
            let mut session = Session::new(doc);
            session.run("para.alignCenter", &json!({})).ok()?;
            session
                .run("insert.equation", &json!({"linear":linear,"edit":false}))
                .ok()?;
            let layout = session.layout();
            let page = layout.pages.first()?;
            let rendered =
                wordcraft_engine::render::render_page(&session.doc, page, 2., &Default::default());
            let img = egui::ColorImage::from_rgba_premultiplied(
                [rendered.width as usize, rendered.height as usize],
                &rendered.pixels,
            );
            let tex =
                ui.ctx()
                    .load_texture("native-equation-preview", img, egui::TextureOptions::LINEAR);
            ui.ctx()
                .data_mut(|d| d.insert_temp(key, (linear.to_owned(), tex.clone())));
            Some(tex)
        });
    if let Some(tex) = texture {
        let width = ui.available_width();
        ui.add(egui::Image::new(&tex).fit_to_exact_size(egui::vec2(width, width * 100. / 420.)));
    } else {
        ui.label("Complétez la formule pour voir son aperçu.");
    }
}
fn number(ui: &mut egui::Ui, label: &str, value: &mut u32, max: u32) {
    ui.label(RichText::new(label).size(12.).strong().color(INK));
    ui.add(egui::DragValue::new(value).range(1..=max).speed(0.2));
}
pub(super) fn table(ui: &mut egui::Ui, rows: &mut u32, cols: &mut u32) {
    ui.spacing_mut().interact_size.y = 36.;
    ui.columns(2, |c| {
        number(&mut c[0], "Lignes", rows, 40);
        number(&mut c[1], "Colonnes", cols, 12);
    });
    ui.add_space(12.);
    let w = ui.available_width();
    let r = ui.allocate_space(egui::vec2(w, 130.)).1;
    let nr = (*rows).min(6);
    let nc = (*cols).min(8);
    for row in 0..nr {
        for col in 0..nc {
            let cell = egui::Rect::from_min_size(
                r.min + egui::vec2(col as f32 * w / nc as f32, row as f32 * 130. / nr as f32),
                egui::vec2(w / nc as f32, 130. / nr as f32),
            )
            .shrink(2.);
            ui.painter().rect_filled(
                cell,
                4.,
                if row == 0 {
                    Color32::from_rgb(223, 234, 255)
                } else {
                    Color32::from_rgb(243, 246, 251)
                },
            );
        }
    }
    ui.label(
        RichText::new(format!(
            "{rows} lignes × {cols} colonnes{}",
            if *rows > 6 || *cols > 8 {
                " · aperçu réduit"
            } else {
                ""
            }
        ))
        .size(11.)
        .color(ribbon::MUTED),
    );
}
pub(super) fn page(ui: &mut egui::Ui, margin: &mut f32, line: &mut f32, spacing: &mut f32) {
    for (label, value, range, step, suffix) in [
        ("Marges de la page", margin, 10. ..=35., 1., " mm"),
        ("Interligne", line, 1. ..=3., 0.1, ""),
        ("Espace entre les lettres", spacing, 0. ..=5., 0.25, " pt"),
    ] {
        egui::Frame::new()
            .fill(Color32::from_rgb(247, 249, 253))
            .corner_radius(10.)
            .inner_margin(12.)
            .show(ui, |ui| {
                ui.set_min_width(ui.available_width());
                ui.label(RichText::new(label).size(13.).strong().color(INK));
                ui.add(egui::Slider::new(value, range).step_by(step).suffix(suffix));
            });
    }
    ui.label(
        RichText::new("Interligne et espacement s’appliquent à votre sélection.")
            .size(11.)
            .color(ribbon::MUTED),
    );
}

pub(super) fn calculation(ui: &mut egui::Ui, c: &mut ecrinator::arithmetic::Calculation) {
    use ecrinator::arithmetic::Operation;
    ui.horizontal_wrapped(|ui| {
        for op in Operation::ALL {
            ui.selectable_value(
                &mut c.operation,
                op,
                format!("{}  {}", op.symbol(), op.label()),
            );
        }
    });
    ui.add_space(6.);
    ui.label("Les nombres sont facultatifs : tu peux tout remplir dans le cours.");
    ui.columns(2, |cols| {
        input(
            &mut cols[0],
            if c.operation == Operation::Divide {
                "Nombre à diviser"
            } else {
                "Premier nombre"
            },
            &mut c.a,
        );
        input(
            &mut cols[1],
            if c.operation == Operation::Divide {
                "Diviseur"
            } else {
                "Deuxième nombre"
            },
            &mut c.b,
        );
    });
    ui.label(
        RichText::new("Entiers ou décimaux · virgule française · aucun calcul automatique")
            .size(11.)
            .color(ribbon::MUTED),
    );
    ui.horizontal_wrapped(|ui| {
        ui.label("Cases par nombre");
        ui.add(egui::DragValue::new(&mut c.columns).range(3..=18));
        ui.label("Lignes à remplir");
        ui.add(egui::DragValue::new(&mut c.blank_rows).range(2..=12));
        ui.checkbox(&mut c.grid, "Quadrillage");
    });
    if let Err(error) = c.validate() {
        ui.colored_label(Color32::from_rgb(165, 55, 40), error);
        return;
    }
    // Preview the actual editable table through the document renderer.
    let key = egui::Id::new("operation-scaffold-preview");
    let signature = serde_json::to_string(c).unwrap_or_default();
    let cached = ui
        .ctx()
        .data(|d| d.get_temp::<(String, std::sync::Arc<[u8]>)>(key));
    let bytes = cached
        .filter(|(s, _)| s == &signature)
        .map(|(_, b)| b)
        .or_else(|| {
            let table = c.table().ok()?;
            let mut doc = wordcraft_doc::Document::new();
            doc.last_section.page_w = table.grid.iter().sum::<f32>() + 24.;
            doc.last_section.page_h = table.rows.len() as f32 * 42. + 60.;
            doc.last_section.margin_left = 12.;
            doc.last_section.margin_right = 12.;
            doc.last_section.margin_top = 12.;
            doc.last_section.margin_bottom = 12.;
            doc.body = vec![std::sync::Arc::new(wordcraft_doc::Block::Table(table))];
            let mut session = Session::new(doc);
            let layout = session.layout();
            let png = wordcraft_engine::render::render_page(
                &session.doc,
                layout.pages.first()?,
                1.5,
                &Default::default(),
            )
            .to_png();
            let data: std::sync::Arc<[u8]> = png.into();
            ui.ctx()
                .data_mut(|d| d.insert_temp(key, (signature.clone(), data.clone())));
            Some(data)
        });
    if let Some(bytes) = bytes {
        ui.add(
            egui::Image::from_bytes(format!("bytes://operation/{}", signature), bytes)
                .max_size(egui::vec2(ui.available_width(), 250.))
                .maintain_aspect_ratio(true),
        );
    }
    ui.label(RichText::new("Après insertion : clique dans les cases et écris tes chiffres, tes retenues et tes étapes. Tab passe à la case suivante. Le résultat reste à faire par toi.").size(12.).color(INK));
}
