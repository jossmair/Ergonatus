# Ressources Écrinator

- `icons/*.svg` : pictogrammes originaux de PDFinator/Ergonatus, réutilisés dans la même suite ; MIT ou Apache-2.0 du projet.
- `ecrinator.svg` : dessin vectoriel original Écrinator, même licence que ce projet.
- `ecrinator.png`, `ecrinator.ico` : rendus du dessin vectoriel original `ecrinator.svg`, livre blanc sur orb bleu, générés par `scripts/generate_app_icon.py`.
- `school-header.png` : ancienne illustration commune de la version 0.3, conservée comme ressource historique ; remplacée dans l'application 0.4 par les illustrations distinctes de `subjects/`. Générée avec le service intégré ImageGen le 22 octobre 2026. Prompt : « illustration scolaire commune : cahier ouvert, crayon bleu, règle translucide et étoile, aquarelle discrète, contours bleu sombre, sans texte, fond transparent, lisible dans un en-tête de 35 mm ». Aucune génération à l'exécution.
- Ressources Wordcraft : voir `vendor/wordcraft/ATTRIBUTION.md` et les notices amont.
- Extension locale Wordcraft pour les cartes arrondies : `vendor/wordcraft/ECRINATOR-PATCHES.md`, 23 octobre 2026. Le texte et les tableaux restent natifs. Les pictogrammes des encadrés sont des rendus PNG des SVG originaux de `school-icons`, préparés par `build.rs`, sans nouveau service de génération.
- `school-icons/*.svg` : 91 pictogrammes vectoriels originaux, générés par `scripts/generate_icons.py`, dont les nouvelles commandes de gomme, bandeau, panneau et feuille blanche. Les lettres et symboles utilisent des contours de Noto Serif (SIL OFL, notice `fonts/NotoSerif-OFL.txt`) ; aucun chargement de police n'est nécessaire pour afficher ces icônes. La planche `icon-catalog.svg` sert au contrôle de toute la famille.
- `subjects/*.png` : 13 illustrations distinctes générées avec l'outil intégré ImageGen le 23 octobre 2026, une par matière. Les objets, palettes et consignes complètes sont conservés dans `subjects/PROMPTS.json`. Originaux transparents conservés ; le script Rust de construction produit des ressources 512 × 256 proportionnées pour alléger les documents. Aucune génération ni connexion réseau dans l'application.
- Borel : © 2023 The Borel Project Authors, SIL OFL 1.1 (`fonts/Borel-OFL.txt`).
- OpenDyslexic : version officielle Forgejo, commit `48218028cc8bd9f4f244cd4ce4049e6c879d4d1a`, © Abbie Gonzalez, SIL OFL 1.1 (`fonts/OpenDyslexic-OFL.txt`). L'ancien fichier GitHub sous licence différente a été remplacé avant distribution.
- Sources des composants modifiés ou embarqués : Wordcraft `v0.9.0` dans ce dépôt ; craft-libs `c3487320b2d1de657b860b3c8abb44e1f2b32bd8` et `d27646a5f7c8b4fc85d9dd3213b8c88b58e0088d` (https://github.com/storytold/craft-libs), notamment `vendor/krilla`. Les avis tiers, dont les fichiers couverts par MPL 2.0, sont conservés dans `LICENCES.txt`.

- `workspace-banner-v1.png` : fond panoramique original généré par le service intégré ImageGen le 23 octobre 2026. Consigne complète dans `workspace-banner-v1.PROMPT.json`. Préparé à la construction en 1024 × 341 ; incorporé dans le logiciel et dans les bandeaux natifs, en transparence sur la couleur de chaque matière. Aucune génération à l’exécution.

- `workspace-banner-v2.png` : variante réellement transparente du fond v1, retouchée avec le service intégré ImageGen le 23 octobre 2026 à la demande de l’utilisateur. Original et alpha préservés ; consigne complète et référence dans `workspace-banner-v2.PROMPT.json`. Les zones vides laissent voir la feuille derrière l’illustration et autour du panneau coloré arrondi.


### Retouche nacrée du 23 octobre 2026

Nouveau décor IA transparent neutre, source et consigne dans assets/workspace-banner-v3.*. Utilisé dans le bandeau du cours et la barre supérieure. Fonds des matières éclaircis (10 % de couleur), contours plus fins et encadrés moins délimités. Les 13 illustrations et les contrôles natifs restent présents. Sources et consignes incluses dans le paquet graphique 0.6.0.


## Fonds panoramiques de matière — 24 octobre 2026

13 créations ImageGen distinctes, générées pour Écrinator. Sources PNG non modifiées dans subject-backgrounds/, consignes exactes et chemin de génération dans subject-backgrounds/PROMPTS.json. Distribution avec les ressources du projet. Le logiciel embarque des JPEG proportionnels optimisés ; le recadrage d’affichage est non destructif. Les anciens pictogrammes/illustrations restent conservés.

- subject-backgrounds/french.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/mathematics.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/history.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/emc.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/english.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/spanish.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/german.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/biology.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/physics.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/technology.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/art.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/music.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.
- subject-backgrounds/other.png : création IA ImageGen pour Écrinator, 24/10/2026 ; source et consigne dans PROMPTS.json.


## Bibliothèque scolaire — 0.9.0

1 203 images : 26 ressources Wikimedia Commons, 1 000 figures OpenStax de versions historiques CC BY 4.0 et 177 cartes de situation réalisées depuis les géométries Natural Earth du domaine public. Les figures avec un crédit tiers explicite ont été écartées ; les licences plus restrictives des éditions OpenStax actuelles ne sont pas appliquées aux copies historiques ici utilisées. Auteurs, licences, liens, commits, dates, adaptations et empreintes par image sont dans library/ATTRIBUTION.md et library/catalog.json. Les preuves et sources conservées sont dans library/licenses/, library/sources/ et les fichiers library/*.source.json. Ces ressources tierces gardent leurs licences propres ; elles ne relèvent pas de la licence des images originales Ergonatus.
