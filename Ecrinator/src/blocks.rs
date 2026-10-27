//! Pedagogical boxes are ordinary, editable one-cell tables in the document flow.
use crate::core::text;
use serde_json::json;
use std::sync::Arc;
use wordcraft_doc::{
    Path, Pos, para_block,
    props::{Border, Borders, Rgb},
};
use wordcraft_engine::{Selection, Session};
pub const TEMPLATES: &[&str] = &[
    "Définition",
    "Propriété",
    "Théorème",
    "Exemple",
    "À retenir",
    "Remarque",
    "Méthode",
    "Attention",
    "Exercice",
    "Observation",
    "Hypothèse",
    "Résultat",
    "Conclusion",
    "Vocabulaire",
];
fn color(title: &str) -> Rgb {
    crate::pedagogy::theme(title).ink
}
#[derive(Clone)]
pub struct Appearance {
    pub title: String,
    pub model: String,
    pub background: [u8; 3],
    pub border: [u8; 3],
    pub width: f32,
    pub radius: f32,
}
impl Appearance {
    pub fn use_model_colors(&mut self) {
        let ink = color(&self.model);
        let bg = background(&self.model);
        self.border = [ink.0, ink.1, ink.2];
        self.background = [bg.0, bg.1, bg.2];
    }
}
fn background(title: &str) -> Rgb {
    crate::pedagogy::theme(title).background
}
pub const DESIGN: &str = "Écrinator · encadré illustré v1";
fn title_text(p: &wordcraft_doc::Paragraph) -> String {
    p.plain_text()
        .trim_start_matches(['\u{fffc}', ' ', '\u{2002}'])
        .into()
}
fn heading(title: &str, model: &str, ink: Rgb) -> Result<wordcraft_doc::Paragraph, String> {
    let mut p = text(&format!("\u{2002}{title}"), 12.5, true, ink);
    p.insert_object(
        0,
        wordcraft_doc::InlineObject::Image {
            media: crate::pedagogy::icon_key(model),
            w: 18.,
            h: 18.,
            alt: format!("Encadré {model}"),
            float: Default::default(),
            crop: [0.; 4],
            ole: None,
        },
        &wordcraft_doc::CharProps::default(),
    )
    .map_err(|e| e.to_string())?;
    p.props.space_after = Some(5.);
    p.props.keep_next = Some(true);
    p.props.line_spacing = Some(wordcraft_doc::props::LineSpacing::Multiple(1.05));
    Ok(p)
}
fn borders(ink: Rgb, width: f32) -> Borders {
    let mut b = Borders::box_(Border {
        color: Some(crate::pedagogy::outline(ink)),
        ..Border::single(width.clamp(0.5, 6.))
    });
    b.left = Some(Border {
        color: Some(ink),
        ..Border::single(3.)
    });
    b
}
pub fn current_path(s: &Session) -> Result<Path, String> {
    let mut path = s.sel.focus.path.0.clone();
    while path.len() >= 4 {
        path.truncate(path.len() - 3);
        let tp = Path(path.clone());
        if s.doc.table(s.sel.focus.story, &tp).is_some_and(|t| {
            t.props
                .caption
                .as_deref()
                .is_some_and(|c| c.starts_with("Écrinator · ") && c != crate::core::HEADER)
        }) {
            return Ok(tp);
        }
    }
    Err("Placez le curseur dans un encadré pédagogique.".into())
}
pub fn selected(s: &Session) -> bool {
    current_path(s).is_ok()
}
/// Remove the selected pedagogical block and its content in one undo step.
pub fn delete(s: &mut Session) -> Result<(), String> {
    let tp = current_path(s)?;
    let story = s.sel.focus.story;
    let at = tp.last();
    s.checkpoint("Supprimer l’encadré et son contenu");
    let list = s.doc.container_mut(story, &tp).map_err(|e| e.to_string())?;
    if at >= list.len() {
        return Err("Encadré absent".into());
    }
    list.remove(at);
    let target = if list.get(at).is_some_and(|b| b.as_para().is_some()) {
        at
    } else if at > 0 && list.get(at - 1).is_some_and(|b| b.as_para().is_some()) {
        at - 1
    } else {
        list.insert(at, para_block(text("", 12., false, Rgb(30, 49, 73))));
        at
    };
    s.sel = Selection::caret(Pos::new(story, tp.with_last(target), 0));
    s.touch();
    s.relayout();
    Ok(())
}
pub fn appearance(s: &Session) -> Result<Appearance, String> {
    let path = current_path(s)?;
    let t = s
        .doc
        .table(s.sel.focus.story, &path)
        .ok_or("Encadré absent")?;
    let title = t
        .rows
        .first()
        .and_then(|r| r.cells.first())
        .and_then(|c| c.blocks.first())
        .and_then(|b| b.as_para())
        .map(title_text)
        .unwrap_or_default();
    let model = t
        .props
        .caption
        .as_deref()
        .unwrap_or("")
        .trim_start_matches("Écrinator · ")
        .to_string();
    let bg = t.props.shading.unwrap_or(Rgb(240, 247, 255));
    let border = t
        .props
        .borders
        .and_then(|b| b.top)
        .unwrap_or(Border::single(1.));
    let ink = t
        .props
        .borders
        .and_then(|b| b.left)
        .and_then(|b| b.color)
        .unwrap_or(color(&model));
    Ok(Appearance {
        title,
        model,
        background: [bg.0, bg.1, bg.2],
        border: [ink.0, ink.1, ink.2],
        width: border.width,
        radius: t.props.corner_radius.unwrap_or(8.),
    })
}
pub fn change(s: &mut Session, style: &Appearance) -> Result<(), String> {
    let path = current_path(s)?;
    let new_heading = heading(
        &style.title,
        &style.model,
        Rgb(style.border[0], style.border[1], style.border[2]),
    )?;
    s.checkpoint("Modifier l’encadré");
    s.doc.media.insert(
        crate::pedagogy::icon_key(&style.model),
        Arc::new(crate::pedagogy::icon_png(&style.model).to_vec()),
    );
    let t = s
        .doc
        .table_mut(s.sel.focus.story, &path)
        .map_err(|e| e.to_string())?;
    let bg = Rgb(
        style.background[0],
        style.background[1],
        style.background[2],
    );
    let ink = Rgb(style.border[0], style.border[1], style.border[2]);
    t.props.caption = Some(format!("Écrinator · {}", style.model));
    t.props.shading = Some(bg);
    t.props.description = Some(DESIGN.into());
    t.props.corner_radius = Some(style.radius.clamp(0., 16.));
    t.props.borders = Some(borders(ink, style.width));
    if let Some(cell) = t.rows.first_mut().and_then(|r| r.cells.first_mut()) {
        cell.props.shading = Some(bg);
        if let Some(p) = cell.blocks.first_mut() {
            *p = para_block(new_heading);
        }
    }
    s.touch();
    s.relayout();
    Ok(())
}
pub fn move_box(s: &mut Session, down: bool) -> Result<(), String> {
    let path = current_path(s)?;
    let index = path.last();
    let list = s
        .doc
        .container(s.sel.focus.story, &path)
        .ok_or("Encadré absent")?;
    let target = if down {
        index.checked_add(1).filter(|n| *n < list.len())
    } else {
        index.checked_sub(1)
    }
    .ok_or("L’encadré est déjà au bord du document.")?;
    if list
        .get(target)
        .and_then(|b| b.as_table())
        .is_some_and(|t| t.props.caption.as_deref() == Some(crate::core::HEADER))
    {
        return Err("L’encadré reste sous l’en-tête scolaire.".into());
    }
    s.checkpoint("Déplacer l’encadré");
    s.doc
        .container_mut(s.sel.focus.story, &path)
        .map_err(|e| e.to_string())?
        .swap(index, target);
    if let Some(at) = s.sel.focus.path.0.get_mut(path.0.len() - 1) {
        *at = target as u32;
    }
    s.sel.anchor = s.sel.focus.clone();
    s.touch();
    s.relayout();
    Ok(())
}
pub fn insert(s: &mut Session, title: &str) -> Result<(), String> {
    let (a, b) = s.sel.ordered();
    if a.story != b.story {
        return Err("Sélectionnez du texte dans une seule partie du document.".into());
    }
    let fragment = (!s.sel.is_collapsed()).then(|| s.doc.copy_range(&a, &b));
    let snapshot = s.edit_snapshot();
    let result = (|| {
        s.run("insert.table", &json!({"rows":1,"cols":1}))
            .map_err(|e| e.to_string())?;
        s.doc.media.insert(
            crate::pedagogy::icon_key(title),
            Arc::new(crate::pedagogy::icon_png(title).to_vec()),
        );
        let mut path = s.sel.focus.path.0.clone();
        path.truncate(path.len().saturating_sub(3));
        let table = s.doc.container(s.sel.focus.story, &Path(path.clone()));
        let at = Path(path.clone()).last();
        let adjacent = table
            .and_then(|bs| at.checked_sub(1).and_then(|n| bs.get(n)))
            .is_some_and(|b| b.as_table().is_some());
        if adjacent {
            // An ordinary, editable paragraph separates cards in every format.
            let mut gap = text("", 12., false, Rgb(30, 49, 73));
            gap.props.space_before = Some(0.);
            gap.props.space_after = Some(0.);
            gap.props.line_spacing = Some(wordcraft_doc::props::LineSpacing::Multiple(1.));
            s.doc
                .container_mut(s.sel.focus.story, &Path(path.clone()))
                .map_err(|e| e.to_string())?
                .insert(at, para_block(gap));
            if let Some(last) = path.last_mut() {
                *last = last.saturating_add(1);
            }
        }
        let table = s
            .doc
            .table_mut(s.sel.focus.story, &Path(path.clone()))
            .map_err(|e| e.to_string())?;
        let c = color(title);
        let pale = background(title);
        table.props.caption = Some(format!("Écrinator · {title}"));
        table.props.style = None;
        table.props.cell_margins = Some([9., 14., 9., 14.]);
        table.props.shading = Some(pale);
        table.props.description = Some(DESIGN.into());
        table.props.corner_radius = Some(8.);
        table.props.borders = Some(borders(c, 0.65));
        let cell = table
            .rows
            .first_mut()
            .and_then(|r| r.cells.first_mut())
            .ok_or("Encadré vide")?;
        cell.props.shading = Some(pale);
        cell.blocks = vec![para_block(heading(title, title, c)?)];
        if let Some(f) = fragment {
            cell.blocks.extend(f.blocks.into_iter().map(Arc::new));
        } else {
            cell.blocks
                .push(para_block(text("", 12., false, Rgb(30, 49, 73))));
        }
        path.extend([0, 0, 1]);
        s.sel = Selection::caret(Pos::new(a.story, Path(path), 0));
        s.touch();
        s.relayout();
        Ok(())
    })();
    if result.is_err() {
        s.restore(snapshot);
    }
    result
}
pub fn remove_frame(s: &mut Session) -> Result<(), String> {
    let focus = s.sel.focus.clone();
    let mut path = focus.path.0.clone();
    if path.len() < 4 {
        return Err("Placez le curseur dans un encadré.".into());
    }
    path.truncate(path.len() - 3);
    let tp = Path(path);
    let t = s.doc.table(focus.story, &tp).ok_or("Encadré absent")?;
    if t.props
        .caption
        .as_deref()
        .is_none_or(|c| !c.starts_with("Écrinator · ") || c == crate::core::HEADER)
    {
        return Err("Ce tableau n’est pas un encadré pédagogique.".into());
    }
    let content = t
        .rows
        .first()
        .and_then(|r| r.cells.first())
        .map(|c| c.blocks.clone())
        .ok_or("Encadré vide")?;
    s.checkpoint("Retirer le cadre");
    let container = s
        .doc
        .container_mut(focus.story, &tp)
        .map_err(|e| e.to_string())?;
    let at = tp.last();
    container.splice(at..at + 1, content);
    s.sel = Selection::caret(Pos::new(focus.story, tp, 0));
    s.touch();
    s.relayout();
    Ok(())
}
/// Upgrade only our own older blocks; retain every body block and custom colour.
/// One undo step, and no disk write: the pupil chooses whether to save the result.
pub fn modernize(s: &mut Session) -> Result<usize, String> {
    fn find(blocks: &wordcraft_doc::Blocks, prefix: &[u32], paths: &mut Vec<Path>, depth: usize) {
        if depth > 16 {
            return;
        }
        for (i, b) in blocks.iter().enumerate() {
            let Some(t) = b.as_table() else { continue };
            let mut p = prefix.to_vec();
            p.push(i as u32);
            if t.props
                .caption
                .as_deref()
                .and_then(|c| c.strip_prefix("Écrinator · "))
                .is_some_and(|m| TEMPLATES.contains(&m))
                && t.props.description.as_deref() != Some(DESIGN)
            {
                paths.push(Path(p.clone()));
            }
            for (r, row) in t.rows.iter().enumerate() {
                for (c, cell) in row.cells.iter().enumerate() {
                    let mut at = p.clone();
                    at.extend([r as u32, c as u32]);
                    find(&cell.blocks, &at, paths, depth + 1);
                }
            }
        }
    }
    let mut paths = Vec::new();
    find(&s.doc.body, &[], &mut paths, 0);
    if paths.is_empty() {
        return Ok(0);
    }
    let snapshot = s.edit_snapshot();
    s.checkpoint("Moderniser les encadrés");
    let result = (|| {
        for path in &paths {
            let t = s
                .doc
                .table(wordcraft_doc::StoryRef::Body, path)
                .ok_or("Encadré absent")?;
            let model = t
                .props
                .caption
                .as_deref()
                .unwrap_or("")
                .trim_start_matches("Écrinator · ")
                .to_string();
            let title = t
                .rows
                .first()
                .and_then(|r| r.cells.first())
                .and_then(|c| c.blocks.first())
                .and_then(|b| b.as_para())
                .map(title_text)
                .unwrap_or_else(|| model.clone());
            let old_ink = match model.as_str() {
                "Définition" | "Vocabulaire" => Rgb(169, 100, 0),
                "Attention" => Rgb(182, 48, 48),
                "À retenir" | "Théorème" => Rgb(104, 56, 176),
                "Propriété" | "Observation" | "Conclusion" => Rgb(22, 119, 103),
                _ => Rgb(46, 99, 174),
            };
            let old_bg = match model.as_str() {
                "Définition" | "Vocabulaire" => Rgb(255, 248, 225),
                "À retenir" | "Théorème" => Rgb(243, 236, 255),
                "Attention" => Rgb(255, 238, 238),
                "Propriété" | "Observation" | "Conclusion" => Rgb(232, 248, 240),
                _ => Rgb(237, 246, 255),
            };
            let ink = t
                .props
                .borders
                .and_then(|b| b.left)
                .and_then(|b| b.color)
                .filter(|c| *c != old_ink)
                .unwrap_or(color(&model));
            let bg = t
                .props
                .shading
                .filter(|c| *c != old_bg)
                .unwrap_or(background(&model));
            let title = heading(&title, &model, ink)?;
            s.doc.media.insert(
                crate::pedagogy::icon_key(&model),
                Arc::new(crate::pedagogy::icon_png(&model).to_vec()),
            );
            let t = s
                .doc
                .table_mut(wordcraft_doc::StoryRef::Body, path)
                .map_err(|e| e.to_string())?;
            t.props.description = Some(DESIGN.into());
            t.props.corner_radius = Some(8.);
            t.props.style = None;
            t.props.cell_margins = Some([9., 14., 9., 14.]);
            t.props.shading = Some(bg);
            t.props.borders = Some(borders(ink, 0.65));
            if let Some(cell) = t.rows.first_mut().and_then(|r| r.cells.first_mut()) {
                cell.props.shading = Some(bg);
                if let Some(first) = cell.blocks.first_mut() {
                    *first = para_block(title);
                }
            }
        }
        s.touch();
        s.relayout();
        Ok(paths.len())
    })();
    if result.is_err() {
        s.restore(snapshot);
    }
    result
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn selection_box_edit_undo() {
        let mut s = Session::new(wordcraft_doc::Document::new());
        s.run("text.insert", &json!({"text":"Définition avec accents"}))
            .unwrap();
        s.sel = Selection {
            anchor: Pos::body(0, 0),
            focus: Pos::body(0, "Définition avec accents".len()),
        };
        let before = s.doc.clone();
        insert(&mut s, "Définition").unwrap();
        assert!(
            s.doc
                .plain_text(a_story())
                .contains("Définition avec accents")
        );
        s.run("text.insert", &json!({"text":"Ajout "})).unwrap();
        assert!(s.doc.plain_text(a_story()).contains("Ajout"));
        s.undo();
        s.undo();
        assert_eq!(s.doc, before);
    }
    fn a_story() -> wordcraft_doc::StoryRef {
        wordcraft_doc::StoryRef::Body
    }
}
