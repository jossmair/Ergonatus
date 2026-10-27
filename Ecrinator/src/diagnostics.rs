//! Small local technical log. No network or telemetry.
use std::{
    fs::{self, OpenOptions},
    io::Write,
};
pub fn record(message: &str) {
    let root = crate::storage::data_dir();
    if fs::create_dir_all(&root).is_err() {
        return;
    }
    let path = root.join("diagnostic.log");
    if fs::metadata(&path).is_ok_and(|m| m.len() > 1024 * 1024) {
        let _ = fs::rename(&path, root.join("diagnostic.previous.log"));
    }
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let message: String = message.chars().take(4000).collect();
        let _ = writeln!(file, "{} | {}", chrono::Local::now().to_rfc3339(), message);
    }
}
pub fn init() {
    record(concat!("Démarrage Écrinator ", env!("CARGO_PKG_VERSION")));
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        record(&format!("Incident : {info}"));
        previous(info);
    }));
}
