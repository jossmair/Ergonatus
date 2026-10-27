//! Editable school tables. Operations are annotations, never automatic answers.
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use wordcraft_doc::{
    Block, InlineObject, Paragraph, Path, Pos, Table,
    graphic::{Graphic, GraphicItem, GraphicKind, PathSeg, TextAlign},
    para::{Float, ShapeKind},
    para_block,
    props::{Align, Border, Borders, HeightRule, Rgb, VAlign},
};
use wordcraft_engine::{Selection, Session};

const PREFIX: &str = "ecrinator-math-table-v1:";
const INK: Rgb = Rgb(30, 49, 73);
const BLUE: Rgb = Rgb(40, 99, 206);

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub enum ColumnLink {
    Operation {
        from: usize,
        to: usize,
        label: String,
    },
    Sum {
        first: usize,
        second: usize,
        to: usize,
    },
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Proportion {
    pub values: Vec<Vec<String>>,
    pub links: Vec<ColumnLink>,
    pub row_operation: String,
    #[serde(default)]
    pub row_reverse: bool,
    pub width: f32,
    pub row_height: f32,
    pub font_size: f32,
}
impl Default for Proportion {
    fn default() -> Self {
        Self {
            values: vec![vec![String::new(); 4]; 2],
            links: vec![],
            row_operation: String::new(),
            row_reverse: false,
            width: 450.,
            row_height: 36.,
            font_size: 14.,
        }
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct UnitGroup {
    pub label: String,
    pub places: usize,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Conversion {
    pub family: String,
    pub units: Vec<UnitGroup>,
    pub values: Vec<Vec<String>>,
    pub width: f32,
    pub row_height: f32,
    pub font_size: f32,
    pub capacities: bool,
}
pub const FAMILIES: &[&str] = &[
    "Longueur",
    "Aire",
    "Volume",
    "Volume et contenance",
    "Contenance",
    "Masse",
    "Durée",
    "Énergie",
    "Puissance",
    "Tension",
    "Intensité",
    "Fréquence",
    "Pression",
    "Personnalisé",
];
impl Default for Conversion {
    fn default() -> Self {
        Self::preset("Longueur")
    }
}
impl Conversion {
    pub fn preset(family: &str) -> Self {
        let (names, places): (&[&str], usize) = match family {
            "Aire" => (&["km²", "hm²", "dam²", "m²", "dm²", "cm²", "mm²"], 2),
            "Volume" => (&["km³", "hm³", "dam³", "m³", "dm³", "cm³", "mm³"], 3),
            "Volume et contenance" => (&["m³", "dm³", "cm³", "mm³"], 3),
            "Contenance" => (&["kL", "hL", "daL", "L", "dL", "cL", "mL"], 1),
            "Masse" => (
                &[
                    "t", "100 kg", "10 kg", "kg", "hg", "dag", "g", "dg", "cg", "mg",
                ],
                1,
            ),
            "Durée" => (&["j", "h", "min", "s"], 1),
            "Énergie" => (&["MJ", "kJ", "J", "mJ"], 3),
            "Puissance" => (&["MW", "kW", "W", "mW"], 3),
            "Tension" => (&["kV", "V", "mV"], 3),
            "Intensité" => (&["A", "mA", "µA"], 3),
            "Fréquence" => (&["MHz", "kHz", "Hz"], 3),
            "Pression" => (&["bar", "hPa", "Pa"], 1),
            "Personnalisé" => (&["Unité 1", "Unité 2", "Unité 3"], 1),
            _ => (&["km", "hm", "dam", "m", "dm", "cm", "mm"], 1),
        };
        let mut units: Vec<_> = names
            .iter()
            .map(|s| UnitGroup {
                label: (*s).into(),
                places,
            })
            .collect();
        if family == "Pression" {
            units[1].places = 3;
            units[2].places = 2;
        }
        let cols = units.iter().map(|u| u.places).sum();
        Self {
            family: family.into(),
            units,
            values: vec![vec![String::new(); cols]; 4],
            width: 450.,
            row_height: 30.,
            font_size: 14.,
            capacities: family == "Volume et contenance",
        }
    }
    pub fn columns(&self) -> usize {
        self.units.iter().map(|u| u.places).sum()
    }
    pub fn header_rows(&self) -> usize {
        if self.capacities || self.units.iter().any(|u| u.places > 1) {
            2
        } else {
            1
        }
    }
    pub fn resize_rows(&mut self, rows: usize) {
        let cols = self.columns();
        self.values.resize_with(rows, || vec![String::new(); cols]);
        for row in &mut self.values {
            row.resize(cols, String::new());
        }
    }
    pub fn hint(&self) -> &str {
        if self.family == "Durée" {
            "Les durées ne sont pas décimales : 1 j = 24 h, 1 h = 60 min, 1 min = 60 s."
        } else {
            "Un chiffre par case. Le tableau ne calcule et ne complète aucune réponse."
        }
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub enum Model {
    Proportion(Proportion),
    Conversion(Conversion),
}

fn dimensions(width: f32, height: f32, size: f32) -> Result<(), String> {
    if !width.is_finite()
        || !(100. ..=1100.).contains(&width)
        || !height.is_finite()
        || !(24. ..=90.).contains(&height)
        || !size.is_finite()
        || !(10. ..=26.).contains(&size)
    {
        return Err("Choisis une taille lisible : largeur de 4 à 38 cm, lignes de 24 à 90 points et texte de 10 à 26 points.".into());
    }
    if height < size * 1.5 {
        return Err("Augmente la hauteur des cases pour conserver la taille du texte.".into());
    }
    Ok(())
}
impl Model {
    pub fn width(&self) -> f32 {
        match self {
            Self::Proportion(p) => p.width,
            Self::Conversion(c) => c.width,
        }
    }
    pub fn validate(&self) -> Result<(), String> {
        match self {
            Self::Proportion(p) => {
                dimensions(p.width, p.row_height, p.font_size)?;
                if p.values.len() != 2
                    || !(2..=12).contains(&p.values[0].len())
                    || p.values[1].len() != p.values[0].len()
                    || p.links.len() > 6
                    || p.row_operation.chars().count() > 10
                {
                    return Err("Deux lignes, 2 à 12 colonnes et 6 bulles maximum.".into());
                }
                let n = p.values[0].len();
                for link in &p.links {
                    match link {
                        ColumnLink::Operation { from, to, label }
                            if *from < n
                                && *to < n
                                && from != to
                                && !label.trim().is_empty()
                                && label.chars().count() <= 10 => {}
                        ColumnLink::Sum { first, second, to }
                            if *first < n
                                && *second < n
                                && *to < n
                                && first != second
                                && first != to
                                && second != to => {}
                        _ => {
                            return Err(
                                "Vérifie les colonnes de départ et d’arrivée de chaque bulle."
                                    .into(),
                            );
                        }
                    }
                }
                let cell = (p.width
                    - if p.row_operation.trim().is_empty() {
                        0.
                    } else {
                        82.
                    })
                    / n as f32;
                if cell < 42. {
                    return Err(
                        "Élargis le tableau ou passe en paysage pour conserver des cases lisibles."
                            .into(),
                    );
                }
                for value in p.values.iter().flatten() {
                    if value.chars().count() > 24
                        || value.chars().count() as f32 * p.font_size * 0.58 > cell - 8.
                    {
                        return Err("Une valeur dépasse la largeur de sa case. Élargis le tableau sans réduire le texte.".into());
                    }
                }
            }
            Self::Conversion(c) => {
                dimensions(c.width, c.row_height, c.font_size)?;
                if !(2..=16).contains(&c.units.len())
                    || c.units.iter().any(|u| {
                        u.label.trim().is_empty()
                            || u.label.chars().count() > 12
                            || !(1..=3).contains(&u.places)
                    })
                    || !(1..=64).contains(&c.values.len())
                    || c.columns() > 48
                {
                    return Err(
                        "Choisis 2 à 16 unités, 1 à 3 cases par unité et 1 à 64 lignes.".into(),
                    );
                }
                if c.values.iter().any(|r| {
                    r.len() != c.columns()
                        || r.iter().any(|v| {
                            v.chars().count() > 1
                                || v.chars().any(|ch| {
                                    !ch.is_ascii_digit()
                                        && !matches!(ch, ',' | '.' | '−' | '-' | '+' | ' ')
                                })
                        })
                }) {
                    return Err(
                        "Le tableau de conversion accueille un chiffre ou une virgule par case."
                            .into(),
                    );
                }
                if (c.width / c.columns() as f32) < c.font_size * 0.7 + 8. {
                    return Err("Le tableau est trop étroit. Augmente sa largeur ou passe en paysage ; la police ne sera pas réduite.".into());
                }
                if c.capacities
                    && (c.units.iter().map(|u| u.label.as_str()).collect::<Vec<_>>()
                        != ["m³", "dm³", "cm³", "mm³"]
                        || c.units.iter().any(|u| u.places != 3))
                {
                    return Err("L’équivalence volume/contenance nécessite les groupes m³, dm³, cm³, mm³ à trois cases.".into());
                }
            }
        }
        Ok(())
    }
    pub fn table(&self) -> Result<Table, String> {
        self.validate()?;
        let mut table = match self {
            Self::Proportion(p) => proportion_table(p),
            Self::Conversion(c) => conversion_table(c),
        };
        table.props.caption = Some(
            match self {
                Self::Proportion(_) => "Tableau de proportionnalité",
                Self::Conversion(_) => "Tableau de conversion",
            }
            .into(),
        );
        table.props.description = Some(format!(
            "{PREFIX}{}",
            serde_json::to_string(self).map_err(|e| e.to_string())?
        ));
        Ok(table)
    }
}
fn blank_table(rows: usize, cols: usize, width: f32, height: f32, size: f32) -> Table {
    let mut t = Table::new(rows, cols, width);
    t.props.style = None;
    t.props.fixed = true;
    t.props.geometry_locked = false;
    t.props.width = Some(width);
    t.props.cell_margins = Some([0.; 4]);
    for row in &mut t.rows {
        row.props.height = Some(height);
        row.props.height_rule = HeightRule::AtLeast;
        row.props.cant_split = true;
        for cell in &mut row.cells {
            cell.props.valign = Some(VAlign::Center);
            cell.props.margins = Some([0.; 4]);
            let mut border = Border::single(0.7);
            border.color = Some(Rgb(150, 170, 197));
            cell.props.borders = Some(Borders::all(border));
            cell.blocks = vec![para_block(cell_text("", size, false))];
        }
    }
    t
}
fn cell_text(s: &str, size: f32, bold: bool) -> Paragraph {
    let mut p = crate::core::text(s, size, bold, INK);
    p.props.align = Some(Align::Center);
    p.props.space_before = Some(0.);
    p.props.space_after = Some(0.);
    p
}
fn conversion_table(c: &Conversion) -> Table {
    let columns = c.columns();
    let headers = c.header_rows();
    let mut t = blank_table(
        c.values.len() + headers,
        columns,
        c.width,
        c.row_height,
        c.font_size,
    );
    let prototype = t.rows[0].cells[0].clone();
    t.rows[0].cells.clear();
    for unit in &c.units {
        let mut cell = prototype.clone();
        cell.props.span = unit.places as u32;
        cell.props.shading = Some(Rgb(230, 240, 254));
        cell.blocks = vec![para_block(cell_text(&unit.label, 12., true))];
        t.rows[0].cells.push(cell);
    }
    t.rows[0].props.header = true;
    if headers == 2 {
        t.rows[1].props.header = true;
    }
    let capacities = ["", "", "kL", "hL", "daL", "L", "dL", "cL", "mL", "", "", ""];
    let mut at = 0;
    for (group, unit) in c.units.iter().enumerate() {
        for place in 0..unit.places {
            let caption = if c.capacities {
                capacities[at]
            } else {
                match (unit.places, place) {
                    (3, 0) => "c",
                    (3, 1) | (2, 0) => "d",
                    _ => "u",
                }
            };
            if headers == 2 {
                t.rows[1].cells[at].blocks = vec![para_block(cell_text(caption, 10., false))];
            }
            for row in t.rows.iter_mut().skip(headers) {
                row.cells[at].props.shading = Some(if group % 2 == 0 {
                    Rgb(247, 250, 255)
                } else {
                    Rgb(255, 255, 255)
                });
            }
            at += 1;
        }
    }
    for (r, values) in c.values.iter().enumerate() {
        for (col, value) in values.iter().enumerate() {
            t.rows[r + headers].cells[col].blocks =
                vec![para_block(cell_text(value, c.font_size, false))];
        }
    }
    t
}
fn line(items: &mut Vec<GraphicItem>, segs: Vec<PathSeg>) {
    items.push(GraphicItem::Path {
        segs,
        fill: None,
        stroke: Some(BLUE),
        stroke_width: 1.4,
    });
}
fn bubble(items: &mut Vec<GraphicItem>, x: f32, y: f32, label: String) {
    items.push(GraphicItem::Shape {
        rect: [x - 33., y - 11., 66., 22.],
        kind: ShapeKind::RoundedRectangle,
        fill: Some(Rgb(235, 243, 255)),
        stroke: Some(BLUE),
        stroke_width: 1.,
    });
    items.push(GraphicItem::Text {
        rect: [x - 31., y - 8., 62., 18.],
        text: label,
        size: 11.,
        color: BLUE,
        bold: true,
        align: TextAlign::Center,
        font: Some("Arial".into()),
    });
}
fn graphic(items: Vec<GraphicItem>, w: f32, h: f32) -> Arc<Block> {
    let object = InlineObject::Graphic {
        w,
        h,
        alt: "Bulles d’opérations à compléter, sans calcul automatique".into(),
        float: Float::default(),
        graphic: Arc::new(Graphic {
            kind: GraphicKind::Diagram,
            items,
            w,
            h,
            ..Default::default()
        }),
    };
    let mut paragraph = cell_text("", 12., false);
    paragraph
        .insert_object(0, object, &wordcraft_doc::CharProps::default())
        .expect("An empty paragraph accepts its first inline object");
    paragraph.props.line_spacing = Some(wordcraft_doc::props::LineSpacing::Exactly(h));
    para_block(paragraph)
}
fn proportion_table(p: &Proportion) -> Table {
    let side = if p.row_operation.trim().is_empty() {
        0.
    } else {
        82.
    };
    let data_width = p.width - side;
    let columns = p.values[0].len();
    let cell = data_width / columns as f32;
    let mut data = blank_table(2, columns, data_width, p.row_height, p.font_size);
    for (r, values) in p.values.iter().enumerate() {
        for (c, value) in values.iter().enumerate() {
            data.rows[r].cells[c].blocks = vec![para_block(cell_text(value, p.font_size, false))];
        }
    }
    let mut outer = blank_table(1, if side > 0. { 2 } else { 1 }, p.width, 24., p.font_size);
    outer.grid = if side > 0. {
        vec![data_width, side]
    } else {
        vec![data_width]
    };
    outer.props.borders = Some(Borders::all(Border::default()));
    for cell in &mut outer.rows[0].cells {
        cell.props.borders = Some(Borders::all(Border::default()));
        cell.props.valign = Some(VAlign::Top);
    }
    let mut left = vec![];
    for link in &p.links {
        let mut items = vec![];
        let (sources, target, label) = match link {
            ColumnLink::Operation { from, to, label } => (vec![*from], *to, label.clone()),
            ColumnLink::Sum { first, second, to } => (
                vec![*first, *second],
                *to,
                format!("C{} + C{}", first + 1, second + 1),
            ),
        };
        let end = (target as f32 + 0.5) * cell;
        let start = sources
            .iter()
            .map(|n| (*n as f32 + 0.5) * cell)
            .sum::<f32>()
            / sources.len() as f32;
        let middle = ((start + end) / 2.).clamp(34., data_width - 34.);
        for source in sources {
            let x = (source as f32 + 0.5) * cell;
            line(
                &mut items,
                vec![
                    PathSeg::Move(x, 43.),
                    PathSeg::Cubic(x, 8., middle, 8., middle, 18.),
                ],
            );
        }
        line(
            &mut items,
            vec![
                PathSeg::Move(middle, 18.),
                PathSeg::Cubic(end, 8., end, 24., end, 43.),
                PathSeg::Move(end - 3., 38.),
                PathSeg::Line(end, 43.),
                PathSeg::Line(end + 3., 38.),
            ],
        );
        bubble(&mut items, middle, 18., label);
        left.push(graphic(items, data_width, 46.));
    }
    left.push(Arc::new(Block::Table(data)));
    left.push(para_block(cell_text("", 1., false)));
    outer.rows[0].cells[0].blocks = left;
    if side > 0. {
        let h = p.row_height * 2.;
        let mut items = vec![];
        let (a, b) = if p.row_reverse {
            (1.5 * p.row_height, p.row_height / 2.)
        } else {
            (p.row_height / 2., 1.5 * p.row_height)
        };
        line(
            &mut items,
            vec![
                PathSeg::Move(0., a),
                PathSeg::Cubic(68., a, 68., b, 0., b),
                PathSeg::Move(5., b - 3.),
                PathSeg::Line(0., b),
                PathSeg::Line(5., b + 3.),
            ],
        );
        bubble(&mut items, 42., h / 2., p.row_operation.clone());
        let block = graphic(items, side, h);
        let mut paragraph = block.as_para().unwrap().clone();
        paragraph.props.space_before = Some(p.links.len() as f32 * 46.);
        outer.rows[0].cells[1].blocks = vec![para_block(paragraph)];
    }
    outer
}

pub fn selected(s: &Session) -> Option<(Path, Model)> {
    let mut path = s.sel.focus.path.0.clone();
    while path.len() >= 4 {
        path.truncate(path.len() - 3);
        let p = Path(path.clone());
        let table = s.doc.table(s.sel.focus.story, &p)?;
        let Some(text) = table
            .props
            .description
            .as_deref()
            .and_then(|d| d.strip_prefix(PREFIX))
        else {
            continue;
        };
        if text.len() > 128_000 {
            return None;
        }
        let mut model: Model = serde_json::from_str(text).ok()?;
        match &mut model {
            Model::Proportion(m) => {
                let data = table
                    .rows
                    .first()?
                    .cells
                    .first()?
                    .blocks
                    .iter()
                    .find_map(|b| b.as_table())?;
                if data.rows.len() != 2 || data.cols() != m.values[0].len() {
                    return None;
                }
                for (r, row) in data.rows.iter().enumerate() {
                    for (c, cell) in row.cells.iter().enumerate() {
                        m.values[r][c] = cell
                            .blocks
                            .iter()
                            .filter_map(|b| b.as_para())
                            .map(|p| p.plain_text())
                            .collect::<Vec<_>>()
                            .join("\n");
                    }
                }
            }
            Model::Conversion(m) => {
                if table.rows.len() != m.values.len() + m.header_rows() {
                    return None;
                }
                for (r, row) in table.rows.iter().skip(m.header_rows()).enumerate() {
                    if row.cells.len() != m.columns() {
                        return None;
                    }
                    for (c, cell) in row.cells.iter().enumerate() {
                        m.values[r][c] = cell
                            .blocks
                            .iter()
                            .filter_map(|b| b.as_para())
                            .map(|p| p.plain_text())
                            .collect::<Vec<_>>()
                            .join("\n");
                    }
                }
            }
        }
        return Some((p, model));
    }
    None
}
pub fn apply(s: &mut Session, model: &Model) -> Result<(), String> {
    crate::core::ensure_writing_selection(s)?;
    let table = model.table()?;
    let sections = s.doc.sections();
    let index = s
        .doc
        .section_index_of(s.sel.focus.path.0.first().copied().unwrap_or(0) as usize);
    let available = sections
        .get(index)
        .map(|(_, p)| p.text_width())
        .unwrap_or(468.);
    if model.width() > available + 1. {
        return Err("Le tableau dépasse la zone d’écriture. Passe en paysage ou choisis une largeur plus petite ; le texte ne sera pas réduit.".into());
    }
    let existing = selected(s);
    if existing
        .as_ref()
        .is_some_and(|(_, old)| std::mem::discriminant(old) != std::mem::discriminant(model))
    {
        return Err("Place le curseur hors de l’autre tableau pour insérer ce modèle.".into());
    }
    let snapshot = s.edit_snapshot();
    s.checkpoint("Créer ou modifier un tableau de mathématiques");
    let result = (|| {
        let at = if let Some((path, _)) = existing {
            *s.doc
                .table_mut(s.sel.focus.story, &path)
                .map_err(|e| e.to_string())? = table;
            Pos {
                story: s.sel.focus.story,
                path,
                off: 0,
            }
        } else {
            let focus = s.sel.focus.clone();
            let at = if focus.path.0.len() == 1 {
                s.doc.split_paragraph(&focus).map_err(|e| e.to_string())?
            } else {
                return Err(
                    "Place le curseur hors d’un autre tableau pour insérer ce modèle.".into(),
                );
            };
            let index = at.path.last();
            s.doc
                .container_mut(at.story, &at.path)
                .map_err(|e| e.to_string())?
                .insert(index, Arc::new(Block::Table(table)));
            at
        };
        let mut path = at.path.0.clone();
        match model {
            Model::Conversion(c) => path.extend([c.header_rows() as u32, 0, 0]),
            Model::Proportion(p) => path.extend([0, 0, p.links.len() as u32, 0, 0, 0]),
        };
        s.sel = Selection::caret(Pos {
            story: at.story,
            path: Path(path),
            off: 0,
        });
        s.touch();
        s.relayout();
        Ok(())
    })();
    if result.is_err() {
        s.restore(snapshot)
    }
    result
}
