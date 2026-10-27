//! Individual AI illustrations, optimized at build time; no network at runtime.
pub struct Art {
    pub slug: &'static str,
    pub alt: &'static str,
    pub png: &'static [u8],
    pub background: &'static [u8],
}
pub const WORKSPACE_BG: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/workspace-banner.png"));
pub const BANNER_BG: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/course-banner.png"));
pub const BG_KEY: &str = "ecr-background-v3.png";
pub const SLUGS: &[&str] = &[
    "french",
    "mathematics",
    "history",
    "emc",
    "english",
    "spanish",
    "german",
    "biology",
    "physics",
    "technology",
    "art",
    "music",
    "other",
];
macro_rules! art {
    ($slug:literal,$alt:literal) => {
        Art {
            slug: $slug,
            alt: $alt,
            background: include_bytes!(concat!(
                env!("OUT_DIR"),
                "/subject-backgrounds/",
                $slug,
                ".jpg"
            )),
            png: include_bytes!(concat!(env!("OUT_DIR"), "/subjects/", $slug, ".png")),
        }
    };
}
pub fn for_subject(subject: &str) -> Art {
    match subject {
        "Français" => art!("french", "Livre, plume et manuscrit"),
        "Mathématiques" => art!("mathematics", "Compas, équerre et volume géométrique"),
        "Histoire-géographie" => art!("history", "Tour historique, carte et globe"),
        "EMC" => art!("emc", "Mains, balance et bouclier"),
        "Anglais" => art!("english", "Tour londonienne, cabine rouge et livre"),
        "Espagnol" => art!("spanish", "Arche, guitare et éventail"),
        "Allemand" => art!("german", "Porte de Brandebourg, livre et branche de chêne"),
        "SVT" => art!("biology", "Microscope, feuilles et cellule"),
        "Physique-chimie" => art!("physics", "Bécher, fiole et modèle atomique"),
        "Technologie" => art!("technology", "Circuit, engrenages et tournevis"),
        "Arts plastiques" => art!("art", "Palette, pinceaux et crayons"),
        "Éducation musicale" => art!("music", "Clé de sol, notes et casque"),
        _ => art!("other", "Ordinateur, cahier et crayon"),
    }
}

/// Wide images retain their proportions with a non-destructive presentation crop.
pub fn background_crop(bytes: &[u8], target_width: f32, target_height: f32) -> [f32; 4] {
    let dimensions = image::ImageReader::new(std::io::Cursor::new(bytes))
        .with_guessed_format()
        .ok()
        .and_then(|r| r.into_dimensions().ok());
    let Some((w, h)) = dimensions else {
        return [0.; 4];
    };
    if w == 0 || h == 0 || target_width <= 0. || target_height <= 0. {
        return [0.; 4];
    }
    let source = w as f32 / h as f32;
    let target = target_width / target_height;
    if source < target {
        let y = (1. - source / target) * 0.5;
        [0., y, 0., y]
    } else {
        let x = (1. - target / source) * 0.5;
        [x, 0., x, 0.]
    }
}
pub fn background_key(subject: &str) -> String {
    format!("ecr-banner-v2-{}.jpg", for_subject(subject).slug)
}
