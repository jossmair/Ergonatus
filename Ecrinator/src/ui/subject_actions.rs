use super::*;
use ecrinator::blocks;
impl App {
    pub(super) fn subject_action(&mut self, action: u8, ctx: &egui::Context) {
        match action {
            0..=2 => {
                self.dialog = Some(dialogs::Dialog::Formula {
                    kind: action as usize,
                    a: "3".into(),
                    b: "4".into(),
                })
            }
            30 => self.dialog = Some(dialogs::Dialog::Calculation(Default::default())),
            31 | 32 => {
                use ecrinator::math_tables::{self, Model};
                let selected = math_tables::selected(&self.word.session).map(|(_, model)| model);
                let model = match (action, selected) {
                    (31, Some(model @ Model::Proportion(_)))
                    | (32, Some(model @ Model::Conversion(_))) => model,
                    (31, _) => Model::Proportion(Default::default()),
                    _ => Model::Conversion(Default::default()),
                };
                self.dialog = Some(dialogs::Dialog::MathTable(model));
            }
            3 => self.dialog = Some(dialogs::Dialog::Symbols),
            19 => self.dialog = Some(dialogs::Dialog::Units(Default::default())),
            4 => self.command("text.insert", json!({"text":"∠"})),
            5 => self.dialog = Some(dialogs::Dialog::Shapes),
            6 => self.dialog = Some(dialogs::Dialog::Table { rows: 3, cols: 3 }),
            7 => {
                self.dialog = Some(dialogs::Dialog::Chart {
                    labels: "A;B;C".into(),
                    values: "1;2;3".into(),
                })
            }
            8 => {
                self.dialog = Some(dialogs::Dialog::Formula {
                    kind: 0,
                    a: "a".into(),
                    b: "b".into(),
                })
            }
            9 => {
                self.dialog = Some(dialogs::Dialog::Timeline(
                    ecrinator::timeline::selected(&self.word.session)
                        .map(|(_, t)| t)
                        .unwrap_or_default(),
                ))
            }
            10 => self.subject_action(29, ctx),
            29 => {
                self.dialog = Some(dialogs::Dialog::Library {
                    category: match self.school.subject.as_str() {
                        "Histoire-géographie" | "EMC" => "Cartes",
                        "SVT" => "SVT",
                        "Physique-chimie" => "Physique-chimie",
                        "Anglais" | "Espagnol" | "Allemand" => "Langues",
                        v if core::SUBJECTS.contains(&v) && v != core::BLANK => v,
                        _ => "",
                    }
                    .into(),
                    query: String::new(),
                    selected: None,
                    topic: String::new(),
                    page: 0,
                });
            }
            11 => self.command("text.insert", json!({"text":"Légende : "})),
            12 | 13 | 14 | 15 | 16 | 17 | 18 | 23 => {
                let title = match action {
                    12 => "Document source",
                    13 => "Définition",
                    14 => "Observation",
                    15 => "Hypothèse",
                    16 => "Résultat",
                    17 => "Conclusion",
                    18 => "Exercice",
                    _ => "Vocabulaire",
                };
                let r = blocks::insert(&mut self.word.session, title);
                self.message(r, "Encadré ajouté");
            }
            20 => {
                self.dialog = Some(dialogs::Dialog::Page {
                    margin: 18.,
                    line: 1.25,
                    spacing: 0.,
                })
            }
            21 => self.dialog = Some(dialogs::Dialog::Colors),
            22 => {
                let r = blocks::insert(&mut self.word.session, "Activité d’écoute");
                self.message(r, "Activité d’écoute ajoutée");
            }
            24 => self.command("para.bullets", json!({})),
            25 => {
                let r = blocks::insert(&mut self.word.session, "Note");
                self.message(r, "Note ajoutée");
            }
            26 => self.command("para.style", json!({"style":"Heading1"})),
            27 => {
                let r = core::clear_formatting(&mut self.word.session);
                self.message(r, "Texte normal · mise en forme retirée");
            }
            _ => self.command("para.style", json!({"style":"Quote"})),
        }
    }
}
