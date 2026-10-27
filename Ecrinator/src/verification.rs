//! Reproducible offline acceptance documents, also usable from the packaged executable.
use crate::{
    blocks,
    core::{self, School},
    storage,
};
use serde_json::json;
use std::{fs, path::Path, time::Instant};
use wordcraft_doc::{InlineObject, Pos, StoryRef};
use wordcraft_engine::{Selection, Session};
pub fn init_fonts() {
    static INIT: std::sync::Once = std::sync::Once::new();
    INIT.call_once(|| {
        let db = wordcraft_fonts::FontDb::global();
        db.add_font(include_bytes!("../assets/fonts/Borel-Regular.ttf").to_vec());
        db.add_font(include_bytes!("../assets/fonts/OpenDyslexic-Regular.otf").to_vec());
        db.add_font(include_bytes!("../assets/fonts/NotoSerif-Variable.ttf").to_vec());
    });
}
pub fn fixture(long: bool) -> Result<Session, String> {
    init_fonts();
    let school = School {
        subject: "Mathématiques".into(),
        title: "Les fractions".into(),
        date: "22/10/2026".into(),
        time: "19:30".into(),
        ..Default::default()
    };
    let mut s = Session::new(core::new_document(&school)?);
    s.sel = Selection::caret(core::writing_position(&s.doc));
    s.run("text.insert",&json!({"text":"1. Les fractions\nUne fraction représente une partie d’un tout. Écrivons avec précision : élève, méthode, égalité, cœur.\n"})).map_err(|e|e.to_string())?;
    blocks::insert(&mut s, "Définition")?;
    s.run("text.insert",&json!({"text":"Le numérateur indique les parts choisies. Le dénominateur indique le nombre total de parts égales.\nOn peut conserver plusieurs paragraphes, un schéma ou une formule."})).map_err(|e|e.to_string())?;
    let mut p = s.sel.focus.path.0.clone();
    p.truncate(p.len().saturating_sub(3));
    let next = wordcraft_doc::Path(p)
        .with_last(s.sel.focus.path.0.first().copied().unwrap_or(0) as usize + 1);
    s.sel = Selection::caret(Pos::new(StoryRef::Body, next, 0));
    s.run("text.insert", &json!({"text":"\n2. Écrire une fraction\n"}))
        .map_err(|e| e.to_string())?;
    s.run(
        "insert.equation",
        &json!({"linear":"(3)/(4)","display":true,"edit":false}),
    )
    .map_err(|e| e.to_string())?;
    s.run(
        "text.insert",
        &json!({"text":"\n3. Tableau de proportionnalité\n"}),
    )
    .map_err(|e| e.to_string())?;
    s.run("insert.table", &json!({"rows":2,"cols":5}))
        .map_err(|e| e.to_string())?;
    let mut path = s.sel.focus.path.0.clone();
    path.truncate(path.len().saturating_sub(3));
    let tp = wordcraft_doc::Path(path.clone());
    if let Ok(t) = s.doc.table_mut(StoryRef::Body, &tp) {
        for (r, row) in t.rows.iter_mut().enumerate() {
            for (c, cell) in row.cells.iter_mut().enumerate() {
                let label = if c == 0 {
                    if r == 0 {
                        "Cahiers".into()
                    } else {
                        "Prix (€)".into()
                    }
                } else {
                    format!("{}", c * (r + 1))
                };
                cell.blocks = vec![wordcraft_doc::para_block(core::text(
                    &label,
                    12.,
                    c == 0,
                    wordcraft_doc::props::Rgb(30, 49, 73),
                ))];
            }
        }
    }
    s.sel = Selection::caret(Pos::body(tp.last() + 1, 0));
    if long {
        for i in 0..85 {
            s.run("text.insert",&json!({"text":format!("\nExercice {}. Zoé partage équitablement des quantités. Calcule la fraction, explique la méthode puis vérifie le résultat avec un tableau. Les accents restent lisibles : à, é, è, ê, ç, œ.\n",i+1)})).map_err(|e|e.to_string())?;
        }
    }
    s.touch();
    s.relayout();
    Ok(s)
}
pub fn run(dir: &Path) -> Result<(), String> {
    fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    let started = Instant::now();
    let mut s = fixture(true)?;
    let original = s.doc.clone();
    let native = dir.join("Cours de mathématiques.ecr");
    storage::save(&native, &s.doc)?;
    let short = fixture(false)?;
    storage::save(&dir.join("Exemple court.ecr"), &short.doc)?;
    let biology = School {
        subject: "SVT".into(),
        chapter: 2,
        title: "La cellule".into(),
        ..Default::default()
    };
    let mut biology = Session::new(core::new_document(&biology)?);
    biology.sel = Selection::caret(core::writing_position(&biology.doc));
    biology.run("text.insert",&json!({"text":"Observer le vivant\nLa cellule est l’unité du vivant. J’observe, je décris et j’explique.\n"})).map_err(|e|e.to_string())?;
    blocks::insert(&mut biology, "Observation")?;
    biology.run("text.insert",&json!({"text":"Je note ce que je vois au microscope, puis je compare les cellules observées."})).map_err(|e|e.to_string())?;
    storage::save(&dir.join("SVT.ecr"), &biology.doc)?;
    let mut history = Session::new(core::new_document(&School {
        subject: "Histoire-géographie".into(),
        chapter: 3,
        title: "La Révolution française".into(),
        ..Default::default()
    })?);
    history.sel = Selection::caret(core::writing_position(&history.doc));
    crate::timeline::apply(&mut history, &Default::default())?;
    history.sel = Selection::caret(history.sel.focus.clone());
    history.run("text.insert",&json!({"text":"\nUne frise pour situer les événements et retrouver les grandes étapes.\n"})).map_err(|e|e.to_string())?;
    if let Some(e) = crate::library::catalog()
        .iter()
        .find(|e| e.id == "france-regions")
    {
        crate::library::insert(&mut history, e)?;
    }
    storage::save(&dir.join("Frise et bibliothèque.ecr"), &history.doc)?;
    for ext in ["pdf", "odt"] {
        let bytes = if ext == "odt" {
            crate::odt_project::encode(&history.doc)?
        } else {
            crate::exporters::bytes("cours.pdf", &history.doc)?
        };
        storage::atomic_write(&dir.join(format!("frise-et-bibliotheque.{ext}")), &bytes)?;
    }
    let odt = crate::odt_project::encode(&biology.doc)?;
    storage::atomic_write(&dir.join("SVT.odt"), &odt)?;
    if crate::odt_project::open("SVT.odt", &odt)? != biology.doc {
        return Err("Réouverture ODT incomplète".into());
    }
    for subject in core::SUBJECTS.iter().filter(|s| **s != core::BLANK) {
        let school = School {
            subject: (*subject).into(),
            chapter: 4,
            title: "Un cours pour apprendre".into(),
            ..Default::default()
        };
        let doc = core::new_document(&school)?;
        storage::save(&dir.join(format!("Bandeau {subject}.ecr")), &doc)?;
        storage::atomic_write(
            &dir.join(format!("bandeau-{subject}.pdf")),
            &crate::exporters::bytes("bandeau.pdf", &doc)?,
        )?;
    }
    let blank = core::new_document(&School {
        subject: core::BLANK.into(),
        show_banner: false,
        ..Default::default()
    })?;
    storage::save(&dir.join("Page blanche.ecr"), &blank)?;
    let mut design = Session::new(core::new_document(&School {
        subject: "Mathématiques".into(),
        chapter: 3,
        title: "Des repères pour apprendre".into(),
        ..Default::default()
    })?);
    design.sel = Selection::caret(core::writing_position(&design.doc));
    design
        .run(
            "text.insert",
            &json!({"text":"Des idées faciles à retrouver dans mon cours.\n"}),
        )
        .map_err(|e| e.to_string())?;
    for (model, body) in [
        (
            "Définition",
            "Une fraction représente une partie d’un tout.",
        ),
        (
            "Propriété",
            "Multiplier le numérateur et le dénominateur par un même nombre conserve la valeur de la fraction.",
        ),
        ("Remarque", "Le dénominateur doit être différent de zéro."),
        (
            "À retenir",
            "Je repère les données, je choisis une méthode et je vérifie mon résultat.",
        ),
    ] {
        blocks::insert(&mut design, model)?;
        design
            .run("text.insert", &json!({"text":body}))
            .map_err(|e| e.to_string())?;
        let at = design.sel.focus.path.0.first().copied().unwrap_or(0) as usize;
        design.sel = Selection::caret(Pos::body(at + 1, 0));
    }
    storage::save(&dir.join("Encadrés.ecr"), &design.doc)?;
    storage::atomic_write(
        &dir.join("encadres.pdf"),
        &crate::exporters::bytes("encadres.pdf", &design.doc)?,
    )?;
    if storage::read(&native)? != original {
        return Err("Échec : réouverture native différente.".into());
    }
    let layout = s.layout();
    if layout.pages.len() < 3 {
        return Err("Échec : document long non paginé.".into());
    }
    for ext in ["pdf", "odt", "docx"] {
        let bytes = if ext == "odt" {
            crate::odt_project::encode(&s.doc)?
        } else {
            crate::exporters::bytes(&format!("cours.{ext}"), &s.doc)?
        };
        storage::atomic_write(&dir.join(format!("cours.{ext}")), &bytes)?;
    }
    for (i, page) in layout.pages.iter().take(3).enumerate() {
        let png =
            wordcraft_engine::render::render_page(&s.doc, page, 1.2, &Default::default()).to_png();
        storage::atomic_write(&dir.join(format!("reference-page-{}.png", i + 1)), &png)?;
    }
    let recovery = dir.join("recovery-interruption.ecr");
    storage::save(&recovery, &s.doc)?;
    if storage::read(&recovery)? != original {
        return Err("Reprise incorrecte".into());
    }
    let mut equations = 0;
    let mut images = 0;
    s.doc.objects_in_reading_order(&mut |o| match o {
        InlineObject::Equation { .. } => equations += 1,
        InlineObject::Image { .. } => images += 1,
        _ => {}
    });
    let mut ocrdoc = wordcraft_doc::Document::new();
    ocrdoc.body = vec![wordcraft_doc::para_block(core::text(
        "La température augmente. Élève et méthode.",
        28.,
        false,
        wordcraft_doc::props::Rgb(0, 0, 0),
    ))];
    let mut ocrsession = Session::new(ocrdoc);
    let ol = ocrsession.layout();
    let ocr = if let Some(p) = ol.pages.first() {
        let png =
            wordcraft_engine::render::render_page(&ocrsession.doc, p, 1., &Default::default())
                .to_png();
        storage::atomic_write(&dir.join("ocr-francais.png"), &png)?;
        match crate::ocr::recognize(&png, None) {
            Ok(r) => json!({"recognized":true,"text":r.text,"lines":r.lines.len()}),
            Err(e) => json!({"recognized":false,"reason":e}),
        }
    } else {
        json!({"recognized":false})
    };
    let report = json!({"native_roundtrip":true,"recovery_roundtrip":true,"pages":layout.pages.len(),"equations":equations,"images":images,"ocr_french":ocr,"elapsed_ms":started.elapsed().as_millis(),"wordcraft":"0.9.0","library_images":crate::library::verify_pack()?,"offline":true,"limitations":["Impression physique non déclenchée","LibreOffice non vérifié par ce contrôle","Windows sans Python non vérifié"]});
    storage::atomic_write(
        &dir.join("verification.json"),
        &serde_json::to_vec_pretty(&report).map_err(|e| e.to_string())?,
    )?;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn creation_metadata_and_header_are_fixed() {
        let mut s = fixture(false).unwrap();
        let school = School::read(&s.doc);
        let before = s.doc.clone();
        let mut changed = school.clone();
        changed.subject = "SVT".into();
        core::update_header(&mut s, &changed).unwrap();
        assert_eq!(School::read(&s.doc).date, school.date);
        assert_eq!(School::read(&s.doc).time, school.time);
        s.undo();
        assert_eq!(before, s.doc);
    }
    #[test]
    fn exports_real_packages_and_paginated_pdf() {
        let dir = tempfile::tempdir().unwrap();
        run(dir.path()).unwrap();
        let pdf = fs::read(dir.path().join("cours.pdf")).unwrap();
        assert!(pdf.starts_with(b"%PDF-"));
        let mut zip = zip::ZipArchive::new(std::io::Cursor::new(
            fs::read(dir.path().join("cours.odt")).unwrap(),
        ))
        .unwrap();
        assert!(zip.by_name("content.xml").is_ok());
        assert!(zip.by_name("META-INF/manifest.xml").is_ok());
    }
}
