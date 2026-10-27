//! Compact controls keep the writing surface in the foreground.
use super::*;
use ecrinator::blocks;
pub(super) const MUTED: Color32 = Color32::from_rgb(105, 119, 139);
const LINE: Color32 = Color32::from_rgb(223, 230, 239);
impl App {
    pub(super) fn header_bar(&mut self, root: &mut egui::Ui) {
        let ctx = root.ctx().clone();
        let compact = ctx.content_rect().width() < 1120.;
        let bg = if self.school.banner_visible() {
            self.school.banner_background()
        } else {
            wordcraft_doc::props::Rgb(248, 250, 254)
        };
        egui::Panel::top("identity")
            .exact_size(54.)
            .frame(
                egui::Frame::new()
                    .fill(Color32::from_rgb(bg.0, bg.1, bg.2))
                    .inner_margin(egui::Margin::symmetric(12, 6)),
            )
            .show(root, |ui| {
                egui::Image::from_bytes("bytes://workspace-banner", ecrinator::subjects::BANNER_BG)
                    .tint(Color32::from_white_alpha(140))
                    .paint_at(ui, ui.max_rect().expand2(egui::vec2(12., 6.)));
                ui.horizontal(|ui| {
                    ui.spacing_mut().item_spacing.x = 5.;
                    let brand = if compact { 150. } else { 184. };
                    let identity = ui.allocate_ui_with_layout(
                        egui::vec2(brand, 40.),
                        egui::Layout::left_to_right(egui::Align::Center),
                        |ui| {
                            ui.set_min_width(brand);
                            ui.add(
                                egui::Image::new(egui::include_image!(
                                    "../../assets/ecrinator.svg"
                                ))
                                .fit_to_exact_size(egui::vec2(34., 34.)),
                            );
                            ui.vertical(|ui| {
                                ui.spacing_mut().item_spacing.y = 0.;
                                ui.label(RichText::new("Écrinator").size(20.).strong().color(INK));
                                ui.label(RichText::new("ERGONATUS").size(9.).color(MUTED));
                            });
                        },
                    );
                    let drag = identity.response.interact(egui::Sense::click_and_drag());
                    if drag.drag_started_by(egui::PointerButton::Primary) {
                        ctx.send_viewport_cmd(egui::ViewportCommand::StartDrag);
                    }
                    if drag.double_clicked() {
                        let max = ctx.input(|i| i.viewport().maximized.unwrap_or(false));
                        ctx.send_viewport_cmd(egui::ViewportCommand::Maximized(!max));
                    }
                    let right = if compact { 272. } else { 312. };
                    let actions = (ui.available_width() - right - 8.).max(150.);
                    ui.allocate_ui_with_layout(
                        egui::vec2(actions, 36.),
                        egui::Layout::left_to_right(egui::Align::Center),
                        |ui| {
                            ui.set_min_width(actions);
                            egui::ScrollArea::horizontal()
                                .id_salt("main-actions-scroll")
                                .auto_shrink([false, true])
                                .show(ui, |ui| {
                                    ui.horizontal(|ui| {
                                        for (icon, label, action) in [
                                            ("new", "Nouveau", 0),
                                            ("open", "Ouvrir", 1),
                                            ("save", "Enregistrer", 2),
                                        ] {
                                            if control(
                                                ui,
                                                icon,
                                                if compact { "" } else { label },
                                                label,
                                                action == 2,
                                            )
                                            .clicked()
                                            {
                                                match action {
                                                    0 => self.request(Action::New, &ctx),
                                                    1 => self.pick(Pick::Open, &ctx),
                                                    _ => self.save(false, &ctx),
                                                }
                                            }
                                        }
                                        ui.separator();
                                        if control(ui, "undo", "", "Annuler · Ctrl+Z", false)
                                            .clicked()
                                        {
                                            self.command("edit.undo", json!({}));
                                        }
                                        if control(ui, "redo", "", "Rétablir · Ctrl+Y", false)
                                            .clicked()
                                        {
                                            self.command("edit.redo", json!({}));
                                        }
                                        ui.separator();
                                        if control(
                                            ui,
                                            "pdf",
                                            if compact { "" } else { "PDF" },
                                            "Exporter une copie PDF",
                                            false,
                                        )
                                        .clicked()
                                        {
                                            self.pick(Pick::Export("pdf".into()), &ctx);
                                        }
                                        if control(ui, "print", "", "Imprimer · Ctrl+P", false)
                                            .clicked()
                                        {
                                            self.print_dialog(&ctx);
                                        }
                                        if control(
                                            ui,
                                            "focus",
                                            "",
                                            "Concentration · F11",
                                            self.focus,
                                        )
                                        .clicked()
                                        {
                                            self.focus = !self.focus;
                                        }
                                        ui.menu_button(RichText::new("···").size(19.), |ui| {
                                            self.more_menu(ui, &ctx)
                                        });
                                    });
                                });
                        },
                    );
                    ui.allocate_ui_with_layout(
                        egui::vec2(right, 36.),
                        egui::Layout::left_to_right(egui::Align::Center),
                        |ui| {
                            let mut subject = self.school.subject.clone();
                            egui::ComboBox::from_id_salt("subject")
                                .width(right - 103.)
                                .height(420.)
                                .selected_text(RichText::new(&subject).size(13.))
                                .show_ui(ui, |ui| {
                                    for name in core::SUBJECTS {
                                        ui.selectable_value(&mut subject, (*name).into(), *name);
                                    }
                                });
                            if subject != self.school.subject {
                                let mut school = self.school.clone();
                                if subject == core::BLANK {
                                    school.show_banner = false;
                                } else if school.subject == core::BLANK {
                                    school.show_banner = true;
                                }
                                school.subject = subject;
                                let r = core::update_header(&mut self.word.session, &school);
                                self.message(r, "Matière actualisée");
                            }
                            if window_button(ui, "minimize", "Réduire").clicked() {
                                ctx.send_viewport_cmd(egui::ViewportCommand::Minimized(true));
                            }
                            if window_button(ui, "maximize", "Agrandir ou restaurer").clicked() {
                                let max = ctx.input(|i| i.viewport().maximized.unwrap_or(false));
                                ctx.send_viewport_cmd(egui::ViewportCommand::Maximized(!max));
                            }
                            if window_button(ui, "close", "Fermer").clicked() {
                                self.request(Action::Close, &ctx);
                            }
                        },
                    );
                });
            });
    }
    pub(super) fn editing_bar(&mut self, root: &mut egui::Ui) {
        let ctx = root.ctx().clone();
        egui::Panel::top("editing")
            .exact_size(44.)
            .frame(
                egui::Frame::new()
                    .fill(Color32::WHITE)
                    .inner_margin(egui::Margin::symmetric(12, 5)),
            )
            .show(root, |ui| {
                ui.horizontal(|ui| {
                    ui.spacing_mut().item_spacing.x = 4.;
                    for (i, label) in ["Écrire", "Insérer", "Page"].iter().enumerate() {
                        let selected = self.ribbon_tab == i;
                        let tab = ui.add_sized(
                            [if i == 1 { 61. } else { 55. }, 32.],
                            egui::Button::new(RichText::new(*label).size(12.).color(if selected {
                                BLUE
                            } else {
                                MUTED
                            }))
                            .fill(Color32::TRANSPARENT)
                            .stroke(egui::Stroke::NONE)
                            .corner_radius(6.),
                        );
                        if selected {
                            ui.painter().line_segment(
                                [
                                    tab.rect.left_bottom() + egui::vec2(10., -1.),
                                    tab.rect.right_bottom() + egui::vec2(-10., -1.),
                                ],
                                egui::Stroke::new(2., BLUE),
                            );
                        }
                        if tab.clicked() {
                            self.ribbon_tab = i;
                        }
                    }
                    ui.separator();
                    let selected_box = blocks::selected(&self.word.session);
                    let available =
                        (ui.available_width() - if selected_box { 225. } else { 185. }).max(100.);
                    ui.allocate_ui_with_layout(
                        egui::vec2(available, 32.),
                        egui::Layout::left_to_right(egui::Align::Center),
                        |ui| {
                            ui.set_min_width(available);
                            egui::ScrollArea::horizontal()
                                .id_salt("format-scroll")
                                .auto_shrink([false, true])
                                .show(ui, |ui| {
                                    ui.horizontal(|ui| {
                                        ui.spacing_mut().item_spacing.x = 3.;
                                        match self.ribbon_tab {
                                            0 => self.writing_tools(ui),
                                            1 => self.insertion_tools(ui, &ctx),
                                            _ => self.page_tools(ui, &ctx),
                                        }
                                    });
                                });
                        },
                    );
                    if selected_box
                        && control(
                            ui,
                            "delete",
                            "",
                            "Supprimer l’encadré et son contenu · Annuler avec Ctrl+Z",
                            false,
                        )
                        .clicked()
                    {
                        let r = blocks::delete(&mut self.word.session);
                        self.message(r, "Encadré supprimé · Ctrl+Z pour annuler");
                    }
                    if control(
                        ui,
                        "header",
                        "Bandeau",
                        "Matière, chapitre, date et cases du bandeau",
                        false,
                    )
                    .clicked()
                    {
                        self.dialog = Some(dialogs::Dialog::Header(self.school.clone()));
                    }
                    if control(
                        ui,
                        "panel",
                        "Outils",
                        "Afficher ou masquer les outils de matière",
                        self.tools,
                    )
                    .clicked()
                    {
                        self.tools = !self.tools;
                        self.prefs.tools = self.tools;
                        self.remember();
                    }
                });
            });
    }
    fn writing_tools(&mut self, ui: &mut egui::Ui) {
        let state = self
            .word
            .session
            .run("format.state", &json!({}))
            .unwrap_or_default();
        if let Some(name) = state.get("font").and_then(|v| v.as_str()) {
            if ["Arial", "Borel", "OpenDyslexic"].contains(&name) {
                self.font = name.into();
            }
        }
        if let Some(size) = state.get("size").and_then(|v| v.as_f64()) {
            self.size = size as f32;
        }
        let mut font = self.font.clone();
        egui::ComboBox::from_id_salt("font")
            .width(116.)
            .selected_text(if font == "Borel" { "Cursive" } else { &font })
            .show_ui(ui, |ui| {
                for name in ["Arial", "OpenDyslexic", "Borel"] {
                    ui.selectable_value(
                        &mut font,
                        name.into(),
                        if name == "Borel" { "Cursive" } else { name },
                    );
                }
            });
        if font != self.font {
            self.font = font.clone();
            self.command("format.font", json!({"name":font}));
        }
        let old = self.size;
        ui.add(
            egui::DragValue::new(&mut self.size)
                .range(8. ..=72.)
                .speed(1.)
                .suffix(" pt"),
        );
        if self.size != old {
            self.command("format.size", json!({"size":self.size}));
        }
        ui.separator();
        for (icon, id, label, key) in [
            ("bold", "format.bold", "Gras", "bold"),
            ("italic", "format.italic", "Italique", "italic"),
            ("underline", "format.underline", "Souligné", "underline"),
        ] {
            let active = state.get(key).is_some_and(|v| {
                v.as_bool() == Some(true) || v.as_str().is_some_and(|s| s != "none")
            });
            if control(ui, icon, "", label, active).clicked() {
                self.command(id, json!({}));
            }
        }
        if control(ui, "textcolor", "", "Couleur du texte", false).clicked() {
            self.dialog = Some(dialogs::Dialog::Colors);
        }
        ui.separator();
        let current = self
            .word
            .session
            .doc
            .para_at(&self.word.session.sel.focus)
            .and_then(|p| p.props.style.as_deref())
            .unwrap_or("Normal")
            .to_string();
        let label = match current.as_str() {
            "Heading1" => "Titre 1",
            "Heading2" => "Titre 2",
            "Quote" => "Citation",
            core::CHAPTER => "Titre",
            _ => "Normal",
        };
        egui::ComboBox::from_id_salt("paragraph-style")
            .width(94.)
            .selected_text(label)
            .show_ui(ui, |ui| {
                for (name, style) in [
                    ("Normal", "Normal"),
                    ("Titre 1", "Heading1"),
                    ("Titre 2", "Heading2"),
                    ("Citation", "Quote"),
                ] {
                    if ui.selectable_label(current == style, name).clicked() {
                        if style == "Normal" {
                            self.normal_text();
                        } else {
                            self.command("para.style", json!({"style":style}));
                        }
                        ui.close();
                    }
                }
            });
        if control(
            ui,
            "clear-format",
            "",
            "Effacer la mise en forme du texte ou du titre",
            false,
        )
        .clicked()
        {
            self.normal_text();
        }
        ui.separator();
        for (icon, id, label) in [
            ("alignleft", "para.alignLeft", "Aligner à gauche"),
            ("aligncenter", "para.alignCenter", "Centrer"),
            ("alignright", "para.alignRight", "Aligner à droite"),
            ("alignjustify", "para.justify", "Justifier"),
            ("list", "para.bullets", "Liste à puces"),
            ("numbered", "para.numbering", "Liste numérotée"),
        ] {
            if control(ui, icon, "", label, false).clicked() {
                self.command(id, json!({}));
            }
        }
    }
    fn normal_text(&mut self) {
        let r = core::clear_formatting(&mut self.word.session);
        self.message(r, "Texte normal · mise en forme retirée");
    }
    fn insertion_tools(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.menu_button("Encadré ▾", |ui| self.box_menu(ui));
        for (icon, label, action) in [
            ("image", "Images", 29),
            ("table", "Tableau", 6),
            ("formula", "Formule", 8),
            ("symbol", "Symbole", 3),
            ("figure", "Figure", 5),
            ("graph", "Graphique", 7),
            ("timeline", "Frise", 9),
        ] {
            if control(ui, icon, label, label, false).clicked() {
                self.subject_action(action, ctx);
            }
        }
        if control(ui, "ocr", "OCR", "Reconnaître le texte d’une image", false).clicked() {
            self.recognize(ctx);
        }
        if control(ui, "page", "Saut", "Insérer un saut de page", false).clicked() {
            self.command("insert.pageBreak", json!({}));
        }
    }
    fn page_tools(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        let wide = ecrinator::page_setup::landscape(&self.word.session);
        for (value, label) in [(false, "Portrait"), (true, "Paysage")] {
            if control(
                ui,
                "layout",
                label,
                "Changer l’orientation sans réduire le texte",
                wide == value,
            )
            .clicked()
            {
                let result = ecrinator::page_setup::set_orientation(&mut self.word.session, value);
                self.message(result, "Orientation modifiée · taille du texte conservée");
            }
        }
        if control(
            ui,
            "layout",
            "Marges et espacement",
            "Marges, interligne et caractères",
            false,
        )
        .clicked()
        {
            self.subject_action(20, ctx);
        }
        if control(
            ui,
            "pages",
            "Pages",
            "Vignettes des pages",
            self.pages.visible,
        )
        .clicked()
        {
            self.pages.visible = !self.pages.visible;
            self.prefs.pages = self.pages.visible;
            self.remember();
        }
        if control(ui, "zoom", "Largeur", "Ajuster la page à la largeur", false).clicked() {
            self.command("view.pageWidth", json!({}));
        }
        if control(
            ui,
            "settings",
            "Confort",
            "Profils et préférences de lecture",
            false,
        )
        .clicked()
        {
            self.dialog = Some(dialogs::Dialog::Accessibility);
        }
        if control(
            ui,
            "focus",
            "Concentration",
            "Mode concentration · F11",
            false,
        )
        .clicked()
        {
            self.focus = true;
        }
    }
    fn more_menu(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.label(RichText::new("DOCUMENT").size(10.).color(MUTED));
        if ui.button("Enregistrer sous…   Ctrl+Maj+S").clicked() {
            self.save(true, ctx);
            ui.close();
        }
        for ext in ["odt", "docx"] {
            if ui
                .button(format!("Exporter une copie {}…", ext.to_uppercase()))
                .clicked()
            {
                self.pick(Pick::Export(ext.into()), ctx);
                ui.close();
            }
        }
        ui.separator();
        if ui.button("Rechercher et remplacer…   Ctrl+F").clicked() {
            self.dialog = Some(dialogs::Dialog::Search);
            ui.close();
        }
        if ui.button("Mon confort d’écriture…").clicked() {
            self.dialog = Some(dialogs::Dialog::Accessibility);
            ui.close();
        }
        if ui.button("Ranger avec Organisator…").clicked() {
            self.dialog = Some(dialogs::Dialog::organizer());
            ui.close();
        }
        if ui.button("Mode d’emploi…").clicked() {
            self.dialog = Some(dialogs::Dialog::Help);
            ui.close();
        }
    }
    fn box_menu(&mut self, ui: &mut egui::Ui) {
        if blocks::selected(&self.word.session)
            && quick(ui, "delete", "Supprimer cet encadré").clicked()
        {
            let r = blocks::delete(&mut self.word.session);
            self.message(r, "Encadré supprimé · Ctrl+Z pour annuler");
            ui.close();
        }
        for title in blocks::TEMPLATES {
            if box_card(ui, title).clicked() {
                let r = blocks::insert(&mut self.word.session, title);
                self.message(r, "Encadré ajouté");
                ui.close();
            }
        }
        ui.separator();
        if ui.button("Personnaliser l’encadré…").clicked() {
            match blocks::appearance(&self.word.session) {
                Ok(s) => self.dialog = Some(dialogs::Dialog::Box(s)),
                Err(e) => self.status = format!("Action impossible : {e}"),
            };
            ui.close();
        }
        for (down, label) in [(false, "Monter l’encadré"), (true, "Descendre l’encadré")] {
            if ui.button(label).clicked() {
                let r = blocks::move_box(&mut self.word.session, down);
                self.message(r, "Encadré déplacé");
                ui.close();
            }
        }
        if ui.button("Retirer le cadre, garder le texte").clicked() {
            let r = blocks::remove_frame(&mut self.word.session);
            self.message(r, "Cadre retiré");
            ui.close();
        }
    }
    pub(super) fn subject_tools(&mut self, root: &mut egui::Ui) {
        let ctx = root.ctx().clone();
        egui::Panel::right("subject-tools")
            .exact_size(248.)
            .resizable(false)
            .frame(
                egui::Frame::new()
                    .fill(Color32::from_rgb(248, 250, 253))
                    .inner_margin(12.),
            )
            .show(root, |ui| {
                ui.horizontal(|ui| {
                    ui.vertical(|ui| {
                        ui.label(RichText::new("Outils du cours").size(16.).strong());
                        let c = self.school.color();
                        ui.label(
                            RichText::new(&self.school.subject)
                                .size(11.)
                                .color(Color32::from_rgb(c.0, c.1, c.2)),
                        );
                    });
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if control(ui, "close", "", "Fermer les outils", false).clicked() {
                            self.tools = false;
                            self.prefs.tools = false;
                            self.remember();
                        }
                    });
                });
                ui.add_space(10.);
                egui::ScrollArea::vertical().show(ui, |ui| {
                    let tools: Vec<(&str, &str, u8)> = match self.school.subject.as_str() {
                        "Mathématiques" => vec![
                            ("calculation", "Opération posée", 30),
                            ("table", "Proportionnalité", 31),
                            ("units", "Conversions", 32),
                            ("fraction", "Fraction", 0),
                            ("root", "Racine carrée", 1),
                            ("power", "Puissance", 2),
                            ("symbol", "Symboles", 3),
                            ("angle", "Angle", 4),
                            ("figure", "Figure", 5),
                            ("table", "Tableau", 6),
                            ("graph", "Graphique", 7),
                        ],
                        "Histoire-géographie" | "EMC" => vec![
                            ("timeline", "Frise", 9),
                            ("map", "Carte", 29),
                            ("legend", "Légende", 11),
                            ("source", "Source", 12),
                            ("image", "Image", 10),
                            ("definition", "Notion", 13),
                        ],
                        "SVT" => vec![
                            ("diagram", "Schéma", 29),
                            ("legend", "Légende", 11),
                            ("image", "Image", 10),
                            ("observation", "Observer", 14),
                            ("hypothesis", "Hypothèse", 15),
                            ("results", "Résultats", 16),
                            ("conclusion", "Conclusion", 17),
                            ("table", "Tableau", 6),
                        ],
                        "Physique-chimie" | "Technologie" => vec![
                            ("units", "Convertir", 19),
                            ("table", "Tableau d’unités", 32),
                            ("formula", "Formule", 8),
                            ("diagram", "Schéma", 29),
                            ("table", "Tableau", 6),
                            ("hypothesis", "Hypothèse", 15),
                            ("results", "Résultats", 16),
                            ("conclusion", "Conclusion", 17),
                            ("graph", "Graphique", 7),
                        ],
                        "Arts plastiques" => vec![
                            ("image", "Image", 10),
                            ("legend", "Légende", 11),
                            ("layout", "Mise en page", 20),
                            ("frame", "Encadré", 13),
                            ("palette", "Couleur", 21),
                            ("search", "Observer", 14),
                        ],
                        "Éducation musicale" => vec![
                            ("headphones", "Écoute", 22),
                            ("music", "Partition", 10),
                            ("vocabulary", "Vocabulaire", 23),
                            ("frame", "Encadré", 13),
                            ("list", "Liste", 24),
                            ("note", "Note", 25),
                        ],
                        _ => vec![
                            ("chapter", "Titre", 26),
                            ("source", "Paragraphe", 27),
                            ("quote", "Citation", 28),
                            ("vocabulary", "Vocabulaire", 23),
                            ("image", "Image", 10),
                            ("list", "Liste", 24),
                        ],
                    };
                    egui::Grid::new("subject-grid")
                        .spacing([6., 6.])
                        .show(ui, |ui| {
                            for (i, (icon, label, action)) in tools.iter().enumerate() {
                                if tool_tile(ui, icon, label).clicked() {
                                    self.subject_action(*action, &ctx);
                                }
                                if i % 3 == 2 {
                                    ui.end_row();
                                }
                            }
                        });
                    ui.add_space(12.);
                    if ui
                        .add_sized(
                            [ui.available_width(), 34.],
                            egui::Button::new("Bibliothèque : cartes et schémas"),
                        )
                        .clicked()
                    {
                        self.subject_action(29, &ctx);
                    }
                    egui::CollapsingHeader::new("Fiches pour m’aider")
                        .default_open(true)
                        .show(ui, |ui| {
                            for tool in ecrinator::college_tools::for_subject(&self.school.subject)
                            {
                                let r = ui.add_sized(
                                    [ui.available_width(), 32.],
                                    egui::Button::new(tool.title),
                                );
                                if r.clicked() {
                                    if tool.id == "proportion" {
                                        self.subject_action(31, &ctx);
                                    } else {
                                        self.dialog =
                                            Some(dialogs::Dialog::Worksheet(tool.id.into()));
                                    }
                                }
                                r.on_hover_text(tool.help);
                            }
                        });
                    if self.word.session.sel.focus.path.cell().is_some()
                        && !ecrinator::blocks::selected(&self.word.session)
                    {
                        ui.horizontal_wrapped(|ui| {
                            if ui.button("+ Ligne").clicked() {
                                self.command("table.insertRowBelow", json!({}));
                            }
                            if ui.button("+ Colonne").clicked() {
                                self.command("table.insertColumnRight", json!({}));
                            }
                        });
                    }
                    ui.add_space(18.);
                    ui.label(
                        RichText::new("Encadrés du cours")
                            .size(13.)
                            .strong()
                            .color(INK),
                    );
                    ui.add_space(6.);
                    let titles: &[&str] = match self.school.subject.as_str() {
                        "Mathématiques" => &[
                            "Définition",
                            "Propriété",
                            "Théorème",
                            "Méthode",
                            "Remarque",
                            "Exercice",
                        ],
                        "SVT" => &[
                            "Observation",
                            "Hypothèse",
                            "Résultat",
                            "Conclusion",
                            "À retenir",
                            "Exercice",
                        ],
                        "Physique-chimie" | "Technologie" => &[
                            "Observation",
                            "Méthode",
                            "À retenir",
                            "Attention",
                            "Exemple",
                            "Exercice",
                        ],
                        _ => &[
                            "À retenir",
                            "Définition",
                            "Vocabulaire",
                            "Méthode",
                            "Exemple",
                            "Exercice",
                        ],
                    };
                    for title in titles {
                        if box_card(ui, title).clicked() {
                            let r = blocks::insert(&mut self.word.session, title);
                            self.message(r, "Encadré ajouté");
                        }
                    }
                    let fixed_banner = self
                        .word
                        .session
                        .sel
                        .focus
                        .path
                        .0
                        .first()
                        .and_then(|n| self.word.session.doc.body.get(*n as usize))
                        .and_then(|b| b.as_table())
                        .is_some_and(|t| t.props.geometry_locked);
                    if self.word.session.sel.focus.path.0.len() >= 4 && !fixed_banner {
                        if blocks::selected(&self.word.session) {
                            ui.add_space(10.);
                            if quick(ui, "delete", "Supprimer cet encadré").clicked() {
                                let r = blocks::delete(&mut self.word.session);
                                self.message(r, "Encadré supprimé · Ctrl+Z pour annuler");
                            }
                        }
                        ui.add_space(12.);
                        ui.separator();
                        ui.label(RichText::new("TABLEAU SÉLECTIONNÉ").size(10.).color(MUTED));
                        for (icon, label, id) in [
                            ("row", "Ajouter une ligne", "table.insertRowBelow"),
                            ("column", "Ajouter une colonne", "table.insertColumnRight"),
                            ("delete", "Supprimer la ligne", "table.deleteRow"),
                            ("delete", "Supprimer la colonne", "table.deleteColumn"),
                        ] {
                            if quick(ui, icon, label).clicked() {
                                self.command(id, json!({}));
                            }
                        }
                    }
                });
            });
    }
}
pub(super) fn control(
    ui: &mut egui::Ui,
    icon: &str,
    label: &str,
    help: &str,
    selected: bool,
) -> egui::Response {
    let text = ui
        .painter()
        .layout_no_wrap(label.into(), egui::FontId::proportional(12.), INK);
    let width = if label.is_empty() {
        32.
    } else {
        text.size().x + 38.
    };
    let r = ui.add_sized(
        [width, 32.],
        egui::Button::new("")
            .fill(if selected {
                Color32::from_rgb(232, 240, 255)
            } else {
                Color32::TRANSPARENT
            })
            .stroke(egui::Stroke::NONE)
            .corner_radius(6.),
    );
    if r.hovered() {
        ui.painter()
            .rect_filled(r.rect, 6., Color32::from_rgb(232, 240, 250));
    }
    glyph::paint(
        ui,
        icon,
        egui::Rect::from_center_size(
            egui::pos2(r.rect.left() + 16., r.rect.center().y),
            egui::vec2(19., 19.),
        ),
    );
    if !label.is_empty() {
        ui.painter().galley(
            egui::pos2(r.rect.left() + 32., r.rect.center().y - text.size().y / 2.),
            text,
            INK,
        );
    }
    glyph::focus(ui, &r);
    r.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, ui.is_enabled(), help));
    r.on_hover_text(help)
}
fn window_button(ui: &mut egui::Ui, icon: &str, label: &str) -> egui::Response {
    let r = ui.add_sized(
        [28., 32.],
        egui::Button::new("")
            .fill(Color32::TRANSPARENT)
            .stroke(egui::Stroke::NONE),
    );
    let down = r.is_pointer_button_down_on();
    let over = r.hovered() || r.has_focus();
    let bg = if icon == "close" {
        if down {
            Color32::from_rgb(184, 35, 45)
        } else {
            Color32::from_rgb(222, 51, 64)
        }
    } else if down {
        Color32::from_rgb(174, 202, 241)
    } else {
        Color32::from_rgb(213, 229, 251)
    };
    if over || down {
        ui.painter().rect_filled(r.rect, 5., bg);
    }
    let ink = if icon == "close" && (over || down) {
        Color32::WHITE
    } else {
        INK
    };
    let p = ui.painter();
    let c = r.rect.center();
    let stroke = egui::Stroke::new(1.2, ink);
    match icon {
        "close" => {
            p.line_segment([c + egui::vec2(-4., -4.), c + egui::vec2(4., 4.)], stroke);
            p.line_segment([c + egui::vec2(-4., 4.), c + egui::vec2(4., -4.)], stroke);
        }
        "minimize" => {
            p.line_segment([c + egui::vec2(-4.5, 3.), c + egui::vec2(4.5, 3.)], stroke);
        }
        _ => {
            if ui.ctx().input(|i| i.viewport().maximized.unwrap_or(false)) {
                p.rect_stroke(
                    egui::Rect::from_center_size(c + egui::vec2(1.5, -1.5), egui::vec2(7., 7.)),
                    1.,
                    stroke,
                    egui::StrokeKind::Inside,
                );
                p.rect_filled(
                    egui::Rect::from_center_size(c + egui::vec2(-1., 1.), egui::vec2(7., 7.)),
                    1.,
                    if over || down {
                        bg
                    } else {
                        Color32::from_rgb(245, 248, 252)
                    },
                );
                p.rect_stroke(
                    egui::Rect::from_center_size(c + egui::vec2(-1., 1.), egui::vec2(7., 7.)),
                    1.,
                    stroke,
                    egui::StrokeKind::Inside,
                );
            } else {
                p.rect_stroke(
                    egui::Rect::from_center_size(c, egui::vec2(9., 9.)),
                    1.,
                    stroke,
                    egui::StrokeKind::Inside,
                );
            }
        }
    }
    ui.ctx().data_mut(|d| {
        d.insert_temp(
            egui::Id::new(("window-button-state", icon)),
            (over, down, r.rect),
        );
    });
    glyph::focus(ui, &r);
    if icon == "close" {
        ui.ctx()
            .data_mut(|d| d.insert_temp(egui::Id::new("ecr-close-rect"), r.rect));
    }
    r.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, ui.is_enabled(), label));
    r.on_hover_cursor(egui::CursorIcon::PointingHand)
        .on_hover_text(label)
}
fn tool_tile(ui: &mut egui::Ui, icon: &str, label: &str) -> egui::Response {
    let r = ui.add_sized(
        [68., 68.],
        egui::Button::new("")
            .fill(Color32::WHITE)
            .stroke(egui::Stroke::new(0.6, Color32::from_rgb(231, 235, 242)))
            .corner_radius(10.),
    );
    if r.hovered() {
        ui.painter()
            .rect_filled(r.rect, 10., Color32::from_rgb(236, 242, 253));
    }
    let badge = egui::Rect::from_center_size(
        egui::pos2(r.rect.center().x, r.rect.top() + 23.),
        egui::vec2(28., 28.),
    );
    glyph::paint(ui, icon, badge.shrink(3.));
    let text = ui
        .painter()
        .layout(label.into(), egui::FontId::proportional(10.5), INK, 60.);
    ui.painter().galley(
        egui::pos2(r.rect.center().x - text.size().x / 2., r.rect.top() + 43.),
        text,
        INK,
    );
    glyph::focus(ui, &r);
    r.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, ui.is_enabled(), label));
    r
}
fn quick(ui: &mut egui::Ui, icon: &str, label: &str) -> egui::Response {
    let r = ui.add_sized(
        [ui.available_width().min(224.), 31.],
        egui::Button::new("")
            .fill(Color32::WHITE)
            .stroke(egui::Stroke::new(0.7, LINE))
            .corner_radius(6.),
    );
    if r.hovered() {
        ui.painter()
            .rect_filled(r.rect, 6., Color32::from_rgb(233, 241, 255));
    }
    glyph::paint(
        ui,
        icon,
        egui::Rect::from_center_size(
            egui::pos2(r.rect.left() + 17., r.rect.center().y),
            egui::vec2(18., 18.),
        ),
    );
    ui.painter().text(
        egui::pos2(r.rect.left() + 34., r.rect.center().y),
        egui::Align2::LEFT_CENTER,
        label,
        egui::FontId::proportional(12.),
        INK,
    );
    glyph::focus(ui, &r);
    r.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, ui.is_enabled(), label));
    r
}
pub(super) fn box_card(ui: &mut egui::Ui, title: &str) -> egui::Response {
    let theme = ecrinator::pedagogy::theme(title);
    let rgb = |c: wordcraft_doc::props::Rgb| Color32::from_rgb(c.0, c.1, c.2);
    let r = ui.add_sized(
        [ui.available_width().min(224.), 36.],
        egui::Button::new("")
            .fill(rgb(theme.background))
            .stroke(egui::Stroke::NONE)
            .corner_radius(9.),
    );
    if r.hovered() {
        ui.painter().rect_stroke(
            r.rect.shrink(0.5),
            9.,
            egui::Stroke::new(1., rgb(ecrinator::pedagogy::outline(theme.ink))),
            egui::StrokeKind::Inside,
        );
    }
    let accent =
        egui::Rect::from_min_size(r.rect.left_top() + egui::vec2(0., 9.), egui::vec2(2.5, 18.));
    ui.painter().rect_filled(accent, 2., rgb(theme.ink));
    glyph::paint(
        ui,
        theme.icon,
        egui::Rect::from_center_size(
            egui::pos2(r.rect.left() + 21., r.rect.center().y),
            egui::vec2(23., 23.),
        ),
    );
    ui.painter().text(
        egui::pos2(r.rect.left() + 42., r.rect.center().y),
        egui::Align2::LEFT_CENTER,
        title,
        egui::FontId::proportional(12.),
        rgb(theme.ink),
    );
    glyph::focus(ui, &r);
    r.widget_info(|| {
        egui::WidgetInfo::labeled(
            egui::WidgetType::Button,
            ui.is_enabled(),
            format!("Insérer un encadré {title}"),
        )
    });
    r.on_hover_text(format!("Encadrer la sélection ou créer un bloc {title}"))
}
