//! Original, non-interactive suite hourglass. Keep in sync across native apps.
use eframe::egui::{self, Color32, Pos2, Rect, Stroke, Vec2};

pub(super) fn show(ctx: &egui::Context, name: &str, color: Color32, animated: bool) {
    let center = ctx.content_rect().center();
    let painter = ctx.layer_painter(egui::LayerId::new(egui::Order::Foreground, egui::Id::new("suite-hourglass")));
    let rect = Rect::from_center_size(center, Vec2::new(136., 154.));
    painter.rect_filled(rect, 18, Color32::from_rgba_unmultiplied(250, 253, 253, 246));
    painter.rect_stroke(rect, 18, Stroke::new(1., color.gamma_multiply(0.55)), egui::StrokeKind::Inside);
    let elapsed = if animated { ctx.input(|i| i.time) } else { 1.5 };
    let phase = if elapsed.is_finite() { elapsed.rem_euclid(4.8) as f32 } else { 0. };
    let progress = (phase / 4.1).clamp(0., 1.);
    let turn = ((phase - 4.1) / 0.7).clamp(0., 1.);
    let angle = std::f32::consts::PI * turn * turn * (3. - 2. * turn);
    let origin = center + Vec2::new(0., -12.);
    let point = |x: f32, y: f32| -> Pos2 { origin + Vec2::new(x * angle.cos() - y * angle.sin(), x * angle.sin() + y * angle.cos()) };
    let line = Stroke::new(2., color);
    for (a,b) in [((-28.,-36.),(28.,-36.)),((-28.,36.),(28.,36.)),((-23.,-32.),(0.,0.)),((23.,-32.),(0.,0.)),((0.,0.),(-23.,32.)),((0.,0.),(23.,32.))] {
        painter.line_segment([point(a.0,a.1),point(b.0,b.1)],line);
    }
    let width = 20. * (1. - progress);
    let level = -29. * (1. - progress);
    painter.add(egui::Shape::convex_polygon(vec![point(-width,level),point(width,level),point(0.,0.)],color,Stroke::NONE));
    let peak = 30. - progress * 26.;
    painter.add(egui::Shape::convex_polygon(vec![point(-20.,30.),point(20.,30.),point(0.,peak)],color,Stroke::NONE));
    if progress < 1. {
        for n in 0..7 {
            let y = 2. + (phase * 55. + n as f32 * 6.).rem_euclid((peak - 2.).max(3.));
            painter.circle_filled(point(0.,y),1.,color);
        }
    }
    painter.text(center + Vec2::new(0.,46.),egui::Align2::CENTER_CENTER,name,egui::FontId::proportional(12.),color);
    painter.text(center + Vec2::new(0.,65.),egui::Align2::CENTER_CENTER,"Traitement en cours",egui::FontId::proportional(11.),Color32::from_rgb(83,103,122));
    if animated { ctx.request_repaint_after(std::time::Duration::from_millis(40)); }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn hourglass_paints_without_capturing_input() {
        let ctx = egui::Context::default();
        let mut output = ctx.run_ui(egui::RawInput::default(), |root| show(root.ctx(),"Test",Color32::BLUE,true));
        output.textures_delta.clear();
        assert!(!output.shapes.is_empty());
        assert!(!ctx.egui_wants_keyboard_input());
        assert!(!ctx.egui_wants_pointer_input());
    }
}
