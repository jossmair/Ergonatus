use super::*;
#[test]
fn window_controls_show_hover_and_pressed_feedback() {
    let (mut a, ctx) = app();
    let size = [1280., 720.];
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], size);
    }
    for icon in ["minimize", "maximize", "close"] {
        let id = egui::Id::new(("window-button-state", icon));
        let (_, _, rect) = ctx
            .data(|d| d.get_temp::<(bool, bool, egui::Rect)>(id))
            .unwrap();
        let at = rect.center();
        frame(&mut a, &ctx, vec![egui::Event::PointerMoved(at)], size);
        let (hover, pressed, _) = ctx
            .data(|d| d.get_temp::<(bool, bool, egui::Rect)>(id))
            .unwrap();
        assert!(hover, "{icon} must highlight on hover");
        assert!(!pressed);
        frame(
            &mut a,
            &ctx,
            vec![egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: Modifiers::default(),
            }],
            size,
        );
        assert!(
            ctx.data(|d| d.get_temp::<(bool, bool, egui::Rect)>(id))
                .unwrap()
                .1,
            "{icon} must highlight while pressed"
        );
        // Release away from the control: do not minimize or close the test window.
        frame(
            &mut a,
            &ctx,
            vec![
                egui::Event::PointerMoved(egui::pos2(500., 500.)),
                egui::Event::PointerButton {
                    pos: egui::pos2(500., 500.),
                    button: egui::PointerButton::Primary,
                    pressed: false,
                    modifiers: Modifiers::default(),
                },
            ],
            size,
        );
    }
}
fn frame(
    app: &mut App,
    ctx: &egui::Context,
    events: Vec<egui::Event>,
    size: [f32; 2],
) -> egui::FullOutput {
    let mut output = ctx.run_ui(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(size[0], size[1]),
            )),
            events,
            ..Default::default()
        },
        |ui| app.show(ui),
    );
    output.textures_delta.clear();
    output
}
fn click_at(a: &mut App, ctx: &egui::Context, at: egui::Pos2, size: [f32; 2]) {
    frame(
        a,
        ctx,
        vec![
            egui::Event::PointerMoved(at),
            egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: Modifiers::default(),
            },
        ],
        size,
    );
    frame(
        a,
        ctx,
        vec![egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Modifiers::default(),
        }],
        size,
    );
}

#[test]
fn plus_follows_the_last_tab_and_creates_a_separate_document() {
    let (mut a, ctx) = app();
    let size = [1280., 720.];
    a.command("text.insert", json!({"text":"Mon cours à garder"}));
    let original = a.active_id;
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], size);
    }
    let first = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("new-tab-rect")))
        .unwrap();
    let last = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("last-tab-rect")))
        .unwrap();
    assert!(
        (first.center().y - last.center().y).abs() < 1.5,
        "Plus baseline differs from tabs"
    );
    assert!(first.left() - last.right() >= 4. && first.left() - last.right() < 20.);
    assert_eq!(first.size(), egui::vec2(32., 32.));
    assert!(
        first.left() < 280.,
        "Plus is separated from the last tab: {first:?}"
    );
    click_at(&mut a, &ctx, first.center(), size);
    assert_eq!(a.tab_order.len(), 2);
    assert_ne!(a.active_id, original);
    a.dialog = None;
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], size);
    }
    let second = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("new-tab-rect")))
        .unwrap();
    assert!(second.left() > first.right() && second.left() < 490.);
    a.activate_tab(original);
    assert!(
        a.word
            .session
            .doc
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("Mon cours à garder")
    );
}

#[test]
fn tool_actions_stay_visible_and_equations_insert_with_undo() {
    let (mut a, ctx) = app();
    for size in [[560., 560.], [800., 580.]] {
        for tool in 0..5 {
            a.dialog = Some(match tool {
                0..=2 => dialogs::Dialog::Formula {
                    kind: tool,
                    a: "3".into(),
                    b: "4".into(),
                },
                3 => dialogs::Dialog::Table { rows: 3, cols: 4 },
                _ => dialogs::Dialog::Page {
                    margin: 18.,
                    line: 1.25,
                    spacing: 0.,
                },
            });
            let before = a.word.session.doc.clone();
            for _ in 0..4 {
                frame(&mut a, &ctx, vec![], size);
            }
            assert_eq!(
                a.word.session.doc, before,
                "Preview must not edit the course"
            );
            let rect = ctx
                .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("ecr-design-apply-rect")))
                .unwrap();
            assert!(ctx.content_rect().contains_rect(rect));
            frame(
                &mut a,
                &ctx,
                vec![key(Key::Escape, Modifiers::default())],
                size,
            );
            assert!(a.dialog.is_none());
        }
    }
    let before = a.word.session.doc.clone();
    a.dialog = Some(dialogs::Dialog::Formula {
        kind: 0,
        a: "3".into(),
        b: "4".into(),
    });
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], [800., 580.]);
    }
    let rect = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("ecr-design-apply-rect")))
        .unwrap();
    click_at(&mut a, &ctx, rect.center(), [800., 580.]);
    assert!(a.dialog.is_none());
    assert_ne!(a.word.session.doc, before);
    a.word.session.undo();
    assert_eq!(a.word.session.doc, before);
}
fn key(key: Key, modifiers: Modifiers) -> egui::Event {
    egui::Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers,
    }
}
fn app() -> (App, egui::Context) {
    let ctx = egui::Context::default();
    let mut a = App::new(&ctx, None, None);
    a.dialog = None;
    a.recoveries.clear();
    for _ in 0..4 {
        frame(&mut a, &ctx, vec![], [1448., 1086.]);
    }
    (a, ctx)
}
#[test]
fn design_dialog_actions_remain_visible_in_small_windows() {
    let (mut a, ctx) = app();
    for size in [[800., 580.], [1280., 720.], [560., 560.]] {
        for header in [true, false] {
            if header {
                a.dialog = Some(dialogs::Dialog::Header(a.school.clone()));
            } else {
                a.word.session.sel = Selection::caret(core::writing_position(&a.word.session.doc));
                ecrinator::blocks::insert(&mut a.word.session, "Définition").unwrap();
                a.dialog = Some(dialogs::Dialog::Box(
                    ecrinator::blocks::appearance(&a.word.session).unwrap(),
                ));
            }
            for _ in 0..4 {
                frame(&mut a, &ctx, vec![], size);
            }
            let button = ctx
                .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("ecr-design-apply-rect")))
                .unwrap();
            assert!(
                ctx.content_rect().contains_rect(button),
                "Apply outside {size:?}: {button:?}"
            );
            frame(
                &mut a,
                &ctx,
                vec![key(Key::Escape, Modifiers::default())],
                size,
            );
            assert!(a.dialog.is_none());
        }
    }
}
#[test]
fn typing_keyboard_formatting_undo_redo() {
    let (mut a, ctx) = app();
    a.word.canvas.want_focus = true;
    frame(&mut a, &ctx, vec![], [1448., 1086.]);
    frame(
        &mut a,
        &ctx,
        vec![egui::Event::Text("Écrire avec précision".into())],
        [1448., 1086.],
    );
    assert!(
        a.word
            .session
            .doc
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("Écrire avec précision")
    );
    let ctrl = Modifiers {
        ctrl: true,
        command: true,
        ..Default::default()
    };
    frame(&mut a, &ctx, vec![key(Key::Z, ctrl)], [1448., 1086.]);
    assert!(
        !a.word
            .session
            .doc
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("Écrire avec précision")
    );
    frame(&mut a, &ctx, vec![key(Key::Y, ctrl)], [1448., 1086.]);
    assert!(
        a.word
            .session
            .doc
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("Écrire avec précision")
    );
}
#[test]
fn small_screen_keeps_close_control_and_editor() {
    let (mut a, ctx) = app();
    for size in [[800., 580.], [1280., 720.], [1448., 1086.]] {
        for _ in 0..3 {
            frame(&mut a, &ctx, vec![], size);
        }
        assert!(!a.word.canvas.page_rects.is_empty());
        assert!(a.word.canvas.canvas_rect.is_some());
        let close = ctx
            .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("ecr-close-rect")))
            .unwrap();
        assert!(
            close.right() <= size[0] + 1.,
            "close button outside {size:?}: {close:?}"
        );
    }
}
#[test]
fn compact_controls_leave_most_of_the_window_for_writing() {
    let (mut a, ctx) = app();
    a.tools = false;
    a.pages.visible = false;
    for size in [[800., 580.], [1280., 720.], [1448., 1086.]] {
        for _ in 0..4 {
            frame(&mut a, &ctx, vec![], size);
        }
        let rect = a.word.canvas.canvas_rect.unwrap();
        assert!(rect.top() <= 140., "toolbar too tall at {size:?}: {rect:?}");
        assert!(
            rect.height() >= size[1] - 184.,
            "writing surface too short: {rect:?}"
        );
        assert!(
            rect.width() >= size[0] * 0.90,
            "writing surface too narrow: {rect:?}"
        );
    }
}

#[test]
fn stale_open_cannot_replace_new_writing() {
    let (mut a, ctx) = app();
    let rev = a.word.session.rev();
    a.command("text.insert", json!({"text":"À conserver"}));
    a.tx.send(Event::Opened {
        path: "autre.ecr".into(),
        result: Ok(wordcraft_doc::Document::new()),
        rev,
    })
    .unwrap();
    a.poll(&ctx);
    assert!(
        a.word
            .session
            .doc
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("À conserver")
    );
}
#[test]
fn dropping_another_document_keeps_its_own_save_destination() {
    let (mut a, ctx) = app();
    let dir = tempfile::tempdir().unwrap();
    let original_path = dir.path().join("original.ecr");
    let incoming_path = dir.path().join("autre.ecr");
    storage::save(&original_path, &a.word.session.doc).unwrap();
    let original_bytes = std::fs::read(&original_path).unwrap();
    let incoming = core::new_document(&School {
        title: "Autre cours".into(),
        ..Default::default()
    })
    .unwrap();
    storage::save(&incoming_path, &incoming).unwrap();
    a.path = Some(original_path.clone());
    a.stamp = storage::stamp(&original_path);
    a.command("text.insert", json!({"text":"Modifications à garder"}));
    let old_id = a.active_id;
    a.dropped_file(incoming_path.clone(), &ctx);
    assert!(a.pending.is_none());
    assert_eq!(a.tab_order.len(), 2);
    let deadline = Instant::now() + Duration::from_secs(5);
    while a.busy && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(10));
        a.poll(&ctx);
    }
    assert!(!a.busy);
    assert_eq!(a.path.as_ref(), Some(&incoming_path));
    assert_eq!(a.word.session.doc, incoming);
    a.activate_tab(old_id);
    assert_eq!(a.path.as_ref(), Some(&original_path));
    assert!(a.word.session.dirty);
    assert!(
        a.word
            .session
            .doc
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("Modifications à garder")
    );
    assert_eq!(std::fs::read(&original_path).unwrap(), original_bytes);
}
#[test]
fn save_receipt_does_not_mark_newer_edits_saved() {
    let (mut a, ctx) = app();
    let rev = a.word.session.rev();
    a.command("text.insert", json!({"text":"Encore modifié"}));
    a.tx.send(Event::Saved {
        path: "cours.ecr".into(),
        result: Ok(()),
        rev,
        export: false,
    })
    .unwrap();
    a.poll(&ctx);
    assert!(a.word.session.dirty);
}
#[test]
fn every_subject_and_ribbon_draws() {
    let (mut a, ctx) = app();
    a.tools = true;
    for subject in core::SUBJECTS {
        let s = School {
            subject: (*subject).into(),
            ..Default::default()
        };
        core::update_header(&mut a.word.session, &s).unwrap();
        for tab in 0..3 {
            a.ribbon_tab = tab;
            frame(&mut a, &ctx, vec![], [1448., 1086.]);
        }
    }
}

fn blank_school() -> School {
    School {
        subject: core::BLANK.into(),
        show_banner: false,
        ..Default::default()
    }
}
fn text(a: &App) -> String {
    a.word.session.doc.plain_text(wordcraft_doc::StoryRef::Body)
}
fn finish_workers(a: &mut App, ctx: &egui::Context) {
    // This is a completion bound, not a performance benchmark. CPU-heavy
    // export tests and an optimized build can run concurrently on the host.
    let deadline = Instant::now() + Duration::from_secs(30);
    while (a.busy || a.inactive.iter().any(|s| s.busy)) && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(10));
        a.maintain_tabs(ctx);
    }
    assert!(!a.busy && a.inactive.iter().all(|s| !s.busy));
}
#[test]
fn automatic_organisator_saves_follow_the_only_selected_work_type() {
    let (mut a, ctx) = app();
    let root = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(root.path().join(".organisator")).unwrap();
    std::fs::write(
        root.path().join(".organisator/space.json"),
        r#"{"version":1,"profile":"Collège","categories":["Français"]}"#,
    )
    .unwrap();
    for folder in ["Cours", "Exercices", "Évaluations"] {
        std::fs::create_dir_all(root.path().join("Français").join(folder)).unwrap();
    }
    a.prefs.space = Some(root.path().to_path_buf());
    a.prefs.organize = true;
    a.command("text.insert", json!({"text":"Mon travail à classer"}));
    let mut paths = Vec::new();
    for (index, (tag, folder)) in [
        ("ecr.lesson", "Cours"),
        ("ecr.exercises", "Exercices"),
        ("ecr.assessment", "Évaluations"),
    ]
    .into_iter()
    .enumerate()
    {
        // No UI frame refreshes the cached School before the autosave.
        a.last_backup = Instant::now();
        a.command("developer.toggleCheckBox", json!({"control":tag}));
        a.sync_routing();
        if index == 0 {
            a.last_backup = Instant::now() - Duration::from_secs(11);
        } else {
            assert!(
                a.last_backup.elapsed() >= Duration::from_secs(10),
                "A type change must request immediate autosaving"
            );
        }
        a.autosave(&ctx);
        finish_workers(&mut a, &ctx);
        let path = a
            .path
            .clone()
            .expect("Automatic saving must produce a document");
        let expected = std::fs::canonicalize(root.path().join("Français").join(folder)).unwrap();
        assert_eq!(path.parent(), Some(expected.as_path()));
        let saved = storage::read(&path).unwrap();
        let school = School::read(&saved);
        assert_eq!(school.folder_kind(), folder);
        assert_eq!(
            [school.lesson, school.exercises, school.assessment]
                .into_iter()
                .filter(|b| *b)
                .count(),
            1
        );
        assert!(
            saved
                .plain_text(wordcraft_doc::StoryRef::Body)
                .contains("Mon travail à classer")
        );
        assert!(!a.word.session.dirty);
        paths.push(path);
    }
    assert!(paths.last().unwrap().is_file());
    assert!(
        paths[..paths.len() - 1].iter().all(|p| !p.exists()),
        "Changing type must move the previous file"
    );
}
#[test]
fn select_all_replaces_only_the_course_body() {
    let (mut a, ctx) = app();
    let banner = a.word.session.doc.body[0].clone();
    a.command("text.insert", json!({"text":"Ancien texte"}));
    let ctrl = Modifiers {
        ctrl: true,
        command: true,
        ..Default::default()
    };
    frame(&mut a, &ctx, vec![key(Key::A, ctrl)], [1280., 720.]);
    a.command("text.insert", json!({"text":"Nouveau texte"}));
    assert_eq!(a.word.session.doc.body[0], banner);
    assert!(text(&a).contains("Nouveau texte"));
    assert!(!text(&a).contains("Ancien texte"));
}
#[test]
fn tabs_keep_text_history_selection_zoom_and_recovery_independent() {
    let (mut a, ctx) = app();
    a.command("text.insert", json!({"text":"Premier cours"}));
    a.word.session.view.zoom = 1.4;
    let first = a.active_id;
    let caret = a.word.session.sel.clone();
    let recovery = a.recovery.clone();
    a.new_tab(blank_school()).unwrap();
    let second = a.active_id;
    assert_ne!(recovery, a.recovery);
    a.command("text.insert", json!({"text":"Deuxième cours"}));
    a.word.session.view.zoom = 0.8;
    a.activate_tab(first);
    assert!(text(&a).contains("Premier cours"));
    assert!(!text(&a).contains("Deuxième cours"));
    assert_eq!(a.word.session.sel.focus, caret.focus);
    assert_eq!(a.word.session.view.zoom, 1.4);
    a.command("edit.undo", json!({}));
    assert!(!text(&a).contains("Premier cours"));
    a.activate_tab(second);
    assert_eq!(text(&a), "Deuxième cours");
    assert_eq!(a.word.session.view.zoom, 0.8);
    a.next_tab(false);
    assert_eq!(a.active_id, first);
    a.next_tab(true);
    assert_eq!(a.active_id, second);
    a.maintain_tabs(&ctx);
}
#[test]
fn asynchronous_save_stays_with_its_source_tab() {
    let (mut a, ctx) = app();
    let dir = tempfile::tempdir().unwrap();
    a.command("text.insert", json!({"text":"Texte enregistré dans A"}));
    let first = a.active_id;
    let destination = dir.path().join("cours A.ecr");
    a.command(
        "developer.toggleCheckBox",
        json!({"control":"ecr.assessment","value":true}),
    );
    assert!(!a.school.assessment); // metadata cache has not seen a UI frame yet
    a.path = Some(destination.clone());
    a.save(false, &ctx);
    assert!(a.school.assessment);
    a.new_tab(blank_school()).unwrap();
    let second = a.active_id;
    a.command("text.insert", json!({"text":"Travail en cours dans B"}));
    a.write(destination.clone(), false, &ctx);
    assert!(
        !a.busy,
        "the other tab must own its first save path before the receipt arrives"
    );
    assert!(a.status.contains("autre onglet"));
    finish_workers(&mut a, &ctx);
    assert_eq!(a.active_id, second);
    assert!(a.path.is_none());
    assert!(a.word.session.dirty);
    assert_eq!(text(&a), "Travail en cours dans B");
    assert!(
        storage::read(&destination)
            .unwrap()
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("Texte enregistré dans A")
    );
    a.activate_tab(first);
    assert_eq!(a.path.as_ref(), Some(&destination));
    assert!(a.file_job.is_none());
    assert!(!a.word.session.dirty);
    assert!(a.already_open(&destination));
    assert_eq!(a.tab_order.len(), 2);
    a.activate_tab(second);
    a.write(destination.clone(), false, &ctx);
    assert!(!a.busy);
    assert!(a.status.contains("autre onglet"));
}
#[test]
fn inactive_document_gets_its_own_crash_recovery() {
    let (mut a, ctx) = app();
    a.command("text.insert", json!({"text":"Cours resté en arrière-plan"}));
    let first = a.active_id;
    let recovery = a.recovery.clone();
    a.last_backup = Instant::now() - Duration::from_secs(11);
    a.new_tab(blank_school()).unwrap();
    a.maintain_tabs(&ctx);
    finish_workers(&mut a, &ctx);
    assert!(
        storage::read(&recovery)
            .unwrap()
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("arrière-plan")
    );
    a.activate_tab(first);
    assert!(a.word.session.dirty);
    let _ = std::fs::remove_file(recovery);
}
#[test]
fn close_prompts_keep_each_modified_tab_and_escape_cancels_quit() {
    let (mut a, ctx) = app();
    a.command("text.insert", json!({"text":"Cours A"}));
    let first = a.active_id;
    a.new_tab(blank_school()).unwrap();
    a.command("text.insert", json!({"text":"Cours B"}));
    a.request(Action::CloseTab, &ctx);
    assert!(matches!(a.pending, Some(Action::CloseTab)));
    assert_eq!(a.tab_order.len(), 2);
    frame(&mut a, &ctx, vec![], [1280., 720.]);
    frame(
        &mut a,
        &ctx,
        vec![key(Key::Escape, Modifiers::default())],
        [1280., 720.],
    );
    assert!(a.pending.is_none());
    assert_eq!(a.tab_order.len(), 2);
    a.request(Action::Close, &ctx);
    assert!(a.closing_all);
    // Explicitly discard B. A must still be protected by its own prompt.
    let action = a.pending.take().unwrap();
    a.word.session.dirty = false;
    a.perform(action, &ctx);
    assert_eq!(a.active_id, first);
    assert!(matches!(a.pending, Some(Action::Close)));
    assert!(!a.closing);
    assert!(text(&a).contains("Cours A"));
    frame(&mut a, &ctx, vec![], [1280., 720.]);
    frame(
        &mut a,
        &ctx,
        vec![key(Key::Escape, Modifiers::default())],
        [1280., 720.],
    );
    assert!(!a.closing_all);
    assert!(a.pending.is_none());
    assert!(!a.closing);
    // Closing the last clean tab leaves an immediately usable document.
    a.word.session.dirty = false;
    a.request(Action::CloseTab, &ctx);
    assert_eq!(a.tab_order.len(), 1);
    assert_ne!(a.active_id, first);
    assert!(!a.word.session.dirty);
    assert!(a.path.is_none());
}

#[test]
fn document_shortcuts_switch_tabs_and_keep_independent_scroll() {
    let (mut a, ctx) = app();
    a.tools = false;
    a.pages.visible = false;
    a.command(
        "text.insert",
        json!({"text":"Un long cours à faire défiler.\n".repeat(130)}),
    );
    a.word.session.sel = Selection::caret(core::writing_position(&a.word.session.doc));
    a.word.canvas.scroll_to_caret = true;
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], [1280., 720.]);
    }
    let first = a.active_id;
    let origin = a.word.canvas.page_rects[0].min.y;
    let center = a.word.canvas.canvas_rect.unwrap().center();
    frame(
        &mut a,
        &ctx,
        vec![
            egui::Event::PointerMoved(center),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                phase: egui::TouchPhase::Move,
                delta: egui::vec2(0., -600.),
                modifiers: Modifiers::default(),
            },
        ],
        [1280., 720.],
    );
    for _ in 0..6 {
        frame(&mut a, &ctx, vec![], [1280., 720.]);
    }
    let scrolled = a.word.canvas.page_rects[0].min.y;
    assert!(
        scrolled < origin - 100.,
        "scroll was not exercised: {origin}->{scrolled}"
    );
    a.new_tab(blank_school()).unwrap();
    let second = a.active_id;
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], [1280., 720.]);
    }
    let ctrl = Modifiers {
        ctrl: true,
        command: true,
        ..Default::default()
    };
    frame(&mut a, &ctx, vec![key(Key::Tab, ctrl)], [1280., 720.]);
    assert_eq!(a.active_id, first);
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], [1280., 720.]);
    }
    assert!(
        (a.word.canvas.page_rects[0].min.y - scrolled).abs() < 2.,
        "scroll changed on return to the first tab"
    );
    frame(
        &mut a,
        &ctx,
        vec![key(
            Key::Tab,
            Modifiers {
                shift: true,
                ..ctrl
            },
        )],
        [1280., 720.],
    );
    assert_eq!(a.active_id, second);
    frame(&mut a, &ctx, vec![key(Key::W, ctrl)], [1280., 720.]);
    assert_eq!(a.active_id, first);
    assert_eq!(a.tab_order.len(), 1);
}

#[test]
fn chapter_dropdown_opens_on_the_page_and_checkbox_label_is_clickable() {
    let (mut a, ctx) = app();
    a.tools = false;
    a.pages.visible = false;
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], [1280., 720.]);
    }
    let screen_range = |a: &mut App, tag: &str| {
        let range = a
            .word
            .session
            .doc
            .control_ranges(wordcraft_doc::StoryRef::Body)
            .into_iter()
            .find(|r| r.control.tag == tag)
            .unwrap();
        let layout = a.word.session.layout();
        let (page, rect) = layout.selection_rects(
            &a.word.session.doc,
            &range.content_start(),
            &range.end,
            a.word.session.page_hint,
        )[0];
        let paper = a.word.canvas.page_rects[page];
        let scale = paper.width() / 595.276;
        (paper, rect, scale)
    };
    let click = |a: &mut App, at: egui::Pos2| {
        frame(
            a,
            &ctx,
            vec![
                egui::Event::PointerMoved(at),
                egui::Event::PointerButton {
                    pos: at,
                    button: egui::PointerButton::Primary,
                    pressed: true,
                    modifiers: Modifiers::default(),
                },
            ],
            [1280., 720.],
        );
        frame(
            a,
            &ctx,
            vec![egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed: false,
                modifiers: Modifiers::default(),
            }],
            [1280., 720.],
        );
    };
    let (paper, rect, scale) = screen_range(&mut a, "ecr.chapter");
    let arrow = egui::pos2(
        paper.min.x + (rect.right() + 9.) * scale,
        paper.min.y + (rect.y + rect.h * 0.5) * scale,
    );
    click(&mut a, arrow);
    // The real list is a foreground egui area. Choosing a value updates its native control.
    assert!(
        ctx.memory(|m| m.area_rect(egui::Id::new("content_control_popup")))
            .is_some(),
        "the chapter list did not open"
    );
    a.command(
        "developer.chooseItem",
        json!({"control":"ecr.chapter","value":"9"}),
    );
    assert_eq!(School::read(&a.word.session.doc).chapter, 9);
    frame(
        &mut a,
        &ctx,
        vec![key(Key::Escape, Modifiers::default())],
        [1280., 720.],
    );
    let (paper, rect, scale) = screen_range(&mut a, "ecr.assessment");
    let label = egui::pos2(
        paper.min.x + (rect.x + 38.) * scale,
        paper.min.y + (rect.y + rect.h * 0.5) * scale,
    );
    assert!(!School::read(&a.word.session.doc).assessment);
    click(&mut a, label);
    assert!(
        School::read(&a.word.session.doc).assessment,
        "clicking the choice label must toggle the native checkbox"
    );
}

#[test]
fn opening_claims_its_path_before_delivery_and_prevents_a_second_writer() {
    let (mut a, ctx) = app();
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("À ouvrir.ecr");
    let incoming = core::new_document(&School {
        title: "À conserver".into(),
        ..Default::default()
    })
    .unwrap();
    storage::save(&path, &incoming).unwrap();
    a.request(Action::Open(path.clone()), &ctx);
    let opening = a.active_id;
    assert_eq!(a.file_job.as_ref(), Some(&path));
    assert!(a.path.is_none());
    a.new_tab(blank_school()).unwrap();
    let other = a.active_id;
    assert!(a.already_open(&path));
    assert_eq!(a.active_id, opening);
    assert_eq!(a.tab_order.len(), 3);
    a.activate_tab(other);
    a.command("text.insert", json!({"text":"Autre document"}));
    a.write(path.clone(), false, &ctx);
    assert!(!a.busy);
    assert!(a.status.contains("autre onglet"));
    finish_workers(&mut a, &ctx);
    assert_eq!(storage::read(&path).unwrap(), incoming);
    a.activate_tab(opening);
    assert!(a.file_job.is_none());
    assert_eq!(a.path.as_ref(), Some(&path));
}
#[test]
fn selected_card_has_a_visible_delete_button_with_one_step_undo() {
    let (mut a, ctx) = app();
    let size = [1280., 720.];
    ecrinator::blocks::insert(&mut a.word.session, "Propriété").unwrap();
    a.command(
        "text.insert",
        json!({"text":"Une propriété à conserver après annulation."}),
    );
    let before = a.word.session.doc.clone();
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], size);
    }
    let rect = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("selected-box-trash-rect")))
        .expect("Visible trash beside the selected card");
    assert!(rect.top() > 120. && rect.bottom() < 690.);
    click_at(&mut a, &ctx, rect.center(), size);
    assert!(
        !a.word
            .session
            .doc
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("Une propriété à conserver")
    );
    a.command("edit.undo", json!({}));
    assert_eq!(a.word.session.doc, before);
}
#[test]
fn odt_open_and_save_keep_the_same_path_and_native_timeline() {
    let (mut a, ctx) = app();
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("Mon cours.odt");
    ecrinator::timeline::apply(&mut a.word.session, &Default::default()).unwrap();
    let initial = a.word.session.doc.clone();
    storage::atomic_write(&path, &ecrinator::odt_project::encode(&initial).unwrap()).unwrap();
    a.request(Action::Open(path.clone()), &ctx);
    finish_workers(&mut a, &ctx);
    assert_eq!(a.path.as_ref(), Some(&path));
    assert_eq!(a.word.session.doc, initial);
    a.command(
        "text.insert",
        json!({"text":"Du texte ajouté sous le bandeau."}),
    );
    a.save(false, &ctx);
    finish_workers(&mut a, &ctx);
    assert!(!a.word.session.dirty);
    assert_eq!(storage::read(&path).unwrap(), a.word.session.doc);
    assert_eq!(
        std::fs::read_dir(dir.path()).unwrap().count(),
        1,
        "A single standard ODT is the saved document"
    );
}
#[test]
fn library_fits_small_windows_and_inserts_the_chosen_image_and_credit() {
    let (mut a, ctx) = app();
    let size = [800., 580.];
    a.dialog = Some(dialogs::Dialog::Library {
        category: "SVT".into(),
        query: String::new(),
        selected: Some("college-fiche-cellule-animale".into()),
        topic: String::new(),
        page: 0,
    });
    for _ in 0..5 {
        frame(&mut a, &ctx, vec![], size);
    }
    let content = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("library-content-rect")))
        .unwrap();
    let insert = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("library-insert-rect")))
        .unwrap();
    assert!(
        ctx.content_rect().contains_rect(content),
        "Library overflow: {content:?}"
    );
    assert!(ctx.content_rect().contains_rect(insert));
    let before = a.word.session.doc.clone();
    click_at(&mut a, &ctx, insert.center(), size);
    assert!(a.dialog.is_none());
    assert!(!text(&a).contains("Écrinator"));
    assert!(
        ecrinator::image_credits::selected(&a.word.session)
            .unwrap()
            .author
            .contains("Écrinator")
    );
    for _ in 0..3 {
        frame(&mut a, &ctx, vec![], size);
    }
    let layout = a.word.session.layout();
    let (pos, _) = wordcraft_engine::cmd::objects::selected(&a.word.session).unwrap();
    let object = layout
        .object(&pos, a.word.session.page_hint)
        .expect("Library image must have an on-page rectangle");
    let (page, rect) = (object.page, object.rect);
    let at = a.word.canvas.page_rects[page].min
        + egui::vec2(rect.x + rect.w / 2., rect.y + rect.h / 2.) * a.word.canvas.scale;
    for pressed in [true, false] {
        frame(
            &mut a,
            &ctx,
            vec![
                egui::Event::PointerMoved(at),
                egui::Event::PointerButton {
                    pos: at,
                    button: egui::PointerButton::Secondary,
                    pressed,
                    modifiers: Default::default(),
                },
            ],
            size,
        );
    }
    frame(&mut a, &ctx, vec![], size);
    assert!(a.word.canvas.context_menu_open);
    let menu = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("image-credit-menu-rect")))
        .expect("Right-click must offer image provenance");
    assert!(ctx.content_rect().contains_rect(menu));
    frame(
        &mut a,
        &ctx,
        vec![key(Key::Escape, Modifiers::default())],
        size,
    );
    a.command("edit.undo", json!({}));
    assert_eq!(a.word.session.doc, before);
}
#[test]
fn imported_documents_are_recovered_without_automatic_reclassification_or_overwrite() {
    let (mut a, ctx) = app();
    let dir = tempfile::tempdir().unwrap();
    let original = dir.path().join("Document externe.odt");
    a.word.session.set_document(wordcraft_doc::Document::new());
    a.command(
        "text.insert",
        json!({"text":"Un cours externe sans matière confirmée."}),
    );
    let raw = ecrinator::exporters::bytes("cours.odt", &a.word.session.doc).unwrap();
    storage::atomic_write(&original, &raw).unwrap();
    a.path = Some(original.clone());
    a.stamp = storage::stamp(&original);
    a.prefs.organize = true;
    assert!(!School::present(&a.word.session.doc));
    assert_eq!(School::read(&a.word.session.doc).subject, core::BLANK);
    a.command("text.insert", json!({"text":" Modification en cours."}));
    a.last_backup = Instant::now() - Duration::from_secs(11);
    a.autosave(&ctx);
    finish_workers(&mut a, &ctx);
    assert_eq!(
        std::fs::read(&original).unwrap(),
        raw,
        "An unclassified import must not be automatically overwritten"
    );
    assert!(a.word.session.dirty);
    assert!(a.dialog.is_none());
    assert!(
        storage::read(&a.recovery)
            .unwrap()
            .plain_text(wordcraft_doc::StoryRef::Body)
            .contains("Modification en cours")
    );
}

#[test]
fn missing_organizer_pauses_once_and_keeps_local_recovery_without_popups() {
    let (mut a, ctx) = app();
    let dir = tempfile::tempdir().unwrap();
    a.prefs.space = Some(dir.path().join("Dossier déplacé"));
    a.prefs.organize = true;
    a.command(
        "text.insert",
        json!({"text":"Mon travail doit rester protégé."}),
    );
    a.last_backup = Instant::now() - Duration::from_secs(11);
    a.autosave(&ctx);
    finish_workers(&mut a, &ctx);
    assert!(
        !a.prefs.organize,
        "Missing root must pause automatic routing"
    );
    assert!(
        a.dialog.is_none(),
        "An automatic backup must not interrupt typing"
    );
    assert!(!a.status.contains("Rangement impossible"));
    assert!(a.recovery.is_file());
    assert_eq!(storage::read(&a.recovery).unwrap(), a.word.session.doc);
    let prefs: Preferences = serde_json::from_slice(
        &std::fs::read(storage::data_dir().join("preferences.json")).unwrap(),
    )
    .unwrap();
    assert!(!prefs.organize, "The pause must survive the next launch");
    a.command(
        "text.insert",
        json!({"text":" Je peux continuer à écrire."}),
    );
    a.last_backup = Instant::now() - Duration::from_secs(11);
    a.autosave(&ctx);
    finish_workers(&mut a, &ctx);
    assert!(a.dialog.is_none());
    assert_eq!(storage::read(&a.recovery).unwrap(), a.word.session.doc);
    a.prefs.organize = true;
    a.save(false, &ctx);
    assert!(
        matches!(a.dialog, Some(dialogs::Dialog::Organizer { .. })),
        "Explicit Save offers to repair or create the space"
    );
}

#[test]
fn choosing_existing_organizer_enables_routing_and_saves_immediately() {
    let (mut a, ctx) = app();
    let dir = tempfile::tempdir().unwrap();
    let made = ecrinator::organizer_space::create(dir.path(), "Espace collège", false).unwrap();
    a.prefs.organize = false;
    a.command(
        "text.insert",
        json!({"text":"Un cours à classer sans activation cachée."}),
    );
    a.tx.send(Event::Picked(
        Pick::Space,
        Some(made.root.join("Français/Cours")),
    ))
    .unwrap();
    a.poll(&ctx);
    finish_workers(&mut a, &ctx);
    assert!(a.prefs.organize);
    assert!(!a.word.session.dirty);
    let path = a.path.as_ref().unwrap();
    assert_eq!(path.parent().unwrap(), made.root.join("Français/Cours"));
    assert_eq!(storage::read(path).unwrap(), a.word.session.doc);
}

#[test]
fn library_image_button_opens_the_integrated_collection() {
    let (mut a, ctx) = app();
    a.subject_action(10, &ctx);
    assert!(matches!(a.dialog, Some(dialogs::Dialog::Library { .. })));
}

#[test]
fn operation_tool_inserts_editable_empty_cells_without_solving() {
    let (mut a, ctx) = app();
    a.school.subject = "Mathématiques".into();
    a.word.session.sel = Selection::caret(core::writing_position(&a.word.session.doc));
    a.subject_action(30, &ctx);
    let Some(dialogs::Dialog::Calculation(c)) = &mut a.dialog else {
        panic!("Operation tool must open");
    };
    c.a = "125,4".into();
    c.b = "37,85".into();
    let size = [1280., 720.];
    for _ in 0..4 {
        frame(&mut a, &ctx, vec![], size);
    }
    let rect = ctx
        .data(|d| d.get_temp::<egui::Rect>(egui::Id::new("ecr-design-apply-rect")))
        .unwrap();
    assert!(ctx.content_rect().contains_rect(rect));
    click_at(&mut a, &ctx, rect.center(), size);
    assert!(a.dialog.is_none());
    let path = ecrinator::arithmetic::selected(&a.word.session).unwrap();
    let table = a
        .word
        .session
        .doc
        .table(a.word.session.sel.focus.story, &path)
        .unwrap();
    for row in &table.rows[3..] {
        for cell in &row.cells {
            assert!(cell.blocks[0].as_para().unwrap().plain_text().is_empty());
        }
    }
    let original_col = a.word.session.sel.focus.path.0[2];
    a.word
        .session
        .run("text.insert", &json!({"text":"1"}))
        .unwrap();
    a.word.session.run("text.tab", &json!({})).unwrap();
    assert_eq!(a.word.session.sel.focus.path.0[2], original_col + 1);
    assert!(!text(&a).contains("163,25"));
}
