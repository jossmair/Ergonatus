use super::*;
pub(super) enum Dialog {
    Box(ecrinator::blocks::Appearance),
    Overwrite {
        path: PathBuf,
        export: bool,
        stamp: Option<storage::Stamp>,
    },
    Calculation(ecrinator::arithmetic::Calculation),
    MathTable(ecrinator::math_tables::Model),
    Symbols,
    Shapes,
    Colors,
    Chart {
        labels: String,
        values: String,
    },
    Header(School),
    Organizer {
        name: String,
    },
    Worksheet(String),
    Units(ecrinator::college_tools::Units),
    Accessibility,
    Search,
    Help,
    Recovery,
    Table {
        rows: u32,
        cols: u32,
    },
    Formula {
        kind: usize,
        a: String,
        b: String,
    },
    Timeline(ecrinator::timeline::Timeline),
    Library {
        category: String,
        query: String,
        selected: Option<String>,
        topic: String,
        page: usize,
    },
    Page {
        margin: f32,
        line: f32,
        spacing: f32,
    },
    Ocr(String),
    Print {
        printers: Vec<craft_print::Printer>,
        index: usize,
        copies: u32,
        duplex: bool,
        gray: bool,
    },
}
impl Dialog {
    pub(super) fn organizer() -> Self {
        Self::Organizer {
            name: "Mes cours - Collège".into(),
        }
    }
}
impl App {
    pub(super) fn show_dialog(&mut self, ctx: &egui::Context) {
        let Some(mut dialog) = self.dialog.take() else {
            return;
        };
        if let Dialog::MathTable(model) = &mut dialog {
            if !self.math_table_dialog(ctx, model) {
                self.dialog = Some(dialog);
            }
            return;
        }
        if let Dialog::Organizer { name } = &mut dialog {
            if !self.organizer_dialog(ctx, name) {
                self.dialog = Some(dialog);
            }
            return;
        }
        if let Dialog::Worksheet(id) = &dialog {
            if !self.worksheet_dialog(ctx, id) {
                self.dialog = Some(dialog);
            }
            return;
        }
        if let Dialog::Units(value) = &mut dialog {
            if !self.units_dialog(ctx, value) {
                self.dialog = Some(dialog);
            }
            return;
        }
        if let Dialog::Library {
            category,
            query,
            selected,
            topic,
            page,
        } = &mut dialog
        {
            if !self.library_dialog(ctx, category, query, selected, topic, page) {
                self.dialog = Some(dialog);
            }
            return;
        }
        if matches!(
            &dialog,
            Dialog::Header(_)
                | Dialog::Box(_)
                | Dialog::Formula { .. }
                | Dialog::Table { .. }
                | Dialog::Page { .. }
                | Dialog::Calculation(_)
                | Dialog::Timeline(_)
                | Dialog::Chart { .. }
        ) {
            if !self.design_dialog(ctx, &mut dialog) {
                self.dialog = Some(dialog);
            } else {
                self.word.canvas.want_focus = true;
            }
            return;
        }
        let mut open = true;
        let mut done = false;
        let title = match &dialog {
            Dialog::Box(_) => "Personnaliser l’encadré",
            Dialog::Overwrite { .. } => "Remplacer ce fichier ?",
            Dialog::Calculation(_) => "Calcul posé",
            Dialog::MathTable(_) => "Tableau de mathématiques",
            Dialog::Symbols => "Symboles et unités",
            Dialog::Shapes => "Insérer une figure",
            Dialog::Colors => "Couleur du texte",
            Dialog::Chart { .. } => "Créer un graphique",
            Dialog::Header(_) => "En-tête du cours",
            Dialog::Organizer { .. } => "Ranger avec Organisator",
            Dialog::Worksheet(_) | Dialog::Units(_) => "Aide au cours",
            Dialog::Accessibility => "Mon confort d’écriture",
            Dialog::Search => "Rechercher et remplacer",
            Dialog::Help => "Écrinator · mode d’emploi",
            Dialog::Recovery => "Reprendre un brouillon",
            Dialog::Table { .. } => "Insérer un tableau",
            Dialog::Formula { .. } => "Formule mathématique",
            Dialog::Timeline(_) => "Frise chronologique",
            Dialog::Library { .. } => "Bibliothèque d’illustrations",
            Dialog::Page { .. } => "Mise en page",
            Dialog::Ocr(_) => "Texte reconnu · à relire",
            Dialog::Print { .. } => "Imprimer le cours",
        };
        let response = egui::Modal::new(egui::Id::new("ecr-dialog"))
            .backdrop_color(Color32::from_rgba_unmultiplied(30,49,73,12))
            .frame(egui::Frame::new().fill(Color32::WHITE).corner_radius(16.)
                .stroke(egui::Stroke::new(0.8,Color32::from_rgb(227,232,240))).inner_margin(20.))
            .show(ctx,|ui|{
            ui.set_width((ctx.content_rect().width()-88.).clamp(260.,470.));
            ui.spacing_mut().item_spacing=egui::vec2(10.,12.);
            ui.spacing_mut().interact_size.y=34.;
            ui.spacing_mut().text_edit_width=ui.available_width()-20.;
            ui.horizontal(|ui|{
                ui.label(RichText::new(title).size(20.).strong().color(INK));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center),|ui|{
                    if ribbon::control(ui,"close","","Fermer",false).clicked(){open=false;}
                });
            });
            ui.add_space(6.);
            egui::ScrollArea::vertical().max_height((ctx.content_rect().height()-180.).clamp(140.,500.)).show(ui,|ui|{
            match &mut dialog {
                Dialog::Header(_) | Dialog::Box(_) | Dialog::Formula { .. } | Dialog::Table { .. } | Dialog::Page { .. } => {},
                Dialog::Overwrite{path,export,stamp}=>{ui.label("Un fichier porte déjà ce nom :");ui.label(path.display().to_string());ui.label("Le remplacer supprimera sa version actuelle. Vous pouvez revenir choisir un autre nom.");if primary(ui,"Remplacer le fichier").clicked(){if storage::stamp(path)!=*stamp{self.status="Le fichier a changé depuis votre choix. Choisissez à nouveau le nom de destination.".into();}else{self.write(path.clone(),*export,ctx);}done=true;}},
                Dialog::Symbols=>{ui.horizontal_wrapped(|ui|{for symbol in ["×","÷","≤","≥","≠","π","α","β","Δ","µ","Ω","∠","∥","⊥","°","°C","kg","m²","m³","→","ñ","¿","¡","ü","ä","ö","ß"]{if ui.add_sized([54.,45.],egui::Button::new(RichText::new(symbol).size(23.))).clicked(){self.command("text.insert",json!({"text":symbol}));done=true;}}});},
                Dialog::Shapes=>{ui.horizontal_wrapped(|ui|{for(name,label,kind)in[("figure","Triangle","triangle"),("frame","Rectangle","rectangle"),("angle","Trait","line"),("observation","Cercle","ellipse")]{if glyph::button(ui,name,label,egui::vec2(98.,82.),true).clicked(){self.command("insert.shape",json!({"kind":kind,"width":120.,"height":90.,"fill":"E6F0FF","stroke":"0757ED"}));done=true;}}});},
                Dialog::Colors=>{ui.horizontal_wrapped(|ui|{for(hex,label)in[("14264B","Encre"),("0757ED","Bleu"),("1B7850","Vert"),("B73131","Rouge"),("713AAE","Violet"),("A46600","Ocre")]{if ui.button(label).clicked(){self.command("format.color",json!({"color":hex}));done=true;}}});},
                Dialog::Calculation(_) | Dialog::MathTable(_)=>{},
                Dialog::Chart{..}=>{},
                Dialog::Organizer{..}|Dialog::Worksheet(_)|Dialog::Units(_)=>{},
                Dialog::Accessibility=>{
                    ui.label("Choisissez un point de départ, puis ajustez selon vos préférences.");
                    for(i,name)in["Standard","Lecture facilitée","Écriture facilitée","Concentration"].iter().enumerate(){if ui.selectable_value(&mut self.prefs.profile,i,*name).clicked(){
                        self.focus=i==3;self.word.session.view.zoom=if i==0{1.0}else{1.2};self.word.session.view.fit=String::new();
                        self.font=if i==1{"OpenDyslexic"}else{"Arial"}.into();self.size=if i==0{12.}else{18.};
                        self.command("format.font",json!({"name":self.font}));self.command("format.size",json!({"size":self.size}));self.command("para.lineSpacing",json!({"value":if i==1{1.5}else{1.25}}));self.remember();
                    }}
                    ui.label("La police et l’interligne s’appliquent à la sélection ou aux prochaines lettres. Le zoom concerne l’affichage.");
                    if ui.checkbox(&mut self.prefs.cream,"Fond de travail crème").changed(){self.remember();}
                    if ui.button("Ajuster interligne et caractères").clicked(){done=true;self.dialog=Some(Dialog::Page{margin:18.,line:1.5,spacing:1.});}
                },
                Dialog::Search=>{
                    ui.label("Rechercher");ui.add(egui::TextEdit::singleline(&mut self.search).desired_width(380.));
                    ui.label("Remplacer par");ui.add(egui::TextEdit::singleline(&mut self.replace).desired_width(380.));
                    ui.horizontal(|ui|{if ui.button("Suivant").clicked(){self.command("edit.find",json!({"text":self.search,"special":false}));self.command("edit.findNext",json!({}));}if ui.button("Remplacer").clicked(){self.command("edit.replace",json!({"text":self.search,"with":self.replace,"special":false}));}if ui.button("Tout remplacer").clicked(){self.command("edit.replaceAll",json!({"text":self.search,"with":self.replace,"special":false}));}});
                },
                Dialog::Timeline(_) | Dialog::Library{..}=>{},
                Dialog::Ocr(text)=>{
                    ui.label("Relisez et corrigez le texte. L’image originale reste dans le cours.");
                    ui.add(egui::TextEdit::multiline(text).desired_rows(14).desired_width(450.));
                    ui.horizontal(|ui|{if ui.button("Copier").clicked(){ctx.copy_text(text.clone());}if primary(ui,"Insérer après l’image").clicked(){self.command("caret.right",json!({}));self.command("text.insert",json!({"text":format!("\n{text}\n")}));done=true;}});
                    ui.label(RichText::new("Les formules et les schémas complexes demandent une correction manuelle.").size(12.));
                },
                Dialog::Print{printers,index,copies,duplex,gray}=>{
                    if printers.is_empty(){ui.label("Aucune imprimante disponible. Ajoutez une imprimante Windows ou exportez le cours en PDF.");}
                    else {
                        egui::ComboBox::from_id_salt("printer").width(400.).selected_text(printers.get(*index).map(|p|p.name.as_str()).unwrap_or("Choisir")).show_ui(ui,|ui|{for(i,p)in printers.iter().enumerate(){ui.selectable_value(index,i,&p.name);}});
                        ui.horizontal(|ui|{ui.label("Exemplaires");ui.add(egui::DragValue::new(copies).range(1..=99));});ui.checkbox(duplex,"Recto verso · bord long");ui.checkbox(gray,"Niveaux de gris");
                        ui.label("Toutes les pages A4 sont imprimées, en ajustant à la zone imprimable.");
                        if primary(ui,"Imprimer").clicked(){if let Some(p)=printers.get(*index){let job=craft_print::Job{printer:Some(p.name.clone()),copies:*copies,grayscale:*gray,duplex:Some(if *duplex{craft_print::Duplex::LongEdge}else{craft_print::Duplex::Off}),scaling:craft_print::Scaling::ShrinkToFit,title:self.school.title.clone(),..Default::default()};self.submit_print(job,ctx);done=true;}}
                    }
                },
                Dialog::Recovery=>{
                    ui.label("Ces instantanés automatiques peuvent contenir un cours interrompu. Ils sont conservés jusqu’à leur suppression explicite dans le dossier de données.");
                    for p in self.recoveries.clone(){if ui.button(p.file_name().map(|s|s.to_string_lossy()).unwrap_or_default()).clicked(){self.request(Action::Open(p),ctx);done=true;}}
                },
                Dialog::Help=>{
                    ui.label(concat!("Écrinator ",env!("CARGO_PKG_VERSION")," · version de développement Rust"));ui.label("1. Choisissez une matière ou Page blanche.\n2. Le bouton Bandeau permet de compléter le chapitre et la date.\n3. Cliquez sur la feuille pour écrire. Normal ou la gomme retire la mise en forme d’un titre.\n4. Outils affiche les outils de matière.\n5. Enregistrez en ODT ; exportez une copie en PDF ou DOCX.");
                    ui.label("Ctrl+S enregistrer · Ctrl+Z annuler · Ctrl+Y rétablir\nCtrl+F rechercher · Ctrl+P imprimer · F11 concentration\nTab navigue dans les contrôles et les cellules.");
                    ui.label("Organisator est facultatif. L’OCR français utilise la langue installée dans Windows. La récupération automatique protège un brouillon toutes les 10 secondes après une modification.");
                    ui.label("Moteur : Wordcraft 0.9.0 (MIT / Apache-2.0). Polices libres : Cursive et OpenDyslexic. Pas de télémétrie ni de connexion à l’exécution.");
                    if ui.button("Reprendre un brouillon automatique").clicked(){done=true;self.dialog=Some(Dialog::Recovery);}
                }
            }
            });
            ui.add_space(8.);if ui.button("Fermer").clicked(){done=true;}
        });
        if response.should_close() {
            open = false;
        }
        if open && !done && self.dialog.is_none() {
            self.dialog = Some(dialog);
        } else {
            self.word.canvas.want_focus = true;
        }
    }
    pub(super) fn unsaved_dialog(&mut self, ctx: &egui::Context) {
        if self.pending.is_none() {
            return;
        }
        let response = egui::Modal::new(egui::Id::new("unsaved"))
            .backdrop_color(Color32::from_rgba_unmultiplied(30, 49, 73, 12))
            .show(ctx, |ui| {
                ui.heading(format!("Enregistrer « {} » ?", self.active_title()));
                ui.label("Ce document contient des modifications non enregistrées.");
                ui.horizontal(|ui| {
                    if ui
                        .add_enabled(!self.busy, egui::Button::new("Enregistrer"))
                        .clicked()
                    {
                        self.save(false, ctx);
                    }
                    if ui
                        .add_enabled(!self.busy, egui::Button::new("Ne pas conserver"))
                        .clicked()
                    {
                        if let Some(action) = self.pending.take() {
                            self.word.session.dirty = false;
                            self.perform(action, ctx);
                        }
                    }
                    if ui.button("Revenir au cours").clicked() {
                        self.pending = None;
                        self.closing_all = false;
                    }
                });
            });
        if response.should_close() && !self.busy {
            self.pending = None;
            self.closing_all = false;
            self.word.canvas.want_focus = true;
        }
    }
}
fn primary(ui: &mut egui::Ui, label: &str) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(label).color(Color32::WHITE))
            .fill(BLUE)
            .min_size(egui::vec2(150., 40.)),
    )
}
