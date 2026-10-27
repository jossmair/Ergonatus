# ÉCRINATOR 0.11.1 — Rust / Wordcraft 0.9

Traitement de texte scolaire Windows x64 de la suite Ergonatus. Application locale autonome, sans Python ni LibreOffice requis à l’exécution. Le moteur Wordcraft est figé à la version 0.9.0. Les sources Python historiques restent conservées, les lanceurs démarrent l’application Rust.

Les nouvelles sauvegardes utilisent **ODT**, y compris le classement automatique dans Organisator. Le paquet ODF contient aussi un état natif Écrinator pour retrouver le bandeau et les objets structurés à la réouverture. Si un autre logiciel modifie le fichier, le contenu ODF modifié prend la priorité. Le PDF conserve le rendu et la pagination exacts de l’éditeur.

## Utiliser

- Lancez `runtime/Ecrinator.exe` ou `Lancer Ecrinator Rust.cmd`.
- Portable : extrayez `dist/Ecrinator-0.11.1-portable-windows-x64.zip`. Préférences et brouillons restent dans le dossier `data` voisin.
- Installeur : `dist/Ecrinator-0.11.1-Setup.exe`, installation par compte sans élévation ni téléchargement.
- Le mode d’emploi est dans `LIRE-MOI.txt` ; les changements sont dans `docs/CHANGES-0.11.1.md`.

L’éditeur propose des onglets indépendants, des pages A4, 13 fonds de matière, un bandeau compact, des types de travail exclusifs, les encadrés pédagogiques, tableaux, images, formules, frises, graphiques et OCR local Windows. Les polices d’écriture proposées sont Arial, OpenDyslexic et Cursive (Borel). Noto Serif dessine les noms des matières. Leurs licences libres accompagnent les ressources redistribuées.

La bibliothèque de cette version est un **lot pilote de 198 ressources intégrées**, après retrait des atlas administratifs et pictogrammes génériques rejetés. Il comprend 23 figures Sésamath de 6e contrôlées visuellement, avec leur source et chapitre. Les filtres niveau et usage utilisent uniquement des métadonnées renseignées. Le grand pack de référence de plusieurs milliers d’images reste en préparation ; il n’est pas annoncé comme livré. Les sources de ce lot sont du domaine public, CC BY ou CC BY-SA.

En mathématiques, **Opération posée** insère une grille réellement éditable pour +, −, × et la division en potence. Les nombres sont facultatifs ; les décimaux gardent leur virgule et s’alignent. L’élève remplit lui-même retenues, étapes et résultat dans les cases. **Aucun calcul, résultat, retenue ou étape n’est généré automatiquement.** Tab passe à la case suivante. L’ODT standard garde de vraies cellules éditables.

Le bandeau est protégé sur la page, avec seuls Chapitre et le type de travail manipulables. Changer de type déplace automatiquement l’ODT dans Organisator après vérification des deux fichiers.

## Ressources

- 91 icônes SVG originales dans `assets/school-icons/`.
- 13 décors ImageGen distincts dans `assets/subject-backgrounds/`, avec les consignes exactes et les PNG sources.
- Archives séparées dans `dist/` : icônes/illustrations, fonds de matières et bibliothèque scolaire avec ses attributions.

## Construire et vérifier

```powershell
./scripts/build.ps1
./scripts/verify.ps1 -Output test-output/acceptance-v09-release -Independent
./scripts/package.ps1
python scripts/verify_distribution.py 0.11.1
```

Le projet utilise le Rust local de PDFinator s’il est présent et le cache Cargo verrouillé hors ligne. Les tests doivent recevoir `ECRINATOR_DATA_DIR` pointant vers un dossier isolé sous `test-output/`, ainsi que TEMP/TMP sous `test-output/tmp`. Les scripts de construction et de vérification le prévoient. La compilation optimisée peut prendre plusieurs minutes.

Le contrôle indépendant utilise pypdf/PDFium. `scripts/test_libreoffice.py` convertit uniquement les documents synthétiques du dossier passé en argument, avec un profil LibreOffice séparé. `scripts/render_lo.py` inspecte ses PDF. Ces outils de développement ne sont pas embarqués dans l’application.

## Limites et suivi

Les angles des encadrés deviennent droits dans Writer ; les frises, graphiques et figures y sont des images haute résolution. Les formules conservent MathML. Le bandeau ODT s’adapte aux marges imprimables. Une édition externe peut perdre les propriétés spécifiques que le lecteur Wordcraft ne sait pas réimporter. La pagination peut varier selon le logiciel et ses polices.

`docs/VALIDATION.md` consigne les contrôles réellement exécutés. `PLAN.md`, `ARCHITECTURE.md`, `DECISIONS.md` et `vendor/wordcraft/ECRINATOR-PATCHES.md` permettent la reprise. La mission initiale n’est pas déclarée intégralement achevée : Windows vierge, impression physique, NVDA, DPI réels et poste scolaire restent à valider.


Si un dossier Organisator associé devient introuvable, le classement est mis en pause et la récupération locale continue. **Classer** permet de choisir un espace existant, d’en créer un sur le Bureau ou d’enregistrer ailleurs. Le choix d’un espace valide active le rangement et enregistre immédiatement le document.
