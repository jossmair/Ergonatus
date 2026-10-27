use super::*;
impl App {
    pub(super) fn organizer_dialog(&mut self, ctx: &egui::Context, name: &mut String) -> bool {
        let mut close = false;
        let mut create = false;
        let desktop = ecrinator::organizer_space::desktop();
        let modal=egui::Modal::new(egui::Id::new("organizer-setup"))
            .backdrop_color(Color32::from_rgba_unmultiplied(30,49,73,12))
            .frame(egui::Frame::new().fill(Color32::WHITE).corner_radius(18.).inner_margin(20.)).show(ctx,|ui|{
                ui.set_width((ctx.content_rect().width()-80.).clamp(280.,540.));
                ui.horizontal(|ui|{ui.label(RichText::new("Mes cours, bien rangés").size(22.).strong());ui.with_layout(egui::Layout::right_to_left(egui::Align::Center),|ui|{close=ribbon::control(ui,"close","","Fermer",false).clicked();});});
                ui.label("Un dossier par matière, puis Leçons, Exercices ou Évaluations. Écrinator s’occupe du rangement.");
                egui::ScrollArea::vertical().max_height((ctx.content_rect().height()-220.).max(150.)).show(ui,|ui|{
                    if let Some(root)=&self.prefs.space{
                        egui::Frame::new().fill(Color32::from_rgb(237,248,244)).corner_radius(12.).inner_margin(12.).show(ui,|ui|{ui.label(RichText::new("Ton espace Organisator").strong());ui.label(root.display().to_string());if ecrinator::integrations::validate_space(root).is_err(){ui.label("Ce dossier n’est plus disponible. Choisis un autre espace, ou crée-le ci-dessous.");}});
                        if ui.checkbox(&mut self.prefs.organize,"Ranger automatiquement mes cours").changed(){self.remember();}
                        if ui.button("Classer ce document maintenant").clicked(){self.prefs.organize=true;self.remember();close=true;self.save(false,ctx);}
                        ui.separator();
                    }
                    egui::Frame::new().fill(Color32::from_rgb(242,247,255)).corner_radius(12.).inner_margin(14.).show(ui,|ui|{
                        ui.label(RichText::new("Créer mon dossier sur le Bureau").strong());
                        ui.label(RichText::new("Comme dans Organisator : matières, sous-dossiers et icônes de couleur.").size(11.).color(ribbon::MUTED));
                        ui.add(egui::TextEdit::singleline(name).hint_text("Nom de ton dossier").char_limit(80).desired_width(ui.available_width()).margin(egui::vec2(10.,9.)));
                        match &desktop{Ok(p)=>{ui.add(egui::Label::new(RichText::new(format!("{} › {}",p.display(),name.trim())).size(10.).color(ribbon::MUTED)).truncate()).on_hover_text(p.join(name.trim()).display().to_string());},Err(error)=>{ui.colored_label(Color32::from_rgb(160,45,35),error);}}
                        let valid=desktop.is_ok()&&ecrinator::organizer_space::valid_name(name)&&!self.busy;
                        let r=ui.add_enabled(valid,egui::Button::new(RichText::new("Créer et ranger mon cours").color(Color32::WHITE)).fill(BLUE).corner_radius(10.).min_size(egui::vec2(215.,38.)));
                        ctx.data_mut(|d|{d.insert_temp(egui::Id::new("create-school-space-rect"),r.rect);});create=r.clicked();
                    });
                    ui.add_space(10.);
                    if ui.button("Enregistrer ailleurs, sans classement…").clicked(){self.prefs.organize=false;self.remember();self.pick(Pick::Save,ctx);close=true;} 
                    if ui.button("J’ai déjà un dossier Organisator…").clicked(){self.pick(Pick::Space,ctx);close=true;}
                    ui.label(RichText::new("Aucun dossier existant n’est remplacé. Si tu changes Leçon / Exercices / Évaluation, le document suit ton choix.").size(11.).color(ribbon::MUTED));
                });
            });
        if create {
            self.create_school_space(name.clone(), ctx);
            close = true;
        }
        close || modal.should_close()
    }
}
