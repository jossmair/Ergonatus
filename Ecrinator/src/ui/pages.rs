//! Optional real page previews, rasterised off the UI thread after typing settles.
use super::*;
pub(super) struct PagePane {
    pub visible: bool,
    key: (u64, u64),
    changed: Instant,
    rx: Option<Receiver<((u64, u64), Vec<egui::ColorImage>)>>,
    textures: Vec<egui::TextureHandle>,
}
impl Default for PagePane {
    fn default() -> Self {
        Self {
            visible: false,
            key: (0, 0),
            changed: Instant::now(),
            rx: None,
            textures: Vec::new(),
        }
    }
}
impl PagePane {
    pub fn sync(&mut self, word: &mut WordApp, ctx: &egui::Context) {
        if !self.visible {
            return;
        }
        let key = (word.session.document_id(), word.session.rev());
        if key != self.key {
            self.key = key;
            self.changed = Instant::now();
        }
        if let Some((done, images)) = self.rx.as_ref().and_then(|r| r.try_recv().ok()) {
            self.rx = None;
            if done == self.key {
                self.textures = images
                    .into_iter()
                    .enumerate()
                    .map(|(i, img)| {
                        ctx.load_texture(
                            format!("page-preview-{i}"),
                            img,
                            egui::TextureOptions::LINEAR,
                        )
                    })
                    .collect();
            }
        }
        if self.rx.is_none() && self.changed.elapsed() > Duration::from_millis(400) {
            self.changed = Instant::now() + Duration::from_secs(86400);
            let doc = word.session.doc.clone();
            let layout = word.session.layout();
            let (tx, rx) = mpsc::channel();
            self.rx = Some(rx);
            let ctx = ctx.clone();
            std::thread::spawn(move || {
                let images = layout
                    .pages
                    .iter()
                    .take(50)
                    .map(|page| {
                        let rendered = wordcraft_engine::render::render_page(
                            &doc,
                            page,
                            0.17,
                            &Default::default(),
                        );
                        egui::ColorImage::from_rgba_premultiplied(
                            [rendered.width as usize, rendered.height as usize],
                            &rendered.pixels,
                        )
                    })
                    .collect();
                let _ = tx.send((key, images));
                ctx.request_repaint();
            });
        }
    }
    pub fn show(&self, root: &mut egui::Ui, count: usize, current: usize) -> Option<usize> {
        if !self.visible {
            return None;
        }
        let mut jump = None;
        egui::Panel::left("page-previews").exact_size(140.).resizable(false).frame(egui::Frame::new().fill(Color32::from_rgb(242,247,252)).inner_margin(12.)).show(root,|ui|{
            ui.label(RichText::new("Pages").strong().size(18.).color(INK));
            let mut n=current+1;ui.horizontal(|ui|{if ui.add(egui::DragValue::new(&mut n).range(1..=count.max(1))).changed(){jump=Some(n-1);}ui.label(format!("/ {count}"));});
            egui::ScrollArea::vertical().show(ui,|ui|{for(i,texture)in self.textures.iter().enumerate(){ui.add_space(9.);let r=ui.add(egui::Button::image(egui::Image::new(texture).fit_to_exact_size(egui::vec2(102.,144.))));r.widget_info(||egui::WidgetInfo::labeled(egui::WidgetType::Button,true,format!("Page {}",i+1)));if current==i{ui.painter().rect_stroke(r.rect.expand(1.),3.,egui::Stroke::new(2.,BLUE),egui::StrokeKind::Outside);}if r.clicked(){jump=Some(i);}ui.label(format!("{}",i+1));}if self.textures.is_empty(){ui.label("Préparation des aperçus…");}if count>50{ui.label("Aperçus des 50 premières pages. Le numéro ci-dessus accède à toutes les pages.");}});
        });
        jump
    }
}
