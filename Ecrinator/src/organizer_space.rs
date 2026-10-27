//! Creation of a genuine Organisator v1 school workspace, with original suite icons.
use serde_json::json;
use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
};
pub const CATEGORIES: &[&str] = &[
    "Français",
    "Mathématiques",
    "Histoire-géographie",
    "EMC",
    "Anglais",
    "Langues",
    "SVT",
    "Physique-chimie",
    "Technologie",
    "EPS",
    "Arts plastiques",
    "Musique",
    "Orientation",
    "Documents école",
    "À classer",
];
pub const COLORS: &[&str] = &[
    "e49b91", "85b7e9", "d9af69", "c4a0e1", "82c8b8", "e8ac7a", "a7b8d8", "97c892", "d6a2c1",
    "d0c27a", "81c8d2", "b5a0d4", "88bd72", "d6aeac", "cab379",
];
macro_rules! icon {
    ($color:literal) => {
        include_bytes!(concat!("../../assets/folders/folder-", $color, ".ico")).as_slice()
    };
}
const ICONS: &[&[u8]] = &[
    icon!("e49b91"),
    icon!("85b7e9"),
    icon!("d9af69"),
    icon!("c4a0e1"),
    icon!("82c8b8"),
    icon!("e8ac7a"),
    icon!("a7b8d8"),
    icon!("97c892"),
    icon!("d6a2c1"),
    icon!("d0c27a"),
    icon!("81c8d2"),
    icon!("b5a0d4"),
    icon!("88bd72"),
    icon!("d6aeac"),
    icon!("cab379"),
];
pub fn desktop() -> Result<PathBuf, String> {
    #[cfg(windows)]
    {
        if let Ok(paths) = windows::Storage::UserDataPaths::GetDefault() {
            if let Ok(value) = paths.Desktop() {
                let p = PathBuf::from(value.to_string());
                if p.is_dir() {
                    return Ok(p);
                }
            }
        }
    }
    if let Some(profile) = std::env::var_os("USERPROFILE") {
        let p = PathBuf::from(profile).join("Desktop");
        if p.is_dir() {
            return Ok(p);
        }
    }
    Err("Le Bureau est introuvable. Choisissez un espace existant, ou vérifiez son emplacement dans Windows.".into())
}
pub fn valid_name(name: &str) -> bool {
    let name = name.trim();
    let stem = name.split('.').next().unwrap_or("").to_uppercase();
    !name.is_empty()
        && name.chars().count() <= 80
        && !name.ends_with(['.', ' '])
        && !name
            .chars()
            .any(|c| c.is_control() || "<>:\"/\\|?*".contains(c))
        && !matches!(stem.as_str(), "CON" | "PRN" | "AUX" | "NUL" | "." | "..")
        && !(1..=9).any(|n| stem == format!("COM{n}") || stem == format!("LPT{n}"))
}
#[derive(Debug)]
pub struct Created {
    pub root: PathBuf,
    pub icon_warnings: usize,
}
fn fresh(path: &Path, data: &[u8]) -> Result<(), String> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|e| e.to_string())?;
    f.write_all(data)
        .and_then(|_| f.sync_all())
        .map_err(|e| e.to_string())
}
fn attributes(path: &Path, folder: bool) -> bool {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let Some(system) = std::env::var_os("SystemRoot") else {
            return false;
        };
        let mut cmd = std::process::Command::new(PathBuf::from(system).join("System32/attrib.exe"));
        // attrib does not accept the verbatim prefix returned by canonicalize.
        let display = path.as_os_str().to_string_lossy();
        let argument = if let Some(unc) = display.strip_prefix(r"\\?\UNC\") {
            PathBuf::from(format!(r"\\{unc}"))
        } else if let Some(local) = display.strip_prefix(r"\\?\") {
            PathBuf::from(local)
        } else {
            path.to_owned()
        };
        if folder {
            cmd.arg("+R");
        } else {
            cmd.args(["+H", "+S"]);
        }
        return cmd
            .arg(argument)
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .creation_flags(0x08000000)
            .status()
            .is_ok_and(|s| s.success());
    }
    #[cfg(not(windows))]
    {
        let _ = (path, folder);
        true
    }
}
/// Only creates a new child; never reuses or replaces any existing directory.
/// The manifest is committed last. On failure, the incomplete new folder is kept.
pub fn create(parent: &Path, name: &str, decorate: bool) -> Result<Created, String> {
    let name = name.trim();
    if !valid_name(name) {
        return Err(
            "Choisissez un nom simple, sans caractère spécial interdit (80 caractères maximum)."
                .into(),
        );
    }
    let parent = parent
        .canonicalize()
        .map_err(|_| "Le Bureau est inaccessible.")?;
    let root = parent.join(name);
    fs::create_dir(&root).map_err(|e| {
        if e.kind() == std::io::ErrorKind::AlreadyExists {
            "Ce nom existe déjà. Choisissez un autre nom ou associez ce dossier.".into()
        } else {
            format!("Impossible de créer le dossier : {e}")
        }
    })?;
    let result = (|| {
        let meta = root.join(".organisator");
        fs::create_dir(&meta).map_err(|e| e.to_string())?;
        let icons = meta.join("icons");
        if decorate {
            fs::create_dir(&icons).map_err(|e| e.to_string())?;
        }
        let mut warnings = 0;
        for (i, category) in CATEGORIES.iter().enumerate() {
            let folder = root.join(category);
            fs::create_dir(&folder).map_err(|e| e.to_string())?;
            let mut folders = vec![folder.clone()];
            if !["À classer", "Documents école", "Orientation"].contains(category) {
                for kind in ["Cours", "Exercices", "Évaluations"] {
                    let child = folder.join(kind);
                    fs::create_dir(&child).map_err(|e| e.to_string())?;
                    folders.push(child);
                }
            }
            if decorate {
                let color = COLORS.get(i).ok_or("Couleur de dossier absente")?;
                let icon = ICONS.get(i).ok_or("Icône de dossier absente")?;
                let filename = format!("folder-{color}.ico");
                fresh(&icons.join(&filename), icon)?;
                for folder in folders {
                    let relative = if folder.parent() == Some(root.as_path()) {
                        format!("..\\.organisator\\icons\\{filename}")
                    } else {
                        format!("..\\..\\.organisator\\icons\\{filename}")
                    };
                    let text = format!("[.ShellClassInfo]\r\nIconResource={relative},0\r\n");
                    let data: Vec<u8> = std::iter::once(0xfeff)
                        .chain(text.encode_utf16())
                        .flat_map(u16::to_le_bytes)
                        .collect();
                    let ini = folder.join("desktop.ini");
                    fresh(&ini, &data)?;
                    if !attributes(&ini, false) || !attributes(&folder, true) {
                        warnings += 1;
                    }
                }
            }
        }
        let id = format!(
            "ecr-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        );
        let config = json!({"version":1,"id":id,"profile":"Collège","categories":CATEGORIES,"created_by":"Écrinator","created_at":chrono::Local::now().to_rfc3339()});
        fresh(
            &meta.join("space.json"),
            &serde_json::to_vec_pretty(&config).map_err(|e| e.to_string())?,
        )?;
        Ok(Created {
            root: root.clone(),
            icon_warnings: warnings,
        })
    })();
    result.map_err(|e: String| {
        format!(
            "{e} Le nouveau dossier {} est conservé ; aucun dossier existant n’a été modifié.",
            root.display()
        )
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn creates_compatible_school_tree_without_overwriting() {
        let t = tempfile::tempdir().unwrap();
        let made = create(t.path(), "Mon collège", true).unwrap();
        for subject in CATEGORIES {
            assert!(made.root.join(subject).is_dir());
        }
        assert!(made.root.join("Mathématiques/Évaluations").is_dir());
        let bytes = fs::read(made.root.join(".organisator/space.json")).unwrap();
        assert_eq!(
            serde_json::from_slice::<serde_json::Value>(&bytes).unwrap()["profile"],
            "Collège"
        );
        assert!(create(t.path(), "Mon collège", false).is_err());
        assert_eq!(
            fs::read(made.root.join(".organisator/space.json")).unwrap(),
            bytes
        );
        assert!(crate::integrations::destination(&made.root, &Default::default()).is_ok());
    }
    #[test]
    fn rejects_invalid_folder_names() {
        for name in [
            "..",
            ".",
            "CON",
            "lpt1.txt",
            "cours/anglais",
            "cours\\anglais",
            "nom.",
            "a:b",
            "",
        ] {
            assert!(!valid_name(name), "{name}");
        }
    }
}
