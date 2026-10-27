use ecrinator::{
    blocks,
    core::{self, School},
    storage,
};
use serde_json::json;
use wordcraft_doc::{Document, Pos, StoryRef};
use wordcraft_engine::{Selection, Session};
fn selected_types(doc: &Document) -> Vec<String> {
    doc.control_ranges(StoryRef::Body)
        .into_iter()
        .filter_map(|r| {
            if r.control.exclusive_group == core::WORK_GROUP
                && matches!(
                    r.control.kind,
                    wordcraft_doc::ControlKind::CheckBox { checked: true, .. }
                )
            {
                Some(r.control.tag)
            } else {
                None
            }
        })
        .collect()
}
#[test]
fn work_type_is_one_native_choice_with_atomic_undo_and_roundtrip() {
    let mut s = Session::new(core::new_document(&School::default()).unwrap());
    assert_eq!(selected_types(&s.doc), ["ecr.lesson"]);
    for (tag, folder) in [
        ("ecr.exercises", "Exercices"),
        ("ecr.assessment", "Évaluations"),
        ("ecr.lesson", "Cours"),
    ] {
        let before = s.doc.clone();
        s.run("developer.toggleCheckBox", &json!({"control":tag}))
            .unwrap();
        assert_eq!(selected_types(&s.doc), [tag]);
        assert_eq!(School::read(&s.doc).folder_kind(), folder);
        let after = s.doc.clone();
        s.undo();
        assert_eq!(s.doc, before);
        s.redo();
        assert_eq!(s.doc, after);
        let saved = storage::decode(&storage::encode(&s.doc).unwrap()).unwrap();
        assert_eq!(selected_types(&saved), [tag]);
        s.run("developer.toggleCheckBox", &json!({"control":tag}))
            .unwrap();
        assert_eq!(
            selected_types(&s.doc),
            [tag],
            "The active type cannot be unticked"
        );
        s.run(
            "developer.toggleCheckBox",
            &json!({"control":tag,"value":false}),
        )
        .unwrap();
        assert_eq!(selected_types(&s.doc), [tag]);
    }
}
#[test]
fn legacy_multiple_or_empty_types_are_normalized_without_rerouting() {
    for (lesson, exercises, assessment, expected) in [
        (true, true, true, core::WorkKind::Assessment),
        (true, true, false, core::WorkKind::Exercises),
        (false, false, false, core::WorkKind::Lesson),
    ] {
        let school = School {
            lesson,
            exercises,
            assessment,
            ..Default::default()
        };
        let doc = core::new_document(&school).unwrap();
        let actual = School::read(&doc);
        assert_eq!(actual.work_kind(), expected);
        assert_eq!(selected_types(&doc).len(), 1);
        assert_eq!(
            [actual.lesson, actual.exercises, actual.assessment]
                .into_iter()
                .filter(|b| *b)
                .count(),
            1
        );
    }
    // Existing 0.7 controls had no group and could all be checked.
    let mut s = Session::new(core::new_document(&School::default()).unwrap());
    for r in s.doc.control_ranges(StoryRef::Body) {
        if let Some(c) = s.doc.control_mut(&r.start) {
            c.exclusive_group.clear();
        }
    }
    for tag in ["ecr.lesson", "ecr.exercises", "ecr.assessment"] {
        s.run(
            "developer.toggleCheckBox",
            &json!({"control":tag,"value":true}),
        )
        .unwrap();
    }
    let school = School::read(&s.doc);
    assert_eq!(school.work_kind(), core::WorkKind::Assessment);
    core::update_header(&mut s, &school).unwrap();
    assert_eq!(selected_types(&s.doc), ["ecr.assessment"]);
    assert_eq!(School::read(&s.doc).folder_kind(), "Évaluations");
}
#[test]
fn header_checkboxes_are_real_and_drive_organisator() {
    let mut s = Session::new(core::new_document(&School::default()).unwrap());
    assert_eq!(s.doc.control_ranges(StoryRef::Body).len(), 4);
    s.run(
        "developer.toggleCheckBox",
        &json!({"control":"ecr.assessment","value":true}),
    )
    .unwrap();
    assert_eq!(School::read(&s.doc).folder_kind(), "Évaluations");
    let again = storage::decode(&storage::encode(&s.doc).unwrap()).unwrap();
    assert!(School::read(&again).assessment);
    s.undo();
    assert!(!School::read(&s.doc).assessment);
}
#[test]
fn paragraphs_styles_lists_tables_and_images_roundtrip() {
    let mut s = Session::new(Document::new());
    s.run("text.insert", &json!({"text":"Élève\nCours de français"}))
        .unwrap();
    for (id, v) in [
        ("format.bold", json!({})),
        ("format.size", json!({"size":18})),
        ("para.lineSpacing", json!({"value":1.5})),
        ("format.spacing", json!({"points":1})),
        ("para.bullets", json!({})),
        ("insert.table", json!({"rows":2,"cols":3})),
        ("table.insertRowBelow", json!({})),
        ("table.insertColumnRight", json!({})),
        ("table.shading", json!({"color":"E0EDFF"})),
    ] {
        s.run(id, &v).unwrap();
    }
    let before = s.doc.clone();
    let after = storage::decode(&storage::encode(&before).unwrap()).unwrap();
    assert_eq!(before, after);
}
#[test]
fn find_replace_and_manual_page_break() {
    let mut s = Session::new(Document::new());
    s.run("text.insert", &json!({"text":"élève méthode élève"}))
        .unwrap();
    s.run(
        "edit.replaceAll",
        &json!({"text":"élève","with":"cours","special":false}),
    )
    .unwrap();
    assert_eq!(s.doc.plain_text(StoryRef::Body), "cours méthode cours");
    s.run("insert.pageBreak", &json!({})).unwrap();
    s.run("text.insert", &json!({"text":"Page suivante"}))
        .unwrap();
    assert_eq!(s.layout().pages.len(), 2);
}
#[test]
fn remove_frame_preserves_content_and_can_undo() {
    let mut s = Session::new(Document::new());
    s.run("text.insert", &json!({"text":"Texte conservé"}))
        .unwrap();
    s.sel = Selection {
        anchor: Pos::body(0, 0),
        focus: Pos::body(0, "Texte conservé".len()),
    };
    blocks::insert(&mut s, "Méthode").unwrap();
    let before = s.doc.clone();
    blocks::remove_frame(&mut s).unwrap();
    assert!(s.doc.plain_text(StoryRef::Body).contains("Texte conservé"));
    s.undo();
    assert_eq!(before, s.doc);
}
#[test]
fn odt_retains_text_tables_images_and_math() {
    let s = ecrinator::verification::fixture(false).unwrap();
    let bytes = ecrinator::exporters::bytes("cours.odt", &s.doc).unwrap();
    let imported = wordcraft_engine::io::open_bytes("cours.odt", &bytes).unwrap();
    let text = imported.plain_text(StoryRef::Body);
    assert!(text.contains("dénominateur"));
    assert!(text.contains("Cahiers"));
    assert!(!imported.media.is_empty());
    let mut math = 0;
    imported.objects_in_reading_order(&mut |o| {
        if matches!(o, wordcraft_doc::InlineObject::Equation { .. }) {
            math += 1
        }
    });
    assert_eq!(
        math, 0,
        "Import ODT : image de secours ; natif : structure mathématique."
    );
    let mut z = zip::ZipArchive::new(std::io::Cursor::new(bytes)).unwrap();
    use std::io::Read;
    let mut ml = String::new();
    z.by_name("Formula1/content.xml")
        .unwrap()
        .read_to_string(&mut ml)
        .unwrap();
    assert!(ml.contains("mfrac"));
}
