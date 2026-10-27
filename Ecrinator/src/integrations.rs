//! Optional Organisator v1 integration. Only existing, declared school destinations.
use crate::core::School;
use serde::Deserialize;
use std::{
    fs,
    path::{Path, PathBuf},
};
#[derive(Deserialize)]
struct Space {
    version: u32,
    profile: String,
    categories: Vec<String>,
}
/// Validate an association without creating destinations or moving documents.
pub fn validate_space(root: &Path) -> Result<PathBuf, String> {
    let root = space_root(root)?;
    let manifest = root.join(".organisator/space.json");
    reject_link(&manifest)?;
    if fs::metadata(&manifest).map_err(|e| e.to_string())?.len() > 64000 {
        return Err("Manifeste Organisator trop volumineux.".into());
    }
    let space: Space = serde_json::from_slice(&fs::read(manifest).map_err(|e| e.to_string())?)
        .map_err(|_| "Ce dossier n’est pas un espace scolaire Organisator valide.")?;
    if space.version != 1 || !["Collège", "École primaire"].contains(&space.profile.as_str()) {
        return Err("Choisissez un espace scolaire Organisator version 1.".into());
    }
    Ok(root)
}
pub fn destination(root: &Path, school: &School) -> Result<PathBuf, String> {
    let root = space_root(root)?;
    let manifest = root.join(".organisator/space.json");
    reject_link(&manifest)?;
    if fs::metadata(&manifest).map_err(|e| e.to_string())?.len() > 64000 {
        return Err("Manifeste Organisator trop volumineux.".into());
    }
    let space: Space = serde_json::from_slice(&fs::read(&manifest).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    if space.version != 1 || !["Collège", "École primaire"].contains(&space.profile.as_str()) {
        return Err("Choisissez un espace scolaire Organisator version 1.".into());
    }
    let category = match school.subject.as_str() {
        "Éducation musicale" => "Musique",
        "Espagnol" | "Allemand" => "Langues",
        "Anglais" if !space.categories.iter().any(|c| c == "Anglais") => "Langues",
        "SVT" | "Physique-chimie" if space.profile == "École primaire" => "Sciences",
        v => v,
    };
    if std::path::Path::new(category).components().count() != 1
        || !matches!(
            std::path::Path::new(category).components().next(),
            Some(std::path::Component::Normal(_))
        )
    {
        return Err("Nom de matière invalide.".into());
    }
    if !space.categories.iter().any(|c| c == category) {
        return Err(format!(
            "La matière {category} n’existe pas dans cet espace."
        ));
    }
    let target = root.join(category).join(school.folder_kind());
    // Restore only the school folders explicitly declared by this manifest.
    // Never make a guessed workspace or follow a link outside the chosen one.
    for child in [root.join(category), target.clone()] {
        if !child.exists() {
            let parent = child
                .parent()
                .ok_or("Dossier invalide")?
                .canonicalize()
                .map_err(|_| "Le dossier parent est inaccessible.")?;
            if !parent.starts_with(&root) {
                return Err("Destination extérieure à l’espace.".into());
            }
            fs::create_dir(&child).map_err(|e| {
                format!(
                    "Impossible de recréer le dossier scolaire {} : {e}",
                    child.display()
                )
            })?;
        }
        reject_link(&child)?;
    }
    let mut cursor = target.as_path();
    while cursor != root {
        reject_link(cursor)?;
        cursor = cursor.parent().ok_or("Dossier invalide")?;
    }
    let canonical = fs::canonicalize(&target)
        .map_err(|_| "Le dossier de destination est absent de cet espace.".to_string())?;
    if !canonical.starts_with(&root) {
        return Err("Destination extérieure à l’espace.".into());
    }
    Ok(canonical)
}
/// Accept the workspace itself, its manifest, or one of its course folders.
pub fn space_root(path: &Path) -> Result<PathBuf, String> {
    let mut candidate = std::path::absolute(path).map_err(|e| e.to_string())?;
    if candidate.is_file() {
        candidate.pop();
    }
    for _ in 0..16 {
        let manifest = candidate.join(".organisator/space.json");
        if manifest.is_file() {
            reject_link(&manifest)?;
            return candidate.canonicalize().map_err(|e| e.to_string());
        }
        if !candidate.pop() {
            break;
        }
    }
    Err("L’espace Organisator est introuvable ou a été déplacé. Cliquez sur Classer pour sélectionner sa racine (le dossier contenant .organisator).".into())
}
/// The target was exclusively reserved by this save. Delete it only while its
/// stamp still matches; never remove a file another application has changed.
pub fn discard_reservation(path: &Path, stamp: &Option<crate::storage::Stamp>) {
    if stamp.is_some() && crate::storage::stamp(path) == *stamp {
        let _ = fs::remove_file(path);
    }
}
/// Durable write, readback, then removal of the old file. Failure keeps the
/// original and rolls back our new target whenever it is still ours.
pub fn write_relocated(
    source: Option<(&Path, &crate::storage::Stamp)>,
    target: &Path,
    reserved: &Option<crate::storage::Stamp>,
    bytes: &[u8],
) -> Result<(), String> {
    // A reservation must be an empty file created by reserve(). These checks
    // precede rollback: a caller cannot authorize deleting an existing document.
    reject_link(target)?;
    if fs::metadata(target).map_err(|e| e.to_string())?.len() != 0 {
        return Err("La destination n’est pas une réservation vide.".into());
    }
    if let Some((path, _)) = source {
        if path.canonicalize().ok() == target.canonicalize().ok() {
            return Err("Le fichier est déjà à cet emplacement.".into());
        }
    }
    let result = (|| {
        if reserved.is_none() || crate::storage::stamp(target) != *reserved {
            return Err("La destination a changé. Aucun fichier existant n’a été remplacé.".into());
        }
        let previous = if let Some((path, stamp)) = source {
            reject_link(path)?;
            if crate::storage::stamp(path).as_ref() != Some(stamp) {
                return Err(
                    "Le fichier d’origine a changé. Il est conservé ; choisissez Enregistrer sous."
                        .into(),
                );
            }
            if fs::metadata(path).map_err(|e| e.to_string())?.len() > crate::storage::MAX_FILE {
                return Err(
                    "Fichier d’origine trop volumineux pour un déplacement vérifié.".into(),
                );
            }
            Some(fs::read(path).map_err(|e| e.to_string())?)
        } else {
            None
        };
        crate::storage::atomic_write(target, bytes)?;
        let written = crate::storage::stamp(target);
        let commit = (|| {
            if fs::read(target).map_err(|e| e.to_string())? != bytes {
                return Err("La nouvelle sauvegarde n’a pas pu être vérifiée.".into());
            }
            if let Some((path, stamp)) = source {
                if crate::storage::stamp(path).as_ref() != Some(stamp)
                    || fs::read(path).map_err(|e| e.to_string())?.as_slice()
                        != previous.as_deref().ok_or("Source non vérifiée")?
                {
                    return Err(
                        "Le fichier d’origine a changé pendant le déplacement. Il est conservé."
                            .into(),
                    );
                }
                fs::remove_file(path).map_err(|e| {
                    format!(
                        "Le fichier d’origine est utilisé ou inaccessible ; il est conservé ({e})."
                    )
                })?;
            }
            Ok(())
        })();
        if commit.is_err() {
            discard_reservation(target, &written);
        }
        commit
    })();
    if result.is_err() {
        discard_reservation(target, reserved);
    }
    result
}
fn reject_link(p: &Path) -> Result<(), String> {
    let m = fs::symlink_metadata(p).map_err(|e| e.to_string())?;
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        if m.file_attributes() & 0x400 != 0 {
            return Err("Les liens et jonctions ne sont pas acceptés.".into());
        }
    }
    if m.file_type().is_symlink() {
        return Err("Lien symbolique non accepté.".into());
    }
    Ok(())
}
pub fn filename(s: &School) -> String {
    if s.subject == crate::core::BLANK {
        return "Document.odt".into();
    }
    let clean: String = s
        .title
        .chars()
        .filter(|c| !c.is_control() && !"<>:\"/\\|?*".contains(*c))
        .take(75)
        .collect();
    let clean = clean.trim().trim_end_matches(['.', ' ']);
    format!(
        "Chapitre {} - {}.odt",
        s.chapter,
        if clean.is_empty() { "Cours" } else { clean }
    )
}
/// Atomically reserve a never-used name before starting an initial save.
pub fn reserve(dir: &Path, s: &School) -> Result<PathBuf, String> {
    let base = filename(s);
    let stem = base.strip_suffix(".odt").unwrap_or(&base);
    for n in 0..10000 {
        let name = if n == 0 {
            base.clone()
        } else {
            format!("{stem} ({n}).odt")
        };
        let p = dir.join(name);
        match fs::OpenOptions::new().write(true).create_new(true).open(&p) {
            Ok(_) => return Ok(p),
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(e) => return Err(e.to_string()),
        }
    }
    Err("Trop de documents portent ce nom.".into())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn respects_existing_tree_and_never_overwrites() {
        let t = tempfile::tempdir().unwrap();
        fs::create_dir_all(t.path().join(".organisator")).unwrap();
        fs::create_dir_all(t.path().join("Mathématiques/Exercices")).unwrap();
        fs::write(
            t.path().join(".organisator/space.json"),
            r#"{"version":1,"profile":"Collège","categories":["Mathématiques"]}"#,
        )
        .unwrap();
        let s = School {
            subject: "Mathématiques".into(),
            exercises: true,
            ..Default::default()
        };
        let dest = destination(t.path(), &s).unwrap();
        let a = reserve(&dest, &s).unwrap();
        let b = reserve(&dest, &s).unwrap();
        assert_ne!(a, b);
        assert!(destination(t.path(), &School::default()).is_err());
    }
    #[test]
    fn relocation_verifies_source_and_preserves_collisions() {
        let t = tempfile::tempdir().unwrap();
        let old = t.path().join("source.odt");
        fs::write(&old, b"original").unwrap();
        let stamp = crate::storage::stamp(&old).unwrap();
        let target = reserve(t.path(), &School::default()).unwrap();
        let reserved = crate::storage::stamp(&target);
        write_relocated(
            Some((&old, &stamp)),
            &target,
            &reserved,
            b"nouveau document complet",
        )
        .unwrap();
        assert!(!old.exists());
        assert_eq!(fs::read(&target).unwrap(), b"nouveau document complet");
        // An existing, populated target cannot be passed off as a reservation.
        let stamp = crate::storage::stamp(&target);
        assert!(write_relocated(None, &target, &stamp, b"intrus").is_err());
        assert_eq!(fs::read(&target).unwrap(), b"nouveau document complet");
        fs::write(&old, b"premiere version").unwrap();
        let stamp = crate::storage::stamp(&old).unwrap();
        fs::write(&old, b"une modification externe plus recente").unwrap();
        let dest = reserve(t.path(), &School::default()).unwrap();
        let reserved = crate::storage::stamp(&dest);
        assert!(
            write_relocated(Some((&old, &stamp)), &dest, &reserved, b"copie obsolete").is_err()
        );
        assert_eq!(
            fs::read(&old).unwrap(),
            b"une modification externe plus recente"
        );
        assert!(!dest.exists());
        assert!(target.exists());
    }
    #[test]
    fn organizer_root_accepts_nested_folders_and_restores_declared_destinations() {
        let t = tempfile::tempdir().unwrap();
        fs::create_dir(t.path().join(".organisator")).unwrap();
        let manifest = t.path().join(".organisator/space.json");
        fs::write(
            &manifest,
            r#"{"version":1,"profile":"Collège","categories":["Français","Langues"]}"#,
        )
        .unwrap();
        let course = destination(&manifest, &School::default()).unwrap();
        assert!(course.is_dir());
        let mut school = School::default();
        school.set_work_kind(crate::core::WorkKind::Exercises);
        let exercises = destination(&course, &school).unwrap();
        assert_eq!(exercises.file_name().unwrap(), "Exercices");
        school.subject = "Espagnol".into();
        assert!(
            destination(t.path(), &school)
                .unwrap()
                .ends_with("Langues/Exercices")
        );
        let absent = tempfile::tempdir().unwrap();
        let missing = absent.path().join("absent");
        let error = space_root(&missing).unwrap_err();
        assert!(error.contains("Classer"));
    }
}
