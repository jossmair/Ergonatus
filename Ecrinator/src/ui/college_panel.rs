use super::*;
use ecrinator::college_tools as college;
impl App {
    pub(super) fn worksheet_dialog(&mut self, ctx: &egui::Context, id: &str) -> bool {
        let Some(tool) = college::get(id) else {
            return true;
        };
        let mut close = false;
        let mut insert = false;
        let response = egui::Modal::new(egui::Id::new("college-sheet"))
            .backdrop_color(Color32::from_rgba_unmultiplied(30, 49, 73, 12))
            .frame(
                egui::Frame::new()
                    .fill(Color32::WHITE)
                    .corner_radius(16.)
                    .inner_margin(20.),
            )
            .show(ctx, |ui| {
                ui.set_width((ctx.content_rect().width() - 80.).clamp(280., 520.));
                ui.horizontal(|ui| {
                    ui.label(RichText::new(tool.title).size(21.).strong());
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        close = ribbon::control(ui, "close", "", "Fermer", false).clicked();
                    });
                });
                ui.label(tool.help);
                ui.add_space(8.);
                egui::ScrollArea::vertical()
                    .max_height((ctx.content_rect().height() - 245.).clamp(90., 390.))
                    .show(ui, |ui| {
                        for (label, hint) in tool.fields {
                            egui::Frame::new()
                                .fill(Color32::from_rgb(246, 248, 252))
                                .corner_radius(10.)
                                .inner_margin(10.)
                                .show(ui, |ui| {
                                    ui.set_width(ui.available_width());
                                    ui.label(RichText::new(*label).strong());
                                    if !hint.is_empty() {
                                        ui.label(
                                            RichText::new(*hint).size(11.).color(ribbon::MUTED),
                                        );
                                    }
                                });
                            ui.add_space(6.);
                        }
                        if !tool.columns.is_empty() {
                            ui.label(
                                RichText::new("Un tableau modifiable avec ces colonnes :").strong(),
                            );
                            for col in tool.columns {
                                ui.label(format!("• {col}"));
                            }
                        }
                    });
                ui.separator();
                ui.label(
                    RichText::new(
                        "Tout reste modifiable dans le cours. Ctrl+Z permet d’annuler l’insertion.",
                    )
                    .size(11.)
                    .color(ribbon::MUTED),
                );
                insert = ui
                    .add(
                        egui::Button::new(
                            RichText::new("Ajouter cette fiche à mon cours").color(Color32::WHITE),
                        )
                        .fill(BLUE)
                        .corner_radius(10.)
                        .min_size(egui::vec2(240., 38.)),
                    )
                    .clicked();
            });
        if insert {
            let result = college::insert(&mut self.word.session, id);
            close = result.is_ok();
            self.message(result, "Fiche ajoutée · complète-la dans ton cours");
        }
        close || response.should_close()
    }
    pub(super) fn units_dialog(&mut self, ctx: &egui::Context, value: &mut college::Units) -> bool {
        let mut close = false;
        let mut insert = false;
        let response = egui::Modal::new(egui::Id::new("college-units"))
            .backdrop_color(Color32::from_rgba_unmultiplied(30, 49, 73, 12))
            .frame(
                egui::Frame::new()
                    .fill(Color32::WHITE)
                    .corner_radius(16.)
                    .inner_margin(20.),
            )
            .show(ctx, |ui| {
                ui.set_width((ctx.content_rect().width() - 80.).clamp(280., 450.));
                ui.horizontal(|ui| {
                    ui.label(RichText::new("Convertir une mesure").size(21.).strong());
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        close = ribbon::control(ui, "close", "", "Fermer", false).clicked();
                    });
                });
                ui.label("Choisis la grandeur et les unités, puis vérifie le résultat.");
                egui::ComboBox::from_id_salt("unit-family")
                    .selected_text(
                        college::FAMILIES
                            .get(value.family)
                            .copied()
                            .unwrap_or("Longueur"),
                    )
                    .show_ui(ui, |ui| {
                        for (i, label) in college::FAMILIES.iter().enumerate() {
                            if ui.selectable_value(&mut value.family, i, *label).changed() {
                                value.from = 0;
                                value.to = 1;
                            }
                        }
                    });
                ui.label("Valeur de départ");
                ui.add(
                    egui::TextEdit::singleline(&mut value.value)
                        .char_limit(40)
                        .hint_text("Par exemple 2,5")
                        .desired_width(ui.available_width())
                        .margin(egui::vec2(10., 9.)),
                );
                let all = college::units(value.family);
                ui.horizontal(|ui| {
                    for (label, index, id) in [
                        ("De", &mut value.from, "unit-from"),
                        ("Vers", &mut value.to, "unit-to"),
                    ] {
                        ui.label(label);
                        egui::ComboBox::from_id_salt(id)
                            .width(100.)
                            .selected_text(all.get(*index).map(|u| u.0).unwrap_or("?"))
                            .show_ui(ui, |ui| {
                                for (i, (unit, _)) in all.iter().enumerate() {
                                    ui.selectable_value(index, i, *unit);
                                }
                            });
                    }
                });
                let result = value.result();
                ui.add_space(12.);
                egui::Frame::new()
                    .fill(Color32::from_rgb(239, 247, 255))
                    .corner_radius(12.)
                    .inner_margin(14.)
                    .show(ui, |ui| {
                        ui.label(
                            RichText::new(result.as_deref().unwrap_or_else(|e| e))
                                .size(19.)
                                .strong(),
                        );
                    });
                ui.add_space(10.);
                insert = ui
                    .add_enabled(
                        result.is_ok(),
                        egui::Button::new(
                            RichText::new("Insérer le résultat").color(Color32::WHITE),
                        )
                        .fill(BLUE)
                        .corner_radius(10.)
                        .min_size(egui::vec2(190., 38.)),
                    )
                    .clicked();
            });
        if insert {
            if let Ok(text) = value.result() {
                self.command("text.insert", json!({"text":text}));
                close = true;
            }
        }
        close || response.should_close()
    }
}
