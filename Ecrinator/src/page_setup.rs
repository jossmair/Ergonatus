//! Orientation changes preserve the document's typography and zoom preference.
use std::sync::Arc;
use wordcraft_engine::Session;

pub fn landscape(s: &Session) -> bool {
    let block = s.sel.focus.path.0.first().copied().unwrap_or(0) as usize;
    let sections = s.doc.sections();
    let index = s.doc.section_index_of(block);
    sections
        .get(index)
        .is_some_and(|(_, p)| p.page_w > p.page_h)
}

pub fn set_orientation(s: &mut Session, wide: bool) -> Result<(), String> {
    s.run(
        "layout.orientation",
        &serde_json::json!({"value": if wide { "landscape" } else { "portrait" }}),
    )
    .map_err(|e| e.to_string())?;
    // Adapt only the banner's geometry: no reduction of font sizes, cell
    // values or the writing zoom. The engine command owns the undo checkpoint.
    let width = s
        .doc
        .sections()
        .first()
        .map(|(_, p)| p.page_w)
        .unwrap_or(595.276);
    for block in &mut s.doc.body {
        let wordcraft_doc::Block::Table(table) = Arc::make_mut(block) else {
            continue;
        };
        if table.props.caption.as_deref() != Some(crate::core::HEADER) {
            continue;
        }
        let left = 222_f32.min(width * 0.38);
        let right = 125_f32.min(width * 0.23);
        table.grid = vec![left, width - left - right, right];
        table.props.width = Some(width);
        for row in &mut table.rows {
            for (i, cell) in row.cells.iter_mut().enumerate() {
                cell.props.width = table.grid.get(i).copied();
            }
        }
    }
    s.touch();
    s.relayout();
    Ok(())
}
