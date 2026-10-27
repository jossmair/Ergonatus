//! Standard ODT output with an optional native editing snapshot in its package.
//! External changes invalidate that snapshot and are read from standard ODF content.
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    io::{Cursor, Read, Write},
};
use wordcraft_doc::Document;
use zip::{CompressionMethod, ZipArchive, ZipWriter, write::SimpleFileOptions};
const STATE: &str = "Ecrinator/document.json";
#[derive(Serialize, Deserialize)]
struct Snapshot {
    version: u32,
    entries: BTreeMap<String, (u32, u64)>,
    project: serde_json::Value,
}
pub fn encode(doc: &Document) -> Result<Vec<u8>, String> {
    let odt = crate::exporters::bytes("cours.odt", doc)?;
    let mut archive = ZipArchive::new(Cursor::new(odt)).map_err(|e| e.to_string())?;
    let mut files = Vec::new();
    let mut entries = BTreeMap::new();
    for i in 0..archive.len() {
        let mut f = archive.by_index(i).map_err(|e| e.to_string())?;
        let mut data = Vec::new();
        f.read_to_end(&mut data).map_err(|e| e.to_string())?;
        files.push((f.name().to_owned(), data));
    }
    let manifest = files
        .iter_mut()
        .find(|(name, _)| name == "META-INF/manifest.xml")
        .ok_or("ODT sans manifeste")?;
    let xml = String::from_utf8(manifest.1.clone()).map_err(|e| e.to_string())?;
    manifest.1=xml.replace("</manifest:manifest>","<manifest:file-entry manifest:full-path=\"Ecrinator/document.json\" manifest:media-type=\"application/json\"/></manifest:manifest>").into_bytes();
    // Build once, then fingerprint the exact public parts. CRC detects changes;
    // it is not used to authenticate untrusted data (native decode is bounded).
    let mut writer = ZipWriter::new(Cursor::new(Vec::new()));
    for (name, data) in &files {
        let method = if name == "mimetype" {
            CompressionMethod::Stored
        } else {
            CompressionMethod::Deflated
        };
        writer
            .start_file(
                &name,
                SimpleFileOptions::default().compression_method(method),
            )
            .map_err(|e| e.to_string())?;
        writer.write_all(&data).map_err(|e| e.to_string())?;
    }
    let raw = writer.finish().map_err(|e| e.to_string())?.into_inner();
    let mut read = ZipArchive::new(Cursor::new(&raw)).map_err(|e| e.to_string())?;
    for i in 0..read.len() {
        let f = read.by_index(i).map_err(|e| e.to_string())?;
        entries.insert(f.name().to_owned(), (f.crc32(), f.size()));
    }
    let project =
        serde_json::from_slice(&crate::storage::encode(doc)?).map_err(|e| e.to_string())?;
    let state = serde_json::to_vec(&Snapshot {
        version: 1,
        entries,
        project,
    })
    .map_err(|e| e.to_string())?;
    if state.len() as u64 > crate::storage::MAX_FILE {
        return Err("Document trop volumineux pour la sauvegarde complète.".into());
    }
    // Write one fresh package. Appending to a completed ZIP leaves a second
    // local-header segment that LibreOffice's ODF package reader rejects.
    let mut append = ZipWriter::new(Cursor::new(Vec::new()));
    for (name, data) in files {
        let method = if name == "mimetype" {
            CompressionMethod::Stored
        } else {
            CompressionMethod::Deflated
        };
        append
            .start_file(
                &name,
                SimpleFileOptions::default().compression_method(method),
            )
            .map_err(|e| e.to_string())?;
        append.write_all(&data).map_err(|e| e.to_string())?;
    }
    append
        .start_file(
            STATE,
            SimpleFileOptions::default().compression_method(CompressionMethod::Deflated),
        )
        .map_err(|e| e.to_string())?;
    append.write_all(&state).map_err(|e| e.to_string())?;
    Ok(append.finish().map_err(|e| e.to_string())?.into_inner())
}
/// None means a normal or externally edited ODT: use the standards reader.
pub fn native_snapshot(bytes: &[u8]) -> Result<Option<Document>, String> {
    let mut archive = ZipArchive::new(Cursor::new(bytes)).map_err(|e| e.to_string())?;
    let state = {
        let Ok(f) = archive.by_name(STATE) else {
            return Ok(None);
        };
        if f.size() > crate::storage::MAX_FILE {
            return Err("État Écrinator trop volumineux.".into());
        }
        let mut data = Vec::new();
        f.take(crate::storage::MAX_FILE + 1)
            .read_to_end(&mut data)
            .map_err(|e| e.to_string())?;
        data
    };
    let snap: Snapshot = serde_json::from_slice(&state).map_err(|e| e.to_string())?;
    if snap.version != 1 {
        return Ok(None);
    }
    let mut actual = BTreeMap::new();
    for i in 0..archive.len() {
        let f = archive.by_index(i).map_err(|e| e.to_string())?;
        if f.name() != STATE {
            actual.insert(f.name().to_owned(), (f.crc32(), f.size()));
        }
    }
    if actual != snap.entries {
        return Ok(None);
    }
    crate::storage::decode(&serde_json::to_vec(&snap.project).map_err(|e| e.to_string())?).map(Some)
}
pub fn open(name: &str, bytes: &[u8]) -> Result<Document, String> {
    if name.to_ascii_lowercase().ends_with(".odt") {
        if let Some(doc) = native_snapshot(bytes)? {
            return Ok(doc);
        }
    }
    let mut doc = wordcraft_engine::io::open_bytes(name, bytes)?;
    if name.to_ascii_lowercase().ends_with(".odt") {
        crate::image_credits::restore_odt(&mut doc, bytes)?;
    }
    Ok(doc)
}
