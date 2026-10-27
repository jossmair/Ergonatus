# Temporator — cadran minimaliste

Clic sur l’Orb : afficher ou masquer le cadran flottant, sans arrêter le décompte. Double-clic sur l’Orb ou le cadran : ouvrir les réglages. Clic droit sur le cadran : réglages ou masquage.

Le réglage Sans chiffres affiche un disque coloré qui diminue avec le temps et une aiguille qui atteint le bord du disque et indique la limite du temps restant. Le cadran avec chiffres reste disponible en décochant ce réglage. Ce choix est aussi accessible au clic droit, sans redémarrer le minuteur.

## Régler à la souris

1. Cliquer sur Minutes ou Secondes, puis sur les chiffres du pavé. Deux chiffres par champ ; secondes de 00 à 59. Effacer remet la saisie à zéro ; retour arrière enlève un chiffre du champ sélectionné.
2. Ou choisir directement 1, 5, 10 ou 25 minutes.
3. Cliquer sur Démarrer le minuteur : les réglages se masquent et le widget s’affiche.

Durée de 00:01 à 99:59. Le cadran mesure 200 pixels logiques de diamètre par défaut, réglable avec le curseur Taille de 160 à 280. Les deux commandes sont alignées dessous ; le widget reste au-dessus des autres fenêtres. L’extérieur du cercle est transparent et laisse passer les clics ; le cercle reste opaque et lisible. Glisser le cercle pour le déplacer. Le pointeur reste une flèche normale, sans infobulle de déplacement. Deux icônes seulement, sous le cercle : Démarrer/Pause/Reprendre à gauche, Reset à droite. Le clic droit permet de masquer sans arrêter le décompte ; l’Orb le retrouve. À la fin : le contour clignote lentement, avec un signal sonore système. Aucune notification Windows. Le clignotement continue jusqu’à Reset ou un nouveau démarrage. Le volume suit les réglages Windows.

L’option Alterner travail/pause conserve les séquences de l’ancienne version. Cliquer sur Travail ou Pause pour choisir la durée à régler avec le même pavé. Le cycle continue tant que Temporator fonctionne ; aucune nouvelle période n’est imposée dans le mode minuteur simple. Les réglages préparés pendant un minuteur en cours ne le remettent pas à zéro. Cliquer sur Démarrer lance explicitement la nouvelle durée.

Choix sans chiffres, taille du widget, dernières durées valides, alternance et positions sont sauvegardés localement. Un minuteur actif n’est pas repris automatiquement après fermeture complète du logiciel. Quitter dans le menu de l’Orb arrête Temporator. Aucun compte, Internet, IA ou téléchargement.

## Technique et validation

Moteur de décompte monotone dans shared/countdown.py, sans dérive liée au rafraîchissement. Un retard de boucle ou une veille rattrape les cycles sans multiplier les alertes sonores. Le cadran, la portion de temps restant et l’aiguille sont dessinés dans Qt. L’icône Reset générée est fournie dans assets/icons/temporator-reset.png ; Démarrer/Pause reste vectoriel. Les réglages conservent le fond et la couleur de Temporator.

Sources : `python run_satellite.py --app temporator` depuis la racine Ergonatus. Tests : `python -m pytest tests/test_temporator.py -q`. Exécutable : runtime/Temporator.exe, ou Lancer Temporator.cmd. Test compilé : `runtime/Temporator.exe --smoke-test` avec un dossier de données de test isolé.

Compilation ciblée PowerShell depuis la racine : `$env:ERGONATUS_BUILD_APP='temporator'`, puis `python -m PyInstaller --noconfirm --distpath .package-satellites --workpath .build-satellites scripts/satellites.spec`. Fermer Temporator puis exécuter `python scripts/deploy_satellites.py --app temporator`. Retirer la variable ERGONATUS_BUILD_APP pour compiler de nouveau tous les satellites ; les scripts complets conservent leur fonctionnement par défaut.

Données : %LOCALAPPDATA%/Ergonatus/temporator/. Voir docs/VALIDATION_V2.md pour les résultats et limites des tests.

Le curseur Taille utilise une piste fine et une poignée toujours entièrement visible. Le focus clavier reste visible par un accent corail discret, sans grands cadres bleus. La largeur des réglages est limitée pour conserver une présentation compacte.
