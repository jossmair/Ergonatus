# PDFinator — Ergonatus

Application Windows x64 de lecture et de modification de PDF, gratuite et hors ligne.
Elle fonctionne indépendamment du hub, sans Python, compte, publicité, service réseau
ou téléchargement lors de l’utilisation.

## Version 1.0.0

La V1 sécurise la fermeture pendant les opérations en cours et les conflits de
sauvegarde. Les changements et les limites connues sont décrits dans
[docs/RELEASE-1.0.0.md](docs/RELEASE-1.0.0.md).

## Correctifs de l’audit — 0.5.15

La récupération après interruption, les traitements en arrière-plan, l’export annulable, les plages d’impression et le recentrage du panneau sont décrits dans [docs/CORRECTIFS-0.5.15.md](docs/CORRECTIFS-0.5.15.md). L’aide aux commandes s’ouvre avec `?` ou `F1`.


## Lancer

Pour la version portable, extrayez entièrement le ZIP dans le dossier de votre
choix. Double-cliquez sur **PDFinator.exe**, directement à la racine du dossier
extrait, avec son icône PDFinator. Ce fichier est l’application Windows native.
Aucune installation n’est nécessaire ; ne lancez pas le programme directement
à l’intérieur du ZIP.
Le ZIP ne contient que **PDFinator.exe** et **LICENCES.txt**. Gardez ce fichier
légal unique avec l’exécutable lors d’une redistribution.

Pour installer l’application, lancez **PDFinator-1.0.0-Setup.exe**. L’assistant
français installe PDFinator pour votre compte Windows, ajoute un raccourci au
menu Démarrer et propose un raccourci sur le Bureau. La désinstallation est
disponible dans les applications Windows. Aucun téléchargement pendant l’installation.

Un document peut être transmis directement :

```powershell
./PDFinator.exe "C:/Documents/mon document.pdf"
```

## Utiliser

Les onglets occupent une seule ligne en haut. Les commandes, les pages et le zoom
sont à gauche. Les réglages d’un élément apparaissent à droite. Le document
occupe toute la hauteur restante, sans bandeau d’accueil ni barre de statut permanente.
La barre d’outils fixe utilise deux colonnes et ne défile pas, même à la taille
minimale de 760 × 540. Les vignettes des pages conservent leur propre défilement.

* **Lecture** : sélectionner/copier, rechercher, parcourir les pages, afficher les
  miniatures, zoomer, adapter à la largeur ou à la page entière, surligner et commenter.
  Les miniatures sont visibles à l’ouverture ; cliquer sur une vignette rejoint sa page.
  Le glisser-déposer des miniatures change aussi leur ordre en Lecture.
  **Main**, à côté de **Sélectionner**, permet de saisir le document pour déplacer
  la vue dans les deux directions. La main est ouverte sur la feuille et fermée
  pendant le déplacement ; le curseur reste une flèche dans les marges grises.
  Cet outil est aussi disponible dans Modifier.
  Fermer la recherche, appuyer sur **Échap** ou désélectionner retire les repères
  jaunes des résultats. Les véritables annotations de surlignage sont conservées.
* **Pages** : toutes les pages sont accessibles dans une grille centrale défilante.
  Les outils de rotation et de position sont dans la barre gauche.
  Sélectionner une vignette puis tourner à gauche ou à droite ; déplacer une page
  par glisser-déposer, par les flèches ou en indiquant sa nouvelle position.
  Pendant le glissement, la vignette suit la souris et un trait bleu indique
  l’insertion avant ou après une page. Maintenir près du bord fait défiler la grille ;
  **Échap** abandonne le déplacement. Le document change seulement au relâchement.
  Un double-clic ouvre la page en lecture. Rotation et ordre sont enregistrés
  dans le PDF et bénéficient d’Annuler/Rétablir.
  **Ajouter des PDF** dans la barre gauche (**Ctrl+Maj+O**) permet de choisir un
  ou plusieurs fichiers. Toutes leurs pages sont ajoutées à la fin, dans l’ordre
  de sélection. Réordonnez-les ensuite par glisser-déposer. Un seul **Annuler**
  retire l’ajout entier ; les fichiers sources restent intacts.
* **Modifier** : les blocs reconnus sont encadrés. Cliquez dans un texte pour le
  corriger à son emplacement. **Entrée** valide en conservant le curseur dans le
  bloc ; un clic extérieur valide et termine la saisie.
  Le menu **Taille** propose les tailles courantes. **Autre** permet de saisir
  une valeur personnalisée de 4 à 200 points, avec une virgule ou un point décimal.
  Le choix concerne automatiquement les caractères sélectionnés, ou tout le bloc
  sans sélection de caractères ; validez la taille personnalisée avec **Entrée**.
  **Puces** ajoute ou retire les puces sur les paragraphes sélectionnés.
  **Interligne** propose 1, 1,15, 1,5, 2, 2,5 et 3, ainsi qu’une valeur personnalisée
  entre 0,5 et 5. Ces réglages sont conservés à la sauvegarde et à la copie du bloc.
  **Maj+Entrée** ajoute une ligne ; **Échap** annule la saisie.
  Les miniatures de gauche acceptent aussi le glisser-déposer pour changer l’ordre
  des pages, avec aperçu mobile, repère d’insertion et Annuler/Rétablir.
  **Copier le bloc** puis **Coller le bloc** permettent de transférer un paragraphe
  entre les PDF ouverts dans les onglets. Sélectionnez le bloc, copiez-le, ouvrez
  l’onglet de destination, passez dans **Modifier** puis collez. **Ctrl+C/Ctrl+V**
  fonctionnent aussi ; une sélection de caractères garde la copie de texte normale.
  Les polices PDF, couleurs, tailles et styles sont transférés ; le résultat reste
  éditable, déplaçable et annulable. Cette copie de blocs fonctionne dans une même
  instance de PDFinator ; les boutons restent disponibles pendant la saisie.
* Dans **Modifier → Sélectionner** ou **Modifier le texte**, tracez un rectangle autour des éléments à
  réunir, puis glissez le cadre pour les déplacer ensemble. La sélection peut
  commencer dans la marge grise et inclut les textes, images, tracés, fonds colorés,
  courbes, pointes de flèche et annotations entièrement encadrés. Les traits PDF
  très fins restent sélectionnables. **Maj** ajoute à la sélection, **Ctrl+A**
  sélectionne les objets de la page, **Suppr** les supprime et les flèches déplacent
  le groupe. **Échap** désélectionne. Un seul **Annuler** rétablit le déplacement.
  Les formes PDF restent vectorielles après sauvegarde.
  Dans un bloc en cours de saisie, glisser la souris sélectionne ses caractères.
  Ouvrir ou fermer les réglages conserve le zoom et la position de la page,
  y compris lorsque **Ajuster à la largeur** est actif.
  Les changements de couleur ou de police conservent le curseur ; enregistrer
  pendant la saisie permet de continuer à écrire au même endroit.
* Pour déplacer un bloc, glissez **son bord** ou utilisez les flèches. Saisissez
  l’un des **quatre coins** pour changer sa largeur et redistribuer le texte.
  La hauteur du texte enregistré suit le contenu ; un cadre n’ajoute pas de texte.
  L’outil **Déplacer** permet aussi de saisir le contenu d’un bloc. **Sélectionner**
  ferme les réglages ; passer à **Lecture** ou cliquer dans le gris autour de la
  page valide la saisie et désélectionne le bloc. Une saisie refusée reste ouverte.
  Un **clic droit sur un bord ou un coin** affiche Copier, Couper, Coller et
  Supprimer. **Suppr** efface le bloc sélectionné après avoir quitté la saisie
  de caractères en cliquant sur son bord. **Ctrl+X** coupe un bloc de texte.
  La suppression du texte d’origine retire réellement ses opérateurs PDF ;
  **Ctrl+Z** la restaure.
* Dans **Modifier**, **Ajouter du texte** et **Insérer une image** permettent
  d’écrire dans une zone libre ou de placer un PNG/JPEG. Les images peuvent être
  déplacées, redimensionnées, remplacées et supprimées. Leurs proportions sont
  conservées par défaut. La transparence PNG reste dans le PDF.
  Avec **Insérer du texte**, tracez un cadre à la souris pour choisir sa largeur
  et sa hauteur. Son bord et ses coins restent utilisables même vide. Cliquez
  dans le cadre pour écrire ; un simple clic sur la page crée aussi un cadre.
  Un cadre vide reste un brouillon de travail et n’est pas enregistré dans le PDF.
* Dans **Modifier**, activez **Modifier le texte**, puis **double-cliquez sur une
  image** pour reconnaître son texte hors ligne. Les autres outils et Lecture
  ne déclenchent pas cette reconnaissance. Le double-clic crée automatiquement
  un vrai bloc modifiable pour chaque zone reconnue, sans fenêtre de validation.
  Les lettres
  reconnues sont retirées du bitmap ; l’illustration reste dans une image de fond.
  Les polices sont approximatives, des petites lettres peuvent
  être manquées et le fond près des traits peut être imparfait. **Annuler** restaure
  toute l’image en une étape. Le bouton **Modifier le texte de l’image** dans
  les propriétés garde une relecture facultative avant conversion.
  La reconnaissance ajoute une passe de contraste local et d’agrandissement pour
  les textes pâles ou petits. Les petits cercles en exposant sont distingués des
  zéros ordinaires pour conserver les signes de degré sur les schémas.
* Dans **Modifier**, **Dessin** affiche les outils à droite : trait, cercle, carré,
  rectangle et tableau. La palette propose douze couleurs et une couleur personnalisée.
  Le menu d’épaisseur propose onze valeurs de 0,25 à 12 points, avec une saisie
  libre dans **Autre**. **Type de trait** propose continu, tirets, pointillés,
  tirets et points, tirets longs et double (pour les traits), avec aperçu visuel.
  Ces réglages s’appliquent aux futurs dessins ou à la sélection.
  Tracez la forme ou cliquez pour
  utiliser une taille standard. Sélectionnez un trait pour modifier sa longueur,
  déplacer ses extrémités ou changer son épaisseur. **Tout sélectionner** permet
  de déplacer les dessins ensemble ; les flèches du clavier ou les boutons de
  position sont également disponibles. Un tableau créé peut être divisé en traits
  avec **Modifier les traits séparément**. Les traits vectoriels simples d’un PDF
  existant sont aussi sélectionnables individuellement. Les traits présents dans
  une photographie restent des pixels ; l’OCR ne les convertit pas en vecteurs.
  Cliquez directement sur un trait dans **Modifier** pour le sélectionner, le
  déplacer, modifier son épaisseur ou saisir son extrémité. Les bordures fines
  exportées par LibreOffice et les fonds rectangulaires de cellules sont reconnus.
  Cliquez dans une partie vide d’une cellule colorée pour changer sa couleur de
  fond, la déplacer ou la redimensionner. **Sélectionner le tableau**, dans les
  réglages, regroupe ses bordures et ses fonds ; son déplacement entraîne aussi
  les textes contenus. **Suppr** supprime alors l’ensemble ; **Ctrl+Z** le restaure.
* Dans **Modifier**, **Ajouter une page blanche**, juste après Dessin, insère une
  feuille après la page active et l’ouvre. Elle conserve son format visible et son
  orientation, y compris après rotation ou avec une échelle de page particulière.
  L’ajout est enregistré dans le PDF et peut être annulé.
* Dans **Lecture**, **Surligner** : glisser sur des mots crée une annotation PDF.
  Le curseur devient un **I de sélection de texte** sur la page et redevient
  normal dans la marge grise ; les autres contrôles gardent leur curseur habituel.
  Cliquez dessus pour changer sa couleur ou la supprimer.
  **Commentaire** ajoute une note PDF avec un texte modifiable dans le panneau droit.
* **Exporter en DOCX ou ODT** dans **Modifier** : le bouton ouvre le choix entre
  Word (.docx) et OpenDocument (.odt), puis la boîte d’enregistrement. La conversion
  utilise le document actuel, y compris les modifications validées. Elle fonctionne
  hors ligne, en arrière-plan, sans Word, LibreOffice ou service externe installé.
  Le texte est reconstruit en paragraphes ; les grilles reconnues deviennent des
  cellules avec leurs fusions et fonds. Les figures sont intégrées comme images.
  Des tableaux sans bordures organisent les colonnes, sans zones de texte flottantes.
  Les positions et espacements, les bordures et épaisseurs, les soulignements,
  les pointillés, les angles et les fractions mathématiques sont reconstruits.
  Les blocs placés à côté des tableaux restent dans leur colonne sur toute leur
  hauteur. Les fractions conservent leurs numérateurs et dénominateurs modifiables. Les versions des polices
  intégrées au PDF sont conservées dans la copie quand leurs restrictions
  le permettent. Les scans non reconnus restent des images ; utilisez
  Modifier le texte pour reconnaître leurs textes avant l’export.
* **Imprimer** : une boîte de dialogue centrée permet de choisir l’imprimante
  Windows, les exemplaires, la couleur, le recto verso (bord long ou court) et
  l’adaptation à la zone imprimable ou la taille réelle. Les noms longs sont
  tronqués dans le sélecteur et visibles au survol. Le bouton bleu **Imprimer**
  déclenche l’envoi de toutes les pages. Les pages actuelles, avec modifications,
  sont transmises au spooler natif ; aucune application PDF externe n’est lancée.

Le menu **Police** affiche les vrais noms des polices locales incorporables, avec
un champ de recherche. Sélectionnez les caractères pour les formater ; sans
sélection de caractères, les réglages concernent automatiquement tout le bloc. Taille, couleur, gras, italique,
soulignement, barré, exposant, indice, surlignage, alignement, puces et interligne sont disponibles.
Les polices sélectionnées sont incorporées au document lorsque leurs permissions
le permettent ; aucune police Windows n’est distribuée dans l’application.
La liste se charge en arrière-plan, sans bloquer l’ouverture du PDF.

La police source est conservée autant que possible. Si elle ne couvre pas un
caractère ajouté, l’application cherche une face complète puis une police locale
qui le contient ; le nom de la police utilisée apparaît dans les réglages et le
changement est annulable. Une structure non modifiable est refusée sans changement.
L’édition ne peint pas un rectangle blanc dans le fichier et ne rasterise pas le PDF.
Le collage avec conservation des polices d’un bloc d’origine sur une page tournée
reste limité : remettez cette page à l’endroit dans Pages avant de coller. Le texte
ajouté avec les polices standard peut être collé aux quatre rotations. Les blocs
d’image ne sont pas encore pris en charge par cette commande de copie.

Plusieurs PDF peuvent être ouverts dans les onglets de la barre du haut. Chaque
document garde son historique, son zoom et ses modifications. Glissez un onglet
latéralement pour changer sa position ; **Échap** abandonne. Un double-clic sur
la partie libre de la barre sombre agrandit ou restaure la fenêtre. **Enregistrer sous**
se trouve directement sous **Enregistrer** dans la barre latérale.

## Raccourcis

| Action | Raccourci |
|---|---|
| Ouvrir / enregistrer / imprimer / rechercher | Ctrl+O / Ctrl+S / Ctrl+P / Ctrl+F |
| Enregistrer sous | Ctrl+Maj+S |
| Onglet suivant / précédent / fermer | Ctrl+Tab / Ctrl+Maj+Tab / Ctrl+W |
| Gras / italique / souligner pendant la saisie | Ctrl+B / Ctrl+I / Ctrl+U |
| Annuler / rétablir | Ctrl+Z / Ctrl+Y |
| Copier la sélection | Ctrl+C |
| Ouvrir la saisie du bloc sélectionné | F2 |
| Sélectionner le bloc suivant | F6 |
| Valider / nouvelle ligne / annuler la saisie | Entrée / Maj+Entrée / Échap |
| Déplacer le bloc sélectionné | Flèches ; Maj pour un pas de 10 points |
| Supprimer une image ajoutée ou un surlignage | Suppr |
| Défiler / zoomer dans le document | Molette ou deux doigts / Ctrl+molette ou pincement du pavé tactile |
| Page précédente / suivante en lecture | Page précédente / Page suivante du clavier |
| Vue Pages : sélectionner / déplacer une page | Flèches gauche/droite / Ctrl+flèches gauche/droite |
| Vue Pages : lire la page sélectionnée | Entrée |

Les contrôles portent des noms accessibles et restent utilisables au clavier.
Le réglage Windows de réduction des animations est lu au démarrage.

## Sauvegarde

Les modifications se font sur un clone transactionnel du graphe PDF. Un échec
laisse la version précédente intacte. Enregistrer écrit et synchronise d’abord
un fichier temporaire dans le dossier cible puis remplace atomiquement le fichier.
Une modification externe du fichier source est détectée. Un PDF signé nécessite
une confirmation avant édition ; ses signatures peuvent être invalidées.
La fermeture d’un document modifié demande quoi faire des changements non enregistrés.
L’ouverture d’un autre fichier crée un onglet. L’historique conserve jusqu’à 100
opérations par document pendant la session.

## Compiler

Prérequis : Rust stable >= 1.95, Windows SDK, Visual Studio Build Tools C++ x64
et Python 3 pour regrouper les mentions légales pendant la construction.
Inno Setup 6 ou 7 est requis uniquement pour créer l’installateur.
Une chaîne locale peut aussi être placée dans `.tools/cargo` / `.tools/rustup`.

```powershell
./build.ps1
# ZIP portable de la version déjà construite
./scripts/package-portable.ps1
# Installateur Windows de la même version
./scripts/package-setup.ps1
# Contrôles de développement
cargo test --locked -j 2
cargo clippy --locked --all-targets -j 2 -- -D warnings
cargo fmt --check
# Document d’essai original
cargo run --example atelier
```

La première compilation requiert Internet pour récupérer les dépendances Rust.
Dans les sources, le programme construit se trouve dans `runtime/pdfinator.exe`.
L’exécutable final fonctionne hors ligne. `build.ps1` produit un dossier `runtime`
avec l’exécutable et un fichier `LICENCES.txt`. Les avis de copyright obligatoires
sont conservés et les textes identiques regroupés ; les rapports et inventaires
restent dans les sources. Le moteur et les correctifs fournisseur utiles
sont conservés dans `vendor` ; les applications et catalogues du fournisseur
ne sont pas compilés dans PDFinator.

L’icône de fenêtre et celle de l’exécutable proviennent de la même création SVG.
Le Windows SDK fournit `rc.exe`, utilisé pour intégrer l’ICO et les informations
de version. Pour régénérer les formats PNG/ICO depuis le SVG :

```powershell
$env:PDFINATOR_GENERATE_ICONS = '1'
cargo run --locked --example app_icon
Remove-Item Env:PDFINATOR_GENERATE_ICONS
```

## Validation et limites

Voir **docs/VALIDATION.md** pour les commandes réellement exécutées, les résultats
et les vérifications qui restent à faire. Les PDF synthétiques sont générés dans
`test-output` par les tests ; ils sont distincts des documents personnels.

Les PDF ne contiennent pas toujours des paragraphes éditables : textes vectorisés,
scans, certains sous-ensembles de police et transformations complexes peuvent
limiter l’édition. Une couche OCR invisible n’est jamais recouverte silencieusement.
La mise en forme riche refuse certains scripts et les blocs dont les caractères
sont tournés dans le flux PDF. Les collections TTC et les polices variables ne
sont pas proposées par le sélecteur actuel. Le rendu des scripts complexes et
les aperçus de texte tourné nécessitent davantage de couverture.
L’accessibilité avec Narrateur et les DPI mixtes restent à valider
sur les configurations concernées. L’impression physique doit être vérifiée avec
les pilotes et imprimantes de l’utilisateur.

Le pont `main.py` permet à un futur adaptateur d’Orb de lancer le programme natif.
Cette version ne reprend pas le protocole de l’ancienne Orb Python ; le lancement
direct reste indépendant de la suite.

L’OCR utilise les langues de reconnaissance déjà installées dans Windows, avec
priorité au français, sans téléchargement de modèle ni exécution de Python.
Les images floues et les petites légendes de schémas peuvent produire des erreurs
ou des omissions : la relecture reste nécessaire. La conversion OCR reconstruit
le fond dans les seules zones de mots reconnus. Les intersections avec un dessin,
les textures et la transparence d’une image peuvent être altérées. Une correction
plus longue peut nécessiter d’élargir son bloc pour ne pas recouvrir un voisin.
Une image portant déjà une couche de texte et les groupes vectoriels sont refusés
pour éviter un doublon. La conversion conserve les caractères français et refuse
explicitement les caractères qu’elle ne peut pas écrire.
Le backend Windows a été exécuté avec succès sur cette machine. Microsoft ne
garantit cette API pour les applications de bureau que lorsqu’elles possèdent une
identité de package ; son fonctionnement dans ce binaire portable reste à vérifier
sur les autres configurations ([documentation Microsoft](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr?view=winrt-26100)).
Si la reconnaissance n’est pas disponible, l’image et le document restent inchangés.

Dans **Modifier le texte**, sélectionner une image propose aussi **Textes des
images de la page**. Relisez et validez chaque image ; **Image suivante** permet
de la passer. Les conversions validées créent des blocs indépendants : **Ctrl+F**
retrouve ensuite leurs mots, y compris dans plusieurs images de la même page.
Les images non validées restent intactes. Les lettres isolées des schémas bénéficient
d’une seconde reconnaissance locale ; leur relecture reste nécessaire.

La sélection par rectangle travaille sur les objets d’une seule page. Un groupe
Form existant ou une image reste un élément ; les pixels d’un dessin ne deviennent
pas automatiquement des traits vectoriels. Les textes utilisés comme masques et
certaines structures complexes restent limités. Le panneau Dessin modifie les
segments droits reconnus ; les courbes d’origine peuvent être sélectionnées et
déplacées comme objets. La sélection spécifique **Sélectionner le tableau** garde
ses limites pour les textes remis en forme ; la sélection par rectangle inclut
aussi ces blocs de texte.

Les mentions obligatoires des composants réutilisés sont dans **licenses/**.
