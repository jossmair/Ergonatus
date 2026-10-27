# Memorinator 1.0 — mur de post-it

Le nouveau Memorinator remplace l’interface de révision par un mur de notes personnel, entièrement local.

- Clic sur l’Orb : afficher ou masquer le mur en plein écran sur l’écran du pointeur.
- **+** en haut à gauche : ajouter un post-it et écrire directement.
- Glisser la bande de date / poignée : déplacer le post-it sur le mur.
- Le post-it s’agrandit automatiquement lorsque le texte s’allonge ; le mur devient défilable si nécessaire.
- Sélectionner des mots puis **Surligner** ou **Barrer**. Cliquer à nouveau pour retirer ce format.
- Icône corbeille sur chaque carte : retirer le post-it. Annulation immédiate et restauration via Corbeille, y compris après redémarrage.
- **Fond** : opacité de 25 % à 100 %. Les post-it gardent leur opacité ; ce réglage ne les rend pas transparents.
- Échap ou × : masquer le mur et retrouver les applications derrière.

Couleurs pastel distinctes attribuées à l’ajout, date de création en heure de Paris, ombres discrètes, icône corbeille vectorielle et texte éditable. Les positions, textes, surlignages, passages barrés et couleurs sont conservés dans SQLite. Enregistrement après une courte pause de frappe, immédiat lors de la mise en forme / du déplacement et à la fermeture du mur.

## Clavier et données

Ctrl+N ajoute une note ; Ctrl+Maj+H surligne ; Ctrl+5 barre la sélection. La poignée de déplacement est accessible par Tab puis les flèches déplacent la carte. Aucun clic automatique ni commande IA.

Données dans `%LOCALAPPDATA%/Ergonatus/memorinator/records.sqlite3`, sauf profil ERGONATUS_DATA personnalisé. Si des anciennes fiches question/réponse existent, une archive `archive-revisions-v1.sqlite3` est créée une fois. L’ancienne interface et ses actions sont retirées ; les données ne sont pas supprimées silencieusement. Les anciennes fiches ne deviennent pas automatiquement des post-it.

Le fond est un voile teinté translucide, sans flou système. Il couvre l’écran sur lequel le mur est ouvert ; les autres écrans restent disponibles. La transparence est limitée à 25 % minimum pour garder un fond cliquable et éviter les actions involontaires derrière.

## Lancement et validation

Lancer `runtime/Memorinator.exe` ou `Lancer Memorinator.cmd`. Depuis la racine : `python run_satellite.py --app memorinator`. Avec `--minimized`, seule l’Orb apparaît jusqu’à son utilisation.

Tests : `python -m pytest tests/test_sticky_wall.py -q`. Le test `--smoke-test` dans un profil ERGONATUS_DATA isolé vérifie un ajout, le surlignage et le texte barré, la corbeille et la restauration, le plein écran et le réglage du fond sans rendre les cartes transparentes.

Build : PyInstaller `scripts/satellites.spec`, puis `python scripts/deploy_satellites.py --app memorinator`, application arrêtée. Le thème et le nom de l’Orb restent ceux de Memorinator.

Les commandes de surlignage, texte barré et corbeille sont maintenant des icônes avec infobulles. Leur nom reste disponible aux outils d’accessibilité. Le bandeau conserve un fond sombre lisible, indépendamment du réglage de transparence du mur.
