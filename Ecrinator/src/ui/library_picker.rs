use super::*;
use ecrinator::library;
impl App {
    pub(super) fn library_dialog(
        &mut self,
        ctx: &egui::Context,
        category: &mut String,
        query: &mut String,
        selected: &mut Option<String>,
        topic: &mut String,
        page: &mut usize,
    ) -> bool {
        let preview_id = egui::Id::new("library-preview-image");
        if let Some((id, data)) =
            ctx.data(|d| d.get_temp::<(String, std::sync::Arc<[u8]>)>(preview_id))
        {
            let mut done = false;
            let modal = egui::Modal::new(egui::Id::new("library-preview"))
                .backdrop_color(Color32::from_rgba_unmultiplied(30, 49, 73, 12))
                .frame(
                    egui::Frame::new()
                        .fill(Color32::WHITE)
                        .corner_radius(16.)
                        .inner_margin(18.),
                )
                .show(ctx, |ui| {
                    ui.set_width((ctx.content_rect().width() - 85.).clamp(260., 1000.));
                    if let Some(e) = library::catalog().iter().find(|e| e.id == id) {
                        ui.add(egui::Label::new(RichText::new(&e.title).strong()).truncate())
                            .on_hover_text(&e.title);
                        ui.horizontal_wrapped(|ui| {
                            let level = if e.grades.is_empty() {
                                e.cycle.clone()
                            } else {
                                e.grades.join(" · ")
                            };
                            if !level.is_empty() {
                                ui.label(RichText::new(level).size(12.).strong().color(BLUE));
                            }
                            if !e.educational_use.is_empty() {
                                ui.label(RichText::new(&e.educational_use).size(12.));
                            }
                            if !e.language.is_empty()
                                && !matches!(e.language.as_str(), "fr" | "zxx")
                            {
                                ui.label(
                                    RichText::new(format!("Texte de l’image : {}", e.language))
                                        .size(12.)
                                        .color(ribbon::MUTED),
                                );
                            }
                        });
                        if !e.learning_objective.is_empty() {
                            ui.add(egui::Label::new(&e.learning_objective).wrap());
                        }
                        ui.add(
                            egui::Image::from_bytes(
                                format!("bytes://library-full/{}", e.filename),
                                data,
                            )
                            .max_size(egui::vec2(
                                ui.available_width(),
                                (ctx.content_rect().height() - 295.).max(110.),
                            ))
                            .maintain_aspect_ratio(true),
                        );
                        ui.horizontal(|ui| {
                            ui.label(RichText::new(&e.license).size(11.).color(ribbon::MUTED));
                            if e.source_url.starts_with("https://") {
                                ui.hyperlink_to("Source", &e.source_url);
                            } else {
                                ui.label("Création Écrinator · SVG source inclus");
                            }
                            ui.with_layout(
                                egui::Layout::right_to_left(egui::Align::Center),
                                |ui| {
                                    done = ui.button("Fermer l’aperçu").clicked();
                                },
                            );
                        });
                    }
                });
            if done || modal.should_close() {
                ctx.data_mut(|d| d.remove::<(String, std::sync::Arc<[u8]>)>(preview_id));
            }
            return false;
        }
        let mut close = false;
        let mut insert = false;
        let mut own = false;
        let filter_id = egui::Id::new("school-library-filters");
        let (mut bw, mut blank) = ctx
            .data(|d| d.get_temp::<(bool, bool)>(filter_id))
            .unwrap_or((false, false));
        let collection_id = egui::Id::new("school-library-collection");
        let mut collection = ctx
            .data(|d| d.get_temp::<String>(collection_id))
            .unwrap_or_else(|| "Images du collège".into());
        let school_filter_id = egui::Id::new("library-school-filters");
        let (mut grade, mut usage, mut french_only) = ctx
            .data(|d| d.get_temp::<(String, String, bool)>(school_filter_id))
            .unwrap_or_default();
        let available: Vec<_> = library::catalog().iter().collect();
        let response = egui::Modal::new(egui::Id::new("school-library"))
            .backdrop_color(Color32::from_rgba_unmultiplied(30, 49, 73, 12))
            .frame(
                egui::Frame::new()
                    .fill(Color32::WHITE)
                    .corner_radius(16.)
                    .inner_margin(20.),
            )
            .show(ctx, |ui| {
                ui.set_width((ctx.content_rect().width() - 85.).clamp(280., 700.));
                ui.spacing_mut().item_spacing = egui::vec2(10., 10.);
                ui.horizontal(|ui| {
                    ui.label(RichText::new("La bibliothèque du cours").size(22.).strong());
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ribbon::control(ui, "close", "", "Fermer", false).clicked() {
                            close = true;
                        }
                    });
                });
                ui.label(
                    RichText::new(format!(
                        "{} images intégrées · hors ligne · sources conservées",
                        available.len()
                    ))
                    .size(11.)
                    .color(ribbon::MUTED),
                );
                ui.horizontal_wrapped(|ui| {
                    egui::ComboBox::from_id_salt("library-subject")
                        .width(175.)
                        .selected_text(if category.is_empty() {
                            "Toutes les matières"
                        } else {
                            category.as_str()
                        })
                        .show_ui(ui, |ui| {
                            for value in [
                                "",
                                "Cartes",
                                "Mathématiques",
                                "SVT",
                                "Physique-chimie",
                                "Technologie",
                                "Français",
                                "Histoire-géographie",
                                "EMC",
                                "Langues",
                                "Anglais",
                                "Espagnol",
                                "Allemand",
                                "Arts plastiques",
                                "Éducation musicale",
                            ] {
                                if ui
                                    .selectable_value(
                                        category,
                                        value.into(),
                                        if value.is_empty() {
                                            "Toutes les matières"
                                        } else {
                                            value
                                        },
                                    )
                                    .changed()
                                {
                                    topic.clear();
                                    *page = 0;
                                }
                            }
                        });
                    if ui.checkbox(&mut bw, "Noir et blanc").changed() {
                        *page = 0;
                    }
                    if ui.checkbox(&mut blank, "Sans légende").changed() {
                        *page = 0;
                    }
                });
                ctx.data_mut(|d| d.insert_temp(filter_id, (bw, blank)));
                if ui
                    .add(
                        egui::TextEdit::singleline(query)
                            .hint_text("Rechercher : cellule, France, circuit…")
                            .desired_width(ui.available_width())
                            .margin(egui::vec2(10., 9.)),
                    )
                    .changed()
                {
                    *page = 0;
                }
                ui.horizontal_wrapped(|ui| {
                    egui::ComboBox::from_id_salt("library-collection")
                        .width(190.)
                        .selected_text(&collection)
                        .show_ui(ui, |ui| {
                            for name in [
                                "Images du collège",
                                "France",
                                "Monde",
                                "Histoire",
                                "Cartes de géographie",
                                "Schémas scientifiques",
                                "Littérature et arts",
                                "Tout",
                            ] {
                                if ui
                                    .selectable_value(&mut collection, name.into(), name)
                                    .changed()
                                {
                                    topic.clear();
                                    *page = 0;
                                    *selected = None;
                                }
                            }
                        });
                    ui.label(
                        RichText::new("Documents à étudier et supports à compléter")
                            .size(10.)
                            .color(ribbon::MUTED),
                    );
                });
                ui.horizontal_wrapped(|ui| {
                    egui::ComboBox::from_id_salt("library-grade")
                        .selected_text(if grade.is_empty() {
                            "Tous les niveaux"
                        } else {
                            &grade
                        })
                        .show_ui(ui, |ui| {
                            for value in ["", "6e", "5e", "4e", "3e", "Cycle 4"] {
                                if ui
                                    .selectable_value(
                                        &mut grade,
                                        value.into(),
                                        if value.is_empty() {
                                            "Tous les niveaux"
                                        } else {
                                            value
                                        },
                                    )
                                    .changed()
                                {
                                    *page = 0;
                                }
                            }
                        });
                    egui::ComboBox::from_id_salt("library-use")
                        .selected_text(if usage.is_empty() {
                            "Tous les usages"
                        } else {
                            &usage
                        })
                        .show_ui(ui, |ui| {
                            for value in ["", "À étudier", "À compléter"] {
                                if ui
                                    .selectable_value(
                                        &mut usage,
                                        value.into(),
                                        if value.is_empty() {
                                            "Tous les usages"
                                        } else {
                                            value
                                        },
                                    )
                                    .changed()
                                {
                                    *page = 0;
                                }
                            }
                        });
                    if ui
                        .checkbox(&mut french_only, "Français ou sans texte")
                        .changed()
                    {
                        *page = 0;
                    }
                });
                ctx.data_mut(|d| {
                    d.insert_temp(
                        school_filter_id,
                        (grade.clone(), usage.clone(), french_only),
                    )
                });
                ctx.data_mut(|d| d.insert_temp(collection_id, collection.clone()));
                let in_collection = |e: &&library::Entry| match collection.as_str() {
                    "Images du collège" => !e.id.starts_with("college-atlas-region-"),
                    "France" => {
                        e.topic.starts_with("France")
                            || e.topic == "Atlas détaillé · France"
                            || e.title.starts_with("France")
                    }
                    "Monde" => e.topic.starts_with("Monde") || e.id.starts_with("ne-country-"),
                    "Histoire" => e.domain == "history" || e.topic.starts_with("Histoire"),
                    "Cartes de géographie" => e.domain == "geography",
                    "Schémas scientifiques" => e.domain == "science",
                    "Littérature et arts" => matches!(e.domain.as_str(), "literature" | "art"),
                    _ => true,
                };
                let mut topics: Vec<_> = available
                    .iter()
                    .filter(|e| {
                        e.matches(category, "")
                            && in_collection(e)
                            && e.matches_school_filters(&grade, &usage, french_only)
                    })
                    .map(|e| e.topic.as_str())
                    .filter(|s| !s.is_empty())
                    .collect();
                topics.sort();
                topics.dedup();
                let mut entries: Vec<_> = available
                    .iter()
                    .copied()
                    .filter(|e| {
                        e.matches(category, query)
                            && e.matches_school_filters(&grade, &usage, french_only)
                            && in_collection(e)
                            && (topic.is_empty() || e.topic == *topic)
                            && (!bw || e.monochrome)
                            && (!blank || e.unlabelled)
                    })
                    .collect();
                entries.sort_by_key(|e| {
                    (
                        if e.id.starts_with("college-atlas-region-") {
                            9
                        } else {
                            match e.kind.as_str() {
                                "Schéma" => 0,
                                "Figure géométrique" => 1,
                                "Support à compléter" => 2,
                                "Fond de carte" => 3,
                                "Pictogramme" => 5,
                                _ => 4,
                            }
                        },
                        e.topic.as_str(),
                        e.title.as_str(),
                    )
                });
                if selected
                    .as_deref()
                    .is_some_and(|id| !entries.iter().any(|e| e.id == id))
                {
                    *selected = None;
                }
                ctx.data_mut(|d| {
                    d.insert_temp(egui::Id::new("library-visible-count"), entries.len())
                });
                const PAGE: usize = 24;
                let pages = entries.len().div_ceil(PAGE).max(1);
                *page = (*page).min(pages - 1);
                ui.horizontal(|ui| {
                    egui::ComboBox::from_id_salt("library-topic")
                        .width(190.)
                        .selected_text(if topic.is_empty() {
                            "Tous les thèmes"
                        } else {
                            topic.as_str()
                        })
                        .show_ui(ui, |ui| {
                            if ui
                                .selectable_value(topic, String::new(), "Tous les thèmes")
                                .changed()
                            {
                                *page = 0;
                            }
                            for value in topics {
                                if ui.selectable_value(topic, value.into(), value).changed() {
                                    *page = 0;
                                }
                            }
                        });
                    ui.label(
                        RichText::new(format!("{} résultats", entries.len()))
                            .size(11.)
                            .color(ribbon::MUTED),
                    );
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui
                            .add_enabled(*page + 1 < pages, egui::Button::new("›"))
                            .on_hover_text("Page suivante")
                            .clicked()
                        {
                            *page += 1;
                        }
                        ui.label(format!("{} / {pages}", *page + 1));
                        if ui
                            .add_enabled(*page > 0, egui::Button::new("‹"))
                            .on_hover_text("Page précédente")
                            .clicked()
                        {
                            *page -= 1;
                        }
                    });
                });
                egui::ScrollArea::vertical()
                    .id_salt("library-grid")
                    .max_height((ctx.content_rect().height() - 500.).clamp(70., 360.))
                    .show(ui, |ui| {
                        if entries.is_empty() {
                            ui.label("Aucune image pour cette recherche.");
                        }
                        let cols = if ui.available_width() > 550. { 3 } else { 2 };
                        let width = (ui.available_width() - 12. * (cols - 1) as f32) / cols as f32;
                        for row in entries
                            .iter()
                            .skip(*page * PAGE)
                            .take(PAGE)
                            .collect::<Vec<_>>()
                            .chunks(cols)
                        {
                            ui.horizontal(|ui| {
                                for e in row {
                                    let on = selected.as_deref() == Some(e.id.as_str());
                                    egui::Frame::new()
                                        .fill(if on {
                                            Color32::from_rgb(237, 244, 255)
                                        } else {
                                            Color32::from_rgb(249, 250, 253)
                                        })
                                        .stroke(egui::Stroke::new(
                                            1.,
                                            if on {
                                                BLUE
                                            } else {
                                                Color32::from_rgb(230, 235, 244)
                                            },
                                        ))
                                        .corner_radius(12.)
                                        .inner_margin(9.)
                                        .show(ui, |ui| {
                                            ui.vertical(|ui| {
                                                ui.set_width(width - 20.);
                                                ui.set_max_width(width - 20.);
                                                let r = ui
                                                    .allocate_space(egui::vec2(width - 20., 94.))
                                                    .1;
                                                if let Ok(bytes) = library::thumbnail(e) {
                                                    let fit = (r.width() / e.width as f32)
                                                        .min(r.height() / e.height as f32);
                                                    let target = egui::Rect::from_center_size(
                                                        r.center(),
                                                        egui::vec2(e.width as f32, e.height as f32)
                                                            * fit,
                                                    );
                                                    egui::Image::from_bytes(
                                                        format!("bytes://library/{}", e.filename),
                                                        bytes,
                                                    )
                                                    .paint_at(ui, target);
                                                }
                                                let short = if e.title.chars().count() > 65 {
                                                    format!(
                                                        "{}…",
                                                        e.title
                                                            .chars()
                                                            .take(62)
                                                            .collect::<String>()
                                                    )
                                                } else {
                                                    e.title.clone()
                                                };
                                                let label = ui
                                                    .allocate_ui_with_layout(
                                                        egui::vec2(width - 20., 32.),
                                                        egui::Layout::top_down(egui::Align::Center),
                                                        |ui| {
                                                            ui.add(
                                                                egui::Label::new(
                                                                    RichText::new(short)
                                                                        .size(11.)
                                                                        .strong(),
                                                                )
                                                                .wrap()
                                                                .halign(egui::Align::Center),
                                                            )
                                                        },
                                                    )
                                                    .inner;
                                                let hit = ui.interact(
                                                    r.union(label.rect),
                                                    egui::Id::new(("library-item", &e.id)),
                                                    egui::Sense::click(),
                                                );
                                                hit.widget_info(|| {
                                                    egui::WidgetInfo::labeled(
                                                        egui::WidgetType::Button,
                                                        true,
                                                        &e.title,
                                                    )
                                                });
                                                glyph::focus(ui, &hit);
                                                if hit.clicked() {
                                                    *selected = Some(e.id.clone());
                                                }
                                                hit.on_hover_text(format!(
                                                    "{}\n{} · {}",
                                                    e.title, e.topic, e.license
                                                ));
                                            });
                                        });
                                }
                            });
                        }
                    });
                if let Some(e) = selected
                    .as_deref()
                    .and_then(|id| library::catalog().iter().find(|e| e.id == id))
                {
                    egui::Frame::new()
                        .fill(Color32::from_rgb(245, 248, 252))
                        .corner_radius(10.)
                        .inner_margin(10.)
                        .show(ui, |ui| {
                            ui.add(egui::Label::new(RichText::new(&e.title).strong()).truncate())
                                .on_hover_text(&e.title);
                            ui.add(
                                egui::Label::new(
                                    RichText::new(format!("{} · {}", e.author, e.license))
                                        .size(10.)
                                        .color(ribbon::MUTED),
                                )
                                .truncate(),
                            )
                            .on_hover_text(e.credit());
                            ui.horizontal(|ui| {
                                if ui.button("Voir en grand").clicked() {
                                    match library::read_asset(e, false) {
                                        Ok(data) => {
                                            ctx.data_mut(|d| {
                                                d.insert_temp(preview_id, (e.id.clone(), data))
                                            });
                                        }
                                        Err(error) => self.status = error,
                                    }
                                }
                                if e.source_url.starts_with("https://") {
                                    ui.hyperlink_to("Source et attribution", &e.source_url);
                                } else {
                                    ui.label("Création Écrinator · SVG source inclus");
                                }
                                if !e.license_url.is_empty() {
                                    ui.hyperlink_to("Licence", &e.license_url);
                                }
                            });
                        });
                } else {
                    ui.label(
                        RichText::new("Choisissez une image pour l’insérer dans votre cours.")
                            .size(11.)
                            .color(ribbon::MUTED),
                    );
                }
                ui.separator();
                ui.horizontal(|ui| {
                    if ui.button("Depuis mon ordinateur…").clicked() {
                        own = true;
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        let r = ui.add_enabled(
                            selected.is_some(),
                            egui::Button::new(
                                RichText::new("Insérer dans le cours").color(Color32::WHITE),
                            )
                            .fill(BLUE)
                            .corner_radius(10.)
                            .min_size(egui::vec2(165., 38.)),
                        );
                        ctx.data_mut(|d| {
                            d.insert_temp(egui::Id::new("library-insert-rect"), r.rect)
                        });
                        insert = r.clicked();
                    });
                });
                ctx.data_mut(|d| {
                    d.insert_temp(egui::Id::new("library-content-rect"), ui.min_rect())
                });
            });
        if own {
            self.pick(Pick::Image, ctx);
            close = true;
        }
        if insert {
            if let Some(e) = selected
                .as_deref()
                .and_then(|id| library::catalog().iter().find(|e| e.id == id))
            {
                let result = library::insert(&mut self.word.session, e);
                close = result.is_ok();
                self.message(
                    result,
                    "Illustration ajoutée · source disponible au clic droit",
                );
            }
        }
        close || response.should_close()
    }
}
