//! School metadata lives in the document, so undo and native saves preserve it together.
use chrono::Local;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use wordcraft_doc::props::{Border, Borders, LineSpacing, Rgb, TextColor};
use wordcraft_doc::{
    Block, CharProps, CustomProp, Document, InlineObject, Paragraph, Table, para_block,
};
use wordcraft_engine::Session;

pub const NATIVE_VERSION: u32 = 1;
pub const SUBJECTS: &[&str] = &[
    "Page blanche",
    "Français",
    "Mathématiques",
    "Histoire-géographie",
    "EMC",
    "Anglais",
    "Espagnol",
    "Allemand",
    "SVT",
    "Physique-chimie",
    "Technologie",
    "Arts plastiques",
    "Éducation musicale",
    "Autre matière",
];
const META: &str = "Ergonatus.Ecrinator.School.v1";
pub const HEADER: &str = "Écrinator · en-tête scolaire";
pub const CHAPTER: &str = "EcrChapter";
pub const BANNER_CHAPTER: &str = "EcrBannerChapter";
pub const BANNER_VERSION: &str = "Écrinator · bandeau protégé v11";
pub const BANNER_HEIGHT: f32 = 100.;
pub const WORK_GROUP: &str = "ecr.work-kind";
pub const BANNER_TITLE: &str = "EcrBannerTitle";
pub const BLANK: &str = "Page blanche";
/// Structured teaching objects belong to the writing area, outside the fixed banner.
pub fn ensure_writing_selection(s: &Session) -> Result<(), String> {
    for pos in [&s.sel.anchor, &s.sel.focus] {
        let mut path = pos.path.0.clone();
        while path.len() >= 4 {
            path.truncate(path.len() - 3);
            if s.doc
                .table(pos.story, &wordcraft_doc::Path(path.clone()))
                .is_some_and(|t| t.props.geometry_locked)
            {
                return Err("Placez le curseur dans la page, sous le bandeau.".into());
            }
        }
    }
    Ok(())
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WorkKind {
    Lesson,
    Exercises,
    Assessment,
}
impl WorkKind {
    pub const ALL: [Self; 3] = [Self::Lesson, Self::Exercises, Self::Assessment];
    pub fn label(self) -> &'static str {
        match self {
            Self::Lesson => "Leçon",
            Self::Exercises => "Exercices",
            Self::Assessment => "Évaluation",
        }
    }
    pub fn folder(self) -> &'static str {
        match self {
            Self::Lesson => "Cours",
            Self::Exercises => "Exercices",
            Self::Assessment => "Évaluations",
        }
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct School {
    pub subject: String,
    pub date: String,
    pub time: String,
    pub chapter: u32,
    pub title: String,
    pub lesson: bool,
    pub exercises: bool,
    pub assessment: bool,
    pub show_date: bool,
    pub show_time: bool,
    pub show_banner: bool,
}
impl Default for School {
    fn default() -> Self {
        let now = Local::now();
        Self {
            subject: "Français".into(),
            date: now.format("%d/%m/%Y").to_string(),
            time: now.format("%H:%M").to_string(),
            chapter: 1,
            title: String::new(),
            lesson: true,
            exercises: false,
            assessment: false,
            show_date: true,
            show_time: true,
            show_banner: true,
        }
    }
}
impl School {
    /// A distinct, quiet background derived from the subject's identity colour.
    pub fn banner_background(&self) -> Rgb {
        let c = self.color();
        let pale = |v: u8| ((v as u16 * 14 + 255 * 86) / 100) as u8;
        Rgb(pale(c.0), pale(c.1), pale(c.2))
    }
    pub fn banner_visible(&self) -> bool {
        self.show_banner && self.subject != BLANK
    }
    /// Legacy multiple selections retain the previous routing priority.
    pub fn work_kind(&self) -> WorkKind {
        if self.assessment {
            WorkKind::Assessment
        } else if self.exercises {
            WorkKind::Exercises
        } else {
            WorkKind::Lesson
        }
    }
    pub fn set_work_kind(&mut self, kind: WorkKind) {
        self.lesson = kind == WorkKind::Lesson;
        self.exercises = kind == WorkKind::Exercises;
        self.assessment = kind == WorkKind::Assessment;
    }
    pub fn normalized(&self) -> Self {
        let mut school = self.clone();
        school.set_work_kind(self.work_kind());
        school
    }
    pub fn folder_kind(&self) -> &'static str {
        self.work_kind().folder()
    }
    pub fn color(&self) -> Rgb {
        match self.subject.as_str() {
            "Français" => Rgb(165, 62, 88),
            "Mathématiques" => Rgb(43, 93, 196),
            "Histoire-géographie" => Rgb(153, 98, 32),
            "SVT" => Rgb(31, 119, 74),
            "Physique-chimie" => Rgb(9, 119, 143),
            "Arts plastiques" => Rgb(153, 69, 163),
            "Éducation musicale" => Rgb(105, 65, 168),
            "Anglais" => Rgb(74, 84, 160),
            "Espagnol" => Rgb(178, 81, 55),
            "Allemand" => Rgb(153, 112, 35),
            "EMC" => Rgb(34, 119, 120),
            "Technologie" => Rgb(45, 103, 140),
            _ => Rgb(67, 94, 139),
        }
    }
    pub fn read(doc: &Document) -> Self {
        let mut school: Self = doc
            .custom_props
            .iter()
            .find(|p| p.name == META)
            .and_then(|p| serde_json::from_str(&p.value).ok())
            .unwrap_or_else(|| Self {
                subject: BLANK.into(),
                show_banner: false,
                ..Default::default()
            });
        for range in doc.control_ranges(wordcraft_doc::StoryRef::Body) {
            if range.control.tag == "ecr.chapter" {
                if let Ok(number) = doc.control_text(&range).trim().parse::<u32>() {
                    school.chapter = number;
                }
            }

            if let wordcraft_doc::ControlKind::CheckBox { checked, .. } = range.control.kind {
                match range.control.tag.as_str() {
                    "ecr.lesson" => school.lesson = checked,
                    "ecr.exercises" => school.exercises = checked,
                    "ecr.assessment" => school.assessment = checked,
                    _ => {}
                }
            }
        }
        if let Some(table) = doc
            .body
            .iter()
            .filter_map(|b| b.as_table())
            .find(|t| t.props.caption.as_deref() == Some(HEADER))
        {
            if let Some(cell) = table.rows.first().and_then(|r| r.cells.get(1)) {
                if let Some(p) = cell.blocks.first().and_then(|b| b.as_para()) {
                    school.subject = p.plain_text();
                }
                for p in cell.blocks.iter().filter_map(|b| b.as_para()) {
                    if p.props.style.as_deref() == Some(BANNER_TITLE) {
                        school.title = p.plain_text();
                    }
                    if p.props.style.as_deref() == Some(BANNER_CHAPTER) {
                        let t = p.plain_text();
                        if let Some((number, title)) = t
                            .strip_prefix("Chapitre ")
                            .and_then(|t| t.split_once(" · "))
                        {
                            if let Ok(n) = number.trim().parse() {
                                school.chapter = n;
                                school.title = title.into();
                            }
                        }
                    }
                }
            }
        }
        if let Some(p) = doc
            .body
            .iter()
            .filter_map(|b| b.as_para())
            .find(|p| p.props.style.as_deref() == Some(CHAPTER))
        {
            let title = p.plain_text();
            if let Some((n, title)) = title.split_once(". ") {
                if let Ok(chapter) = n.parse::<u32>() {
                    school.chapter = chapter;
                    school.title = title.into();
                }
            }
        }
        school.normalized()
    }
    pub fn present(doc: &Document) -> bool {
        doc.custom_props.iter().any(|p| p.name == META)
    }
    pub fn write(&self, doc: &mut Document) -> Result<(), String> {
        let value = serde_json::to_string(&self.normalized()).map_err(|e| e.to_string())?;
        doc.custom_props.retain(|p| p.name != META);
        doc.custom_props.push(CustomProp {
            name: META.into(),
            kind: "lpwstr".into(),
            value,
        });
        doc.core.title = if self.subject == BLANK {
            "Document".into()
        } else if self.title.trim().is_empty() {
            format!("Chapitre {}", self.chapter)
        } else {
            format!("Chapitre {} — {}", self.chapter, self.title)
        };
        doc.core.subject = self.subject.clone();
        Ok(())
    }
}
pub fn text(s: &str, size: f32, bold: bool, color: Rgb) -> Paragraph {
    let mut p = Paragraph::with_text(
        s,
        CharProps {
            font: Some("Arial".into()),
            size: Some(size),
            bold: Some(bold),
            color: Some(TextColor::Rgb(color)),
            ..Default::default()
        },
    );
    p.props.space_after = Some(6.0);
    p.props.line_spacing = Some(LineSpacing::Multiple(1.25));
    p
}
fn header(s: &School, width: f32) -> Result<Table, String> {
    let s = s.normalized();
    let mut table = Table::new(1, 3, width);
    let art_width = 222_f32.min(width * 0.38);
    let kind_width = 125_f32.min(width * 0.23);
    table.grid = vec![art_width, width - art_width - kind_width, kind_width];
    table.props.geometry_locked = true;
    table.props.content_locked = true;
    table.props.style = None;
    table.props.caption = Some(HEADER.into());
    table.props.fixed = true;
    table.props.description = Some(BANNER_VERSION.into());
    table.props.cell_margins = Some([8., 12., 8., 12.]);
    table.props.corner_radius = Some(8.);
    table.props.surface_inset = Some([0.; 4]);
    let art = crate::subjects::for_subject(&s.subject);
    table.props.background_media = Some(crate::subjects::background_key(&s.subject));
    table.props.background_alpha = Some(1.);
    table.props.background_wash = Some(0.88);
    table.props.background_crop = Some(crate::subjects::background_crop(
        art.background,
        width,
        BANNER_HEIGHT,
    ));
    table.props.float = Some(wordcraft_doc::props::TableFloat {
        h_rel: wordcraft_doc::para::Anchor::Page,
        v_rel: wordcraft_doc::para::Anchor::Page,
        h_align: Some(wordcraft_doc::para::FloatAlign::Start),
        x: 0.,
        y: 0.,
        dist: [0., 0., 0., 12.],
        overlap: false,
        ..Default::default()
    });
    let c = s.color();
    let bg = s.banner_background();
    table.props.shading = Some(bg);
    let border = Border {
        color: Some(crate::pedagogy::outline(c)),
        ..Border::single(0.35)
    };
    let mut borders = Borders::box_(border);
    borders.left = Some(Border {
        color: Some(bg),
        ..Border::single(0.35)
    });
    borders.inside_v = Some(Border::default());
    borders.between = Some(Border::default());
    table.props.borders = Some(borders);
    let row = table.rows.first_mut().ok_or("En-tête vide")?;
    row.props.cant_split = true;
    // Row height excludes the 8-point top and bottom cell padding.
    row.props.height = Some(BANNER_HEIGHT - 16.);
    row.props.height_rule = wordcraft_doc::props::HeightRule::AtLeast;
    for (i, cell) in row.cells.iter_mut().enumerate() {
        cell.props.width = table.grid.get(i).copied();
        cell.props.shading = Some(bg);
        cell.props.valign = Some(wordcraft_doc::props::VAlign::Center);
    }
    if let Some(cell) = row.cells.get_mut(0) {
        cell.blocks = vec![para_block(text("", 12., false, c))];
    }
    if let Some(cell) = row.cells.get_mut(1) {
        let date = [
            s.show_date.then_some(s.date.clone()),
            s.show_time.then_some(s.time.clone()),
        ]
        .into_iter()
        .flatten()
        .collect::<Vec<_>>()
        .join("  ·  ");
        let mut subject = text(&s.subject, 17., true, c);
        subject
            .format(0, subject.text.len(), &|p| {
                p.font = Some("Noto Serif".into());
                p.italic = Some(true);
            })
            .map_err(|e| e.to_string())?;
        subject.props.space_after = Some(3.);
        subject.props.line_spacing = Some(LineSpacing::Multiple(1.05));
        let prefix = "Chapitre : ";
        let value = s.chapter.to_string();
        let mut chapter = text(&format!("{prefix}{value}"), 11., false, Rgb(30, 49, 73));
        let mut items: Vec<_> = (1..=99)
            .map(|n| wordcraft_doc::control::ListItem {
                display: n.to_string(),
                value: n.to_string(),
            })
            .collect();
        if s.chapter > 99 {
            items.push(wordcraft_doc::control::ListItem {
                display: value.clone(),
                value: value.clone(),
            });
        }
        let ctl = wordcraft_doc::ContentControl {
            tag: "ecr.chapter".into(),
            title: "Numéro du chapitre".into(),
            kind: wordcraft_doc::ControlKind::DropDown {
                items,
                last_value: value,
            },
            ..Default::default()
        };
        chapter
            .format(prefix.len(), chapter.text.len(), &|p| {
                p.bold = Some(true);
                p.color = Some(TextColor::Rgb(c));
            })
            .map_err(|e| e.to_string())?;
        chapter
            .insert_object(
                chapter.text.len(),
                InlineObject::ControlEnd,
                &CharProps::default(),
            )
            .map_err(|e| e.to_string())?;
        chapter
            .insert_object(
                prefix.len(),
                InlineObject::ControlStart {
                    control: Box::new(ctl),
                },
                &CharProps::default(),
            )
            .map_err(|e| e.to_string())?;
        chapter.props.style = Some(BANNER_CHAPTER.into());
        chapter.props.space_after = Some(3.);
        chapter.props.line_spacing = Some(LineSpacing::Multiple(1.1));
        let mut stamp = text(&date, 8.5, false, Rgb(88, 103, 122));
        stamp.props.space_after = Some(0.);
        stamp.props.line_spacing = Some(LineSpacing::Multiple(1.));
        let mut title = text(&s.title, 13., true, Rgb(30, 49, 73));
        title.props.style = Some(BANNER_TITLE.into());
        title.props.space_after = Some(3.);
        title.props.line_spacing = Some(LineSpacing::Multiple(1.05));
        cell.blocks = vec![
            para_block(subject),
            para_block(title),
            para_block(chapter),
            para_block(stamp),
        ];
    }
    if let Some(cell) = row.cells.get_mut(2) {
        cell.blocks = [
            (s.lesson, "Leçon", "ecr.lesson"),
            (s.exercises, "Exercices", "ecr.exercises"),
            (s.assessment, "Évaluation", "ecr.assessment"),
        ]
        .into_iter()
        .map(|(on, label, tag)| {
            let mut p = text(
                &format!("{} {}", if on { "☑" } else { "☐" }, label),
                9.5,
                false,
                Rgb(30, 49, 73),
            );
            p.format(0, '☑'.len_utf8(), &|p| {
                p.size = Some(12.);
                p.color = Some(TextColor::Rgb(c));
            })
            .map_err(|e| e.to_string())?;
            p.props.space_after = Some(4.);
            p.props.line_spacing = Some(LineSpacing::Multiple(1.05));
            let ctl = wordcraft_doc::ContentControl {
                tag: tag.into(),
                title: label.into(),
                exclusive_group: WORK_GROUP.into(),
                kind: wordcraft_doc::ControlKind::CheckBox {
                    checked: on,
                    checked_char: '☑',
                    checked_font: "Arial".into(),
                    unchecked_char: '☐',
                    unchecked_font: "Arial".into(),
                },
                ..Default::default()
            };
            p.insert_object(
                '☑'.len_utf8(),
                InlineObject::ControlEnd,
                &CharProps::default(),
            )
            .map_err(|e| e.to_string())?;
            p.insert_object(
                0,
                InlineObject::ControlStart {
                    control: Box::new(ctl),
                },
                &CharProps::default(),
            )
            .map_err(|e| e.to_string())?;
            Ok(para_block(p))
        })
        .collect::<Result<Vec<_>, String>>()?;
    }
    Ok(table)
}
fn add_art(doc: &mut Document, s: &School) {
    let art = crate::subjects::for_subject(&s.subject);
    doc.media
        .entry(crate::subjects::background_key(&s.subject))
        .or_insert_with(|| Arc::new(art.background.to_vec()));
}
/// First editable body paragraph, independent of whether a banner exists.
pub fn writing_position(doc: &Document) -> wordcraft_doc::Pos {
    let index = doc
        .body
        .iter()
        .position(|b| {
            b.as_para()
                .is_some_and(|p| p.props.style.as_deref() != Some(CHAPTER))
        })
        .unwrap_or(0);
    wordcraft_doc::Pos::body(index, 0)
}
pub fn needs_banner_refresh(doc: &Document) -> bool {
    School::present(doc)
        && School::read(doc).banner_visible()
        && !doc.body.iter().filter_map(|b| b.as_table()).any(|t| {
            t.props.caption.as_deref() == Some(HEADER)
                && t.props.description.as_deref() == Some(BANNER_VERSION)
                && t.props.geometry_locked
                && t.props.content_locked
                && {
                    let controls: Vec<_> = t
                        .rows
                        .iter()
                        .flat_map(|r| &r.cells)
                        .flat_map(|c| &c.blocks)
                        .filter_map(|b| b.as_para())
                        .flat_map(|p| &p.objects)
                        .filter_map(|o| match o {
                            InlineObject::ControlStart { control }
                                if control.exclusive_group == WORK_GROUP =>
                            {
                                Some(control)
                            }
                            _ => None,
                        })
                        .collect();
                    controls.len() == 3
                        && controls
                            .iter()
                            .filter(|c| {
                                matches!(
                                    c.kind,
                                    wordcraft_doc::ControlKind::CheckBox { checked: true, .. }
                                )
                            })
                            .count()
                            == 1
                }
        })
}
/// Clear the whole paragraph at a caret, so direct font/colour/shading from an
/// old school title really disappears. A nonempty selection stays a selection.
pub fn clear_formatting(s: &mut Session) -> Result<(), String> {
    let caret = s.sel.is_collapsed().then(|| s.sel.focus.clone());
    if let Some(pos) = &caret {
        if let Some(p) = s.doc.para_at(pos) {
            let mut start = pos.clone();
            start.off = 0;
            let mut end = pos.clone();
            end.off = p.text.len();
            s.sel = wordcraft_engine::Selection {
                anchor: start,
                focus: end,
            };
        }
    }
    let result = s
        .run("format.clear", &serde_json::json!({}))
        .map(|_| ())
        .map_err(|e| e.to_string());
    if let Some(pos) = caret {
        s.sel = wordcraft_engine::Selection::caret(pos);
    }
    result
}
pub fn new_document(s: &School) -> Result<Document, String> {
    let mut doc = Document::new();
    doc.last_section.page_w = 595.276;
    doc.last_section.page_h = 841.89;
    doc.last_section.margin_left = 51.023;
    doc.last_section.margin_right = 51.023;
    doc.last_section.margin_top = 42.52;
    doc.last_section.margin_bottom = 42.52;
    doc.styles.default_chr.font = Some("Arial".into());
    doc.styles.default_chr.size = Some(12.);
    let mut body = text("", 12., false, Rgb(30, 49, 73));
    if s.banner_visible() {
        body.props.space_before = Some(8.);
    }
    doc.body = vec![para_block(body)];
    if s.banner_visible() {
        doc.body.insert(
            0,
            Arc::new(Block::Table(header(s, doc.last_section.page_w)?)),
        );
        add_art(&mut doc, s);
    }
    s.write(&mut doc)?;
    doc.core.created = Local::now().to_rfc3339();
    doc.core.creator = "Écrinator — Ergonatus".into();
    Ok(doc)
}
pub fn update_header(session: &mut Session, s: &School) -> Result<(), String> {
    let replacement = if s.banner_visible() {
        Some(header(
            s,
            session
                .doc
                .sections()
                .first()
                .map(|(_, p)| p.page_w)
                .unwrap_or(595.276),
        )?)
    } else {
        None
    };
    let old_sel = session.sel.clone();
    let root_block = |p: &wordcraft_doc::Pos| {
        session
            .doc
            .body
            .get(p.path.0.first().copied().unwrap_or(0) as usize)
            .cloned()
    };
    let anchor = root_block(&old_sel.anchor);
    let focus = root_block(&old_sel.focus);
    session.checkpoint("Modifier l’en-tête scolaire");
    session.doc.body.retain(|b| {
        !b.as_table()
            .is_some_and(|t| t.props.caption.as_deref() == Some(HEADER))
    });
    if let Some(table) = replacement {
        // In 0.3 the chapter was an imposed body heading. Its exact text has
        // already been read into School and now belongs inside the banner.
        session.doc.body.retain(|b| {
            !b.as_para()
                .is_some_and(|p| p.props.style.as_deref() == Some(CHAPTER))
        });
        session.doc.body.insert(0, Arc::new(Block::Table(table)));
        add_art(&mut session.doc, s);
    } else {
        for b in &mut session.doc.body {
            if let Some(p) = b
                .as_para()
                .filter(|p| p.props.style.as_deref() == Some(CHAPTER))
            {
                *b = para_block(text(&p.plain_text(), 12., false, Rgb(30, 49, 73)));
            }
        }
    }
    if !session.doc.body.iter().any(|b| b.as_para().is_some()) {
        session
            .doc
            .body
            .push(para_block(text("", 12., false, Rgb(30, 49, 73))));
    }
    s.write(&mut session.doc)?;
    let rebase = |old: &wordcraft_doc::Pos, block: Option<Arc<Block>>| {
        if old.story == wordcraft_doc::StoryRef::Body {
            if let Some(index) =
                block.and_then(|b| session.doc.body.iter().position(|n| Arc::ptr_eq(n, &b)))
            {
                let mut pos = old.clone();
                if let Some(first) = pos.path.0.first_mut() {
                    *first = index as u32;
                }
                return pos;
            }
            return writing_position(&session.doc);
        }
        old.clone()
    };
    session.sel = wordcraft_engine::Selection {
        anchor: rebase(&old_sel.anchor, anchor),
        focus: rebase(&old_sel.focus, focus),
    };
    session.touch();
    session.relayout();
    Ok(())
}
