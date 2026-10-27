//! Shared visual vocabulary for the editable document and its tool palette.
use wordcraft_doc::props::Rgb;
pub struct Theme {
    pub ink: Rgb,
    pub background: Rgb,
    pub icon: &'static str,
}
pub fn theme(model: &str) -> Theme {
    let (ink, background, icon) = match model {
        "Définition" => (Rgb(178, 109, 5), Rgb(255, 250, 234), "definition"),
        "Propriété" => (Rgb(15, 124, 132), Rgb(238, 249, 249), "property"),
        "Théorème" | "À retenir" => (Rgb(103, 55, 190), Rgb(247, 242, 255), "remember"),
        "Remarque" => (Rgb(42, 100, 197), Rgb(241, 247, 255), "remark"),
        "Méthode" => (Rgb(194, 86, 26), Rgb(255, 246, 237), "method"),
        "Attention" => (Rgb(192, 54, 65), Rgb(255, 243, 244), "attention"),
        "Exemple" => (Rgb(180, 108, 12), Rgb(255, 250, 239), "example"),
        "Observation" => (Rgb(53, 126, 55), Rgb(243, 250, 239), "observation"),
        "Hypothèse" => (Rgb(118, 72, 185), Rgb(248, 243, 255), "hypothesis"),
        "Résultat" => (Rgb(39, 103, 197), Rgb(240, 246, 255), "results"),
        "Conclusion" => (Rgb(23, 124, 86), Rgb(239, 250, 244), "conclusion"),
        "Vocabulaire" => (Rgb(163, 116, 5), Rgb(255, 251, 237), "vocabulary"),
        _ => (Rgb(69, 92, 178), Rgb(245, 247, 255), "exercise"),
    };
    Theme {
        ink,
        background,
        icon,
    }
}
/// A delicate outline leaves the strong colour to the icon, title and accent.
pub fn outline(c: Rgb) -> Rgb {
    let pale = |v: u8| ((v as u16 * 22 + 255 * 78) / 100) as u8;
    Rgb(pale(c.0), pale(c.1), pale(c.2))
}
pub fn icon_png(model: &str) -> &'static [u8] {
    macro_rules! png {
        ($s:literal) => {
            include_bytes!(concat!(env!("OUT_DIR"), "/box-icons/", $s, ".png")) as &'static [u8]
        };
    }
    match theme(model).icon {
        "definition" => png!("definition"),
        "property" => png!("property"),
        "remember" => png!("remember"),
        "remark" => png!("remark"),
        "method" => png!("method"),
        "attention" => png!("attention"),
        "example" => png!("example"),
        "observation" => png!("observation"),
        "hypothesis" => png!("hypothesis"),
        "results" => png!("results"),
        "conclusion" => png!("conclusion"),
        "vocabulary" => png!("vocabulary"),
        _ => png!("exercise"),
    }
}
pub fn icon_key(model: &str) -> String {
    format!("ecr-box-{}.png", theme(model).icon)
}
