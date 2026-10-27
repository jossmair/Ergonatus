//! Compact data editors and previews drawn from the same vector model as the page.
use super::*;
use ecrinator::timeline::{Event, Timeline};
use wordcraft_doc::{
    InlineObject,
    graphic::{Graphic, GraphicItem, PathSeg, TextAlign},
    para::ShapeKind,
};
fn input(ui: &mut egui::Ui, text: &mut String, hint: &str, width: f32, limit: usize) {
    ui.add(
        egui::TextEdit::singleline(text)
            .hint_text(hint)
            .desired_width(width)
            .margin(egui::vec2(8., 8.))
            .char_limit(limit),
    );
}
pub(super) fn timeline_fields(ui: &mut egui::Ui, t: &mut Timeline) {
    ui.label(RichText::new("Titre de la frise").strong());
    input(
        ui,
        &mut t.title,
        "Les grandes étapes",
        ui.available_width(),
        70,
    );
    ui.add_space(6.);
    if let Ok(InlineObject::Graphic { graphic, .. }) = t.object(493.) {
        preview(ui, &graphic);
    }
    ui.label(
        RichText::new("Espacement régulier : les distances ne représentent pas les durées.")
            .size(11.)
            .color(ribbon::MUTED),
    );
    ui.add_space(8.);
    let mut remove = None;
    let mut swap = None;
    for (i, event) in t.events.iter_mut().enumerate() {
        egui::Frame::new()
            .fill(Color32::from_rgb(246, 248, 252))
            .corner_radius(10.)
            .inner_margin(8.)
            .show(ui, |ui| {
                ui.horizontal(|ui| {
                    ui.label(RichText::new(format!("{:02}", i + 1)).strong().color(BLUE));
                    input(ui, &mut event.date, "Date", 82., 22);
                    let width = (ui.available_width() - 74.).max(70.);
                    input(ui, &mut event.label, "Événement", width, 100);
                    if ui
                        .add_enabled(i > 0, egui::Button::new("↑"))
                        .on_hover_text("Monter cet événement")
                        .clicked()
                    {
                        swap = Some(i);
                    }
                    if ribbon::control(ui, "delete", "", "Retirer cet événement", false).clicked()
                    {
                        remove = Some(i);
                    }
                });
            });
    }
    if let Some(i) = remove {
        t.events.remove(i);
    }
    if let Some(i) = swap.filter(|i| *i < t.events.len() && *i > 0) {
        t.events.swap(i, i - 1);
    }
    if ui
        .add_enabled(
            t.events.len() < 8,
            egui::Button::new("+ Ajouter un événement"),
        )
        .clicked()
    {
        t.events.push(Event {
            date: String::new(),
            label: String::new(),
        });
    }
    ui.label(RichText::new("2 à 8 repères, placés dans l’ordre de la liste. L’espacement est régulier et ne représente pas les durées.").size(11.).color(ribbon::MUTED));
    if let Err(e) = t.validate() {
        ui.colored_label(Color32::from_rgb(164, 69, 38), e);
    }
}
pub(super) fn chart_data(labels: &str, values: &str) -> Result<(Vec<String>, Vec<f64>), String> {
    let cats: Vec<String> = labels.split(';').map(|s| s.trim().to_owned()).collect();
    let nums = values
        .split(';')
        .map(|s| s.trim().replace(',', ".").parse::<f64>())
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| "Complétez chaque mesure avec un nombre.".to_string())?;
    if !(1..=12).contains(&cats.len())
        || cats.len() != nums.len()
        || cats.iter().any(|s| s.is_empty() || s.chars().count() > 40)
        || nums.iter().any(|n| !n.is_finite())
    {
        return Err("Prévoyez 1 à 12 catégories et une mesure par catégorie.".into());
    }
    Ok((cats, nums))
}
pub(super) fn insert_chart(s: &mut Session, labels: &str, values: &str) -> Result<(), String> {
    let (cats, nums) = chart_data(labels, values)?;
    s.run("insert.chart",&json!({"type":"column","title":"Résultats","data":{"categories":cats,"series":[{"name":"Mesures","values":nums}]}})).map(|_|()).map_err(|e|e.to_string())
}
pub(super) fn chart_fields(ui: &mut egui::Ui, labels: &mut String, values: &mut String) {
    let mut cats: Vec<String> = labels.split(';').map(str::to_owned).collect();
    let mut nums: Vec<String> = values.split(';').map(str::to_owned).collect();
    nums.resize(cats.len(), String::new());
    ui.horizontal(|ui| {
        ui.label(RichText::new("Catégorie").strong());
        ui.add_space(190.);
        ui.label(RichText::new("Mesure").strong());
    });
    let mut remove = None;
    for i in 0..cats.len() {
        ui.horizontal(|ui| {
            input(
                ui,
                &mut cats[i],
                "Ex. : Janvier",
                ui.available_width() - 160.,
                40,
            );
            input(ui, &mut nums[i], "12,5", 90., 24);
            if ribbon::control(ui, "delete", "", "Retirer cette mesure", false).clicked() {
                remove = Some(i);
            }
        });
    }
    if let Some(i) = remove {
        cats.remove(i);
        nums.remove(i);
    }
    if ui
        .add_enabled(cats.len() < 12, egui::Button::new("+ Ajouter une mesure"))
        .clicked()
    {
        cats.push(String::new());
        nums.push(String::new());
    }
    *labels = cats.join(";");
    *values = nums.join(";");
    if let Err(e) = chart_data(labels, values) {
        ui.colored_label(Color32::from_rgb(164, 69, 38), e);
        return;
    }
    let mut s = Session::new(wordcraft_doc::Document::new());
    if insert_chart(&mut s, labels, values).is_ok() {
        let mut graphic = None;
        s.doc.objects_in_reading_order(&mut |o| {
            if let InlineObject::Graphic { graphic: g, .. } = o {
                graphic = Some(g.clone());
            }
        });
        if let Some(g) = graphic {
            preview(ui, &g);
        }
    }
}
fn color(c: wordcraft_doc::props::Rgb) -> Color32 {
    Color32::from_rgb(c.0, c.1, c.2)
}
pub(super) fn preview(ui: &mut egui::Ui, g: &Graphic) {
    ui.add_space(8.);
    ui.label(
        RichText::new("APERÇU")
            .size(10.)
            .strong()
            .color(ribbon::MUTED),
    );
    let w = ui.available_width();
    let scale = w / g.w.max(1.);
    let r = ui.allocate_space(egui::vec2(w, g.h * scale)).1;
    let p = ui.painter().with_clip_rect(r);
    let point = |x, y| r.min + egui::vec2(x * scale, y * scale);
    for item in &g.items {
        match item {
            GraphicItem::Shape {
                rect,
                kind,
                fill,
                stroke,
                stroke_width,
            } => {
                let rr = egui::Rect::from_min_size(
                    point(rect[0], rect[1]),
                    egui::vec2(rect[2], rect[3]) * scale,
                );
                let f = fill.map(color).unwrap_or(Color32::TRANSPARENT);
                let st = stroke
                    .map(|c| egui::Stroke::new(stroke_width * scale, color(c)))
                    .unwrap_or(egui::Stroke::NONE);
                if *kind == ShapeKind::Ellipse {
                    p.circle(rr.center(), rr.width().min(rr.height()) / 2., f, st);
                } else {
                    p.rect(
                        rr,
                        if *kind == ShapeKind::RoundedRectangle {
                            7.
                        } else {
                            0.
                        },
                        f,
                        st,
                        egui::StrokeKind::Inside,
                    );
                }
            }
            GraphicItem::Path {
                segs,
                stroke,
                stroke_width,
                fill,
            } => {
                let points: Vec<_> = segs
                    .iter()
                    .filter_map(|s| match s {
                        PathSeg::Move(x, y) | PathSeg::Line(x, y) => Some(point(*x, *y)),
                        _ => None,
                    })
                    .collect();
                if let Some(c) = fill {
                    p.add(egui::Shape::convex_polygon(
                        points,
                        color(*c),
                        egui::Stroke::NONE,
                    ));
                } else if let Some(c) = stroke {
                    p.add(egui::Shape::line(
                        points,
                        egui::Stroke::new(stroke_width * scale, color(*c)),
                    ));
                }
            }
            GraphicItem::Text {
                rect,
                text,
                size,
                color: c,
                align,
                ..
            } => {
                let (x, anchor) = match align {
                    TextAlign::Left => (rect[0], egui::Align2::LEFT_CENTER),
                    TextAlign::Center => (rect[0] + rect[2] / 2., egui::Align2::CENTER_CENTER),
                    TextAlign::Right => (rect[0] + rect[2], egui::Align2::RIGHT_CENTER),
                };
                p.text(
                    point(x, rect[1] + rect[3] / 2.),
                    anchor,
                    text,
                    egui::FontId::proportional(size * scale),
                    color(*c),
                );
            }
            _ => {}
        }
    }
}
