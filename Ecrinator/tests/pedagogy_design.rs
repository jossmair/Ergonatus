use ecrinator::{blocks, core, pedagogy, storage};
use serde_json::json;
use wordcraft_doc::{Document, Path, StoryRef, para::ShapeKind, para_block};
use wordcraft_engine::{
    Session,
    layout::{
        Placed,
        display::{self, Draw},
    },
};
fn table_path(s: &Session) -> Path {
    let mut p = s.sel.focus.path.0.clone();
    p.truncate(p.len() - 3);
    Path(p)
}

#[test]
fn all_models_embed_their_icon_and_stay_editable_after_reopening() {
    for model in blocks::TEMPLATES {
        let mut s = Session::new(Document::new());
        blocks::insert(&mut s, model).unwrap();
        s.run(
            "text.insert",
            &json!({"text":"Un texte modifiable avec accents."}),
        )
        .unwrap();
        let doc = storage::decode(&storage::encode(&s.doc).unwrap()).unwrap();
        assert_eq!(doc, s.doc);
        assert!(doc.media.contains_key(&pedagogy::icon_key(model)));
        assert!(
            doc.plain_text(StoryRef::Body)
                .contains("Un texte modifiable")
        );
        let appearance = blocks::appearance(&s).unwrap();
        assert_eq!(appearance.title, *model);
        assert_eq!(appearance.radius, 8.);
        s.run("text.insert", &json!({"text":" Suite."})).unwrap();
        assert!(s.doc.plain_text(StoryRef::Body).contains("Suite."));
    }
}
#[test]
fn rounded_decoration_is_in_the_shared_pdf_and_editor_draw_list() {
    let mut s = Session::new(Document::new());
    blocks::insert(&mut s, "Propriété").unwrap();
    s.run(
        "text.insert",
        &json!({"text":"La propriété reste du texte sélectionnable."}),
    )
    .unwrap();
    let layout = s.layout();
    let page = &layout.pages[0];
    let draws = display::page_display(&s.doc, page, &Default::default());
    assert!(draws.iter().any(
        |d| matches!(d,Draw::Shape{kind:ShapeKind::RoundedRectangle,corner:Some(n),..}if *n>0)
    ));
    assert!(
        draws
            .iter()
            .any(|d| matches!(d,Draw::Image{media,..}if media==&pedagogy::icon_key("Propriété")))
    );
    assert!(
        draws
            .iter()
            .any(|d| matches!(d,Draw::Glyphs{text,..}if text.contains("propriété")))
    );
    let path = table_path(&s);
    s.doc
        .table_mut(StoryRef::Body, &path)
        .unwrap()
        .props
        .corner_radius = Some(f32::NAN);
    let draws = display::page_display(&s.doc, page, &Default::default());
    assert!(!draws.iter().any(|d| matches!(
        d,
        Draw::Shape {
            kind: ShapeKind::RoundedRectangle,
            ..
        }
    )));
}
#[test]
fn a_long_rounded_box_keeps_its_decoration_on_each_page_fragment() {
    let mut s = Session::new(Document::new());
    blocks::insert(&mut s, "Remarque").unwrap();
    s.run("text.insert",&json!({"text":(0..90).map(|n|format!("Remarque {n}. Le contenu reste éditable et continue sur la page suivante.\n")).collect::<String>()})).unwrap();
    let layout = s.layout();
    assert!(layout.pages.len() > 1);
    for page in &layout.pages {
        if page.items.iter().any(|i| matches!(i, Placed::Cell { .. })) {
            let draws = display::page_display(&s.doc, page, &Default::default());
            assert!(draws.iter().any(|d| matches!(
                d,
                Draw::Shape {
                    kind: ShapeKind::RoundedRectangle,
                    ..
                }
            )));
        }
    }
}
#[test]
fn upgrading_an_old_box_keeps_body_custom_colours_and_undo() {
    let mut s = Session::new(Document::new());
    blocks::insert(&mut s, "Remarque").unwrap();
    s.run("text.insert", &json!({"text":"Contenu original"}))
        .unwrap();
    let path = table_path(&s);
    let t = s.doc.table_mut(StoryRef::Body, &path).unwrap();
    t.props.description = None;
    t.props.corner_radius = None;
    let custom = wordcraft_doc::props::Rgb(250, 245, 230);
    t.props.shading = Some(custom);
    t.rows[0].cells[0].blocks[0] = para_block(core::text(
        "Remarque personnelle",
        15.,
        true,
        wordcraft_doc::props::Rgb(46, 99, 174),
    ));
    let before = s.doc.clone();
    let body = t_body(&s, path.clone());
    assert_eq!(blocks::modernize(&mut s).unwrap(), 1);
    assert!(std::sync::Arc::ptr_eq(&body, &t_body(&s, path.clone())));
    assert_eq!(
        s.doc.table(StoryRef::Body, &path).unwrap().props.shading,
        Some(custom)
    );
    assert_eq!(
        blocks::appearance(&s).unwrap().title,
        "Remarque personnelle"
    );
    assert_eq!(blocks::modernize(&mut s).unwrap(), 0);
    s.undo();
    assert_eq!(s.doc, before);
}
#[test]
fn adjacent_boxes_have_an_editable_space_between_them() {
    let mut s = Session::new(Document::new());
    blocks::insert(&mut s, "Définition").unwrap();
    let first = table_path(&s).last();
    s.sel = wordcraft_engine::Selection::caret(wordcraft_doc::Pos::body(first + 1, 0));
    let before = s.doc.clone();
    blocks::insert(&mut s, "Propriété").unwrap();
    let next = table_path(&s).last();
    assert_eq!(next, first + 2);
    assert!(
        s.doc.body[first + 1]
            .as_para()
            .is_some_and(|p| p.plain_text().is_empty())
    );
    s.undo();
    assert_eq!(s.doc, before);
}
fn t_body(s: &Session, path: Path) -> std::sync::Arc<wordcraft_doc::Block> {
    s.doc.table(StoryRef::Body, &path).unwrap().rows[0].cells[0].blocks[1].clone()
}
