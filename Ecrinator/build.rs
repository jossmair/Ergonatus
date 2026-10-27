//! Embed the same original identity in Explorer, shortcuts and the Windows window.
use std::{env, fs, path::PathBuf, process::Command};
fn main() {
    prepare_library().expect("Bibliothèque hors ligne");
    prepare_subject_art().expect("Préparation des illustrations de matière");
    prepare_subject_backgrounds().expect("Préparation des fonds de matière");
    prepare_box_icons().expect("Préparation des pictogrammes pédagogiques");
    println!("cargo:rerun-if-changed=assets/workspace-banner-v1.png");
    let workspace_bg = image::open("assets/workspace-banner-v1.png")
        .expect("Fond panoramique")
        .thumbnail(1024, 342);
    workspace_bg
        .save(PathBuf::from(env::var_os("OUT_DIR").expect("OUT_DIR")).join("workspace-banner.png"))
        .expect("Préparation du fond");
    println!("cargo:rerun-if-changed=assets/workspace-banner-v3.png");
    image::open("assets/workspace-banner-v3.png")
        .expect("Fond transparent")
        .thumbnail(1024, 342)
        .save(PathBuf::from(env::var_os("OUT_DIR").expect("OUT_DIR")).join("course-banner.png"))
        .expect("Préparation du fond transparent");
    println!("cargo:rerun-if-changed=assets/ecrinator.ico");
    println!("cargo:rerun-if-env-changed=PDFINATOR_GENERATE_ICONS");
    if env::var("PDFINATOR_GENERATE_ICONS").as_deref() == Ok("1") {
        return;
    }
    if env::var("CARGO_CFG_TARGET_OS").as_deref() != Ok("windows") {
        return;
    }
    if let Err(error) = resource() {
        eprintln!("Icône Windows : {error}");
        std::process::exit(1);
    }
}
fn prepare_library() -> Result<(), Box<dyn std::error::Error>> {
    let path = PathBuf::from("assets/library/catalog.json");
    println!("cargo:rerun-if-changed={}", path.display());
    let entries: Vec<serde_json::Value> = serde_json::from_slice(&fs::read(path)?)?;
    let mut code = String::from("pub fn bytes(id:&str)->Option<&'static [u8]>{match id {\n");
    let mut thumbs =
        String::from("pub fn embedded_thumbnail(id:&str)->Option<&'static [u8]>{match id {\n");
    for entry in entries {
        let id = entry["id"].as_str().ok_or("Image sans identifiant")?;
        let file = entry["filename"].as_str().ok_or("Image sans fichier")?;
        if file.contains(['/', '\\']) {
            return Err("Chemin de bibliothèque invalide".into());
        }
        let asset = fs::canonicalize(PathBuf::from("assets/library").join(file))?;
        println!("cargo:rerun-if-changed={}", asset.display());
        code.push_str(&format!(
            "{id:?}=>Some(include_bytes!({:?})),\n",
            asset.to_string_lossy()
        ));
        let thumb = fs::canonicalize(PathBuf::from("assets/library/thumbs").join(file))?;
        println!("cargo:rerun-if-changed={}", thumb.display());
        thumbs.push_str(&format!(
            "{id:?}=>Some(include_bytes!({:?})),\n",
            thumb.to_string_lossy()
        ));
    }
    code.push_str("_=>None}}\n");
    thumbs.push_str("_=>None}}\n");
    code.push_str(&thumbs);
    fs::write(
        PathBuf::from(env::var_os("OUT_DIR").ok_or("OUT_DIR absent")?).join("library.rs"),
        code,
    )?;
    Ok(())
}
// A normal asset compilation step: preserve the generated originals in the
// project and embed small, proportionate transparent PNGs for fast documents.
fn prepare_subject_art() -> Result<(), Box<dyn std::error::Error>> {
    let out = PathBuf::from(env::var_os("OUT_DIR").ok_or("OUT_DIR absent")?).join("subjects");
    fs::create_dir_all(&out)?;
    for slug in [
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
    ] {
        let source = PathBuf::from(format!("assets/subjects/{slug}.png"));
        println!("cargo:rerun-if-changed={}", source.display());
        let original = image::open(&source)?;
        let thumb = original.thumbnail(512, 256).to_rgba8();
        let mut canvas = image::RgbaImage::new(512, 256);
        let x = (512 - thumb.width()) / 2;
        let y = (256 - thumb.height()) / 2;
        image::imageops::overlay(&mut canvas, &thumb, x.into(), y.into());
        canvas.save(out.join(format!("{slug}.png")))?;
    }
    Ok(())
}
// Preserve generated originals; the compiled app embeds proportionate JPEGs.
fn prepare_subject_backgrounds() -> Result<(), Box<dyn std::error::Error>> {
    let out =
        PathBuf::from(env::var_os("OUT_DIR").ok_or("OUT_DIR absent")?).join("subject-backgrounds");
    fs::create_dir_all(&out)?;
    for slug in [
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
    ] {
        let source = format!("assets/subject-backgrounds/{slug}.png");
        println!("cargo:rerun-if-changed={source}");
        let image = image::open(&source)?.thumbnail(1800, 700).to_rgb8();
        let file = std::fs::File::create(out.join(format!("{slug}.jpg")))?;
        image::codecs::jpeg::JpegEncoder::new_with_quality(file, 88).encode_image(&image)?;
    }
    Ok(())
}
fn prepare_box_icons() -> Result<(), Box<dyn std::error::Error>> {
    let out = PathBuf::from(env::var_os("OUT_DIR").ok_or("OUT_DIR absent")?).join("box-icons");
    fs::create_dir_all(&out)?;
    for name in [
        "definition",
        "property",
        "remember",
        "remark",
        "method",
        "attention",
        "example",
        "exercise",
        "observation",
        "hypothesis",
        "results",
        "conclusion",
        "vocabulary",
    ] {
        let source = format!("assets/school-icons/{name}.svg");
        println!("cargo:rerun-if-changed={source}");
        let tree = resvg::usvg::Tree::from_data(&fs::read(&source)?, &Default::default())?;
        let mut pix = resvg::tiny_skia::Pixmap::new(144, 144).ok_or("Pictogramme invalide")?;
        resvg::render(
            &tree,
            resvg::tiny_skia::Transform::from_scale(3., 3.),
            &mut pix.as_mut(),
        );
        pix.save_png(out.join(format!("{name}.png")))?;
    }
    Ok(())
}
fn resource() -> Result<(), Box<dyn std::error::Error>> {
    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").ok_or("Dossier du projet absent")?);
    if !root.join("assets/ecrinator.ico").is_file() {
        return Err("Générez assets/ecrinator.ico avant de compiler l’application.".into());
    }
    let out = PathBuf::from(env::var_os("OUT_DIR").ok_or("Dossier de compilation absent")?);
    let icon = root
        .join("assets/ecrinator.ico")
        .to_string_lossy()
        .replace('\\', "/");
    let version = env::var("CARGO_PKG_VERSION").unwrap_or_else(|_| "0.3.1".into());
    let numeric = format!("{},0", version.replace('.', ","));
    let script = format!(
        r#"#pragma code_page(65001)
1 ICON "{icon}"
1 VERSIONINFO
FILEVERSION {numeric}
PRODUCTVERSION {numeric}
FILEOS 0x40004
FILETYPE 1
BEGIN
 BLOCK "StringFileInfo"
 BEGIN
  BLOCK "040c04b0"
  BEGIN
   VALUE "CompanyName", "Ergonatus\0"
   VALUE "FileDescription", "Écrinator\0"
   VALUE "FileVersion", "{version}\0"
   VALUE "InternalName", "ecrinator\0"
   VALUE "OriginalFilename", "ecrinator.exe\0"
   VALUE "ProductName", "Écrinator — Ergonatus\0"
   VALUE "ProductVersion", "{version}\0"
  END
 END
 BLOCK "VarFileInfo"
 BEGIN
  VALUE "Translation", 0x040c, 1200
 END
END
"#
    );
    fs::write(out.join("ecrinator.rc"), script)?;
    let mut candidates = Vec::new();
    if let Some(bin) = env::var_os("WindowsSdkVerBinPath") {
        candidates.push(PathBuf::from(bin).join("x64/rc.exe"));
    }
    if let Some(programs) = env::var_os("ProgramFiles(x86)") {
        let bin = PathBuf::from(programs).join("Windows Kits/10/bin");
        if let Ok(directories) = fs::read_dir(bin) {
            let mut versions: Vec<_> = directories
                .flatten()
                .map(|d| d.path().join("x64/rc.exe"))
                .filter(|p| p.is_file())
                .collect();
            versions.sort();
            versions.reverse();
            candidates.extend(versions);
        }
    }
    candidates.push("rc.exe".into());
    let output = out.join("ecrinator.res");
    for compiler in candidates {
        match Command::new(compiler)
            .arg("/nologo")
            .arg("/fo")
            .arg(&output)
            .arg(out.join("ecrinator.rc"))
            .status()
        {
            Ok(status) if status.success() => {
                println!("cargo:rustc-link-arg-bin=ecrinator={}", output.display());
                return Ok(());
            }
            Ok(_) => return Err("La compilation de la ressource Windows a échoué.".into()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
            Err(e) => return Err(e.into()),
        }
    }
    Err("rc.exe est absent : installez le Windows SDK des Build Tools C++.".into())
}
