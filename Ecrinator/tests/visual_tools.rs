use ecrinator::{core, exporters, library, odt_project, storage, timeline};
use std::io::{Cursor, Read, Write};
use wordcraft_doc::{Document, InlineObject, Pos};
use wordcraft_engine::{Selection, Session};
use zip::{ZipArchive, ZipWriter, write::SimpleFileOptions};
fn session() -> Session {
    ecrinator::verification::init_fonts();
    let mut s = Session::new(core::new_document(&core::School::default()).unwrap());
    s.sel = Selection::caret(core::writing_position(&s.doc));
    s
}

#[test]
fn library_never_reintroduces_known_ambiguous_math_labels() {
    let report: serde_json::Value = serde_json::from_str(include_str!(
        "../assets/library/reference/sesamath/COORDINATE-EXCLUSIONS.json"
    ))
    .unwrap();
    let excluded = report["ids"].as_array().unwrap();
    assert!(!excluded.is_empty());
    for id in excluded {
        assert!(
            !library::catalog()
                .iter()
                .any(|entry| entry.id == id.as_str().unwrap())
        );
    }
}
#[test]
fn timeline_edit_roundtrip_undo_and_real_exports() {
    let mut s = session();
    let original = storage::encode(&s.doc).unwrap();
    let mut t = timeline::Timeline::default();
    timeline::apply(&mut s, &t).unwrap();
    assert_eq!(timeline::selected(&s).unwrap().1, t);
    s.run("edit.undo", &serde_json::json!({})).unwrap();
    assert_eq!(storage::encode(&s.doc).unwrap(), original);
    s.run("edit.redo", &serde_json::json!({})).unwrap();
    t.events[1].label = "Une date importante pour la République".into();
    timeline::apply(&mut s, &t).unwrap();
    let recovered = storage::decode(&storage::encode(&s.doc).unwrap()).unwrap();
    let mut seen = Vec::new();
    recovered.objects_in_reading_order(&mut |o| {
        if let Some(m) = timeline::model(o) {
            seen.push(m);
        }
    });
    assert_eq!(seen, vec![t]);
    for ext in ["odt", "docx", "pdf"] {
        let bytes = exporters::bytes(&format!("cours.{ext}"), &recovered).unwrap();
        assert!(bytes.len() > 1000);
        if ext != "pdf" {
            let imported =
                wordcraft_engine::io::open_bytes(&format!("cours.{ext}"), &bytes).unwrap();
            let mut images = 0;
            imported.objects_in_reading_order(&mut |o| {
                images += usize::from(matches!(o, InlineObject::Image { .. }));
            });
            assert!(images >= 1);
        }
    }
    assert_eq!(
        storage::encode(&s.doc).unwrap(),
        storage::encode(&recovered).unwrap()
    );
}
#[test]
fn timeline_invalid_data_never_changes_document() {
    let mut s = session();
    let original = storage::encode(&s.doc).unwrap();
    let mut t = timeline::Timeline::default();
    t.events[0].date.clear();
    assert!(timeline::apply(&mut s, &t).is_err());
    assert_eq!(original, storage::encode(&s.doc).unwrap());
    t = timeline::Timeline::default();
    t.events.resize(9, t.events[0].clone());
    assert!(timeline::apply(&mut s, &t).is_err());
    let t = timeline::Timeline::default();
    assert!(t.object(f32::NAN).is_err());
    s.sel = Selection::caret(Pos::new(
        wordcraft_doc::StoryRef::Body,
        wordcraft_doc::Path(vec![0, 0, 1, 0]),
        0,
    ));
    assert!(timeline::apply(&mut s, &t).is_err());
    assert!(library::insert(&mut s, &library::catalog()[0]).is_err());
    assert_eq!(original, storage::encode(&s.doc).unwrap());
}
#[test]
fn offline_library_is_complete_attributed_and_undoable() {
    let all = library::catalog();
    assert!(!all.is_empty());
    assert!(all.iter().all(|e| e.license.starts_with("CC BY")
        || e.license.starts_with("CC0")
        || e.license.starts_with("Public domain")));
    for cat in ["Cartes", "SVT", "Physique-chimie"] {
        assert!(all.iter().filter(|e| e.category == cat).count() >= 5);
    }
    let mut s = session();
    let original = storage::encode(&s.doc).unwrap();
    for e in all {
        assert!(!e.author.is_empty());
        assert!(
            e.source_url.starts_with("https://")
                || e.source_url
                    .starts_with("urn:ergonatus:ecrinator:illustration:")
        );
        assert!(!e.license.is_empty());
        let bytes = library::read_asset(e, false).unwrap();
        let img = image::load_from_memory(&bytes).unwrap();
        assert_eq!((img.width(), img.height()), (e.width, e.height));
        assert!(!library::thumbnail(e).unwrap().is_empty());
    }
    let e = all.iter().find(|e| e.id == "cellule-animale").unwrap();
    library::insert(&mut s, e).unwrap();
    let text = s
        .doc
        .body
        .iter()
        .filter_map(|b| b.as_para())
        .map(|p| p.plain_text())
        .collect::<Vec<_>>()
        .join("\n");
    assert!(!text.contains(&e.source_url));
    assert!(!text.contains(&e.license));
    let credit = ecrinator::image_credits::selected(&s).unwrap();
    assert_eq!(credit.source_url, e.source_url);
    let bytes = odt_project::encode(&s.doc).unwrap();
    let open = odt_project::open("cours.odt", &bytes).unwrap();
    assert_eq!(
        storage::encode(&open).unwrap(),
        storage::encode(&s.doc).unwrap()
    );
    let mut zip = ZipArchive::new(Cursor::new(&bytes)).unwrap();
    let mut meta = String::new();
    zip.by_name("meta.xml")
        .unwrap()
        .read_to_string(&mut meta)
        .unwrap();
    assert!(meta.contains("meta:user-defined"));
    assert!(meta.contains(&e.source_url));
    // A standard ODT copy has no private editing snapshot, yet its attribution survives.
    let standard = exporters::bytes("cours.odt", &s.doc).unwrap();
    let external = odt_project::open("cours.odt", &standard).unwrap();
    assert_eq!(
        ecrinator::image_credits::active(&external)[0].source_url,
        e.source_url
    );
    s.run("edit.undo", &serde_json::json!({})).unwrap();
    assert_eq!(storage::encode(&s.doc).unwrap(), original);
}
#[test]
fn old_automatic_source_lines_are_migrated_but_student_captions_are_preserved() {
    let mut s = session();
    let e = library::catalog()
        .iter()
        .find(|e| e.id == "cellule-animale")
        .unwrap();
    library::insert(&mut s, e).unwrap();
    s.run(
        "text.insert",
        &serde_json::json!({"text":format!("\n{}\nMa légende personnelle",e.credit())}),
    )
    .unwrap();
    let original = s.doc.clone();
    assert_eq!(
        ecrinator::image_credits::migrate_visible(&mut s).unwrap(),
        1
    );
    let text = s.doc.plain_text(wordcraft_doc::StoryRef::Body);
    assert!(!text.contains(&e.source_url));
    assert!(text.contains("Ma légende personnelle"));
    assert_eq!(
        ecrinator::image_credits::active(&s.doc)[0].source_url,
        e.source_url
    );
    s.undo();
    assert_eq!(s.doc, original);
}
#[test]
fn external_library_figures_insert_roundtrip_and_search_without_accents() {
    let e = library::catalog()
        .iter()
        .find(|e| e.id.starts_with("sesamath-"))
        .unwrap();
    assert!(
        library::bytes(&e.id).is_some(),
        "The entire school library must be embedded"
    );
    let mut s = session();
    let before = s.doc.clone();
    library::insert(&mut s, e).unwrap();
    let bytes = odt_project::encode(&s.doc).unwrap();
    assert_eq!(odt_project::open("cours.odt", &bytes).unwrap(), s.doc);
    s.undo();
    assert_eq!(s.doc, before);
    assert_eq!(
        library::normalize("Cœur, ÉLECTRICITÉ"),
        "coeur, electricite"
    );
    assert!(library::catalog().iter().any(|e| e.matches("SVT", "coeur")));
    let mut hostile = e.clone();
    hostile.filename = "../document.odt".into();
    assert!(library::read_asset(&hostile, false).is_err());
    hostile = e.clone();
    hostile.sha256 = "00".repeat(32);
    assert!(library::read_asset(&hostile, false).is_err());
}
#[test]
fn odt_is_standard_and_preserves_native_state_until_external_edits() {
    let mut s = session();
    timeline::apply(&mut s, &timeline::Timeline::default()).unwrap();
    let bytes = odt_project::encode(&s.doc).unwrap();
    let native = odt_project::native_snapshot(&bytes).unwrap().unwrap();
    // Each local record must directly follow the previous compressed payload;
    // a completed ZIP must never be embedded before the private state record.
    let mut zip = ZipArchive::new(Cursor::new(&bytes)).unwrap();
    let mut end = 0;
    for i in 0..zip.len() {
        let entry = zip.by_index(i).unwrap();
        assert_eq!(entry.header_start(), end);
        end = entry.data_start() + entry.compressed_size();
    }
    assert_eq!(
        storage::encode(&native).unwrap(),
        storage::encode(&s.doc).unwrap()
    );
    let standard = wordcraft_engine::io::open_bytes("cours.odt", &bytes).unwrap();
    assert!(!standard.body.is_empty());
    let mut source = ZipArchive::new(Cursor::new(&bytes)).unwrap();
    let first = source.by_index(0).unwrap();
    assert_eq!(first.name(), "mimetype");
    assert_eq!(first.compression(), zip::CompressionMethod::Stored);
    drop(first);
    let mut writer = ZipWriter::new(Cursor::new(Vec::new()));
    for i in 0..source.len() {
        let mut f = source.by_index(i).unwrap();
        let name = f.name().to_owned();
        let mut data = Vec::new();
        f.read_to_end(&mut data).unwrap();
        if name == "content.xml" {
            data.extend_from_slice(b"\n");
        }
        writer
            .start_file(name, SimpleFileOptions::default())
            .unwrap();
        writer.write_all(&data).unwrap();
    }
    let changed = writer.finish().unwrap().into_inner();
    assert!(odt_project::native_snapshot(&changed).unwrap().is_none());
    assert!(
        !odt_project::open("cours.odt", &changed)
            .unwrap()
            .body
            .is_empty()
    );
}
#[test]
fn ordinary_shapes_and_charts_remain_visible_in_odt() {
    let mut s = Session::new(Document::new());
    s.sel = Selection::caret(Pos::body(0, 0));
    s.run("insert.shape",&serde_json::json!({"kind":"triangle","width":120.,"height":90.,"fill":"E6F0FF","stroke":"0757ED"})).unwrap();
    s.sel = Selection::caret(s.sel.focus.clone());
    s.run("text.insert", &serde_json::json!({"text":"\n"}))
        .unwrap();
    s.run("insert.chart",&serde_json::json!({"type":"column","title":"Mesures","data":{"categories":["A","B"],"series":[{"name":"Résultats","values":[3,5]}]}})).unwrap();
    let bytes = exporters::bytes("cours.odt", &s.doc).unwrap();
    let imported = wordcraft_engine::io::open_bytes("cours.odt", &bytes).unwrap();
    let mut count = 0;
    imported.objects_in_reading_order(&mut |o| {
        count += usize::from(matches!(o, InlineObject::Image { .. }));
    });
    assert_eq!(count, 2);
}
#[test]
fn odt_preserves_panoramic_background_and_colored_teaching_card_styles() {
    let mut s = session();
    ecrinator::blocks::insert(&mut s, "Propriété").unwrap();
    s.run(
        "text.insert",
        &serde_json::json!({"text":"Mon texte reste éditable dans un tableau ODT."}),
    )
    .unwrap();
    let original = s.doc.clone();
    let bytes = exporters::bytes("cours.odt", &s.doc).unwrap();
    assert_eq!(original, s.doc);
    let mut zip = ZipArchive::new(Cursor::new(bytes)).unwrap();
    let mut background = Vec::new();
    zip.by_name("Pictures/ecr-banner.png")
        .unwrap()
        .read_to_end(&mut background)
        .unwrap();
    let image = image::load_from_memory(&background).unwrap();
    assert!(image.width() > 1700 && image.height() >= 300 && image.height() <= 305);
    let mut content = String::new();
    zip.by_name("content.xml")
        .unwrap()
        .read_to_string(&mut content)
        .unwrap();
    assert!(content.contains("style:background-image") && content.contains("EcrCell2"));
    assert!(content.contains("fo:border-left=\"3pt solid #"));
    assert!(content.contains("Mon texte reste éditable"));
    let mut manifest = String::new();
    zip.by_name("META-INF/manifest.xml")
        .unwrap()
        .read_to_string(&mut manifest)
        .unwrap();
    assert!(manifest.contains("Pictures/ecr-banner.png"));
}
#[test]
fn odt_drawing_fallback_does_not_replace_an_existing_image_with_the_same_key() {
    let original = library::bytes("cellule-animale").unwrap();
    let mut doc = Document::new();
    let key = "ecr-vector-fallback-0.png".to_string();
    doc.media
        .insert(key.clone(), std::sync::Arc::new(original.to_vec()));
    let end = doc
        .insert_object(
            &Pos::body(0, 0),
            InlineObject::Image {
                media: key,
                w: 80.,
                h: 50.,
                alt: "Original à conserver".into(),
                float: Default::default(),
                crop: [0.; 4],
                ole: None,
            },
            &Default::default(),
        )
        .unwrap();
    let mut s = Session::new(doc);
    s.sel = Selection::caret(end);
    s.run("text.insert", &serde_json::json!({"text":"\n"}))
        .unwrap();
    s.run("insert.shape",&serde_json::json!({"kind":"triangle","width":80.,"height":60.,"fill":"E6F0FF","stroke":"0757ED"})).unwrap();
    let before = s.doc.clone();
    let bytes = exporters::bytes("cours.odt", &s.doc).unwrap();
    assert_eq!(s.doc, before);
    let imported = wordcraft_engine::io::open_bytes("cours.odt", &bytes).unwrap();
    assert!(
        imported
            .media
            .values()
            .any(|data| data.as_slice() == original)
    );
}

#[test]
fn every_college_resource_and_thumbnail_is_available_without_a_sidecar() {
    assert!(!library::catalog().is_empty());
    assert!(
        library::catalog()
            .iter()
            .all(|e| !e.id.starts_with("college-atlas-") && !e.id.starts_with("college-om-"))
    );
    assert!(
        library::catalog()
            .iter()
            .any(|e| e.id.starts_with("sesamath-") && e.grades.iter().any(|g| g == "6e"))
    );
    for entry in library::catalog() {
        assert!(
            library::bytes(&entry.id).is_some(),
            "{} requires a sidecar",
            entry.id
        );
        assert!(
            library::embedded_thumbnail(&entry.id).is_some(),
            "{} has no integrated thumbnail",
            entry.id
        );
    }
    for subject in [
        "Mathématiques",
        "SVT",
        "Physique-chimie",
        "Cartes",
        "Français",
        "Technologie",
        "Éducation musicale",
        "Arts plastiques",
    ] {
        assert!(
            library::catalog().iter().any(|e| e.matches(subject, "")
                && e.monochrome
                && e.unlabelled
                && e.kind != "Pictogramme"),
            "Missing practical supports for {subject}"
        );
    }
}

#[test]
fn monochrome_diagrams_and_school_maps_export_to_pdf_and_standard_odt() {
    let mut s = session();
    let mut expected = Vec::new();
    for id in [
        "college-fiche-circuit-derivation",
        "college-fond-monde-frontieres",
    ] {
        let e = library::catalog().iter().find(|e| e.id == id).unwrap();
        library::insert(&mut s, e).unwrap();
        expected.push(library::read_asset(e, false).unwrap());
        s.run("text.insert", &serde_json::json!({"text":"\n"}))
            .unwrap();
    }
    let odt = exporters::bytes("atlas.odt", &s.doc).unwrap();
    let mut zip = ZipArchive::new(Cursor::new(odt)).unwrap();
    let mut pictures = Vec::new();
    for i in 0..zip.len() {
        let mut file = zip.by_index(i).unwrap();
        if file.name().starts_with("Pictures/") && file.name().ends_with(".png") {
            let mut bytes = Vec::new();
            file.read_to_end(&mut bytes).unwrap();
            pictures.push(bytes);
        }
    }
    for image in expected {
        assert!(
            pictures.iter().any(|p| p.as_slice() == image.as_ref()),
            "Monochrome source must survive the standard ODT export"
        );
    }
    let pdf = exporters::bytes("atlas.pdf", &s.doc).unwrap();
    assert!(pdf.starts_with(b"%PDF-") && pdf.len() > 2000);
}
