use ecrinator::{
    core::{self, School},
    storage,
};
use serde_json::json;
use std::collections::HashSet;
use wordcraft_doc::{Document, Pos, StoryRef, para_block, props::Rgb};
use wordcraft_engine::{Selection, Session};

#[test]
fn thirteen_subjects_have_different_embedded_art_and_the_chapter_in_the_banner() {
    let mut images = HashSet::new();
    let mut colors = HashSet::new();
    for subject in core::SUBJECTS.iter().filter(|s| **s != core::BLANK) {
        let school = School {
            subject: (*subject).into(),
            chapter: 7,
            title: "Les cellules".into(),
            ..Default::default()
        };
        let doc = core::new_document(&school).unwrap();
        assert_eq!(doc.body.len(), 2);
        assert!(
            doc.body[0].as_table().unwrap().props.description.as_deref()
                == Some(core::BANNER_VERSION)
        );
        assert!(doc.plain_text(StoryRef::Body).contains("Chapitre : "));
        assert_eq!(School::read(&doc).chapter, 7);
        assert!(doc.body[1].as_para().unwrap().props.shading.is_none());
        assert_eq!(doc.media.len(), 1);
        let c = school.banner_background();
        assert!(
            colors.insert((c.0, c.1, c.2)),
            "duplicate background for {subject}"
        );
        let table = doc.body[0].as_table().unwrap();
        assert_eq!(table.props.shading, Some(c));
        assert_eq!(table.props.background_alpha, Some(1.));
        let key = ecrinator::subjects::background_key(subject);
        let bytes = doc.media.get(&key).unwrap();
        assert!(
            bytes.len() < 900_000,
            "banner resource too heavy: {subject}"
        );
        let image = image::load_from_memory(bytes).unwrap().to_rgba8();
        assert!(image.width() >= 1400 && image.height() >= 450);
        assert!(table.props.geometry_locked);
        assert_eq!(table.props.background_wash, Some(0.88));
        assert!(table.props.background_crop.is_some());
        assert!(
            images.insert(bytes.to_vec()),
            "same illustration for {subject}"
        );
    }
    assert_eq!(images.len(), 13);
}

#[test]
fn blank_page_has_no_banner_title_art_or_checkbox() {
    let doc = core::new_document(&School {
        subject: core::BLANK.into(),
        ..Default::default()
    })
    .unwrap();
    assert_eq!(doc.body.len(), 1);
    assert!(doc.media.is_empty());
    assert_eq!(doc.plain_text(StoryRef::Body), "");
    assert!(doc.control_ranges(StoryRef::Body).is_empty());
    assert_eq!(core::writing_position(&doc), Pos::body(0, 0));
    assert_eq!(
        storage::decode(&storage::encode(&doc).unwrap()).unwrap(),
        doc
    );
}

#[test]
fn removing_and_restoring_banner_preserves_body_cursor_and_undo() {
    let school = School::default();
    let mut s = Session::new(core::new_document(&school).unwrap());
    s.sel = Selection::caret(core::writing_position(&s.doc));
    s.run("text.insert", &json!({"text":"Mon cours à conserver"}))
        .unwrap();
    let before = s.doc.clone();
    let offset = s.sel.focus.off;
    let hidden = School {
        show_banner: false,
        ..school.clone()
    };
    core::update_header(&mut s, &hidden).unwrap();
    assert_eq!(s.doc.body.len(), 1);
    assert_eq!(s.sel.focus, Pos::body(0, offset));
    assert_eq!(s.doc.plain_text(StoryRef::Body), "Mon cours à conserver");
    s.undo();
    assert_eq!(s.doc, before);
    core::update_header(
        &mut s,
        &School {
            subject: core::BLANK.into(),
            show_banner: false,
            ..school
        },
    )
    .unwrap();
    assert_eq!(s.doc.plain_text(StoryRef::Body), "Mon cours à conserver");
}

#[test]
fn old_imposed_chapter_moves_into_the_banner_without_changing_the_course() {
    let mut doc = core::new_document(&School::default()).unwrap();
    doc.table_mut(StoryRef::Body, &wordcraft_doc::Path(vec![0]))
        .unwrap()
        .props
        .description = None;
    let table = doc
        .table_mut(StoryRef::Body, &wordcraft_doc::Path(vec![0]))
        .unwrap();
    table.rows[0].cells[1].blocks.retain(|b| {
        b.as_para()
            .is_none_or(|p| p.props.style.as_deref() != Some(core::BANNER_CHAPTER))
    });
    let mut title = core::text("3. Ancien chapitre", 22., true, Rgb(40, 90, 180));
    title.props.style = Some(core::CHAPTER.into());
    doc.body.insert(1, para_block(title));
    doc.body[2] = para_block(core::text("Texte conservé", 12., false, Rgb(30, 49, 73)));
    for prop in &mut doc.custom_props {
        if prop.name.contains("School") {
            let mut meta: serde_json::Value = serde_json::from_str(&prop.value).unwrap();
            meta.as_object_mut().unwrap().remove("show_banner");
            prop.value = meta.to_string();
        }
    }
    assert!(core::needs_banner_refresh(&doc));
    let original = doc.clone();
    let mut s = Session::new(doc);
    s.sel = Selection::caret(Pos::body(2, 3));
    let school = School::read(&s.doc);
    assert!(school.show_banner);
    assert_eq!(school.chapter, 3);
    core::update_header(&mut s, &school).unwrap();
    assert!(!core::needs_banner_refresh(&s.doc));
    assert_eq!(s.doc.body.len(), 2);
    assert_eq!(School::read(&s.doc).title, "Ancien chapitre");
    assert!(s.doc.plain_text(StoryRef::Body).contains("Chapitre : "));
    assert_eq!(
        s.doc.body[1].as_para().unwrap().plain_text(),
        "Texte conservé"
    );
    assert_eq!(s.sel.focus, Pos::body(1, 3));
    s.undo();
    assert_eq!(s.doc, original);
}

#[test]
fn clear_formatting_removes_the_entire_title_at_a_caret_and_can_undo() {
    let mut doc = Document::new();
    let mut p = core::text("Un titre que je veux retirer", 22., true, Rgb(40, 90, 180));
    p.props.style = Some(core::CHAPTER.into());
    p.props.shading = Some(Rgb(220, 235, 255));
    doc.body[0] = para_block(p);
    let original = doc.clone();
    let mut s = Session::new(doc);
    s.sel = Selection::caret(Pos::body(0, 5));
    core::clear_formatting(&mut s).unwrap();
    let p = s.doc.body[0].as_para().unwrap();
    assert!(p.props.style.is_none());
    assert!(p.props.shading.is_none());
    assert!(
        p.runs
            .iter()
            .all(|r| r.props.size.is_none() && r.props.bold.is_none() && r.props.color.is_none())
    );
    assert_eq!(p.plain_text(), "Un titre que je veux retirer");
    assert_eq!(s.sel.focus, Pos::body(0, 5));
    s.undo();
    assert_eq!(s.doc, original);
}

#[test]
fn panoramic_banner_touches_page_edges_without_covering_the_writing() {
    use wordcraft_engine::layout::{
        Placed,
        display::{self, Draw},
    };
    let school = School::default();
    let mut s = Session::new(core::new_document(&school).unwrap());
    s.sel = Selection::caret(core::writing_position(&s.doc));
    s.run(
        "text.insert",
        &json!({"text":"Le début du cours.\n".repeat(110)}),
    )
    .unwrap();
    let layout = s.layout();
    assert!(layout.pages.len() > 1);
    let page = &layout.pages[0];
    let cells: Vec<_> = page
        .items
        .iter()
        .filter_map(|i| match i {
            Placed::Cell { table, rect, .. } if table.0 == vec![0] => Some(rect),
            _ => None,
        })
        .collect();
    assert_eq!(cells.len(), 3);
    let left = cells.iter().map(|r| r.x).fold(f32::INFINITY, f32::min);
    let right = cells.iter().map(|r| r.right()).fold(0., f32::max);
    let top = cells.iter().map(|r| r.y).fold(f32::INFINITY, f32::min);
    let bottom = cells.iter().map(|r| r.bottom()).fold(0., f32::max);
    assert!(
        left.abs() < 0.1 && top.abs() < 0.1,
        "Banner origin {left},{top}"
    );
    assert!((right - 595.276).abs() < 0.1, "Banner width: {right}");
    for item in &page.items {
        if let Placed::Lines { path, y, .. } = item {
            if path.0.len() == 1 && path.0[0] > 0 {
                assert!(
                    *y >= bottom + 10.,
                    "body overlaps banner: y={y}, bottom={bottom}"
                );
            }
        }
    }
    let draws = display::page_display(&s.doc, page, &Default::default());
    assert!(draws.iter().any(|d| matches!(d,Draw::Image{media,alpha,..} if media==&ecrinator::subjects::background_key("Français") && (*alpha-1.).abs()<0.001)));
    for page in layout.pages.iter().skip(1) {
        for item in &page.items {
            if let Placed::Lines { path, y, .. } = item {
                if path.0.len() == 1 {
                    assert!(*y >= s.doc.last_section.margin_top - 0.1);
                }
            }
        }
    }
}
#[test]
fn odt_adapts_the_banner_to_printable_width_without_mutating_native() {
    use std::io::{Cursor, Read};
    let doc = core::new_document(&School::default()).unwrap();
    let original = doc.clone();
    let bytes = ecrinator::exporters::bytes("cours.odt", &doc).unwrap();
    assert_eq!(doc, original);
    let mut archive = zip::ZipArchive::new(Cursor::new(bytes)).unwrap();
    let mut xml = String::new();
    archive
        .by_name("content.xml")
        .unwrap()
        .read_to_string(&mut xml)
        .unwrap();
    assert!(xml.contains("Chapitre : "));
    assert!(xml.contains("Français"));
    let roundtrip = wordcraft_engine::io::open_bytes(
        "cours.odt",
        &ecrinator::exporters::bytes("cours.odt", &doc).unwrap(),
    )
    .unwrap();
    let table = roundtrip.body.iter().find_map(|b| b.as_table()).unwrap();
    let width: f32 = table.grid.iter().sum();
    assert!(
        width
            <= doc.last_section.page_w
                - doc.last_section.margin_left
                - doc.last_section.margin_right
                + 1.,
        "ODT header overflow {width}"
    );
}

#[test]
fn chapter_is_a_real_dropdown_with_only_a_number_and_can_undo() {
    let school = School {
        chapter: 7,
        title: "Un titre ancien conservé dans les métadonnées".into(),
        ..Default::default()
    };
    let mut s = Session::new(core::new_document(&school).unwrap());
    let range = s
        .doc
        .control_ranges(StoryRef::Body)
        .into_iter()
        .find(|r| r.control.tag == "ecr.chapter")
        .unwrap();
    assert!(matches!(
        range.control.kind,
        wordcraft_doc::ControlKind::DropDown { .. }
    ));
    assert_eq!(s.doc.control_text(&range), "7");
    assert!(s.doc.plain_text(StoryRef::Body).contains("Un titre ancien"));
    let before = s.doc.clone();
    s.run(
        "developer.chooseItem",
        &json!({"control":"ecr.chapter","value":"12"}),
    )
    .unwrap();
    assert_eq!(School::read(&s.doc).chapter, 12);
    assert_eq!(School::read(&s.doc).title, school.title);
    let loaded = storage::decode(&storage::encode(&s.doc).unwrap()).unwrap();
    assert_eq!(School::read(&loaded).chapter, 12);
    s.undo();
    assert_eq!(s.doc, before);
}
#[test]
fn banner_has_transparent_space_and_vector_checkboxes_in_the_shared_render() {
    use wordcraft_engine::layout::display::{self, Draw};
    let mut s = Session::new(core::new_document(&School::default()).unwrap());
    let table = s.doc.body[0].as_table().unwrap();
    assert_eq!(table.props.surface_inset, Some([0.; 4]));
    let png = image::load_from_memory(ecrinator::subjects::BANNER_BG)
        .unwrap()
        .to_rgba8();
    assert!(png.pixels().filter(|p| p[3] == 0).count() > png.pixels().count() / 2);
    let layout = s.layout();
    let draws = display::page_display(&s.doc, &layout.pages[0], &Default::default());
    assert!(
        draws.iter().any(|d| matches!(
            d,
            Draw::Ink {
                color: Rgb(255, 255, 255),
                ..
            }
        )),
        "checked box must have a clear vector tick"
    );
    assert!(draws.iter().any(|d|matches!(d,Draw::Shape{rect,fill:Some(c),..} if *c==School::default().banner_background() && rect.x.abs()<0.1 && rect.y.abs()<0.1 && rect.w>595.)));
}

#[test]
fn optional_banner_title_is_locked_on_page_but_configurable_and_roundtrips() {
    let mut s = Session::new(core::new_document(&School::default()).unwrap());
    let table = s.doc.body[0].as_table().unwrap();
    let title = table.rows[0].cells[1]
        .blocks
        .iter()
        .position(|b| {
            b.as_para()
                .is_some_and(|p| p.props.style.as_deref() == Some(core::BANNER_TITLE))
        })
        .unwrap();
    let pos = Pos::new(
        StoryRef::Body,
        wordcraft_doc::Path(vec![0, 0, 1, title as u32]),
        0,
    );
    s.sel = Selection::caret(pos.clone());
    assert!(s.run("text.insert", &json!({"text":"Interdit"})).is_err());
    let mut school = School::read(&s.doc);
    school.title = "Le récit d’aventure".into();
    core::update_header(&mut s, &school).unwrap();
    assert_eq!(School::read(&s.doc).title, "Le récit d’aventure");
    let roundtrip = storage::decode(&storage::encode(&s.doc).unwrap()).unwrap();
    assert_eq!(School::read(&roundtrip).title, "Le récit d’aventure");
    let mut school = School::read(&s.doc);
    school.title.clear();
    core::update_header(&mut s, &school).unwrap();
    assert_eq!(School::read(&s.doc).title, "");
    assert!(
        !s.doc
            .plain_text(StoryRef::Body)
            .contains("Le récit d’aventure")
    );
    s.undo();
    assert_eq!(School::read(&s.doc).title, "Le récit d’aventure");
}

#[test]
fn banner_geometry_is_fixed_but_its_fields_remain_editable() {
    let mut s = Session::new(core::new_document(&School::default()).unwrap());
    s.sel = Selection::caret(Pos::new(
        StoryRef::Body,
        wordcraft_doc::Path(vec![0, 0, 1, 0]),
        0,
    ));
    for command in [
        "table.insertRowBelow",
        "table.insertColumnRight",
        "table.deleteRow",
        "table.deleteColumn",
        "table.deleteTable",
    ] {
        let before = s.doc.clone();
        let error = s.run(command, &json!({})).unwrap_err();
        assert!(
            matches!(error, wordcraft_engine::CmdError::Disabled(_)),
            "Unexpected {command}: {error}"
        );
        assert_eq!(s.doc, before, "{command} changed the fixed banner");
    }
    let layout = s.layout();
    for item in &layout.pages[0].items {
        if let wordcraft_engine::layout::Placed::Cell { rect, table, .. } = item {
            if table.0 == vec![0] {
                assert!(
                    (rect.h - core::BANNER_HEIGHT).abs() < 1.,
                    "Banner height: {}",
                    rect.h
                );
            }
        }
    }
    assert!(
        wordcraft_engine::cmd::table_resize::table_under(&layout, &s.doc, 0, 200., 50., 3.)
            .is_none()
    );
    assert!(
        wordcraft_engine::cmd::table_mouse::handle_table(
            &layout,
            &s.doc,
            StoryRef::Body,
            0,
            200.,
            50.,
            3.
        )
        .is_none()
    );
    s.run(
        "developer.chooseItem",
        &json!({"control":"ecr.chapter","value":"9"}),
    )
    .unwrap();
    assert_eq!(School::read(&s.doc).chapter, 9);
    let loaded = storage::decode(&storage::encode(&s.doc).unwrap()).unwrap();
    assert!(loaded.body[0].as_table().unwrap().props.geometry_locked);
    assert_eq!(School::read(&loaded).chapter, 9);
}
#[test]
fn banner_rejects_content_edits_but_keeps_chapter_and_type_controls() {
    let mut s = Session::new(core::new_document(&School::default()).unwrap());
    s.sel = Selection::caret(Pos::new(
        StoryRef::Body,
        wordcraft_doc::Path(vec![0, 0, 1, 0]),
        0,
    ));
    for (id, args) in [
        ("text.insert", json!({"text":"Interdit"})),
        ("format.bold", json!({})),
        ("text.deleteForward", json!({})),
    ] {
        let before = s.doc.clone();
        let _ = s.run(id, &args);
        assert_eq!(s.doc, before, "{id} changed the protected banner");
    }
    s.run(
        "developer.chooseItem",
        &json!({"control":"ecr.chapter","value":"7"}),
    )
    .unwrap();
    s.run(
        "developer.toggleCheckBox",
        &json!({"control":"ecr.exercises"}),
    )
    .unwrap();
    assert_eq!(School::read(&s.doc).chapter, 7);
    assert_eq!(School::read(&s.doc).folder_kind(), "Exercices");
    assert!(s.doc.body[0].as_table().unwrap().props.content_locked);
    s.sel = Selection::caret(core::writing_position(&s.doc));
    s.run("text.insert", &json!({"text":"Mon vrai cours"}))
        .unwrap();
    assert!(s.doc.plain_text(StoryRef::Body).contains("Mon vrai cours"));
}
