//! Editable operation scaffolds. No arithmetic evaluation or answer generation.
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use wordcraft_doc::{
    Block, Path, Pos, Table, para_block,
    props::{Align, Border, Borders, HeightRule, Rgb, VAlign},
};
use wordcraft_engine::{Selection, Session};
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum Operation {
    Add,
    Subtract,
    Multiply,
    Divide,
}
impl Operation {
    pub const ALL: [Self; 4] = [Self::Add, Self::Subtract, Self::Multiply, Self::Divide];
    pub fn symbol(self) -> &'static str {
        match self {
            Self::Add => "+",
            Self::Subtract => "−",
            Self::Multiply => "×",
            Self::Divide => "÷",
        }
    }
    pub fn label(self) -> &'static str {
        match self {
            Self::Add => "Addition",
            Self::Subtract => "Soustraction",
            Self::Multiply => "Multiplication",
            Self::Divide => "Division",
        }
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Calculation {
    pub operation: Operation,
    pub a: String,
    pub b: String,
    pub columns: u8,
    pub blank_rows: u8,
    pub grid: bool,
}
impl Default for Calculation {
    fn default() -> Self {
        Self {
            operation: Operation::Add,
            a: String::new(),
            b: String::new(),
            columns: 8,
            blank_rows: 5,
            grid: true,
        }
    }
}
pub const DESIGN: &str = "ecrinator-operation-scaffold-v1";
fn number(text: &str) -> Result<String, String> {
    let s = text.trim().replace('.', ",").replace('-', "−");
    let digits = s.trim_start_matches('−');
    if s.chars().count() > 18
        || digits.chars().filter(|c| *c == ',').count() > 1
        || !digits.chars().all(|c| c.is_ascii_digit() || c == ',')
        || (!s.is_empty() && !digits.chars().any(|c| c.is_ascii_digit()))
    {
        return Err("Écris un entier ou un décimal avec une virgule, ou laisse le champ vide (18 caractères maximum).".into());
    }
    Ok(s)
}
fn fraction_len(s: &str) -> usize {
    s.split_once(',').map_or(0, |(_, f)| f.chars().count())
}
fn border(width: f32, color: Rgb) -> Border {
    Border {
        color: Some(color),
        ..Border::single(width)
    }
}
impl Calculation {
    pub fn validate(&self) -> Result<(), String> {
        number(&self.a)?;
        number(&self.b)?;
        if !(3..=18).contains(&self.columns) || !(2..=12).contains(&self.blank_rows) {
            return Err("Choisis 3 à 18 cases et 2 à 12 lignes à remplir.".into());
        }
        Ok(())
    }
    pub fn table(&self) -> Result<Table, String> {
        self.validate()?;
        let a = number(&self.a)?;
        let b = number(&self.b)?;
        let (a, b) = if matches!(self.operation, Operation::Add | Operation::Subtract) {
            let decimals = fraction_len(&a).max(fraction_len(&b));
            let pad = |s: &str| {
                if s.is_empty() {
                    return String::new();
                }
                let missing = decimals - fraction_len(s);
                let comma_space = if decimals > 0 && !s.contains(',') {
                    1
                } else {
                    0
                };
                format!("{}{}", s, " ".repeat(missing + comma_space))
            };
            (pad(&a), pad(&b))
        } else {
            (a, b)
        };
        let digits = (self.columns as usize)
            .max(a.chars().count())
            .max(b.chars().count());
        let division = self.operation == Operation::Divide;
        let cols = if division { digits * 2 + 1 } else { digits + 1 };
        let rows = self.blank_rows as usize + if division { 1 } else { 3 };
        let cell = (450. / cols as f32).min(26.);
        let mut t = Table::new(rows, cols, cell * cols as f32);
        t.props.style = None;
        t.props.width = Some(cell * cols as f32);
        t.props.fixed = true;
        t.props.geometry_locked = false;
        t.props.align = Some(Align::Left);
        t.props.caption = Some(format!("Opération posée · {}", self.operation.label()));
        t.props.description = Some(format!(
            "{DESIGN}:{}",
            serde_json::to_string(self).map_err(|e| e.to_string())?
        ));
        t.props.cell_margins = Some([2., 0., 2., 0.]);
        let blank = Border::default();
        t.props.borders = Some(Borders::all(blank));
        for row in &mut t.rows {
            row.props.height = Some(29.);
            row.props.height_rule = HeightRule::AtLeast;
            row.props.cant_split = true;
            for cell in &mut row.cells {
                cell.props.margins = Some([2., 0., 2., 0.]);
                cell.props.valign = Some(VAlign::Center);
                cell.props.no_wrap = true;
                cell.props.borders = Some(Borders::all(if self.grid {
                    border(0.4, Rgb(219, 230, 243))
                } else {
                    blank
                }));
                let mut p = crate::core::text("", 18., false, Rgb(30, 49, 73));
                p.props.align = Some(Align::Center);
                p.props.space_before = Some(0.);
                p.props.space_after = Some(0.);
                p.props.line_spacing = Some(wordcraft_doc::props::LineSpacing::Multiple(1.));
                cell.blocks = vec![para_block(p)];
            }
        }
        let mut put = |r: usize, start: usize, s: &str| {
            for (i, ch) in s.chars().enumerate() {
                let mut p = crate::core::text(&ch.to_string(), 18., false, Rgb(30, 49, 73));
                p.props.align = Some(Align::Center);
                p.props.space_before = Some(0.);
                p.props.space_after = Some(0.);
                p.props.line_spacing = Some(wordcraft_doc::props::LineSpacing::Multiple(1.));
                t.rows[r].cells[start + i].blocks = vec![para_block(p)];
            }
        };
        if division {
            put(0, 0, &a);
            put(0, digits + 1, &b);
        } else {
            put(1, cols - a.chars().count(), &a);
            put(2, cols - b.chars().count(), &b);
            put(2, 0, self.operation.symbol());
        }
        if division {
            for (r, row) in t.rows.iter_mut().enumerate() {
                row.cells[digits].props.borders.as_mut().unwrap().right =
                    Some(border(1.4, Rgb(30, 49, 73)));
                if r == 0 {
                    for c in digits + 1..cols {
                        row.cells[c].props.borders.as_mut().unwrap().bottom =
                            Some(border(1.4, Rgb(30, 49, 73)));
                    }
                }
            }
        } else {
            for cell in &mut t.rows[2].cells {
                cell.props.borders.as_mut().unwrap().bottom = Some(border(1.4, Rgb(30, 49, 73)));
            }
            for cell in &mut t.rows[0].cells {
                let p = Arc::make_mut(&mut cell.blocks[0]);
                if let Block::Para(p) = p {
                    p.mark.size = Some(11.);
                }
            }
        }
        Ok(t)
    }
}
pub fn selected(s: &Session) -> Option<Path> {
    let mut p = s.sel.focus.path.0.clone();
    while p.len() >= 4 {
        p.truncate(p.len() - 3);
        let path = Path(p.clone());
        if s.doc.table(s.sel.focus.story, &path).is_some_and(|t| {
            t.props
                .description
                .as_deref()
                .is_some_and(|s| s.starts_with(DESIGN))
        }) {
            return Some(path);
        }
    }
    None
}
/// Insert a real editable table. Existing text and filled operations are preserved.
pub fn apply(s: &mut Session, c: &Calculation) -> Result<(), String> {
    crate::core::ensure_writing_selection(s)?;
    let table = c.table()?;
    let snapshot = s.edit_snapshot();
    s.checkpoint("Insérer une opération à compléter");
    let result = (|| {
        let focus = s.sel.focus.clone();
        let at = if focus.path.0.len() == 1 {
            s.doc.split_paragraph(&focus).map_err(|e| e.to_string())?
        } else {
            let i = focus.path.0.first().copied().ok_or("Position absente")? as usize + 1;
            if i >= s.doc.body.len() {
                s.doc.body.push(para_block(wordcraft_doc::Paragraph::new()));
            }
            Pos::body(i, 0)
        };
        let table_cols = table.cols();
        let index = at.path.last();
        let container = s
            .doc
            .container_mut(at.story, &at.path)
            .map_err(|e| e.to_string())?;
        container.insert(index, Arc::new(Block::Table(table)));
        let row = if c.operation == Operation::Divide {
            if c.a.is_empty() { 0 } else { 1 }
        } else if c.a.is_empty() {
            1
        } else {
            0
        };
        let col = if c.operation == Operation::Divide {
            if c.a.is_empty() {
                0
            } else {
                table_cols / 2 + 1
            }
        } else {
            1
        };
        let mut path = at.path.0.clone();
        path.extend([row as u32, col as u32, 0]);
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
        s.restore(snapshot);
    }
    result
}
#[cfg(test)]
mod tests {
    use super::*;
    fn all_text(t: &Table) -> String {
        t.rows
            .iter()
            .flat_map(|r| &r.cells)
            .flat_map(|c| &c.blocks)
            .filter_map(|b| b.as_para())
            .map(|p| p.plain_text())
            .collect::<Vec<_>>()
            .join("")
    }
    #[test]
    fn never_computes_or_populates_working_rows() {
        for operation in Operation::ALL {
            let c = Calculation {
                operation,
                a: "125,4".into(),
                b: "37,85".into(),
                ..Default::default()
            };
            let t = c.table().unwrap();
            let from = if operation == Operation::Divide { 1 } else { 3 };
            for r in &t.rows[from..] {
                for cell in &r.cells {
                    assert!(cell.blocks[0].as_para().unwrap().plain_text().is_empty());
                }
            }
            assert!(!all_text(&t).contains("163,25"));
        }
    }
    #[test]
    fn decimal_commas_align_without_adding_zeroes() {
        let t = Calculation {
            a: "125,4".into(),
            b: "37,85".into(),
            ..Default::default()
        }
        .table()
        .unwrap();
        let comma = |r: usize| {
            t.rows[r]
                .cells
                .iter()
                .position(|c| c.blocks[0].as_para().unwrap().plain_text() == ",")
                .unwrap()
        };
        assert_eq!(comma(1), comma(2));
        assert_eq!(
            t.rows[1].cells.last().unwrap().blocks[0]
                .as_para()
                .unwrap()
                .plain_text(),
            " "
        );
    }
    #[test]
    fn completely_blank_templates_and_zero_divisor_are_permitted() {
        for operation in Operation::ALL {
            let c = Calculation {
                operation,
                ..Default::default()
            };
            assert!(c.table().is_ok());
        }
        let c = Calculation {
            operation: Operation::Divide,
            a: "12,5".into(),
            b: "0".into(),
            ..Default::default()
        };
        assert!(c.table().is_ok());
    }
    #[test]
    fn invalid_geometry_and_text_are_rejected() {
        assert!(
            Calculation {
                columns: 0,
                ..Default::default()
            }
            .table()
            .is_err()
        );
        assert!(
            Calculation {
                a: "1,2,3".into(),
                ..Default::default()
            }
            .table()
            .is_err()
        );
    }
}
