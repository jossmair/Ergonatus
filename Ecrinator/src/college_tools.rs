//! Short, editable school scaffolds. Prompts help the pupil; no generated answers.
use std::sync::Arc;
use wordcraft_doc::{Block, Pos, Table, para_block, props::Rgb};
use wordcraft_engine::{Selection, Session};
pub struct Tool {
    pub id: &'static str,
    pub subjects: &'static [&'static str],
    pub title: &'static str,
    pub icon: &'static str,
    pub help: &'static str,
    pub fields: &'static [(&'static str, &'static str)],
    pub columns: &'static [&'static str],
}
macro_rules! tool{($id:literal,[$($s:literal),*],$title:literal,$icon:literal,$help:literal,[$(($label:literal,$hint:literal)),*],[$($col:literal),*])=>{Tool{id:$id,subjects:&[$($s),*],title:$title,icon:$icon,help:$help,fields:&[$(($label,$hint)),*],columns:&[$($col),*]}};}
pub const TOOLS: &[Tool] = &[
    tool!(
        "recit",
        ["Français"],
        "Préparer un récit",
        "chapter",
        "Organise tes idées avant de rédiger.",
        [
            ("Personnages", "Qui ?"),
            ("Lieu et époque", "Où et quand ?"),
            ("Problème", "Que se passe-t-il ?"),
            ("Actions et fin", "Comment l’histoire se termine-t-elle ?")
        ],
        []
    ),
    tool!(
        "lecture",
        ["Français"],
        "Comprendre un texte",
        "book",
        "Repère les informations et justifie avec le texte.",
        [
            ("De quoi parle le texte ?", "Une ou deux phrases."),
            ("Ce que je comprends", "Mes idées et mes indices."),
            (
                "Une citation utile",
                "Je recopie un passage et je l’explique."
            )
        ],
        []
    ),
    tool!(
        "conjugaison",
        ["Français"],
        "Tableau de conjugaison",
        "table",
        "Complète avec le verbe et le temps étudiés.",
        [("Verbe et temps", "")],
        ["Personne", "Forme du verbe"]
    ),
    tool!(
        "probleme",
        ["Mathématiques"],
        "Résoudre un problème",
        "method",
        "Avance étape par étape, puis vérifie.",
        [
            ("Je cherche", "La question, avec l’unité attendue."),
            ("Je connais", "Les données utiles."),
            ("Je calcule", "Mon raisonnement et mes calculs."),
            ("Je réponds et je vérifie", "Une phrase avec l’unité.")
        ],
        []
    ),
    tool!(
        "proportion",
        ["Mathématiques"],
        "Proportionnalité",
        "table",
        "Un tableau prêt à compléter ; indique les grandeurs et leurs unités.",
        [],
        ["Grandeur / unité", "Valeur 1", "Valeur 2", "Valeur 3"]
    ),
    tool!(
        "geometrie",
        ["Mathématiques"],
        "Justifier en géométrie",
        "figure",
        "Distingue ce que tu sais, la propriété et la conclusion.",
        [
            ("Données et figure", "Ce que je sais."),
            ("Propriété utilisée", "La règle qui permet de conclure."),
            ("Conclusion", "Ce que j’ai démontré.")
        ],
        []
    ),
    tool!(
        "document",
        ["Histoire-géographie", "Français", "EMC"],
        "Présenter un document",
        "source",
        "Une aide pour identifier, comprendre et expliquer un document.",
        [
            (
                "Nature, auteur et date",
                "Qui a produit ce document ? Quand ?"
            ),
            ("Sujet et contexte", "De quoi parle-t-il ?"),
            ("Informations importantes", "Les éléments que je relève."),
            ("Ce qu’il nous apprend", "Mon explication.")
        ],
        []
    ),
    tool!(
        "croquis",
        ["Histoire-géographie"],
        "Légende d’un croquis",
        "map",
        "Choisis des figurés simples et classe ta légende.",
        [("Titre du croquis", "")],
        ["Figuré", "Ce qu’il représente", "Partie de la légende"]
    ),
    tool!(
        "reperes",
        ["Histoire-géographie"],
        "Mes repères d’histoire",
        "timeline",
        "Retiens une date, un événement et sa signification.",
        [],
        ["Date / période", "Événement", "Pourquoi c’est important"]
    ),
    tool!(
        "argumenter",
        ["EMC", "Français"],
        "Donner un avis argumenté",
        "quote",
        "Une idée, une raison, un exemple ; écoute aussi les autres avis.",
        [
            ("Mon avis", ""),
            ("Mon argument", "Pourquoi ?"),
            ("Mon exemple", "Un fait ou une situation."),
            ("Un autre point de vue", "Je réponds avec respect.")
        ],
        []
    ),
    tool!(
        "regle",
        ["EMC"],
        "Comprendre une règle",
        "definition",
        "Relie une règle à une situation concrète.",
        [
            ("La règle ou le droit", ""),
            ("À quoi sert-il ?", ""),
            ("Une situation concrète", ""),
            ("Comment agir ?", "")
        ],
        []
    ),
    tool!(
        "lexique",
        ["Anglais", "Espagnol", "Allemand"],
        "Mon lexique bilingue",
        "vocabulary",
        "Ajoute un mot, sa traduction et un exemple personnel.",
        [],
        ["Mot / expression", "Traduction", "Mon exemple"]
    ),
    tool!(
        "dialogue",
        ["Anglais", "Espagnol", "Allemand", "Français"],
        "Préparer un dialogue",
        "quote",
        "Définis la situation, puis répartis les répliques.",
        [("Situation et personnages", "")],
        ["Qui parle ?", "Réplique", "Intention / prononciation"]
    ),
    tool!(
        "comprehension",
        ["Anglais", "Espagnol", "Allemand"],
        "Comprendre un document",
        "headphones",
        "Repère l’essentiel avant les détails.",
        [
            ("Qui ? Où ? Quand ?", ""),
            ("Le sujet principal", ""),
            ("Les mots ou indices utiles", ""),
            ("Ce que je peux résumer", "")
        ],
        []
    ),
    tool!(
        "demarche",
        ["SVT", "Physique-chimie"],
        "Démarche scientifique",
        "hypothesis",
        "Une question, une hypothèse, une vérification, une conclusion.",
        [
            ("Question", ""),
            ("Hypothèse", "Ce que je pense et ce que je prévois."),
            ("Expérience / observations", "Comment vérifier ?"),
            ("Résultats", ""),
            (
                "Conclusion",
                "Mon hypothèse est-elle confirmée par les résultats ?"
            )
        ],
        []
    ),
    tool!(
        "observer",
        ["SVT"],
        "Faire un dessin d’observation",
        "diagram",
        "Prépare ton dessin sans confondre observation et interprétation.",
        [
            (
                "Titre de l’observation",
                "Objet observé, outil utilisé, grossissement si connu."
            ),
            ("Mon dessin", "Insère un schéma à légender ou dessine-le."),
            (
                "Légende",
                "Traits droits, noms lisibles, sans croiser les traits."
            ),
            ("Ce que j’observe", "Je décris les faits.")
        ],
        []
    ),
    tool!(
        "comparer",
        ["SVT", "Arts plastiques", "Éducation musicale"],
        "Comparer deux éléments",
        "table",
        "Choisis des critères et relève les ressemblances et différences.",
        [],
        ["Critère", "Élément A", "Élément B"]
    ),
    tool!(
        "protocole",
        ["Physique-chimie", "SVT"],
        "Préparer une expérience",
        "hypothesis",
        "Prévois le matériel, les étapes et les règles de sécurité indiquées par ton professeur.",
        [
            ("But de l’expérience", ""),
            ("Matériel", ""),
            ("Précautions", ""),
            ("Étapes numérotées", ""),
            ("Ce que je mesure ou observe", "")
        ],
        []
    ),
    tool!(
        "mesures",
        ["Physique-chimie", "Technologie"],
        "Tableau de mesures",
        "results",
        "Écris les unités dans les en-têtes avant de relever les mesures.",
        [],
        [
            "Essai / temps",
            "Grandeur 1 (unité)",
            "Grandeur 2 (unité)",
            "Observation"
        ]
    ),
    tool!(
        "charges",
        ["Technologie"],
        "Cahier des charges",
        "method",
        "Décris le besoin avant de choisir une solution.",
        [
            ("À qui l’objet rend-il service ?", ""),
            ("Sur quoi agit-il ?", ""),
            ("Dans quel but ?", "")
        ],
        ["Contrainte", "Critère", "Valeur attendue"]
    ),
    tool!(
        "fonctions",
        ["Technologie"],
        "Fonctions et solutions",
        "property",
        "Distingue le besoin, la fonction technique et la solution.",
        [],
        ["Fonction technique", "Solution choisie", "Pourquoi ?"]
    ),
    tool!(
        "algorithme",
        ["Technologie", "Mathématiques"],
        "Décrire un algorithme",
        "method",
        "Explique les étapes avec des phrases courtes.",
        [
            ("Données de départ", ""),
            ("Étapes / conditions", "Si… alors… sinon… Répéter…"),
            ("Résultat attendu", ""),
            ("Je teste avec un exemple", "")
        ],
        []
    ),
    tool!(
        "oeuvre",
        ["Arts plastiques"],
        "Observer une œuvre",
        "observation",
        "Décris d’abord ce que tu vois, puis explique tes choix.",
        [
            ("Titre, auteur, date, technique", ""),
            ("Ce que je vois", "Formes, couleurs, composition, matière."),
            (
                "Ce que cela produit",
                "Effets et impressions, avec des indices."
            ),
            ("Mon interprétation", "")
        ],
        []
    ),
    tool!(
        "projet",
        ["Arts plastiques"],
        "Préparer une création",
        "palette",
        "Organise ton projet sans chercher une réponse unique.",
        [
            ("Consigne et intention", ""),
            ("Croquis / recherches", ""),
            ("Matériaux et étapes", ""),
            ("Ce que je garde ou j’améliore", "")
        ],
        []
    ),
    tool!(
        "ecoute",
        ["Éducation musicale"],
        "Fiche d’écoute",
        "headphones",
        "Écoute plusieurs fois et justifie avec ce que tu entends.",
        [
            ("Œuvre, auteur, interprète", ""),
            ("Voix et instruments", ""),
            ("Tempo, nuances, caractère", ""),
            ("Structure et changements", ""),
            ("Mon ressenti et ses indices", "")
        ],
        []
    ),
    tool!(
        "rythme",
        ["Éducation musicale"],
        "Préparer un rythme",
        "music",
        "Insère une portée ou une grille vierge depuis la bibliothèque.",
        [
            ("Mesure et pulsation", ""),
            ("Mon rythme", ""),
            (
                "Comment le réaliser ?",
                "Frapper, parler ou jouer avec les consignes du professeur."
            )
        ],
        []
    ),
    tool!(
        "notes",
        ["Autre matière", "Page blanche"],
        "Organiser mes notes",
        "chapter",
        "Une structure courte pour retrouver l’essentiel.",
        [
            ("Idée principale", ""),
            ("Informations utiles", ""),
            ("Exemple", ""),
            ("À retenir", "")
        ],
        []
    ),
];
pub fn for_subject(subject: &str) -> impl Iterator<Item = &'static Tool> + '_ {
    TOOLS.iter().filter(move |t| t.subjects.contains(&subject))
}
pub fn get(id: &str) -> Option<&'static Tool> {
    TOOLS.iter().find(|t| t.id == id)
}
pub fn insert(s: &mut Session, id: &str) -> Result<(), String> {
    crate::core::ensure_writing_selection(s)?;
    let tool = get(id).ok_or("Modèle inconnu")?;
    let snapshot = s.edit_snapshot();
    s.checkpoint("Insérer une fiche d’aide");
    let result = (|| {
        let focus = s.sel.focus.clone();
        let at = if focus.path.0.len() == 1 {
            s.doc.split_paragraph(&focus).map_err(|e| e.to_string())?
        } else {
            let i = focus.path.0.first().copied().ok_or("Position absente")? as usize + 1;
            if i >= s.doc.body.len() {
                s.doc.body.push(para_block(wordcraft_doc::Paragraph::new()));
            }
            Pos::body(i, 0)
        };
        let mut blocks = vec![para_block(crate::core::text(
            tool.title,
            15.,
            true,
            Rgb(25, 57, 97),
        ))];
        for (label, hint) in tool.fields {
            blocks.push(para_block(crate::core::text(
                label,
                12.,
                true,
                Rgb(25, 57, 97),
            )));
            let mut p = crate::core::text(hint, 11., false, Rgb(98, 111, 128));
            p.props.space_after = Some(12.);
            blocks.push(para_block(p));
        }
        if !tool.columns.is_empty() {
            let mut t = Table::new(
                if id == "proportion" {
                    2
                } else if id == "conjugaison" {
                    7
                } else {
                    5
                },
                tool.columns.len(),
                460.,
            );
            for (i, title) in tool.columns.iter().enumerate() {
                if let Some(cell) = t.rows.first_mut().and_then(|r| r.cells.get_mut(i)) {
                    cell.blocks = vec![para_block(crate::core::text(
                        title,
                        11.,
                        true,
                        Rgb(25, 57, 97),
                    ))];
                    cell.props.shading = Some(Rgb(237, 243, 250));
                }
            }
            if id == "conjugaison" {
                for (row, label) in t.rows.iter_mut().skip(1).zip([
                    "Je",
                    "Tu",
                    "Il / elle / on",
                    "Nous",
                    "Vous",
                    "Ils / elles",
                ]) {
                    row.cells[0].blocks = vec![para_block(crate::core::text(
                        label,
                        11.,
                        false,
                        Rgb(25, 57, 97),
                    ))];
                }
            }
            blocks.push(Arc::new(Block::Table(t)));
        }
        let index = at.path.last();
        let count = blocks.len();
        let container = s
            .doc
            .container_mut(at.story, &at.path)
            .map_err(|e| e.to_string())?;
        container.splice(index..index, blocks);
        s.sel = Selection::caret(Pos {
            path: at.path.with_last(index + count),
            off: 0,
            ..at
        });
        s.touch();
        s.relayout();
        Ok(())
    })();
    if result.is_err() {
        s.restore(snapshot);
    }
    result
}
pub struct Units {
    pub family: usize,
    pub value: String,
    pub from: usize,
    pub to: usize,
}
impl Default for Units {
    fn default() -> Self {
        Self {
            family: 0,
            value: "10".into(),
            from: 2,
            to: 0,
        }
    }
}
pub const FAMILIES: &[&str] = &["Longueur", "Masse", "Durée", "Capacité", "Aire", "Volume"];
pub fn units(family: usize) -> &'static [(&'static str, f64)] {
    match family {
        0 => &[("m", 1.), ("km", 1000.), ("cm", 0.01), ("mm", 0.001)],
        1 => &[("kg", 1.), ("g", 0.001), ("mg", 0.000001), ("t", 1000.)],
        2 => &[("s", 1.), ("min", 60.), ("h", 3600.)],
        3 => &[("L", 1.), ("mL", 0.001), ("cL", 0.01)],
        4 => &[("m²", 1.), ("cm²", 0.0001), ("mm²", 0.000001)],
        _ => &[("m³", 1.), ("dm³", 0.001), ("cm³", 0.000001)],
    }
}
impl Units {
    pub fn result(&self) -> Result<String, String> {
        let value = self
            .value
            .trim()
            .replace(',', ".")
            .parse::<f64>()
            .map_err(|_| "Écris un nombre, par exemple 2,5.")?;
        if !value.is_finite() || value.abs() > 1e12 {
            return Err("Ce nombre est trop grand.".into());
        }
        let all = units(self.family);
        let from = all.get(self.from).ok_or("Choisis l’unité de départ")?;
        let to = all.get(self.to).ok_or("Choisis l’unité d’arrivée")?;
        let answer = value * from.1 / to.1;
        let answer_text = if answer != 0. && answer.abs() < 1e-8 {
            answer.to_string()
        } else {
            format!("{answer:.9}")
                .trim_end_matches('0')
                .trim_end_matches('.')
                .to_owned()
        }
        .replace('.', ",");
        Ok(format!(
            "{} {} = {} {}",
            self.value.trim(),
            from.0,
            answer_text,
            to.0
        ))
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn every_subject_has_actionable_helpers() {
        for subject in crate::core::SUBJECTS {
            assert!(for_subject(subject).next().is_some(), "{subject}");
        }
    }
    #[test]
    fn conversions_handle_french_decimals_and_squared_units() {
        let mut u = Units::default();
        u.value = "2,5".into();
        assert_eq!(u.result().unwrap(), "2,5 cm = 0,025 m");
        u.family = 4;
        u.value = "10000".into();
        u.from = 1;
        u.to = 0;
        assert_eq!(u.result().unwrap(), "10000 cm² = 1 m²");
        u.value = "NaN".into();
        assert!(u.result().is_err());
    }
    #[test]
    fn helpers_preserve_text_undo_and_odt() {
        let mut s = Session::new(crate::core::new_document(&Default::default()).unwrap());
        s.sel = Selection::caret(crate::core::writing_position(&s.doc));
        s.run("text.insert", &serde_json::json!({"text":"Mon cours"}))
            .unwrap();
        let before = s.doc.clone();
        insert(&mut s, "demarche").unwrap();
        assert!(
            s.doc
                .plain_text(wordcraft_doc::StoryRef::Body)
                .contains("Mon cours")
        );
        let bytes = crate::odt_project::encode(&s.doc).unwrap();
        assert_eq!(crate::odt_project::open("test.odt", &bytes).unwrap(), s.doc);
        s.undo();
        assert_eq!(s.doc, before);
    }
}
