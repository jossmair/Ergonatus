//! A visible action beside the selected pedagogical card, independent of the side pane.
use super::*;
pub(super) fn image_credit_menu(session: &Session, ui: &mut egui::Ui) {
    let Some(c) = ecrinator::image_credits::selected(session) else {
        return;
    };
    let response = ui.menu_button("Source et licence de l’image", |ui| {
        ui.set_width(330.);
        ui.label(RichText::new(&c.title).strong());
        ui.label(&c.author);
        ui.label(format!("Licence : {}", c.license));
        ui.label(RichText::new(&c.changes).size(11.).color(ribbon::MUTED));
        for (label, url) in [
            ("Ouvrir la source", &c.source_url),
            ("Lire la licence", &c.license_url),
            ("Licence de cette édition", &c.proof_url),
        ] {
            if url.starts_with("https://") {
                ui.hyperlink_to(label, url);
            }
        }
        ui.label(
            RichText::new(format!("Version : {}", c.version))
                .size(10.)
                .color(ribbon::MUTED),
        );
        if ui.button("Copier le crédit").clicked() {
            ui.ctx().copy_text(format!(
                "{} — {} · {} · {}",
                c.title, c.author, c.license, c.source_url
            ));
        }
    });
    ui.ctx().data_mut(|d| {
        d.insert_temp(
            egui::Id::new("image-credit-menu-rect"),
            response.response.rect,
        );
    });
    ui.separator();
}
impl App {
    pub(super) fn box_context(&mut self, ctx: &egui::Context) {
        if self.dialog.is_some()
            || self.pending.is_some()
            || !ecrinator::blocks::selected(&self.word.session)
        {
            return;
        }
        let Ok(path) = ecrinator::blocks::current_path(&self.word.session) else {
            return;
        };
        let layout = self.word.session.layout();
        let mut position = None;
        for (i, page) in layout.pages.iter().enumerate() {
            let Some(screen) = self.word.canvas.page_rects.get(i) else {
                continue;
            };
            for item in &page.items {
                if let wordcraft_engine::layout::Placed::Cell { table, rect, .. } = item {
                    if *table == path {
                        let scale = self.word.canvas.scale;
                        let point =
                            screen.min + egui::vec2((rect.x + rect.w) * scale, rect.y * scale);
                        if ctx
                            .content_rect()
                            .shrink2(egui::vec2(0., 150.))
                            .contains(point)
                        {
                            position = Some(point);
                            break;
                        }
                    }
                }
            }
            if position.is_some() {
                break;
            }
        }
        let Some(point) = position else {
            return;
        };
        let mut delete = false;
        let mut edit = false;
        egui::Area::new(egui::Id::new("box-context-actions"))
            .order(egui::Order::Foreground)
            .fixed_pos(point - egui::vec2(74., -4.))
            .show(ctx, |ui| {
                egui::Frame::new()
                    .fill(Color32::WHITE)
                    .stroke(egui::Stroke::new(1., Color32::from_rgb(214, 226, 244)))
                    .corner_radius(10.)
                    .inner_margin(3.)
                    .show(ui, |ui| {
                        ui.horizontal(|ui| {
                            ui.spacing_mut().item_spacing.x = 2.;
                            edit =
                                ribbon::control(ui, "edit", "", "Personnaliser cet encadré", false)
                                    .clicked();
                            let trash = ribbon::control(
                                ui,
                                "delete",
                                "",
                                "Supprimer cet encadré et son contenu · Ctrl+Z pour annuler",
                                false,
                            );
                            ctx.data_mut(|d| {
                                d.insert_temp(egui::Id::new("selected-box-trash-rect"), trash.rect)
                            });
                            delete = trash.clicked();
                        });
                    });
            });
        if delete {
            let r = ecrinator::blocks::delete(&mut self.word.session);
            self.message(r, "Encadré supprimé · Ctrl+Z pour annuler");
        }
        if edit {
            if let Ok(style) = ecrinator::blocks::appearance(&self.word.session) {
                self.dialog = Some(dialogs::Dialog::Box(style));
            }
        }
    }
}
