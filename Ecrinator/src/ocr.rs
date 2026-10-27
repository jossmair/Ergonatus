//! French Windows OCR, local and nondestructive. Call on a worker, never on the UI thread.
#[derive(Clone, Debug)]
pub struct Line {
    pub text: String,
    pub rect: [f32; 4],
}
#[derive(Clone, Debug)]
pub struct Recognition {
    pub text: String,
    pub lines: Vec<Line>,
}
pub fn recognize(bytes: &[u8], crop: Option<[u32; 4]>) -> Result<Recognition, String> {
    if bytes.len() > 20 * 1024 * 1024 {
        return Err("Image trop volumineuse pour l’OCR (20 Mo).".into());
    }
    let mut reader = image::ImageReader::new(std::io::Cursor::new(bytes))
        .with_guessed_format()
        .map_err(|e| e.to_string())?;
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(16000);
    limits.max_image_height = Some(16000);
    limits.max_alloc = Some(128 * 1024 * 1024);
    reader.limits(limits);
    let mut img = reader.decode().map_err(|e| e.to_string())?;
    if let Some([x, y, w, h]) = crop {
        let w = w.min(img.width().saturating_sub(x));
        let h = h.min(img.height().saturating_sub(y));
        if w == 0 || h == 0 {
            return Err("Zone d’image vide.".into());
        }
        img = img.crop_imm(x, y, w, h);
    }
    let img = img
        .resize(3200, 3200, image::imageops::FilterType::Triangle)
        .to_rgba8();
    recognize_pixels(img.as_raw(), img.width(), img.height())
}
#[cfg(not(windows))]
fn recognize_pixels(_rgba: &[u8], _w: u32, _h: u32) -> Result<Recognition, String> {
    Err("L’OCR local nécessite Windows 10 ou 11.".into())
}
#[cfg(windows)]
fn recognize_pixels(rgba: &[u8], w: u32, h: u32) -> Result<Recognition, String> {
    use windows::{
        Globalization::Language,
        Graphics::Imaging::{BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap},
        Media::Ocr::OcrEngine,
        Storage::Streams::DataWriter,
    };
    fn run(rgba: &[u8], w: u32, h: u32) -> windows::core::Result<Recognition> {
        let french = Language::CreateLanguage(&windows::core::HSTRING::from("fr-FR"))?;
        if !OcrEngine::IsLanguageSupported(&french)? {
            return Err(windows::core::Error::new(
                windows::core::HRESULT(0x80004005u32 as i32),
                "Le français OCR est absent.",
            ));
        }
        let engine = OcrEngine::TryCreateFromLanguage(&french)?;
        let mut bgra = rgba.to_vec();
        for p in bgra.chunks_exact_mut(4) {
            let a = p[3] as u32;
            for c in &mut p[..3] {
                *c = (((*c as u32) * a + 255 * (255 - a)) / 255) as u8;
            }
            p.swap(0, 2);
            p[3] = 255;
        }
        let writer = DataWriter::new()?;
        writer.WriteBytes(&bgra)?;
        let bmp = SoftwareBitmap::CreateCopyWithAlphaFromBuffer(
            &writer.DetachBuffer()?,
            BitmapPixelFormat::Bgra8,
            w as i32,
            h as i32,
            BitmapAlphaMode::Ignore,
        )?;
        let result = engine.RecognizeAsync(&bmp)?.join()?;
        let mut lines = Vec::new();
        for line in result.Lines()?.into_iter().take(4096) {
            let mut rect = [f32::INFINITY, f32::INFINITY, 0f32, 0f32];
            for word in line.Words()? {
                let b = word.BoundingRect()?;
                rect = [
                    rect[0].min(b.X),
                    rect[1].min(b.Y),
                    rect[2].max(b.X + b.Width),
                    rect[3].max(b.Y + b.Height),
                ];
            }
            lines.push(Line {
                text: line.Text()?.to_string(),
                rect,
            });
        }
        bmp.Close()?;
        let text = lines
            .iter()
            .map(|l| l.text.as_str())
            .collect::<Vec<_>>()
            .join("\n");
        Ok(Recognition { text, lines })
    }
    run(rgba,w,h).map_err(|e|format!("OCR français indisponible : vérifiez la langue française dans les paramètres Windows. {e}"))
}
