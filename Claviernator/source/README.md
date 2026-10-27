# Claviernator 1.3.10

Claviernator est le nouveau nom de Fortinatus. Les réglages et les anciens lanceurs restent compatibles. Le dossier historique de réglages et le verrou d’instance unique sont conservés pour éviter toute perte ou double lancement.

Adapter le clavier et la souris sous Windows, depuis une seule fenêtre.

Ouvrir **Claviernator.exe**, en conservant son dossier `_internal` à côté. Un deuxième lancement ramène la fenêtre déjà ouverte.

Les adaptations sont actives à chaque lancement. Les touches, actions et options enregistrées sont conservées. L’interrupteur **Actif**, en haut, permet de mettre les adaptations en pause sans les effacer.

- **Ajouter une touche** : choisir une touche, puis son action. Par exemple : clic gauche maintenu, double-clic, Ctrl + C ou un texte.
- **Ctrl + V** : le collage reste prioritaire lorsque Ctrl gauche ou droit sert au clic souris. Le clic est relâché et Ctrl agit comme modificateur jusqu’à son relâchement ; les adaptations du clavier sont conservées.
- **Clic gauche** et **Clic droit** : comme une vraie souris, le bouton reste enfoncé tant que la touche est appuyée, pour cliquer ou glisser.
- **Clic gauche maintenu** : garder la touche appuyée pour glisser, puis la relâcher pour déposer.
- **Clic droit maintenu** : même fonctionnement avec le bouton droit.
- **Poubelle**, à droite d’une ligne : supprimer cette ligne. Les autres touches et profils sont conservés. Une sauvegarde est créée avant la suppression.
- **Suite de touches** : enchaîner plusieurs touches ou raccourcis avec un seul appui. Ajouter les étapes dans l’ordre, puis enregistrer. Par exemple : Ctrl + A → Tabulation → Entrée. F12 interrompt la suite.
- **Inverser chiffres et caractères** : taper directement les chiffres de la rangée supérieure. Utiliser Maj pour les symboles AZERTY.
- **Flèches de défilement** : cliquer dans la zone à faire défiler, puis rester sur l’une des flèches en croissant autour de l’orbe. Leur zone de survol mesure 54 × 28 pixels logiques pour faciliter le maintien du pointeur. Le défilement suit la dernière zone cliquée ; survoler une autre zone ne change pas la cible. Quitter la flèche arrête le défilement. Décocher l’option sur l’accueil pour masquer les flèches ; ce choix est mémorisé. La pause arrête aussi le défilement.
- **Clavier virtuel** : afficher ou masquer l’orbe turquoise, au-dessus de celle de Transcrinator.
- **Options → Au démarrage → Démarrer avec Windows** : lancer Claviernator à l’ouverture de la session.
- **Actif / En pause** : désactiver l’interrupteur pour retrouver le clavier d’origine ; le réactiver pour reprendre les adaptations.
- **Tout réinitialiser** : retrouver tous les réglages d’origine, après confirmation.

Le bouton **Mettre en pause · F12** arrête immédiatement les adaptations et libère les touches et clics maintenus. **F12** fait la même chose depuis le clavier physique. Le bouton affiche **En pause** une fois les adaptations arrêtées.

**Options** regroupe les aides de frappe, la vitesse de la souris et les sauvegardes. **Sauvegarder mes réglages** crée un fichier ; **Charger une sauvegarde** ajoute les claviers sauvegardés et sélectionne celui qui était utilisé, en conservant les claviers déjà présents.

**Claviers enregistrés** permet de garder plusieurs réglages, de les copier ou de changer leur nom. **Dépannage → Relancer les commandes souris** redémarre le service sans changer les affectations. Les remises à zéro sont regroupées dans cette fenêtre.

La fenêtre principale mesure **680 × 550 pixels**, comme Transcrinator, et peut être réduite à 600 × 480. Les fenêtres de réglage ont le même en-tête turquoise ; Échap les ferme.

## Clavier virtuel

**Clic droit sur l’orbe** : retrouver le même menu que près de l’horloge, avec Ouvrir Claviernator, Mettre en pause / Activer et Quitter Claviernator.

**Effacer**, en bas du clavier, supprime le caractère avant le curseur dans le champ choisi. Le bouton reste disponible sur toutes les pages et fonctionne même sans texte préparé. Il conserve le texte préparé dans le clavier. **Vider**, en haut, efface ce texte préparé.

**Un champ est caché derrière le clavier ?** Cliquer sur **Choisir où écrire** : le clavier disparaît. Cliquer dans le champ souhaité, ou faire glisser pour sélectionner du texte. Après le relâchement de la souris, le clavier revient automatiquement avec le texte préparé intact. Cliquer ensuite sur **Insérer**. L’orbe permet aussi de revenir au clavier sans choisir un nouveau champ.

1. Cliquer dans votre document et placer le curseur, ou sélectionner le texte à remplacer.
2. Cliquer sur l’orbe turquoise en bas à droite.
3. Préparer le texte avec les touches, les accents, les signes ou les emojis.
4. Cliquer **Insérer** : le texte est collé dans le dernier champ sélectionné.

Le clavier et l’orbe ne prennent pas le focus du document. Vous pouvez sélectionner un autre champ ou une autre application après l’ouverture du clavier, même avec un texte déjà préparé : **Insérer** suit ce nouveau choix, sans rouvrir le clavier. Le texte remplace la sélection du champ choisi. Le presse-papiers est restauré après le collage ; une nouvelle copie effectuée entre-temps est conservée. Si la cible est fermée ou si Windows refuse l’insertion, le brouillon reste dans le clavier.

- **Clavier** : lettres AZERTY, chiffres directs, Maj, Verr. Maj et AltGr. Entrée et Tab ajoutent un saut de ligne ou une tabulation au texte préparé.
- **Caractères** : accents, symboles et emojis en un clic ; **Unicode** permet d’ajouter un caractère par son code, par exemple 20AC pour € ou 1F600 pour 😀.
- **Touches** : navigation, fonctions F1 à F24, pavé numérique, volume et lecture. Ces touches agissent directement dans le document.
- **Ctrl, Alt ou Win puis une touche** : exécuter le raccourci directement dans le document. Les modificateurs se relâchent après la combinaison.
- **F12** garde son rôle de pause des adaptations, y compris sur le clavier virtuel.

Faites glisser la barre **⠿ Clavier** pour déplacer le clavier, y compris sur un autre écran. Les onglets sont à gauche et les actions à droite pour réduire la hauteur. Son format est limité à **900 × 320 pixels logiques** et se réajuste au moniteur pour conserver des rangées rapprochées. Son fond légèrement transparent laisse voir le document, tandis que les touches restent opaques et lisibles. Le document garde le focus et sa sélection. La position choisie sur chaque écran est retrouvée à la réouverture pendant la session.

Le bouton × masque le clavier en conservant le texte préparé. L’option **Clavier virtuel** est mémorisée. L’orbe mesure **36 × 36 pixels**, comme celle de Transcrinator, et suit le pointeur d’un écran à l’autre, y compris lorsque les écrans ont des échelles différentes. Son cœur s’anime en turquoise, sans anneaux autour. Elle se place au-dessus de l’orbe de Transcrinator lorsqu’elle est détectée sur cet écran. Le démarrage Windows est réglé séparément dans **Options → Au démarrage**.

La croix masque la fenêtre près de l’horloge. Le menu de l’icône permet de la rouvrir ou de quitter Claviernator.

Le logo clavier, l’icône d’ajout, les images d’animation de l’orbe et les fonds turquoise sont inclus dans l’application. Les touches sont dessinées d’un seul tenant pour éviter les traits de raccord. Les images et leurs prompts sont documentés dans `assets/ICONES.md`, `assets/keyboard/README.md` et `assets/backgrounds/README.md`.

Les réglages sont enregistrés automatiquement dans `%APPDATA%/Fortinatus/settings.json`. Les remises à zéro et le chargement d’une sauvegarde créent une copie dans le sous-dossier `sauvegardes`. **Options → Charger une sauvegarde** permet de récupérer les touches enregistrées. L’ouverture masquée et le démarrage Windows conservent leurs réglages actuels.

Pour conserver le fonctionnement habituel d’une touche malgré l’inversion des chiffres et caractères ou les aides de frappe, choisir l’action **Fonction normale** dans sa fenêtre de modification.

## Développement

Python 3.11 ou plus récent et PySide6-Essentials. Installer avec `python -m pip install -e ".[dev]"`, puis lancer `python run_claviernator.py`.

```powershell
python -m pytest -q
python scripts/ui_snapshot.py
python scripts/keyboard_snapshot.py
python scripts/virtual_keyboard_regression.py --hooks
python scripts/windows_integration.py
python -m PyInstaller --noconfirm Claviernator.spec
python scripts/frozen_keyboard_regression.py
python scripts/hover_scroll_regression.py
python scripts/ui_release_regression.py
python scripts/click_regression.py --frozen dist/Claviernator-1.3.10/Claviernator.exe
python scripts/single_instance_regression.py --frozen dist/Claviernator-1.3.10/Claviernator.exe
python scripts/package_release.py
```

Les essais natifs utilisent leurs propres réglages et leurs propres fenêtres. `--no-hooks` ouvre l’interface sans intercepter le clavier ; `--config-dir CHEMIN` isole les réglages ; `--smoke-test` vérifie le lancement puis se ferme, avec les adaptations en pause.

Les écrans sécurisés Windows, Ctrl + Alt + Suppr et certaines touches Fn ne sont pas remappables. Les applications administrateur peuvent bloquer les entrées venant d’un programme sans les mêmes droits. Les tests et leurs limites sont décrits dans `docs/VALIDATION.md` ; les licences sont dans `docs/licenses`.
