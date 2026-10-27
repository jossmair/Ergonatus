# Précisionator 1.0.7

Loupe intelligente Windows de la famille Transcrinator / Fortinatus.
Fond sombre aux nuances violettes et commandes améthyste, fonctionnement local, sans compte ni télémétrie.

## Lancer

Décompresser entièrement `Precisionator-1.0.7-Windows-x64.zip`, puis lancer
`Precisionator-1.0.7/Precisionator.exe`. Conserver le dossier `_internal` à côté
de l’exécutable : Python, Qt, NumPy, DXcam et leurs dépendances y sont inclus.
Aucune installation de Python ni connexion Internet n’est nécessaire pour utiliser
la distribution. Aucun droit administrateur n’est demandé.

Le nom affiché est **Précisionator** ; les noms de fichiers et les clés Windows
utilisent `Precisionator` pour éviter les problèmes d’encodage des outils.

Au démarrage, seul l’orbe violet apparaît. **Un clic sur l’orbe active ou
désactive la loupe**, sans ouvrir de fenêtre. Un clic droit donne accès à
**Ouvrir Précisionator** pour les réglages ; un clic sur l’icône près de
l’horloge ouvre également cette fenêtre. Fermer ou réduire les paramètres
les masque vers l’orbe. Glisser l’orbe le déplace sans changer l’activation.
Le menu propose aussi Activer/Désactiver et Quitter.
**Désactiver ne quitte pas l’application** : l’orbe reste disponible et continue
de suivre l’écran du pointeur. Cliquer de nouveau réactive la loupe.
Seule la commande **Quitter** ferme Précisionator.

L’orbe ne contient aucun dessin de loupe. Il reprend le rendu clair de la version
1.0.3, avec une très légère baisse de luminosité (6 %), sans cœur opaque ajouté.
**Activé**, son animation reste douce ; **désactivé**, il est atténué et son
animation devient presque imperceptible. Sa taille et sa position restent stables.

## Utiliser la loupe

Déplacer normalement le pointeur. Une approche lente et volontaire fait apparaître
la loupe ronde, avec un grossissement de ×1,8, ×2,5 ou ×3. Un déplacement rapide
la masque. La loupe reste un moment à l’arrêt pour laisser le temps de viser
et de cliquer. Les très petits tremblements ne suffisent pas à déclencher l’effet.

La fenêtre compacte contient cinq curseurs, avec de grandes poignées rondes
et des mots courants. Les quatre commandes de loupe ont trois positions ;
la vitesse de la souris se règle progressivement de très lente à très rapide.
Cliquer directement sur une barre ou faire glisser son bouton suffit ; le choix s’affiche à droite. Les réglages s’appliquent
immédiatement et sont sauvegardés automatiquement :

| Réglage | Choix |
|---|---|
| Grossissement | ×1,8 · ×2,5 · ×3 |
| Taille de la loupe | Petite · Moyenne · Grande |
| La loupe apparaît | Plus tôt · Normalement · Plus tard |
| Temps pour viser | Court · Confortable · Long |
| Vitesse de la souris | Très lente → Lente → Normale → Rapide → Très rapide |

Par défaut : **Moyenne**, **Plus tôt**, **Confortable**. Si le zoom arrive trop
tard, choisir **Plus tôt**. S’il part trop vite, choisir **Long** : cela laisse
plus de temps à l’arrêt et permet de continuer à viser en bougeant.
Aucune valeur technique en pixels ou millisecondes à saisir. Le grossissement
×1,8 / ×2,5 / ×3 reste indépendant de la taille de la loupe.

**Vitesse de la souris** règle la vitesse du pointeur dans Windows, dans toutes
les applications. Déplacer le curseur vers la gauche ralentit, vers la droite
accélère. La vitesse choisie s’applique au relâchement et Windows la mémorise.
La vitesse actuelle est lue à l’ouverture des paramètres : démarrer, activer,
désactiver ou quitter Précisionator ne la remplace pas. Le réglage reste utilisable
quand la loupe est désactivée. Il ne change ni l’accélération Windows ni les
réglages de clic. Certains dispositifs à positionnement absolu ou à vitesse
propre ne suivent pas ce réglage Windows ; le confort reste à vérifier avec
le dispositif réel.

Le clic reste à la **position réelle du pointeur**, au centre optique de la loupe.
Les éléments agrandis en périphérie ne deviennent pas de nouvelles zones cliquables :
amener leur point réel sous le centre avant de cliquer. La loupe aide à voir ;
elle n’agrandit pas les cibles de clic. Le réglage de vitesse est indépendant
du zoom et ne s’applique que sur votre demande.

Précisionator ne surveille aucune touche, n’installe aucun hook clavier/souris,
n’émet aucun clic et ne déplace jamais le pointeur. Le curseur Windows natif reste
affiché. L’image DXGI ne dessine pas de second curseur. Une application qui dessine
elle-même un curseur dans son contenu peut toutefois rendre ce dessin visible.

## Orbes et écrans

L’application recherche les orbes de Fortinatus, désormais nommé **Claviernator**,
et de Transcrinator, même lorsque leurs fenêtres principales sont masquées.
L’ordre de la pile est **Précisionator, Claviernator, Transcrinator**, du haut
vers le bas. La pile est prioritaire sur les anciennes positions mémorisées.
Précisionator reprend l’espacement réel des compagnons, ou 10 px par défaut.
Sans compagnon, il réserve la troisième place en hauteur près du bord de l’écran.

Les coordonnées des orbes sont converties par écran entre pixels physiques et
logiques. La loupe conserve la taille choisie (Petite, Moyenne ou Grande), y compris
à 150 % ou 200 %. La capture recolle les portions d’écrans voisins ; les zones
hors du bureau restent transparentes. Les coordonnées négatives sont acceptées.
Une modification de résolution ou la disparition d’un écran replace l’orbe dans
une zone accessible.

**L’orbe suit l’écran du pointeur**, y compris lorsque la loupe est désactivée.
Le suivi reprend la cadence de l’orbe réduit de Transcrinator : vérification
toutes les 40 ms, sans délai de stabilisation supplémentaire. Les deux applications
ont des minuteries indépendantes ; leurs déplacements ne sont pas synchronisés
à la même image. L’orbe ne suit pas chaque déplacement à l’intérieur d’un écran.
Le suivi est suspendu pendant son glissement,
pendant l’ouverture de son menu et pendant le verrouillage de session.

Le placement des compagnons est également revérifié toutes les 120 ms sur
l’écran courant : lancement plus tardif, déplacement et changement de forme
ne laissent plus Précisionator dans la mauvaise place. Le glissement manuel
reste possible ; en présence des compagnons, l’orbe reprend le haut de la pile
au relâchement. Sans compagnon, une position personnelle reste mémorisée par écran.
Si un compagnon est déjà au bord supérieur, une colonne voisine est utilisée pour
éviter tout recouvrement. Les fenêtres des deux autres programmes ne sont pas déplacées.

Les flèches de défilement de Claviernator sont aussi prises en compte comme
zones occupées. Précisionator laisse un espace libre au-dessus de la flèche haute,
y compris lorsque Transcrinator est fermé. Masquer les flèches libère cet espace.

## Protection contre la récursion et erreurs

Windows 10 version 2004 (build 19041) ou ultérieure, ou Windows 11, x64, avec
composition DWM et sortie compatible Desktop Duplication sont requis pour la loupe.

La surface de loupe utilise `WDA_EXCLUDEFROMCAPTURE` avec lecture de contrôle.
Avant sa première image, le thread de capture vérifie aussi l’exclusion **effective
dans DXGI** à partir de l’orbe déjà affiché : seule son affinité de capture change,
sans le masquer et sans ajouter de fenêtre de test. Une initialisation bornée
laisse au compositeur le temps de fournir sa première image valide. Une référence
masquée ou ambiguë fait suspendre l’effet et déclenche une nouvelle tentative.
Le contrôle compare la composition réelle des pixels avec leur transparence et
confirme le retour de l’image après restauration de l’affinité. Il ne repose
plus sur une proportion de violet, qui échouait sur des fonds clairs.

Si la protection, la capture, le pilote ou la session deviennent indisponibles,
la loupe est masquée et les clics continuent normalement. L’orbe et les paramètres
restent disponibles et le choix **Activé** est conservé. La reprise est automatique,
avec des tentatives espacées de 0,25 à 4 secondes pour ne pas surcharger Windows.
Les ressources de capture sont recréées ; aucune intervention n’est nécessaire
après une erreur transitoire. Une désactivation volontaire annule les tentatives.
Aucune solution par masquage/réapparition permanent n’est employée.

Les notifications de veille, verrouillage et déconnexion suspendent la capture.
La reprise réinitialise l’analyse et les écrans. Une perte du périphérique DXGI
interrompt l’effet au lieu d’utiliser la boucle de récupération non bornée de DXcam.
Le démarrage Windows est une valeur HKCU Run propre à Précisionator, indépendante
des entrées des deux autres applications. Ne pas déplacer la distribution après
avoir activé le démarrage automatique, ou désactiver puis réactiver cette option.

## Données locales

`%APPDATA%/Precisionator/settings.json` contient les préférences, les seuils, le diamètre
et les positions de l’orbe par écran. Écriture atomique ; récupération des valeurs par défaut si le fichier
est invalide. Le démarrage effectif est lu dans Windows.

`precisionator.log`, dans ce même dossier, contient des erreurs et des compteurs
locaux de rendu, avec rotation (256 Ko × 3 maximum). Aucune image d’écran, frappe
ou trajectoire du pointeur n’est enregistrée par l’application. Aucun envoi réseau.
Les captures de validation fournies dans les sources proviennent des scripts de test.

## Développer et compiler

Python **3.12 x64** et Windows. Depuis ce dossier :

```bat
build.bat
```

Le script prépare `.venv`, installe les versions de `requirements-dev.txt`,
génère l’icône avec Qt, exécute les tests, compile avec PyInstaller et regroupe
la distribution portable, les licences et son empreinte SHA-256.
L’installation des dépendances de développement nécessite Internet. La compilation
n’altère ni Fortinatus ni Transcrinator. Aucun navigateur ni service cloud n’est inclus.

Exécuter depuis les sources :

```bat
.venv\Scripts\pythonw.exe main.py
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\ui_snapshot.py
.venv\Scripts\python.exe scripts\windows_validation.py --monitor-index 0 --seconds 8
.venv\Scripts\python.exe scripts\application_regression.py
.venv\Scripts\python.exe scripts\monitor_regression.py
.venv\Scripts\python.exe scripts\twin_orbs_regression.py
.venv\Scripts\python.exe scripts\recovery_and_stack_regression.py
.venv\Scripts\python.exe scripts\arrow_spacing_regression.py
.venv\Scripts\python.exe scripts\orb_click_regression.py
.venv\Scripts\python.exe scripts\mouse_speed_regression.py
```

Les scripts Windows ouvrent uniquement les surfaces de validation du projet.
`application_regression.py` injecte une trace dans l’analyseur ; il ne génère
aucune entrée système. `windows_validation.py --interactive` fournit une cible
sans action pour essayer volontairement le clic Ctrl gauche via Fortinatus.
Les rapports JSON sont écrits dans `docs/validation`.
`orb_click_regression.py` nécessite de fermer l’application avant son essai.
Il envoie des événements Qt uniquement à son propre orbe, sans entrée système.
`mouse_speed_regression.py` relit et réapplique la vitesse actuelle sans la changer.
L’essai comparatif des orbes nécessite les sources `Transcri/` à côté du projet ;
il utilise leur fenêtre d’orbe sans modifier le programme ni ses préférences.

Pour les développeurs : les choix simples correspondent à des paramètres internes
testés. Petite/Moyenne/Grande donnent des diamètres physiques de 180/300/440 px.
Court/Confortable/Long maintiennent l’effet à l’arrêt environ 0,8/2/4 secondes.
Le filtre garde un lissage, une hystérésis et la protection contre les tremblements.

L’analyse du mouvement est indépendante de Qt. La capture appartient à un thread
avec attente conditionnelle et une boîte d’une image, sans accumulation de signaux.
La copie CPU est limitée à la région utile, bien que DXGI doive transférer la texture
de sortie sur le GPU. Fréquence visée 60 FPS, adaptation à 40/30 selon le coût mesuré.
Pas de capture périodique lorsque l’effet est masqué ; ressources libérées après
environ deux secondes d’inactivité. Lecture du pointeur ramenée à 20 Hz au repos.
La surface native réutilise son DIB au diamètre choisi, peint avec Qt et un masque radial
de 25 px. Ce choix évite les arrondis de coordonnées Qt aux frontières de DPI.

## État de validation

Consulter `VALIDATION.md` dans la distribution (`docs/VALIDATION.md` dans les sources)
pour les essais réellement exécutés et les limites.
L’exécutable est portable et non signé. Les essais Windows 10, le clic physique
avec Fortinatus, les changements matériels d’écran et l’endurance restent à réaliser
avant de considérer cette version comme validée pour un usage quotidien d’accessibilité.

Documentation technique de référence :
[SetWindowDisplayAffinity, Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity),
[DXcam, sources officielles](https://github.com/ra1nty/DXcam),
[SystemParametersInfoW : vitesse Windows, Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-systemparametersinfow).
