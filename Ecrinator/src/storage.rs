//! Bounded, versioned native documents. Writes are synced then atomically replaced.
use crate::core::NATIVE_VERSION;
use serde::{Deserialize, Serialize};
use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
};
use wordcraft_doc::Document;
pub const MAX_FILE: u64 = 64 * 1024 * 1024;
#[derive(Serialize, Deserialize)]
pub struct Project {
    pub format: String,
    pub version: u32,
    pub document: Document,
}
pub fn encode(doc: &Document) -> Result<Vec<u8>, String> {
    serde_json::to_vec(&Project {
        format: "Ergonatus.Ecrinator".into(),
        version: NATIVE_VERSION,
        document: doc.clone(),
    })
    .map_err(|e| e.to_string())
}
pub fn decode(bytes: &[u8]) -> Result<Document, String> {
    if bytes.len() as u64 > MAX_FILE {
        return Err("Document supérieur à la limite de 64 Mo.".into());
    }
    let envelope: serde_json::Value =
        serde_json::from_slice(bytes).map_err(|e| format!("Document illisible : {e}"))?;
    if envelope.get("format").and_then(|v| v.as_str()) != Some("Ergonatus.Ecrinator") {
        return Err("Ce fichier n’est pas un document Écrinator.".into());
    }
    if envelope.get("version").and_then(|v| v.as_u64()) != Some(NATIVE_VERSION as u64) {
        return Err("Version du document non prise en charge. Conservez l’original.".into());
    }
    let mut p: Project = serde_json::from_value(envelope)
        .map_err(|e| format!("Structure du document invalide : {e}"))?;
    p.document.ensure_nonempty();
    Ok(p.document)
}
pub fn read(path: &Path) -> Result<Document, String> {
    if fs::metadata(path).map_err(|e| e.to_string())?.len() > MAX_FILE {
        return Err("Document trop volumineux (64 Mo maximum).".into());
    }
    let bytes = fs::read(path).map_err(|e| e.to_string())?;
    if path
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("odt"))
    {
        crate::odt_project::open(&path.to_string_lossy(), &bytes)
    } else {
        decode(&bytes)
    }
}
pub fn atomic_write(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let mut temp = tempfile::Builder::new()
        .prefix(".ecrinator-")
        .suffix(".tmp")
        .tempfile_in(parent)
        .map_err(|e| e.to_string())?;
    temp.write_all(bytes).map_err(|e| e.to_string())?;
    temp.as_file().sync_all().map_err(|e| e.to_string())?;
    temp.persist(path).map_err(|e| e.error.to_string())?;
    Ok(())
}
pub fn save(path: &Path, doc: &Document) -> Result<(), String> {
    let bytes = encode(doc)?;
    if bytes.len() as u64 > MAX_FILE {
        return Err("Document trop volumineux pour le format natif (64 Mo).".into());
    }
    atomic_write(path, &bytes)
}
pub fn data_dir() -> PathBuf {
    if std::env::var_os("ECRINATOR_DATA_DIR").is_none() {
        if let Some(dir) = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(Path::to_path_buf))
        {
            if dir.join("portable.flag").is_file() {
                return dir.join("data");
            }
        }
    }
    std::env::var_os("ECRINATOR_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            std::env::var_os("LOCALAPPDATA")
                .map(PathBuf::from)
                .unwrap_or_else(std::env::temp_dir)
                .join("Ergonatus/ecrinator-rust")
        })
}
#[derive(Clone, Debug, PartialEq)]
pub struct Stamp {
    size: u64,
    modified: Option<std::time::SystemTime>,
}
pub fn stamp(path: &Path) -> Option<Stamp> {
    fs::metadata(path).ok().map(|m| Stamp {
        size: m.len(),
        modified: m.modified().ok(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn roundtrip_accents_and_media() {
        let d = crate::core::new_document(&Default::default()).unwrap();
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("évaluation élève.ecr");
        save(&p, &d).unwrap();
        assert_eq!(d, read(&p).unwrap());
    }
    #[test]
    fn rejects_future_version_without_touching_file() {
        assert!(
            decode(br#"{"format":"Ergonatus.Ecrinator","version":999}"#)
                .unwrap_err()
                .contains("Version")
        );
    }
    #[test]
    fn failure_preserves_original() {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("cours.ecr");
        fs::write(&p, b"original").unwrap();
        assert!(atomic_write(&p.join("impossible"), b"nouveau").is_err());
        assert_eq!(fs::read(&p).unwrap(), b"original");
    }
}
