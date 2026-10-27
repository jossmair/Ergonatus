//! Editable, native vector timelines. Dates and events survive .ecr round trips.
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use wordcraft_doc::{
    InlineObject, Pos,
    graphic::{Graphic, GraphicItem, GraphicKind, PathSeg, TextAlign},
    para::{Float, ShapeKind},
    props::Rgb,
};
use wordcraft_engine::{Selection, Session};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Event {
    pub date: String,
    pub label: String,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Timeline {
    pub title: String,
    pub events: Vec<Event>,
}
#[derive(Serialize, Deserialize)]
struct Model {
    version: u32,
    timeline: Timeline,
}
impl Default for Timeline {
    fn default() -> Self {
        Self {
            title: "Les grandes étapes".into(),
            events: vec![
                Event {
                    date: "1789".into(),
                    label: "Début de la Révolution".into(),
                },
                Event {
                    date: "1792".into(),
                    label: "Proclamation de la République".into(),
                },
                Event {
                    date: "1799".into(),
                    label: "Début du Consulat".into(),
                },
            ],
        }
    }
}
impl Timeline {
    pub fn validate(&self) -> Result<(), String> {
        if !(2..=8).contains(&self.events.len()) {
            return Err("Ajoutez entre 2 et 8 événements.".into());
        }
        if self.title.chars().count() > 70 {
            return Err("Le titre est limité à 70 caractères.".into());
        }
        for e in &self.events {
            if e.date.trim().is_empty() || e.label.trim().is_empty() {
                return Err("Chaque événement doit avoir une date et un texte.".into());
            }
            if e.date.chars().count() > 22 || e.label.chars().count() > 100 {
                return Err("Limites : 22 caractères par date, 100 par événement.".into());
            }
        }
        Ok(())
    }
    pub fn object(&self, width: f32) -> Result<InlineObject, String> {
        self.validate()?;
        if !width.is_finite() {
            return Err("Largeur de frise invalide.".into());
        }
        let w = width.clamp(250., 720.);
        let n = self.events.len();
        let step = (w - 28.) / n as f32;
        let card_w = (step * 1.8).min(158.).min(w / 2. - 18.);
        let wrap = ((card_w - 20.) / 5.6).floor().max(12.) as usize;
        let lines: Vec<Vec<String>> = self
            .events
            .iter()
            .map(|e| wrap_text(&e.label, wrap))
            .collect();
        let dates: Vec<Vec<String>> = self
            .events
            .iter()
            .map(|e| wrap_text(&e.date, ((card_w - 20.) / 6.5).floor().max(6.) as usize))
            .collect();
        let date_h = dates.iter().map(Vec::len).max().unwrap_or(1) as f32 * 13.;
        let card_h = 21. + date_h + lines.iter().map(Vec::len).max().unwrap_or(1) as f32 * 12.;
        let title_h = if self.title.trim().is_empty() {
            0.
        } else {
            28.
        };
        let axis_y = title_h + card_h + 23.;
        let h = title_h + 2. * card_h + 46.;
        let mut items = Vec::new();
        let ink = Rgb(30, 49, 73);
        let text = |rect, text: String, size, color, bold, align| GraphicItem::Text {
            rect,
            text,
            size,
            color,
            bold,
            align,
            font: Some("Arial".into()),
        };
        if title_h > 0. {
            items.push(text(
                [8., 0., w - 16., 22.],
                self.title.clone(),
                14.,
                ink,
                true,
                TextAlign::Left,
            ));
        }
        items.push(GraphicItem::Path {
            segs: vec![PathSeg::Move(8., axis_y), PathSeg::Line(w - 9., axis_y)],
            fill: None,
            stroke: Some(Rgb(153, 173, 197)),
            stroke_width: 2.,
        });
        items.push(GraphicItem::Path {
            segs: vec![
                PathSeg::Move(w - 14., axis_y - 4.),
                PathSeg::Line(w - 8., axis_y),
                PathSeg::Line(w - 14., axis_y + 4.),
            ],
            fill: None,
            stroke: Some(Rgb(153, 173, 197)),
            stroke_width: 2.,
        });
        let palette = [
            Rgb(37, 99, 206),
            Rgb(15, 137, 126),
            Rgb(129, 70, 183),
            Rgb(196, 96, 34),
        ];
        for i in 0..self.events.len() {
            let c = palette[i % palette.len()];
            let cx = 14. + step * (i as f32 + 0.5);
            let x = (cx - card_w / 2.).clamp(5., w - card_w - 5.);
            let top = i % 2 == 0;
            let y = if top { title_h } else { axis_y + 23. };
            let edge = if top { y + card_h } else { y };
            items.push(GraphicItem::Path {
                segs: vec![PathSeg::Move(cx, axis_y), PathSeg::Line(cx, edge)],
                fill: None,
                stroke: Some(c),
                stroke_width: 1.2,
            });
            let pale = Rgb(
                239 + (c.0 as u16 / 18) as u8,
                239 + (c.1 as u16 / 18) as u8,
                239 + (c.2 as u16 / 18) as u8,
            );
            items.push(GraphicItem::Shape {
                rect: [x, y, card_w, card_h],
                kind: ShapeKind::RoundedRectangle,
                fill: Some(pale),
                stroke: None,
                stroke_width: 0.,
            });
            items.push(GraphicItem::Shape {
                rect: [cx - 5., axis_y - 5., 10., 10.],
                kind: ShapeKind::Ellipse,
                fill: Some(c),
                stroke: Some(Rgb(255, 255, 255)),
                stroke_width: 1.5,
            });
            for (j, line) in dates[i].iter().enumerate() {
                items.push(text(
                    [x + 10., y + 7. + j as f32 * 13., card_w - 20., 13.],
                    line.clone(),
                    11.,
                    c,
                    true,
                    TextAlign::Left,
                ));
            }
            for (j, line) in lines[i].iter().enumerate() {
                items.push(text(
                    [
                        x + 10.,
                        y + 14. + date_h + j as f32 * 12.,
                        card_w - 20.,
                        12.,
                    ],
                    line.clone(),
                    9.5,
                    ink,
                    false,
                    TextAlign::Left,
                ));
            }
        }
        let alt = format!(
            "Frise chronologique — {}. {}. Espacement régulier des événements.",
            self.title,
            self.events
                .iter()
                .map(|e| format!("{} : {}", e.date, e.label))
                .collect::<Vec<_>>()
                .join(" ; ")
        );
        let graphic = Graphic {
            kind: GraphicKind::Diagram,
            items,
            w,
            h,
            app_data: Some(
                serde_json::to_string(&Model {
                    version: 1,
                    timeline: self.clone(),
                })
                .map_err(|e| e.to_string())?,
            ),
            ..Default::default()
        };
        Ok(InlineObject::Graphic {
            w,
            h,
            alt,
            float: Float::default(),
            graphic: Arc::new(graphic),
        })
    }
}
fn wrap_text(s: &str, max: usize) -> Vec<String> {
    let mut lines = Vec::new();
    let mut current = String::new();
    for word in s.split_whitespace() {
        if !current.is_empty() && current.chars().count() + 1 + word.chars().count() > max {
            lines.push(std::mem::take(&mut current));
        }
        for ch in word.chars() {
            if current.chars().count() >= max {
                lines.push(std::mem::take(&mut current));
            }
            current.push(ch);
        }
        current.push(' ');
    }
    if !current.is_empty() {
        lines.push(current.trim_end().into());
    }
    lines
}
pub fn model(object: &InlineObject) -> Option<Timeline> {
    let InlineObject::Graphic { graphic, .. } = object else {
        return None;
    };
    let data = graphic.app_data.as_ref()?;
    if data.len() > 16_384 {
        return None;
    }
    let m: Model = serde_json::from_str(data).ok()?;
    (m.version == 1 && m.timeline.validate().is_ok()).then_some(m.timeline)
}
pub fn selected(s: &Session) -> Option<(Pos, Timeline)> {
    for p in [&s.sel.anchor, &s.sel.focus] {
        for off in [Some(p.off), p.off.checked_sub('\u{fffc}'.len_utf8())]
            .into_iter()
            .flatten()
        {
            let pos = Pos { off, ..p.clone() };
            if let Some(m) = s
                .doc
                .para_at(&pos)
                .and_then(|p| p.object_at(off))
                .and_then(model)
            {
                return Some((pos, m));
            }
        }
    }
    None
}
pub fn apply(s: &mut Session, t: &Timeline) -> Result<(), String> {
    crate::core::ensure_writing_selection(s)?;
    let width = s
        .doc
        .sections()
        .first()
        .map(|(_, p)| p.text_width())
        .unwrap_or(468.);
    let obj = t.object(width)?;
    let snapshot = s.edit_snapshot();
    s.checkpoint("Créer ou modifier la frise");
    let result = (|| {
        if let Some((pos, _)) = selected(s) {
            let p = s
                .doc
                .para_mut(pos.story, &pos.path)
                .map_err(|e| e.to_string())?;
            let slot = p.object_at_mut(pos.off).ok_or("Frise introuvable")?;
            *slot = obj;
            p.touch();
            s.sel = Selection {
                anchor: pos.clone(),
                focus: Pos {
                    off: pos.off + '\u{fffc}'.len_utf8(),
                    ..pos
                },
            };
        } else {
            let (a, b) = s.sel.ordered();
            let (a, b) = (a.clone(), b.clone());
            let props = s.typing_props();
            let at = if a == b {
                a
            } else {
                s.doc.delete_range(&a, &b).map_err(|e| e.to_string())?
            };
            let end = s
                .doc
                .insert_object(&at, obj, &props)
                .map_err(|e| e.to_string())?;
            s.sel = Selection {
                anchor: at,
                focus: end,
            };
        }
        s.touch();
        s.relayout();
        Ok(())
    })();
    if result.is_err() {
        s.restore(snapshot);
    }
    result
}
