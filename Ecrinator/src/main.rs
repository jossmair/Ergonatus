#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod school_icons;
mod ui;
fn main() -> eframe::Result {
    ecrinator::diagnostics::init();
    let args: Vec<String> = std::env::args().skip(1).collect();
    if let Some(i) = args.iter().position(|a| a == "--verify") {
        let path = args
            .get(i + 1)
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| "test-output".into());
        match ecrinator::verification::run(&path) {
            Ok(()) => return Ok(()),
            Err(e) => {
                eprintln!("{e}");
                std::process::exit(1);
            }
        }
    }
    let path = args
        .iter()
        .find(|a| !a.starts_with("--"))
        .map(std::path::PathBuf::from);
    let screenshot = std::env::var_os("ECRINATOR_QA_SCREENSHOT").map(std::path::PathBuf::from);
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_decorations(false)
            .with_maximized(true)
            .with_inner_size([1448., 1000.])
            .with_min_inner_size([800., 580.])
            .with_icon(
                eframe::icon_data::from_png_bytes(include_bytes!("../assets/ecrinator.png"))
                    .unwrap_or_default(),
            ),
        ..Default::default()
    };
    eframe::run_native(
        "Écrinator — Ergonatus",
        options,
        Box::new(move |cc| Ok(Box::new(ui::App::new(&cc.egui_ctx, path, screenshot)))),
    )
}
