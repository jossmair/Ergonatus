//! Small editors for editable teaching tables, with a document-rendered preview.
use super::*;
use ecrinator::math_tables::{self, ColumnLink, Conversion, Model};

fn number(ui: &mut egui::Ui, label: &str, value: &mut usize, min: usize, max: usize) {
    ui.label(label);
    ui.add(egui::DragValue::new(value).range(min..=max));
}
fn dimensions(ui: &mut egui::Ui, width: &mut f32, height: &mut f32, font: &mut f32) {
    let mut cm = *width * 25.4 / 72.;
    ui.horizontal_wrapped(|ui| {
        ui.label("Largeur");
        if ui
            .add(
                egui::DragValue::new(&mut cm)
                    .range(4. ..=38.)
                    .speed(0.1)
                    .suffix(" cm"),
            )
            .changed()
        {
            *width = cm * 72. / 25.4;
        }
        ui.label("Hauteur des cases");
        ui.add(egui::DragValue::new(height).range(24. ..=90.).suffix(" pt"));
        ui.label("Texte");
        ui.add(egui::DragValue::new(font).range(10. ..=26.).suffix(" pt"));
    });
}
fn values(ui: &mut egui::Ui, values: &mut [Vec<String>], conversion: bool) {
    egui::ScrollArea::horizontal()
        .id_salt("math-values-scroll")
        .show(ui, |ui| {
            egui::Grid::new("math-values-grid")
                .spacing(egui::vec2(5., 5.))
                .show(ui, |ui| {
                    ui.label("");
                    for c in 0..values.first().map_or(0, Vec::len) {
                        ui.label(format!("C{}", c + 1));
                    }
                    ui.end_row();
                    for (r, row) in values.iter_mut().enumerate() {
                        ui.label(format!("L{}", r + 1));
                        for (c, value) in row.iter_mut().enumerate() {
                            let response = ui.add(
                                egui::TextEdit::singleline(value)
                                    .desired_width(if conversion { 30. } else { 80. })
                                    .char_limit(if conversion { 8 } else { 24 })
                                    .margin(egui::vec2(6., 7.)),
                            );
                            response.widget_info(|| {
                                egui::WidgetInfo::labeled(
                                    egui::WidgetType::TextEdit,
                                    true,
                                    format!("Ligne {}, colonne {}", r + 1, c + 1),
                                )
                            });
                        }
                        ui.end_row();
                    }
                });
        });
}
fn proportion(ui: &mut egui::Ui, p: &mut math_tables::Proportion) {
    ui.label("Écris les valeurs connues et laisse les cases à chercher vides.");
    let old = p.values[0].len();
    let mut cols = old;
    ui.horizontal_wrapped(|ui| {
        number(ui, "Colonnes", &mut cols, 2, 12);
    });
    if cols != old {
        if cols < old
            && p.values
                .iter()
                .any(|r| r[cols..].iter().any(|v| !v.is_empty()))
        {
            ui.colored_label(
                Color32::from_rgb(163, 56, 35),
                "Vide les colonnes concernées avant de les retirer.",
            );
        } else {
            for row in &mut p.values {
                row.resize(cols, String::new());
            }
        }
    }
    values(ui, &mut p.values, false);
    ui.add_space(8.);
    ui.label(RichText::new("Bulles de calcul").strong());
    ui.horizontal_wrapped(|ui| {
        if ui
            .add_enabled(
                p.links.len() < 6,
                egui::Button::new("+ Entre deux colonnes"),
            )
            .clicked()
        {
            p.links.push(ColumnLink::Operation {
                from: 0,
                to: 1,
                label: "× …".into(),
            });
        }
        if ui
            .add_enabled(
                p.links.len() < 6 && p.values[0].len() >= 3,
                egui::Button::new("+ Somme de deux colonnes"),
            )
            .clicked()
        {
            p.links.push(ColumnLink::Sum {
                first: 0,
                second: 1,
                to: 2,
            });
        }
    });
    let count = p.values[0].len();
    let mut remove = None;
    for (i, link) in p.links.iter_mut().enumerate() {
        ui.push_id(i, |ui| {
            ui.horizontal_wrapped(|ui| {
                match link {
                    ColumnLink::Operation { from, to, label } => {
                        let (mut a, mut b) = (*from + 1, *to + 1);
                        number(ui, "De C", &mut a, 1, count);
                        number(ui, "vers C", &mut b, 1, count);
                        *from = a - 1;
                        *to = b - 1;
                        ui.add(
                            egui::TextEdit::singleline(label)
                                .desired_width(72.)
                                .hint_text("× 3, ÷ 2…")
                                .char_limit(10),
                        );
                    }
                    ColumnLink::Sum { first, second, to } => {
                        let (mut a, mut b, mut c) = (*first + 1, *second + 1, *to + 1);
                        number(ui, "C", &mut a, 1, count);
                        number(ui, "+ C", &mut b, 1, count);
                        number(ui, "→ C", &mut c, 1, count);
                        *first = a - 1;
                        *second = b - 1;
                        *to = c - 1;
                    }
                }
                if ribbon::control(ui, "delete", "", "Supprimer cette bulle", false).clicked() {
                    remove = Some(i);
                }
            })
        });
    }
    if let Some(i) = remove {
        p.links.remove(i);
    }
    let mut right = !p.row_operation.is_empty();
    if ui
        .checkbox(&mut right, "Bulle entre les deux lignes, à droite")
        .changed()
    {
        p.row_operation = if right {
            "× …".into()
        } else {
            String::new()
        };
    }
    if right {
        ui.horizontal_wrapped(|ui| {
            ui.add(
                egui::TextEdit::singleline(&mut p.row_operation)
                    .desired_width(85.)
                    .char_limit(10),
            );
            ui.selectable_value(&mut p.row_reverse, false, "L1 → L2");
            ui.selectable_value(&mut p.row_reverse, true, "L2 → L1");
        });
    }
    ui.label(
        RichText::new("Les bulles indiquent la démarche. Aucune valeur n’est calculée.")
            .size(11.)
            .color(ribbon::MUTED),
    );
    dimensions(ui, &mut p.width, &mut p.row_height, &mut p.font_size);
}
fn conversion(ui: &mut egui::Ui, c: &mut Conversion) {
    let filled = c.values.iter().flatten().any(|s| !s.is_empty());
    let mut family = c.family.clone();
    ui.horizontal_wrapped(|ui| {
        ui.add_enabled_ui(!filled, |ui| {
            egui::ComboBox::from_id_salt("conversion-family")
                .selected_text(&family)
                .show_ui(ui, |ui| {
                    for name in math_tables::FAMILIES {
                        ui.selectable_value(&mut family, (*name).into(), *name);
                    }
                })
        });
        if ui.button("Vider les cases").clicked() {
            for value in c.values.iter_mut().flatten() {
                value.clear();
            }
        }
    });
    if family != c.family {
        let (width, height, font, rows) = (c.width, c.row_height, c.font_size, c.values.len());
        *c = Conversion::preset(&family);
        c.width = width;
        c.row_height = height;
        c.font_size = font;
        c.resize_rows(rows);
    }
    if filled {
        ui.label(
            RichText::new("Vide les cases pour changer de grandeur sans perdre de données.")
                .size(11.)
                .color(ribbon::MUTED),
        );
    }
    ui.label(c.hint());
    ui.collapsing("Unités et nombre de cases", |ui| {
        for unit in &mut c.units {
            ui.horizontal(|ui| {
                ui.add(
                    egui::TextEdit::singleline(&mut unit.label)
                        .desired_width(85.)
                        .char_limit(12),
                );
                ui.add_enabled_ui(!filled && !c.capacities, |ui| {
                    number(ui, "Cases", &mut unit.places, 1, 3);
                });
            });
        }
        if c.capacities {
            ui.label("Les litres restent alignés avec les volumes : 1 dm³ = 1 L et 1 cm³ = 1 mL.");
        }
        if c.family == "Personnalisé" && !filled {
            ui.horizontal_wrapped(|ui| {
                if ui
                    .add_enabled(c.units.len() < 16, egui::Button::new("+ Unité"))
                    .clicked()
                {
                    c.units.push(math_tables::UnitGroup {
                        label: "Unité".into(),
                        places: 1,
                    });
                }
                if ui
                    .add_enabled(
                        c.units.len() > 2,
                        egui::Button::new("Retirer la dernière unité"),
                    )
                    .clicked()
                {
                    c.units.pop();
                }
            });
        }
    });
    let mut rows = c.values.len();
    ui.horizontal_wrapped(|ui| {
        number(ui, "Lignes à remplir", &mut rows, 1, 64);
    });
    if rows < c.values.len() && c.values[rows..].iter().flatten().any(|v| !v.is_empty()) {
        ui.colored_label(
            Color32::from_rgb(163, 56, 35),
            "Vide les lignes concernées avant de les retirer.",
        );
    } else {
        c.resize_rows(rows);
    }
    if c.values.len() <= 8 {
        values(ui, &mut c.values, true);
    } else {
        ui.label("Les cases seront modifiables directement dans le document.");
    }
    dimensions(ui, &mut c.width, &mut c.row_height, &mut c.font_size);
    ui.label(RichText::new("c = centaines · d = dizaines · u = unités. Les durées ont leurs propres équivalences, pas une échelle décimale.").size(11.).color(ribbon::MUTED));
}
fn preview(ui: &mut egui::Ui, model: &Model) {
    let mut small = model.clone();
    if let Model::Conversion(c) = &mut small {
        c.values.truncate(3);
    }
    let signature = serde_json::to_string(&small).unwrap_or_default();
    let key = egui::Id::new("math-table-preview");
    let cached = ui
        .ctx()
        .data(|d| d.get_temp::<(String, std::sync::Arc<[u8]>)>(key));
    let bytes = cached
        .filter(|(s, _)| s == &signature)
        .map(|(_, b)| b)
        .or_else(|| {
            let table = small.table().ok()?;
            let mut doc = wordcraft_doc::Document::new();
            doc.last_section.page_w = small.width() + 24.;
            doc.last_section.page_h = match &small {
                Model::Proportion(p) => p.row_height * 2. + p.links.len() as f32 * 46. + 60.,
                Model::Conversion(c) => {
                    (c.values.len() + c.header_rows()) as f32 * c.row_height + 60.
                }
            };
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
                1.25,
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
            egui::Image::from_bytes(format!("bytes://math-table/{}", signature), bytes)
                .max_size(egui::vec2(ui.available_width(), 230.))
                .maintain_aspect_ratio(true),
        );
    }
}
impl App {
    pub(super) fn math_table_dialog(&mut self, ctx: &egui::Context, model: &mut Model) -> bool {
        let (mut close, mut apply) = (false, false);
        let title = match model {
            Model::Proportion(_) => "Tableau de proportionnalité",
            Model::Conversion(_) => "Tableau de conversion",
        };
        let response=egui::Modal::new(egui::Id::new("math-table-dialog")).backdrop_color(Color32::from_rgba_unmultiplied(30,49,73,12)).frame(egui::Frame::new().fill(Color32::WHITE).corner_radius(16.).inner_margin(20.)).show(ctx,|ui|{
            ui.set_width((ctx.content_rect().width()-80.).clamp(260.,760.));
            ui.horizontal(|ui|{ui.label(RichText::new(title).size(21.).strong());ui.with_layout(egui::Layout::right_to_left(egui::Align::Center),|ui|{close=ribbon::control(ui,"close","","Fermer",false).clicked();});});
            egui::ScrollArea::vertical().id_salt("math-table-fields").max_height((ctx.content_rect().height()-220.).max(90.)).show(ui,|ui|{
                match model{Model::Proportion(p)=>proportion(ui,p),Model::Conversion(c)=>conversion(ui,c)}
                if let Err(error)=model.validate(){ui.colored_label(Color32::from_rgb(163,56,35),error);}else{preview(ui,model);}
            });
            let sections=self.word.session.doc.sections();let available=sections.get(self.word.session.doc.section_index_of(self.word.session.sel.focus.path.0.first().copied().unwrap_or(0)as usize)).map(|(_,p)|p.text_width()).unwrap_or(468.);
            let fits=model.width()<=available+1.;
            if !fits{
                ui.label("Le tableau est trop large pour cette page ; sa police ne sera pas réduite.");
                if ui.button("Mettre la page en paysage").clicked(){let result=ecrinator::page_setup::set_orientation(&mut self.word.session,true);self.message(result,"Page en paysage · taille du texte conservée");}
            }
            ui.separator();ui.horizontal(|ui|{
                if ui.button("Annuler le tableau").clicked(){close=true;}
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center),|ui|{apply=ui.add_enabled(fits&&model.validate().is_ok(),egui::Button::new(RichText::new("Appliquer le tableau").color(Color32::WHITE)).fill(BLUE).min_size(egui::vec2(150.,38.))).clicked();});
            });
        });
        if apply {
            let result = math_tables::apply(&mut self.word.session, model);
            close = result.is_ok();
            self.message(
                result,
                "Tableau modifiable ajouté · clique dans les cases pour écrire",
            );
        }
        close || response.should_close()
    }
}
