//! Image provenance stays with the document without adding text to its pages.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::io::{Cursor, Read};
use wordcraft_doc::{Document, InlineObject};
use wordcraft_engine::Session;
pub const PREFIX: &str = "ecr.image.credit.";
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Credit {
    pub title: String,
    pub author: String,
    pub license: String,
    pub license_url: String,
    pub source_url: String,
    pub version: String,
    pub changes: String,
    pub proof_url: String,
    pub sha256: String,
}
impl From<&crate::library::Entry> for Credit {
    fn from(e: &crate::library::Entry) -> Self {
        Self {
            title: e.title.clone(),
            author: e.author.clone(),
            license: e.license.clone(),
            license_url: e.license_url.clone(),
            source_url: e.source_url.clone(),
            version: e.source_timestamp.clone(),
            changes: e.changes.clone(),
            proof_url: e.license_proof_url.clone(),
            sha256: e.sha256.clone(),
        }
    }
}
fn digest(data: &[u8]) -> String {
    Sha256::digest(data)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}
pub fn store(doc: &mut Document, credit: &Credit) -> Result<(), String> {
    let value = serde_json::to_string(credit).map_err(|e| e.to_string())?;
    doc.set_custom_prop(&format!("{PREFIX}{}", credit.sha256), &value);
    Ok(())
}
fn stored(doc: &Document) -> impl Iterator<Item = Credit> + '_ {
    doc.custom_props
        .iter()
        .filter(|p| p.name.starts_with(PREFIX) && p.value.len() <= 16000)
        .filter_map(|p| serde_json::from_str::<Credit>(&p.value).ok())
}
pub fn for_image(doc: &Document, object: &InlineObject) -> Option<Credit> {
    let InlineObject::Image { media, alt, .. } = object else {
        return None;
    };
    let hash = digest(doc.media.get(media)?.as_slice());
    if let Some(c) = doc
        .custom_prop(&format!("{PREFIX}{hash}"))
        .filter(|s| s.len() <= 16000)
        .and_then(|s| serde_json::from_str::<Credit>(s).ok())
    {
        return Some(c);
    }
    // An external ODT editor may recompress a PNG while preserving its alt text.
    if let Some(c) = stored(doc).find(|c| c.title == *alt) {
        return Some(c);
    }
    // The old starter library can be identified even before a metadata migration.
    crate::library::catalog()
        .iter()
        .find(|e| e.sha256 == hash)
        .map(Credit::from)
}
pub fn selected(s: &Session) -> Option<Credit> {
    let (_, object) = wordcraft_engine::cmd::objects::selected(s)?;
    for_image(&s.doc, &object)
}
pub fn active(doc: &Document) -> Vec<Credit> {
    let mut all = Vec::<Credit>::new();
    doc.objects_in_reading_order(&mut |o| {
        if let Some(c) = for_image(doc, o) {
            if !all.iter().any(|old| old.sha256 == c.sha256) {
                all.push(c);
            }
        }
    });
    all
}
pub fn metadata_xml(doc: &Document) -> Result<String, String> {
    let mut xml = String::new();
    for c in active(doc) {
        let key = format!("{PREFIX}{}", c.sha256);
        let value = serde_json::to_string(&c).map_err(|e| e.to_string())?;
        xml.push_str(&format!(
            "<meta:user-defined meta:name=\"{}\" meta:value-type=\"string\">{}</meta:user-defined>",
            quick_xml::escape::escape(&key),
            quick_xml::escape::escape(&value)
        ));
    }
    Ok(xml)
}
pub fn restore_odt(doc: &mut Document, bytes: &[u8]) -> Result<(), String> {
    let mut archive = zip::ZipArchive::new(Cursor::new(bytes)).map_err(|e| e.to_string())?;
    let Ok(mut file) = archive.by_name("meta.xml") else {
        return Ok(());
    };
    if file.size() > 8 * 1024 * 1024 {
        return Ok(());
    };
    let mut xml = String::new();
    file.by_ref()
        .take(8 * 1024 * 1024 + 1)
        .read_to_string(&mut xml)
        .map_err(|e| e.to_string())?;
    let mut reader = quick_xml::Reader::from_str(&xml);
    let mut count = 0;
    loop {
        match reader.read_event().map_err(|e| e.to_string())? {
            quick_xml::events::Event::Start(e) if e.name().as_ref() == b"meta:user-defined" => {
                let name = e
                    .attributes()
                    .flatten()
                    .find(|a| a.key.as_ref() == b"meta:name")
                    .and_then(|a| {
                        a.decoded_and_normalized_value(
                            quick_xml::XmlVersion::Explicit1_0,
                            reader.decoder(),
                        )
                        .ok()
                        .map(|s| s.into_owned())
                    });
                if name.as_deref().is_some_and(|n| n.starts_with(PREFIX)) {
                    let raw = reader.read_text(e.name()).map_err(|e| e.to_string())?;
                    if raw.len() > 16000 {
                        continue;
                    }
                    let decoded = raw.decode().map_err(|e| e.to_string())?;
                    let text = quick_xml::escape::unescape(&decoded).map_err(|e| e.to_string())?;
                    if let Ok(c) = serde_json::from_str::<Credit>(&text) {
                        store(doc, &c)?;
                        count += 1;
                        if count >= 4096 {
                            break;
                        }
                    }
                }
            }
            quick_xml::events::Event::Eof => break,
            _ => {}
        }
    }
    Ok(())
}
pub fn pdf_metadata(doc: &Document) -> String {
    active(doc)
        .iter()
        .map(|c| {
            format!(
                "{} — {} · {} · {} · {} · {} · {}",
                c.title, c.author, c.license, c.license_url, c.source_url, c.proof_url, c.changes
            )
        })
        .collect::<Vec<_>>()
        .join("\n")
}
/// Remove only the exact automatic credit immediately following a known library
/// picture. Student-edited captions and unrelated source text are kept intact.
pub fn migrate_visible(s: &mut Session) -> Result<usize, String> {
    let mut copy = s.doc.clone();
    let mut credits = Vec::new();
    fn walk(
        blocks: &mut wordcraft_doc::Blocks,
        doc: &Document,
        credits: &mut Vec<Credit>,
        depth: usize,
    ) -> usize {
        if depth > 32 {
            return 0;
        }
        let mut expected = None;
        let mut removed = 0;
        let mut out = Vec::new();
        for mut b in std::mem::take(blocks) {
            if let wordcraft_doc::Block::Para(p) = std::sync::Arc::make_mut(&mut b) {
                // Versions before 0.9 used manual line breaks inside the image
                // paragraph. Match only the exact generated line after an image.
                let mut edits = Vec::new();
                let mut object_index = 0;
                for (off, ch) in p.text.char_indices() {
                    if ch == wordcraft_doc::para::OBJ {
                        if let Some(c) = p.objects.get(object_index).and_then(|o| for_image(doc, o))
                        {
                            let old = format!(
                                "{} — {} · {} · {}",
                                c.title, c.author, c.license, c.source_url
                            );
                            let after = off + ch.len_utf8();
                            let pattern = format!("\n{old}\n");
                            if p.text
                                .get(after..)
                                .is_some_and(|text| text.starts_with(&pattern))
                            {
                                edits.push((after + 1, after + pattern.len(), c));
                            }
                        }
                        object_index += 1;
                    }
                }
                for (a, b, c) in edits.into_iter().rev() {
                    if p.delete(a, b).is_ok() {
                        credits.push(c);
                        removed += 1;
                    }
                }
            }
            if let Some(p) = b.as_para() {
                if let Some(c) = expected.take() {
                    let c: Credit = c;
                    let old = format!(
                        "{} — {} · {} · {}",
                        c.title, c.author, c.license, c.source_url
                    );
                    if p.plain_text() == old {
                        credits.push(c);
                        removed += 1;
                        continue;
                    }
                }
                for o in &p.objects {
                    if let Some(c) = for_image(doc, o) {
                        expected = Some(c);
                    }
                }
            }
            if let wordcraft_doc::Block::Table(t) = std::sync::Arc::make_mut(&mut b) {
                for row in &mut t.rows {
                    for cell in &mut row.cells {
                        removed += walk(&mut cell.blocks, doc, credits, depth + 1);
                    }
                }
            }
            out.push(b);
        }
        *blocks = out;
        removed
    }
    let count = walk(&mut copy.body, &s.doc, &mut credits, 0);
    if count > 0 {
        for c in credits {
            store(&mut copy, &c)?;
        }
        s.checkpoint("Masquer les sources des illustrations");
        s.doc = copy;
        s.touch();
        s.relayout();
    }
    Ok(count)
}
