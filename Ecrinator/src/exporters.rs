//! Wordcraft PDF/DOCX plus ODF formula objects with a faithful PNG fallback.
//! The native document is never changed while producing a copy.
use std::{
    io::{Cursor, Read, Write},
    sync::Arc,
};
use wordcraft_doc::{CharProps, Document, InlineObject, Paragraph, para_block};
use wordcraft_engine::Session;
use zip::{CompressionMethod, ZipArchive, ZipWriter, write::SimpleFileOptions};

pub fn bytes(name: &str, doc: &Document) -> Result<Vec<u8>, String> {
    if std::path::Path::new(name)
        .extension()
        .is_some_and(|s| s.eq_ignore_ascii_case("odt"))
    {
        let copy = vector_interchange_copy(doc, false)?;
        crate::odt_design::polish(&odt(&copy)?, doc)
    } else if std::path::Path::new(name)
        .extension()
        .is_some_and(|s| s.eq_ignore_ascii_case("docx"))
    {
        let copy = school_interchange_copy(&vector_interchange_copy(doc, true)?);
        wordcraft_engine::io::save_bytes(name, &copy)
    } else {
        let credits = crate::image_credits::pdf_metadata(doc);
        if !credits.is_empty()
            && std::path::Path::new(name)
                .extension()
                .is_some_and(|s| s.eq_ignore_ascii_case("pdf"))
        {
            let mut copy = doc.clone();
            copy.core.subject = format!(
                "{}\nSources des illustrations :\n{credits}",
                copy.core.subject
            );
            wordcraft_engine::io::save_bytes(name, &copy)
        } else {
            wordcraft_engine::io::save_bytes(name, doc)
        }
    }
}
/// ODF fallback: drawings remain visible at print resolution; the working model
/// is preserved separately inside an Écrinator ODT save. PDF keeps vectors.
fn vector_interchange_copy(doc: &Document, timelines_only: bool) -> Result<Document, String> {
    let eligible = |o: &InlineObject| {
        if timelines_only {
            crate::timeline::model(o).is_some()
        } else {
            matches!(o, InlineObject::Shape { .. } | InlineObject::Graphic { .. })
        }
    };
    let mut objects = Vec::new();
    doc.objects_in_reading_order(&mut |o| {
        if eligible(o) {
            objects.push(o.clone());
        }
    });
    if objects.len() > 128 {
        return Err("Ce document contient trop de dessins pour cet export (128 maximum).".into());
    }
    let mut prepared = Vec::new();
    for (i, o) in objects.iter().enumerate() {
        let (w, h, alt) = match o {
            InlineObject::Graphic { w, h, alt, .. } => (*w, *h, alt.clone()),
            InlineObject::Shape { w, h, .. } => (*w, *h, "Figure".into()),
            _ => continue,
        };
        if !w.is_finite()
            || !h.is_finite()
            || !(1. ..=2000.).contains(&w)
            || !(1. ..=2000.).contains(&h)
        {
            return Err("Dimensions d’un dessin non prises en charge.".into());
        }
        let mut scratch = Document::new();
        scratch.media = doc.media.clone();
        scratch.last_section.page_w = w + 24.;
        scratch.last_section.page_h = h + 72.;
        scratch.last_section.margin_left = 12.;
        scratch.last_section.margin_right = 12.;
        scratch.last_section.margin_top = 12.;
        scratch.last_section.margin_bottom = 12.;
        let mut object = o.clone();
        match &mut object {
            InlineObject::Graphic { float, .. } | InlineObject::Shape { float, .. } => {
                *float = Default::default()
            }
            _ => {}
        }
        let mut p = Paragraph::new();
        p.insert_object(0, object, &CharProps::default())
            .map_err(|e| e.to_string())?;
        scratch.body = vec![para_block(p)];
        let mut session = Session::new(scratch);
        let layout = session.layout();
        let page = layout.pages.first().ok_or("Dessin non composé")?;
        let rendered =
            wordcraft_engine::render::render_page(&session.doc, page, 3., &Default::default());
        let image = image::RgbaImage::from_raw(rendered.width, rendered.height, rendered.pixels)
            .ok_or("Image du dessin invalide")?;
        let mut bounds = [image.width(), image.height(), 0, 0];
        let mut found = false;
        for (x, y, p) in image.enumerate_pixels() {
            if p.0[..3].iter().any(|v| *v < 249) {
                bounds[0] = bounds[0].min(x);
                bounds[1] = bounds[1].min(y);
                bounds[2] = bounds[2].max(x);
                bounds[3] = bounds[3].max(y);
                found = true;
            }
        }
        if !found {
            return Err("Le rendu d’un dessin est vide. Le fichier précédent est conservé.".into());
        }
        let x = bounds[0].saturating_sub(3);
        let y = bounds[1].saturating_sub(3);
        let pw = (bounds[2] - x + 4).min(image.width() - x);
        let ph = (bounds[3] - y + 4).min(image.height() - y);
        let crop = image::DynamicImage::ImageRgba8(image).crop_imm(x, y, pw, ph);
        let mut encoded = Cursor::new(Vec::new());
        crop.write_to(&mut encoded, image::ImageFormat::Png)
            .map_err(|e| e.to_string())?;
        let base = format!("ecr-vector-fallback-{i}");
        let mut key = format!("{base}.png");
        let mut suffix = 1;
        while doc.media.contains_key(&key) || prepared.iter().any(|(k, _, _, _, _)| k == &key) {
            key = format!("{base}-{suffix}.png");
            suffix += 1;
        }
        prepared.push((
            key,
            encoded.into_inner(),
            pw as f32 / 3.,
            ph as f32 / 3.,
            alt,
        ));
    }
    let mut copy = doc.clone();
    let mut n = 0;
    copy.objects_mut(&eligible, &mut |o| {
        if let Some((key, _, w, h, alt)) = prepared.get(n) {
            *o = InlineObject::Image {
                media: key.clone(),
                w: *w,
                h: *h,
                alt: alt.clone(),
                float: Default::default(),
                crop: [0.; 4],
                ole: None,
            };
        }
        n += 1;
    });
    if n != prepared.len() {
        return Err("Tous les dessins n’ont pas pu être convertis.".into());
    }
    for (key, data, _, _, _) in prepared {
        copy.media.insert(key, Arc::new(data));
    }
    Ok(copy)
}
/// DOCX/ODT currently lack decorative table backgrounds. Retain an editable
/// school header and its illustration explicitly in the interchange copy.
fn school_interchange_copy(doc: &Document) -> Document {
    let mut copy = doc.clone();
    let school = crate::core::School::read(doc);
    let art = crate::subjects::for_subject(&school.subject);
    let key = format!("ecr-interchange-{}.png", art.slug);
    for block in &mut copy.body {
        if let wordcraft_doc::Block::Table(table) = Arc::make_mut(block) {
            if table.props.caption.as_deref() == Some(crate::core::HEADER)
                && table.props.geometry_locked
            {
                if let Some(cell) = table.rows.first_mut().and_then(|r| r.cells.first_mut()) {
                    let mut p = Paragraph::new();
                    if p.insert_object(
                        0,
                        InlineObject::Image {
                            media: key.clone(),
                            w: 96.,
                            h: 48.,
                            alt: art.alt.into(),
                            float: Default::default(),
                            crop: [0.; 4],
                            ole: None,
                        },
                        &CharProps::default(),
                    )
                    .is_ok()
                    {
                        cell.blocks = vec![para_block(p)];
                        copy.media.insert(key.clone(), Arc::new(art.png.to_vec()));
                    }
                }
            }
        }
    }
    copy
}
struct Formula {
    marker: String,
    xml: String,
    png: Vec<u8>,
    width: f32,
    height: f32,
    linear: String,
}
fn render_formula(object: &InlineObject, number: usize) -> Result<Formula, String> {
    let InlineObject::Equation {
        linear, display, ..
    } = object
    else {
        return Err("Objet mathématique attendu".into());
    };
    let mut doc = Document::new();
    doc.last_section.page_w = 700.;
    doc.last_section.page_h = 300.;
    doc.last_section.margin_left = 8.;
    doc.last_section.margin_right = 8.;
    doc.last_section.margin_top = 8.;
    doc.last_section.margin_bottom = 8.;
    let mut p = Paragraph::new();
    p.insert_object(
        0,
        object.clone(),
        &CharProps {
            size: Some(14.),
            ..Default::default()
        },
    )
    .map_err(|e| e.to_string())?;
    doc.body = vec![para_block(p)];
    let mut s = Session::new(doc);
    let layout = s.layout();
    let page = layout.pages.first().ok_or("Formule non composée")?;
    let rendered = wordcraft_engine::render::render_page(&s.doc, page, 3., &Default::default());
    let mut bounds = [rendered.width, rendered.height, 0, 0];
    for (y, row) in rendered
        .pixels
        .chunks_exact(rendered.width as usize * 4)
        .enumerate()
    {
        for (x, px) in row.chunks_exact(4).enumerate() {
            if px[3] > 0 && px[..3].iter().any(|c| *c < 220) {
                bounds[0] = bounds[0].min(x as u32);
                bounds[1] = bounds[1].min(y as u32);
                bounds[2] = bounds[2].max(x as u32 + 1);
                bounds[3] = bounds[3].max(y as u32 + 1);
            }
        }
    }
    if bounds[2] <= bounds[0] || bounds[3] <= bounds[1] {
        return Err(
            "Le moteur n’a pas rendu la formule. L’export est interrompu pour éviter une perte."
                .into(),
        );
    }
    let img = image::RgbaImage::from_raw(rendered.width, rendered.height, rendered.to_straight())
        .ok_or("Rendu de formule invalide")?;
    let x = bounds[0].saturating_sub(3);
    let y = bounds[1].saturating_sub(3);
    let w = (bounds[2] + 3).min(img.width()) - x;
    let h = (bounds[3] + 3).min(img.height()) - y;
    let crop = image::DynamicImage::ImageRgba8(img).crop_imm(x, y, w, h);
    let mut png = Cursor::new(Vec::new());
    crop.write_to(&mut png, image::ImageFormat::Png)
        .map_err(|e| e.to_string())?;
    Ok(Formula {
        marker: format!("ecrinator-formula-{number}"),
        xml: wordcraft_formats::mathml::linear_to_mathml(linear, *display),
        png: png.into_inner(),
        width: w as f32 / 3.,
        height: h as f32 / 3.,
        linear: linear.clone(),
    })
}
fn odt(doc: &Document) -> Result<Vec<u8>, String> {
    let mut copy = school_interchange_copy(doc);
    // ODF's current writer emits inline tables. Keep the header within the
    // printable margins in this copy instead of exporting a page-wide float.
    let width =
        copy.last_section.page_w - copy.last_section.margin_left - copy.last_section.margin_right;
    for block in &mut copy.body {
        if let wordcraft_doc::Block::Table(table) = Arc::make_mut(block) {
            if table.props.caption.as_deref() == Some(crate::core::HEADER) {
                // The ODF background is added as a standard table background;
                // the separate DOCX portrait is unnecessary in this ODT copy.
                if let Some(cell) = table.rows.first_mut().and_then(|r| r.cells.first_mut()) {
                    cell.blocks = vec![para_block(Paragraph::new())];
                }
                let total: f32 = table.grid.iter().sum();
                if total > 0. && width > 0. {
                    for v in &mut table.grid {
                        *v *= width / total;
                    }
                    for row in &mut table.rows {
                        for (i, cell) in row.cells.iter_mut().enumerate() {
                            cell.props.width = table.grid.get(i).copied();
                            let padding = cell
                                .props
                                .margins
                                .or(table.props.cell_margins)
                                .unwrap_or([6., 10., 6., 10.]);
                            let available =
                                (cell.props.width.unwrap_or(120.) - padding[1] - padding[3])
                                    .max(1.);
                            for b in &mut cell.blocks {
                                if let wordcraft_doc::Block::Para(p) = Arc::make_mut(b) {
                                    for object in &mut p.objects {
                                        if let InlineObject::Image { w, h, .. } = object {
                                            if w.is_finite() && *w > available {
                                                *h *= available / *w;
                                                *w = available;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    table.props.width = Some(width);
                }
                table.props.float = None;
                table.props.background_media = None;
                table.props.background_alpha = None;
            }
        }
    }
    let mut originals = Vec::new();
    copy.objects_mut(&|o| matches!(o, InlineObject::Equation { .. }), &mut |o| {
        originals.push(o.clone())
    });
    if originals.is_empty() {
        return wordcraft_engine::io::save_bytes("cours.odt", &copy);
    }
    if originals.len() > 256 {
        return Err(
            "Ce document contient plus de 256 formules. Exportez-le en PDF ou DOCX.".into(),
        );
    }
    let formulas = originals
        .iter()
        .enumerate()
        .map(|(i, o)| render_formula(o, i + 1))
        .collect::<Result<Vec<_>, _>>()?;
    let mut n = 0;
    copy.objects_mut(&|o| matches!(o, InlineObject::Equation { .. }), &mut |o| {
        if let Some(f) = formulas.get(n) {
            *o = InlineObject::Image {
                media: format!("{}.png", f.marker),
                w: f.width,
                h: f.height,
                alt: f.marker.clone(),
                float: Default::default(),
                crop: [0.; 4],
                ole: None,
            };
        }
        n += 1;
    });
    if n != formulas.len() {
        return Err(
            "Toutes les formules n’ont pas pu être préparées. L’original est conservé.".into(),
        );
    }
    for f in &formulas {
        copy.media
            .insert(format!("{}.png", f.marker), Arc::new(f.png.clone()));
    }
    let raw = wordcraft_engine::io::save_bytes("cours.odt", &copy)?;
    let mut source = ZipArchive::new(Cursor::new(raw)).map_err(|e| e.to_string())?;
    let mut files = Vec::new();
    for i in 0..source.len() {
        let mut file = source.by_index(i).map_err(|e| e.to_string())?;
        let mut data = Vec::new();
        file.read_to_end(&mut data).map_err(|e| e.to_string())?;
        files.push((file.name().to_string(), data));
    }
    let content = files
        .iter_mut()
        .find(|(name, _)| name == "content.xml")
        .ok_or("ODT sans contenu")?;
    let mut xml = String::from_utf8(content.1.clone()).map_err(|e| e.to_string())?;
    for (i, f) in formulas.iter().enumerate() {
        let marker = xml
            .find(&f.marker)
            .ok_or("Formule absente du contenu ODT")?;
        let start = xml
            .get(..marker)
            .and_then(|s| s.rfind("<draw:frame"))
            .ok_or("Cadre de formule absent")?;
        let rel_end = xml
            .get(marker..)
            .and_then(|s| s.find("</draw:frame>"))
            .ok_or("Cadre de formule incomplet")?;
        let end = marker + rel_end + "</draw:frame>".len();
        let frame = xml.get(start..end).ok_or("Cadre ODT invalide")?;
        let insert = frame.find('>').ok_or("Cadre ODT invalide")? + 1;
        let object = format!(
            "<draw:object xlink:href=\"./Formula{}\" xlink:type=\"simple\" xlink:show=\"embed\" xlink:actuate=\"onLoad\"/>",
            i + 1
        );
        let mut fixed = frame.to_string();
        fixed.insert_str(insert, &object);
        fixed = fixed.replace(&f.marker, &escape(&format!("Formule : {}", f.linear)));
        xml.replace_range(start..end, &fixed);
    }
    content.1 = xml.into_bytes();
    let manifest = files
        .iter_mut()
        .find(|(name, _)| name == "META-INF/manifest.xml")
        .ok_or("ODT sans manifeste")?;
    let mut xml = String::from_utf8(manifest.1.clone()).map_err(|e| e.to_string())?;
    let mut entries = String::new();
    for i in 0..formulas.len() {
        let name = format!("Formula{}", i + 1);
        entries.push_str(&format!("<manifest:file-entry manifest:full-path=\"{name}/\" manifest:media-type=\"application/vnd.oasis.opendocument.formula\"/><manifest:file-entry manifest:full-path=\"{name}/content.xml\" manifest:media-type=\"text/xml\"/>"));
    }
    let at = xml
        .find("</manifest:manifest>")
        .ok_or("Manifeste ODT invalide")?;
    xml.insert_str(at, &entries);
    manifest.1 = xml.into_bytes();
    for (i, f) in formulas.iter().enumerate() {
        files.push((
            format!("Formula{}/content.xml", i + 1),
            f.xml.as_bytes().to_vec(),
        ));
    }
    let mut out = ZipWriter::new(Cursor::new(Vec::new()));
    for (name, data) in files {
        out.start_file(
            &name,
            SimpleFileOptions::default().compression_method(if name == "mimetype" {
                CompressionMethod::Stored
            } else {
                CompressionMethod::Deflated
            }),
        )
        .map_err(|e| e.to_string())?;
        out.write_all(&data).map_err(|e| e.to_string())?;
    }
    Ok(out.finish().map_err(|e| e.to_string())?.into_inner())
}
fn escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}
