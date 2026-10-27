//! Embedded, offline school illustrations with per-file source and attribution.
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{
    collections::VecDeque,
    sync::{Arc, Mutex, OnceLock},
};
use wordcraft_doc::InlineObject;
use wordcraft_engine::{Selection, Session};
include!(concat!(env!("OUT_DIR"), "/library.rs"));
#[derive(Clone, Debug, Deserialize)]
pub struct Entry {
    #[serde(skip)]
    search_key: OnceLock<String>,
    pub id: String,
    pub title: String,
    pub category: String,
    pub tags: String,
    pub filename: String,
    pub author: String,
    pub license: String,
    pub license_url: String,
    pub source_url: String,
    pub source_timestamp: String,
    pub changes: String,
    pub width: u32,
    pub height: u32,
    pub sha256: String,
    #[serde(default)]
    pub topic: String,
    #[serde(default)]
    pub thumbnail_sha256: String,
    #[serde(default)]
    pub caption: String,
    #[serde(default)]
    pub license_proof_url: String,
    #[serde(default)]
    pub subjects: Vec<String>,
    #[serde(default)]
    pub kind: String,
    #[serde(default)]
    pub monochrome: bool,
    #[serde(default)]
    pub unlabelled: bool,
    #[serde(default)]
    pub grades: Vec<String>,
    #[serde(default)]
    pub cycle: String,
    #[serde(default)]
    pub domain: String,
    #[serde(default)]
    pub curriculum_theme: String,
    #[serde(default)]
    pub learning_objective: String,
    #[serde(default)]
    pub language: String,
    #[serde(default)]
    pub educational_use: String,
}
pub fn catalog() -> &'static [Entry] {
    static CATALOG: OnceLock<Vec<Entry>> = OnceLock::new();
    CATALOG.get_or_init(|| {
        serde_json::from_str(include_str!("../assets/library/catalog.json")).unwrap_or_default()
    })
}
impl Entry {
    pub fn matches(&self, category: &str, query: &str) -> bool {
        let category_matches = category.is_empty()
            || category == self.category
            || self.subjects.iter().any(|s| s == category);
        if !category_matches {
            return false;
        }
        if query.trim().is_empty() {
            return true;
        }
        let key = self.search_key.get_or_init(|| {
            normalize(&format!(
                "{} {} {} {} {} {} {}",
                self.title,
                self.tags,
                self.topic,
                self.curriculum_theme,
                self.learning_objective,
                self.grades.join(" "),
                self.cycle
            ))
        });
        normalize(query)
            .split_whitespace()
            .all(|term| key.contains(term))
    }
    /// Unknown metadata stays unknown: it must not pass a specific school filter.
    pub fn matches_school_filters(&self, grade: &str, usage: &str, french_only: bool) -> bool {
        (grade.is_empty()
            || self.grades.iter().any(|g| g == grade)
            || (!self.cycle.is_empty() && self.cycle == grade))
            && (usage.is_empty() || self.educational_use == usage)
            && (!french_only || matches!(self.language.as_str(), "fr" | "zxx"))
    }
    pub fn credit(&self) -> String {
        format!(
            "{} — {} · {} · {}",
            self.title, self.author, self.license, self.source_url
        )
    }
}
pub fn normalize(text: &str) -> String {
    text.to_lowercase()
        .chars()
        .map(|c| match c {
            'à' | 'â' | 'ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'î' | 'ï' => 'i',
            'ô' | 'ö' => 'o',
            'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            c => c,
        })
        .collect::<String>()
        .replace('œ', "oe")
        .replace('æ', "ae")
}
pub fn available(entry: &Entry) -> bool {
    bytes(&entry.id).is_some() && embedded_thumbnail(&entry.id).is_some()
}
/// Used by the packaged executable's offline acceptance check.
pub fn verify_pack() -> Result<usize, String> {
    for e in catalog() {
        let _ = read_asset(e, false)?;
        let _ = read_asset(e, true)?;
    }
    Ok(catalog().len())
}
pub fn read_asset(entry: &Entry, thumbnail: bool) -> Result<Arc<[u8]>, String> {
    if entry.filename.contains(['/', '\\']) {
        return Err("Chemin de bibliothèque invalide".into());
    }
    let embedded = if thumbnail {
        embedded_thumbnail(&entry.id)
    } else {
        bytes(&entry.id)
    };
    if let Some(data) = embedded {
        let expected = if thumbnail {
            &entry.thumbnail_sha256
        } else {
            &entry.sha256
        };
        let actual = Sha256::digest(data)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>();
        if actual != *expected {
            return Err("L’illustration intégrée est endommagée.".into());
        }
        return Ok(Arc::from(data));
    }
    Err(format!("Illustration intégrée inconnue : {}", entry.title))
}

pub fn thumbnail(entry: &Entry) -> Result<Arc<[u8]>, String> {
    type Cache = VecDeque<(String, Arc<[u8]>)>;
    static CACHE: OnceLock<Mutex<Cache>> = OnceLock::new();
    let mut cache = CACHE
        .get_or_init(Default::default)
        .lock()
        .map_err(|_| "Aperçus occupés")?;
    if let Some((_, data)) = cache.iter().find(|(id, _)| id == &entry.id) {
        return Ok(data.clone());
    }
    let data = read_asset(entry, true)?;
    if cache.len() >= 96 {
        cache.pop_front();
    }
    cache.push_back((entry.id.clone(), data.clone()));
    Ok(data)
}
/// Image and attribution form one undo step; original bytes remain intact.
pub fn insert(s: &mut Session, entry: &Entry) -> Result<(), String> {
    crate::core::ensure_writing_selection(s)?;
    let data = read_asset(entry, false)?;
    if entry.width == 0 || entry.height == 0 {
        return Err("Dimensions d’image invalides".into());
    }
    let snapshot = s.edit_snapshot();
    s.checkpoint("Insérer une illustration et sa source");
    let result = (|| {
        let width = s
            .doc
            .sections()
            .first()
            .map(|(_, sp)| sp.text_width())
            .unwrap_or(468.)
            .min(360.);
        let scale = (width / entry.width as f32).min(230. / entry.height as f32);
        let extension = if data.starts_with(&[0xff, 0xd8, 0xff]) {
            "jpg"
        } else if data.starts_with(b"\x89PNG\r\n\x1a\n") {
            "png"
        } else {
            return Err("Format d’image de bibliothèque non pris en charge.".into());
        };
        let base = format!(
            "ecr-library-{}-{}.{extension}",
            entry.id,
            &entry.sha256.get(..12).unwrap_or("source")
        );
        let mut key = base.clone();
        let mut suffix = 1;
        while s
            .doc
            .media
            .get(&key)
            .is_some_and(|existing| existing.as_slice() != data.as_ref())
        {
            key = format!("{base}-{suffix}.{extension}");
            suffix += 1;
        }
        let (a, b) = s.sel.ordered();
        let (a, b) = (a.clone(), b.clone());
        let at = if a == b {
            a
        } else {
            s.doc.delete_range(&a, &b).map_err(|e| e.to_string())?
        };
        let props = s.typing_props();
        s.doc.media.insert(key.clone(), Arc::new(data.to_vec()));
        crate::image_credits::store(&mut s.doc, &crate::image_credits::Credit::from(entry))?;
        let end = s
            .doc
            .insert_object(
                &at,
                InlineObject::Image {
                    media: key,
                    w: entry.width as f32 * scale,
                    h: entry.height as f32 * scale,
                    alt: entry.title.clone(),
                    float: Default::default(),
                    crop: [0.; 4],
                    ole: None,
                },
                &props,
            )
            .map_err(|e| e.to_string())?;
        s.sel = Selection::caret(end);
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
mod school_filter_tests {
    use super::*;

    #[test]
    fn embedded_catalogue_is_valid_and_nonempty() {
        let entries: Vec<Entry> =
            serde_json::from_str(include_str!("../assets/library/catalog.json"))
                .expect("Embedded catalogue must match the runtime schema");
        assert!(!entries.is_empty());
        assert_eq!(entries.len(), catalog().len());
    }

    #[test]
    fn search_combines_words_and_keeps_cycle_honest() {
        let mut entry = catalog()[0].clone();
        entry.search_key = OnceLock::new();
        entry.title = "Cellule végétale".into();
        entry.tags = "Schéma à légender".into();
        entry.grades.clear();
        entry.cycle = "Cycle 4".into();
        assert!(entry.matches("", "vegetale cellule"));
        assert!(!entry.matches("", "cellule volcan"));
        assert!(entry.matches_school_filters("Cycle 4", "", false));
        assert!(!entry.matches_school_filters("5e", "", false));
    }

    #[test]
    fn jpeg_survives_odt_without_reencoding_or_printed_credit() {
        let entry = catalog()
            .iter()
            .find(|e| e.id.starts_with("dore-fable-"))
            .unwrap();
        let original = read_asset(entry, false).unwrap();
        assert!(original.starts_with(&[0xff, 0xd8, 0xff]));
        let mut session = Session::new(wordcraft_doc::Document::new());
        insert(&mut session, entry).unwrap();
        assert!(
            session
                .doc
                .media
                .iter()
                .any(|(key, value)| key.ends_with(".jpg") && value.as_slice() == original.as_ref())
        );
        let bytes = crate::exporters::bytes("illustration.odt", &session.doc).unwrap();
        let imported = wordcraft_engine::io::open_bytes("illustration.odt", &bytes).unwrap();
        assert!(
            imported
                .media
                .iter()
                .any(|(_, value)| value.as_slice() == original.as_ref())
        );
        assert!(
            !imported
                .plain_text(wordcraft_doc::StoryRef::Body)
                .contains("Gustave Doré")
        );
        session.undo();
        assert!(session.doc.media.is_empty());
    }

    #[test]
    fn school_filters_do_not_invent_unknown_grade_or_language() {
        let mut entry = catalog()[0].clone();
        entry.grades.clear();
        entry.language.clear();
        entry.educational_use.clear();
        assert!(entry.matches_school_filters("", "", false));
        assert!(!entry.matches_school_filters("6e", "", false));
        assert!(!entry.matches_school_filters("", "À compléter", false));
        assert!(!entry.matches_school_filters("", "", true));
        entry.grades = vec!["6e".into(), "5e".into()];
        entry.language = "zxx".into();
        entry.educational_use = "À compléter".into();
        assert!(entry.matches_school_filters("6e", "À compléter", true));
        assert!(!entry.matches_school_filters("3e", "À compléter", true));
        entry.language = "en".into();
        assert!(!entry.matches_school_filters("6e", "À compléter", true));
        assert!(entry.matches_school_filters("6e", "À compléter", false));
    }
}
