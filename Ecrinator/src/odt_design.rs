//! ODF 1.3 teaching-card styles and a standard table background for the banner.
//! This modifies only our generated interchange package, never the working model.
use quick_xml::{
    Reader, Writer,
    events::{BytesStart, Event},
};
use std::{
    io::{Cursor, Read, Write},
    sync::Arc,
};
use wordcraft_doc::{
    Block, Document, Paragraph, Table, para_block,
    props::{Border, BorderStyle},
};
use zip::{CompressionMethod, ZipArchive, ZipWriter, write::SimpleFileOptions};
fn tables<'a>(blocks: &'a [Arc<Block>], out: &mut Vec<&'a Table>, depth: usize) {
    if depth > 32 {
        return;
    }
    for b in blocks {
        if let Some(t) = b.as_table() {
            out.push(t);
            for row in &t.rows {
                for cell in &row.cells {
                    tables(&cell.blocks, out, depth + 1);
                }
            }
        }
    }
}
fn border(b: Option<&Border>) -> String {
    let Some(b) = b else { return "none".into() };
    if b.style == BorderStyle::None {
        return "none".into();
    }
    let kind = match b.style {
        BorderStyle::Double => "double",
        BorderStyle::Dashed => "dashed",
        BorderStyle::Dotted => "dotted",
        _ => "solid",
    };
    format!(
        "{}pt {kind} #{}",
        b.width.clamp(0.1, 8.),
        b.color
            .unwrap_or(wordcraft_doc::props::Rgb(135, 155, 181))
            .hex()
    )
}
fn cell_style(t: &Table, header: bool, tn: usize) -> String {
    let p = t.props.cell_margins.unwrap_or([6., 10., 6., 10.]);
    let borders = t.props.borders.as_ref();
    let mut attrs = format!(
        " style:vertical-align=\"middle\" fo:padding-top=\"{}pt\" fo:padding-right=\"{}pt\" fo:padding-bottom=\"{}pt\" fo:padding-left=\"{}pt\"",
        p[0], p[1], p[2], p[3]
    );
    attrs.push_str(&format!(
        " fo:background-color=\"{}\"",
        if header {
            "transparent".into()
        } else {
            t.props
                .shading
                .map(|c| format!("#{}", c.hex()))
                .unwrap_or_else(|| "transparent".into())
        }
    ));
    for (side, b) in [
        ("top", borders.and_then(|b| b.top.as_ref())),
        ("right", borders.and_then(|b| b.right.as_ref())),
        ("bottom", borders.and_then(|b| b.bottom.as_ref())),
        ("left", borders.and_then(|b| b.left.as_ref())),
    ] {
        attrs.push_str(&format!(
            " fo:border-{side}=\"{}\"",
            if header { "none".into() } else { border(b) }
        ));
    }
    format!(
        "<style:style style:name=\"EcrCell{tn}\" style:family=\"table-cell\"><style:table-cell-properties{attrs}/></style:style>"
    )
}
fn replace_attr(
    e: &BytesStart<'_>,
    key: &[u8],
    value: &str,
) -> Result<BytesStart<'static>, String> {
    let mut out = e.to_owned();
    out.clear_attributes();
    for attr in e.attributes() {
        let a = attr.map_err(|e| e.to_string())?;
        if a.key.as_ref() != key {
            out.push_attribute((a.key.as_ref(), a.value.as_ref()));
        }
    }
    out.push_attribute((key, value.as_bytes()));
    Ok(out)
}
fn banner_png(doc: &Document, t: &Table) -> Result<Vec<u8>, String> {
    let mut scratch = Document::new();
    scratch.media = doc.media.clone();
    scratch.last_section.page_h = crate::core::BANNER_HEIGHT + 24.;
    scratch.last_section.margin_top = 0.;
    scratch.last_section.margin_bottom = 0.;
    let mut t = t.clone();
    for row in &mut t.rows {
        for c in &mut row.cells {
            c.blocks = vec![para_block(Paragraph::new())];
        }
    }
    scratch.body = vec![Arc::new(wordcraft_doc::Block::Table(t))];
    let mut s = wordcraft_engine::Session::new(scratch);
    let layout = s.layout();
    let page = layout.pages.first().ok_or("Fond de bandeau non composé")?;
    let r = wordcraft_engine::render::render_page(&s.doc, page, 3., &Default::default());
    let image = image::RgbaImage::from_raw(r.width, r.height, r.pixels)
        .ok_or("Fond de bandeau invalide")?;
    let h = ((crate::core::BANNER_HEIGHT * 3.).ceil() as u32).min(image.height());
    let crop = image::DynamicImage::ImageRgba8(image).crop_imm(0, 0, r.width, h);
    let mut bytes = Cursor::new(Vec::new());
    crop.write_to(&mut bytes, image::ImageFormat::Png)
        .map_err(|e| e.to_string())?;
    Ok(bytes.into_inner())
}
pub fn polish(raw: &[u8], doc: &Document) -> Result<Vec<u8>, String> {
    let mut all = Vec::new();
    tables(&doc.body, &mut all, 0);
    let managed: Vec<_> = all
        .iter()
        .enumerate()
        .filter_map(|(i, t)| {
            let caption = t.props.caption.as_deref()?;
            caption.starts_with("Écrinator · ").then_some((
                i + 1,
                *t,
                caption == crate::core::HEADER,
            ))
        })
        .collect();
    let credit_xml = crate::image_credits::metadata_xml(doc)?;
    if managed.is_empty() && credit_xml.is_empty() {
        return Ok(raw.to_vec());
    }
    let mut source = ZipArchive::new(Cursor::new(raw)).map_err(|e| e.to_string())?;
    let mut files = Vec::new();
    for i in 0..source.len() {
        let mut f = source.by_index(i).map_err(|e| e.to_string())?;
        let mut data = Vec::new();
        f.read_to_end(&mut data).map_err(|e| e.to_string())?;
        files.push((f.name().to_owned(), data));
    }
    if !credit_xml.is_empty() {
        if let Some((_, meta)) = files.iter_mut().find(|(n, _)| n == "meta.xml") {
            let xml = String::from_utf8(meta.clone()).map_err(|e| e.to_string())?;
            *meta = xml
                .replace("</office:meta>", &format!("{credit_xml}</office:meta>"))
                .into_bytes();
        }
    }
    let mut styles = String::new();
    let mut background = None;
    for (tn, t, header) in &managed {
        styles.push_str(&cell_style(t, *header, *tn));
        if *header {
            background = Some(banner_png(doc, t)?);
            let width = doc.last_section.text_width();
            styles.push_str(&format!("<style:style style:name=\"EcrBanner\" style:family=\"table\"><style:table-properties style:width=\"{width}pt\" table:align=\"margins\" fo:margin-bottom=\"12pt\"><style:background-image xlink:href=\"Pictures/ecr-banner.png\" xlink:type=\"simple\" xlink:actuate=\"onLoad\" style:repeat=\"stretch\"/></style:table-properties></style:style><style:style style:name=\"EcrBannerRow\" style:family=\"table-row\"><style:table-row-properties style:min-row-height=\"{}pt\" fo:keep-together=\"always\"/></style:style>",crate::core::BANNER_HEIGHT));
        }
    }
    let content = files
        .iter_mut()
        .find(|(name, _)| name == "content.xml")
        .ok_or("ODT sans contenu")?;
    let input = String::from_utf8(content.1.clone())
        .map_err(|e| e.to_string())?
        .replace(
            "</office:automatic-styles>",
            &format!("{styles}</office:automatic-styles>"),
        );
    let mut reader = Reader::from_str(&input);
    let mut writer = Writer::new(Vec::new());
    let mut stack: Vec<Option<(usize, bool)>> = Vec::new();
    let mut count = 0;
    loop {
        let event = reader.read_event().map_err(|e| e.to_string())?;
        let next = match event {
            Event::Start(e) if e.name().as_ref() == b"table:table" => {
                count += 1;
                let m = managed
                    .iter()
                    .find(|(tn, _, _)| *tn == count)
                    .map(|(tn, _, h)| (*tn, *h));
                stack.push(m);
                Event::Start(if m.is_some_and(|(_, h)| h) {
                    replace_attr(&e, b"table:style-name", "EcrBanner")?
                } else {
                    e.into_owned()
                })
            }
            Event::Start(e) if e.name().as_ref() == b"table:table-cell" => {
                Event::Start(if let Some((tn, _)) = stack.last().copied().flatten() {
                    replace_attr(&e, b"table:style-name", &format!("EcrCell{tn}"))?
                } else {
                    e.into_owned()
                })
            }
            Event::Start(e)
                if e.name().as_ref() == b"table:table-row"
                    && stack.last().copied().flatten().is_some_and(|(_, h)| h) =>
            {
                Event::Start(replace_attr(&e, b"table:style-name", "EcrBannerRow")?)
            }
            Event::End(e) if e.name().as_ref() == b"table:table" => {
                stack.pop();
                Event::End(e.into_owned())
            }
            Event::Eof => break,
            e => e.into_owned(),
        };
        writer.write_event(next).map_err(|e| e.to_string())?;
    }
    content.1 = writer.into_inner();
    if let Some(data) = background {
        files.push(("Pictures/ecr-banner.png".into(), data));
        let manifest = files
            .iter_mut()
            .find(|(name, _)| name == "META-INF/manifest.xml")
            .ok_or("ODT sans manifeste")?;
        manifest.1=String::from_utf8(manifest.1.clone()).map_err(|e|e.to_string())?.replace("</manifest:manifest>","<manifest:file-entry manifest:full-path=\"Pictures/ecr-banner.png\" manifest:media-type=\"image/png\"/></manifest:manifest>").into_bytes();
    }
    let mut zip = ZipWriter::new(Cursor::new(Vec::new()));
    for (name, data) in files {
        let method = if name == "mimetype" {
            CompressionMethod::Stored
        } else {
            CompressionMethod::Deflated
        };
        zip.start_file(
            name,
            SimpleFileOptions::default().compression_method(method),
        )
        .map_err(|e| e.to_string())?;
        zip.write_all(&data).map_err(|e| e.to_string())?;
    }
    Ok(zip.finish().map_err(|e| e.to_string())?.into_inner())
}
