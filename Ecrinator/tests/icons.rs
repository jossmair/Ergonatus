use std::{fs, path::Path};
#[test]
fn every_icon_is_scalable_and_visible_without_system_fonts() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let mut count = 0;
    for file in fs::read_dir(root.join("assets/school-icons")).unwrap() {
        let path = file.unwrap().path();
        let bytes = fs::read(&path).unwrap();
        assert!(
            !String::from_utf8_lossy(&bytes).contains("<text"),
            "{} depends on a font",
            path.display()
        );
        let tree = resvg::usvg::Tree::from_data(&bytes, &Default::default()).unwrap();
        let mut pix = resvg::tiny_skia::Pixmap::new(96, 96).unwrap();
        resvg::render(
            &tree,
            resvg::tiny_skia::Transform::from_scale(2., 2.),
            &mut pix.as_mut(),
        );
        let visible = pix.data().chunks_exact(4).filter(|p| p[3] > 50).count();
        assert!(visible > 40, "{} is empty", path.display());
        count += 1;
    }
    assert_eq!(count, 92);
    let tree = resvg::usvg::Tree::from_data(
        &fs::read(root.join("assets/icon-catalog.svg")).unwrap(),
        &Default::default(),
    )
    .unwrap();
    let mut pix =
        resvg::tiny_skia::Pixmap::new(tree.size().width() as u32, tree.size().height() as u32)
            .unwrap();
    resvg::render(&tree, Default::default(), &mut pix.as_mut());
    fs::create_dir_all(root.join("test-output")).unwrap();
    pix.save_png(root.join("test-output/icon-catalog.png"))
        .unwrap();
}
