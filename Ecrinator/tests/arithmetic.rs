use ecrinator::{
    arithmetic::{Calculation, DESIGN, Operation},
    core, exporters, odt_project, storage, verification,
};
use std::path::Path as FsPath;
use wordcraft_doc::{Path, Pos};
use wordcraft_engine::{Selection, Session};
#[test]
fn operation_scaffolds_stay_blank_editable_and_survive_odt_pdf() {
    verification::init_fonts();
    let out = FsPath::new(env!("CARGO_MANIFEST_DIR")).join("test-output/arithmetic-scaffolds");
    std::fs::create_dir_all(&out).unwrap();
    for (name, operation, a, b) in [
        ("addition", Operation::Add, "125,4", "37,85"),
        ("soustraction", Operation::Subtract, "100,02", "38,57"),
        ("multiplication", Operation::Multiply, "12,3", "4,5"),
        ("division", Operation::Divide, "12,54", "2,5"),
    ] {
        let mut school = core::School::default();
        school.subject = core::BLANK.into();
        school.show_banner = false;
        let mut s = Session::new(core::new_document(&school).unwrap());
        s.sel = Selection::caret(core::writing_position(&s.doc));
        let before = storage::encode(&s.doc).unwrap();
        let c = Calculation {
            operation,
            a: a.into(),
            b: b.into(),
            ..Default::default()
        };
        ecrinator::arithmetic::apply(&mut s, &c).unwrap();
        let table_path = ecrinator::arithmetic::selected(&s).unwrap();
        let idx = table_path.last();
        let t = s.doc.table(s.sel.focus.story, &table_path).unwrap();
        let first_working = if operation == Operation::Divide { 1 } else { 3 };
        for row in &t.rows[first_working..] {
            for cell in &row.cells {
                assert!(cell.blocks[0].as_para().unwrap().plain_text().is_empty());
            }
        }
        s.run("edit.undo", &serde_json::json!({})).unwrap();
        assert_eq!(storage::encode(&s.doc).unwrap(), before);
        s.run("edit.redo", &serde_json::json!({})).unwrap();
        // Actual student text editing in the page, not a generated answer object.
        s.sel = Selection::caret(Pos {
            story: s.sel.focus.story,
            path: Path(vec![idx as u32, first_working as u32, 2, 0]),
            off: 0,
        });
        s.run("text.insert", &serde_json::json!({"text":"7"}))
            .unwrap();
        let table = s.doc.table(s.sel.focus.story, &table_path).unwrap();
        assert_eq!(
            table.rows[first_working].cells[2].blocks[0]
                .as_para()
                .unwrap()
                .plain_text(),
            "7"
        );
        // Additional working rows must be possible without calculating any value.
        let rows_before = s
            .doc
            .table(s.sel.focus.story, &table_path)
            .unwrap()
            .rows
            .len();
        s.run("table.insertRowBelow", &serde_json::json!({}))
            .unwrap();
        assert_eq!(
            s.doc
                .table(s.sel.focus.story, &table_path)
                .unwrap()
                .rows
                .len(),
            rows_before + 1
        );
        s.run("edit.undo", &serde_json::json!({})).unwrap();
        let native = storage::encode(&s.doc).unwrap();
        let restored = storage::decode(&native).unwrap();
        assert_eq!(storage::encode(&restored).unwrap(), native);
        let odt = odt_project::encode(&s.doc).unwrap();
        std::fs::write(out.join(format!("{name}.odt")), &odt).unwrap();
        let restored = odt_project::open("operation.odt", &odt).unwrap();
        assert!(restored.body.iter().filter_map(|b| b.as_table()).any(|t| {
            t.props
                .description
                .as_deref()
                .is_some_and(|s| s.starts_with(DESIGN))
        }));
        let public = wordcraft_engine::io::open_bytes("operation.odt", &odt).unwrap();
        assert!(
            public
                .body
                .iter()
                .filter_map(|b| b.as_table())
                .any(|t| t.rows.len() >= 6 && t.cols() >= 8),
            "Standard ODT must keep editable cells"
        );
        let pdf = exporters::bytes("operation.pdf", &s.doc).unwrap();
        assert!(pdf.starts_with(b"%PDF-"));
        std::fs::write(out.join(format!("{name}.pdf")), pdf).unwrap();
        let layout = s.layout();
        assert_eq!(layout.pages.len(), 1);
        let png = wordcraft_engine::render::render_page(
            &s.doc,
            &layout.pages[0],
            1.5,
            &Default::default(),
        )
        .to_png();
        std::fs::write(out.join(format!("{name}.png")), png).unwrap();
    }
}
