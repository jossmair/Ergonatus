use ecrinator::blocks;
use serde_json::json;
use wordcraft_doc::{Document, StoryRef};
use wordcraft_engine::Session;
#[test]
fn box_restyle_move_and_undo_keep_text() {
    let mut s = Session::new(Document::new());
    blocks::insert(&mut s, "Définition").unwrap();
    s.run("text.insert", &json!({"text":"Contenu à garder"}))
        .unwrap();
    let mut style = blocks::appearance(&s).unwrap();
    style.title = "Ma définition".into();
    style.model = "À retenir".into();
    style.use_model_colors();
    assert_eq!(style.border, [103, 55, 190]);
    assert_eq!(style.background, [247, 242, 255]);
    style.background = [240, 250, 230];
    blocks::change(&mut s, &style).unwrap();
    assert!(s.doc.plain_text(StoryRef::Body).contains("Ma définition"));
    let before = s.doc.clone();
    blocks::move_box(&mut s, true).unwrap();
    assert!(
        s.doc
            .plain_text(StoryRef::Body)
            .contains("Contenu à garder")
    );
    s.undo();
    assert_eq!(before, s.doc);
}

#[test]
fn trash_removes_entire_box_and_undo_restores_it() {
    let mut s = Session::new(Document::new());
    blocks::insert(&mut s, "Définition").unwrap();
    s.run("text.insert", &json!({"text":"Contenu de la définition"}))
        .unwrap();
    let before = s.doc.clone();
    let caret = s.sel.focus.clone();
    assert!(blocks::selected(&s));
    blocks::delete(&mut s).unwrap();
    assert!(!blocks::selected(&s));
    assert!(
        !s.doc
            .plain_text(StoryRef::Body)
            .contains("Contenu de la définition")
    );
    assert!(s.doc.para_at(&s.sel.focus).is_some());
    s.undo();
    assert_eq!(s.doc, before);
    assert_eq!(s.sel.focus, caret);
    s.redo();
    assert!(
        !s.doc
            .plain_text(StoryRef::Body)
            .contains("Contenu de la définition")
    );
}
#[test]
fn trash_never_targets_the_header_or_an_ordinary_table() {
    let mut s = Session::new(ecrinator::core::new_document(&Default::default()).unwrap());
    s.sel = wordcraft_engine::Selection::caret(wordcraft_doc::Pos::new(
        StoryRef::Body,
        wordcraft_doc::Path(vec![0, 0, 1, 0]),
        0,
    ));
    let before = s.doc.clone();
    assert!(!blocks::selected(&s));
    assert!(blocks::delete(&mut s).is_err());
    assert_eq!(s.doc, before);
    s.sel = wordcraft_engine::Selection::caret(ecrinator::core::writing_position(&s.doc));
    s.run("insert.table", &json!({"rows":2,"cols":2})).unwrap();
    let before = s.doc.clone();
    assert!(!blocks::selected(&s));
    assert!(blocks::delete(&mut s).is_err());
    assert_eq!(s.doc, before);
}
